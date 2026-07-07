import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import RecruitmentTerm, Seminar, SeminarMember, User, UserRole
from api.schemas import AssignmentImportError, AssignmentImportResult

router = APIRouter(prefix="/admin/assignments", tags=["admin"])

require_admin = require_role(UserRole.admin)

_REQUIRED_COLUMNS = ("student_id", "seminar_id", "term_id")


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


@router.post("/import", response_model=AssignmentImportResult)
async def import_assignments(
    file: UploadFile = File(...),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AssignmentImportResult:
    """配属結果CSVを取り込み、所属ゼミ生(seminar_members)に反映する。

    CSV列: student_id(学籍番号), seminar_id, term_id(募集ラウンド=前期/後期)。
    (seminar, student, term) が既にあればスキップ、無ければ作成(べき等)。
    """
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
                    row=row_number, reason="必須列(student_id/seminar_id/term_id)が不足"
                )
            )
            continue

        seminar_uuid = _parse_uuid(values["seminar_id"])
        term_uuid = _parse_uuid(values["term_id"])
        if seminar_uuid is None or term_uuid is None:
            errors.append(
                AssignmentImportError(
                    row=row_number, reason="seminar_id/term_id がUUID形式ではありません"
                )
            )
            continue

        student = (
            await db.execute(
                select(User).where(User.student_id == values["student_id"]).limit(1)
            )
        ).scalar_one_or_none()
        if student is None:
            errors.append(
                AssignmentImportError(
                    row=row_number,
                    reason=f"学生が見つかりません: {values['student_id']}",
                )
            )
            continue

        if await db.get(Seminar, seminar_uuid) is None:
            errors.append(
                AssignmentImportError(
                    row=row_number, reason=f"ゼミが見つかりません: {seminar_uuid}"
                )
            )
            continue
        if await db.get(RecruitmentTerm, term_uuid) is None:
            errors.append(
                AssignmentImportError(
                    row=row_number,
                    reason=f"募集ラウンドが見つかりません: {term_uuid}",
                )
            )
            continue

        already = (
            await db.execute(
                select(SeminarMember).where(
                    SeminarMember.seminar_id == seminar_uuid,
                    SeminarMember.student_id == student.id,
                    SeminarMember.term_id == term_uuid,
                )
            )
        ).scalar_one_or_none()
        if already is not None:
            existing += 1
            continue

        db.add(
            SeminarMember(
                seminar_id=seminar_uuid,
                student_id=student.id,
                term_id=term_uuid,
            )
        )
        created += 1

    await db.flush()
    return AssignmentImportResult(created=created, existing=existing, errors=errors)
