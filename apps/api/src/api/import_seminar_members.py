"""所属ゼミCSVをDBへ投入するスクリプト。

使い方: uv run python -m api.import_seminar_members <CSVファイルパス> <年度>

CSV列: 学籍番号, 名前, 配属先
- 学籍番号は数字のみ(例: 2522091)。DBのstudent_id(s/g接頭辞付き、例:
  s2522091)と照合するため、s/g両方の接頭辞を試す。
- 名前は照合には使わず、学生が見つからない場合の警告メッセージ表示のみに使う
  (氏名の正本はimport_users.pyが管理する)。
- 配属先はSeminar.nameと完全一致で照合する(import_seminars.pyと同じ運用)。

指定年度の募集期間(recruitment_terms)が無ければ作成する
(api.ensure_recruitment_termと同じget_or_create_recruitment_termを使う)。
学生・ゼミどちらかが見つからない行はエラーで止めずスキップする。
同一学生が当該年度に既に別ゼミへ所属登録されていた場合は、CSVの内容で
上書きする(配属訂正・異動を想定したべき等処理)。
"""

import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session
from api.models import RecruitmentTerm, Seminar, SeminarMember, User
from api.recruitment_terms import get_or_create_recruitment_term


async def _find_student(session: AsyncSession, *, student_number: str) -> User | None:
    result = await session.execute(
        select(User).where(
            User.student_id.in_([f"s{student_number}", f"g{student_number}"])
        )
    )
    return result.scalars().first()


async def _find_seminar(session: AsyncSession, *, name: str) -> Seminar | None:
    result = await session.execute(select(Seminar).where(Seminar.name == name))
    return result.scalar_one_or_none()


async def _upsert_membership(
    session: AsyncSession, *, seminar: Seminar, student: User, term: RecruitmentTerm
) -> str:
    """学生の当該年度の所属を作成/訂正する。"created"/"updated"/"unchanged" を返す。

    同一学生・同一年度に所属行が複数残っている場合(過去の重複データ等)は、
    scalar_one_or_none()がMultipleResultsFoundで落ちてバッチ全体が失敗する
    のを避けるため、それらを削除してCSVの内容で1件に統一する。
    """
    result = await session.execute(
        select(SeminarMember).where(
            SeminarMember.student_id == student.id,
            SeminarMember.term_id == term.id,
        )
    )
    existing_rows = list(result.scalars().all())

    if not existing_rows:
        session.add(
            SeminarMember(seminar_id=seminar.id, student_id=student.id, term_id=term.id)
        )
        return "created"

    if len(existing_rows) == 1 and existing_rows[0].seminar_id == seminar.id:
        return "unchanged"

    for row in existing_rows:
        await session.delete(row)
    await session.flush()
    session.add(
        SeminarMember(seminar_id=seminar.id, student_id=student.id, term_id=term.id)
    )
    return "updated"


async def import_csv(path: Path, academic_year: int) -> None:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    async with async_session() as session:
        term, term_created = await get_or_create_recruitment_term(
            session, academic_year
        )
        if term_created:
            print(
                f"{academic_year}年度の募集期間を作成しました"
                f"({term.starts_at} 〜 {term.ends_at})"
            )

        created = 0
        updated = 0
        unchanged = 0
        skipped = 0

        for row in rows:
            student_number = row["学籍番号"].strip()
            name = row["名前"].strip()
            seminar_name = row["配属先"].strip()

            student = await _find_student(session, student_number=student_number)
            if student is None:
                skipped += 1
                print(f"skip(学生が見つかりません): {student_number} {name!r}")
                continue

            seminar = await _find_seminar(session, name=seminar_name)
            if seminar is None:
                skipped += 1
                print(f"skip(ゼミが見つかりません): {seminar_name!r} ({name})")
                continue

            result = await _upsert_membership(
                session, seminar=seminar, student=student, term=term
            )
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            else:
                unchanged += 1

        await session.commit()

    print(
        f"seminar_members({academic_year}年度): +{created} created, "
        f"{updated} updated, {unchanged} unchanged, {skipped} skipped"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="所属ゼミCSVをDBへ投入する")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("academic_year", type=int)
    args = parser.parse_args()
    asyncio.run(import_csv(args.csv_path, args.academic_year))


if __name__ == "__main__":
    main()
