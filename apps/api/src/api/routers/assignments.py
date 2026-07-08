import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import RecruitmentTerm, Seminar, SeminarMember, User, UserRole
from api.schemas import AssignmentImportError, AssignmentImportResult

router = APIRouter(prefix="/admin/assignments", tags=["admin"])

require_admin = require_role(UserRole.admin)

_REQUIRED_COLUMNS = ("student_id", "seminar_id")


class _AmbiguousMatch(Exception):
    """student_id/seminar_idの値に対して複数のレコードが一致し、
    どれを使うべきか一意に決められない場合。student_id(users)にも
    Seminar.nameにもDBのユニーク制約が無いため起こりうる。

    呼び出し側でこの行だけの取り込みエラーとして扱う(例外を伝播させて
    アップロード全体を失敗させると、既に処理済みの他の行の配属まで
    ロールバックされてしまうため)。
    """


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


async def _find_student(db: AsyncSession, *, value: str) -> User | None:
    """student_idの完全一致を優先し、無ければ学籍番号(接頭辞なし)として
    s/g両方の接頭辞を試す(api.import_seminar_membersと同じ運用。実際の
    配属結果CSVは学籍番号の生数字(例: 2522091)で運用されているため)。
    """
    result = await db.execute(select(User).where(User.student_id == value))
    students = result.scalars().all()
    if len(students) > 1:
        raise _AmbiguousMatch(f"学籍番号が重複しています: {value}")
    if len(students) == 1:
        return students[0]

    result = await db.execute(
        select(User).where(User.student_id.in_([f"s{value}", f"g{value}"]))
    )
    students = result.scalars().all()
    if len(students) > 1:
        raise _AmbiguousMatch(f"学籍番号(s/g接頭辞)に複数の学生が該当します: {value}")
    return students[0] if students else None


async def _find_seminar(db: AsyncSession, *, value: str) -> Seminar | None:
    """値がUUID形式ならIDとして、そうでなければゼミ名の完全一致として照合する
    (api.import_seminar_membersと同じ運用)。
    """
    seminar_uuid = _parse_uuid(value)
    if seminar_uuid is not None:
        return await db.get(Seminar, seminar_uuid)

    result = await db.execute(select(Seminar).where(Seminar.name == value))
    seminars = result.scalars().all()
    if len(seminars) > 1:
        raise _AmbiguousMatch(f"ゼミ名が重複しています: {value}")
    return seminars[0] if seminars else None


@router.post("/import", response_model=AssignmentImportResult)
async def import_assignments(
    term_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AssignmentImportResult:
    """配属結果CSVを取り込み、所属ゼミ生(seminar_members)に反映する。

    term_id(募集ラウンド)は1回のアップロード全体で1つ選択し、CSV自体には
    含めない(1回のアップロードは常に単一の募集ラウンドに対する配属結果
    であるため。前期/後期で異なるラウンドに配属する場合は、ラウンドごとに
    アップロードし直す)。

    CSV列: student_id, seminar_id。どちらもID(DBの値)と人が読める文字列
    (学籍番号の生数字/ゼミ名)のどちらでも受け付ける。実際の配属結果CSVは
    学籍番号・ゼミ名で運用されているため(_find_student/_find_seminar参照)。
    (seminar, student, term) が既にあればスキップ、無ければ作成(べき等)。
    """
    if await db.get(RecruitmentTerm, term_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="募集ラウンドが見つかりません。",
        )

    raw = await file.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    existing = 0
    errors: list[AssignmentImportError] = []

    for row_number, row in enumerate(reader, start=1):
        values = {col: (row.get(col) or "").strip() for col in _REQUIRED_COLUMNS}
        if not all(values.values()):
            errors.append(
                AssignmentImportError(
                    row=row_number, reason="必須列(student_id/seminar_id)が不足"
                )
            )
            continue

        try:
            student = await _find_student(db, value=values["student_id"])
        except _AmbiguousMatch as exc:
            errors.append(AssignmentImportError(row=row_number, reason=str(exc)))
            continue
        if student is None:
            errors.append(
                AssignmentImportError(
                    row=row_number,
                    reason=f"学生が見つかりません(学籍番号): {values['student_id']}",
                )
            )
            continue

        try:
            seminar = await _find_seminar(db, value=values["seminar_id"])
        except _AmbiguousMatch as exc:
            errors.append(AssignmentImportError(row=row_number, reason=str(exc)))
            continue
        if seminar is None:
            errors.append(
                AssignmentImportError(
                    row=row_number,
                    reason=f"ゼミが見つかりません(ID/名前): {values['seminar_id']}",
                )
            )
            continue

        already = (
            await db.execute(
                select(SeminarMember).where(
                    SeminarMember.seminar_id == seminar.id,
                    SeminarMember.student_id == student.id,
                    SeminarMember.term_id == term_id,
                )
            )
        ).scalar_one_or_none()
        if already is not None:
            existing += 1
            continue

        db.add(
            SeminarMember(
                seminar_id=seminar.id,
                student_id=student.id,
                term_id=term_id,
            )
        )
        created += 1

    await db.flush()
    return AssignmentImportResult(created=created, existing=existing, errors=errors)
