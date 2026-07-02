import asyncio
from datetime import date
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session
from api.models import (
    Answer,
    AnswerSource,
    MaterialType,
    Question,
    QuestionStatus,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMaterial,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
    UserRole,
)

CURRENT_ACADEMIC_YEAR = 2026


class SeminarSeed(TypedDict):
    name: str
    capacity: int


class TeacherSeed(TypedDict):
    seminar: str
    name: str
    research_theme: str


class StudentSeed(TypedDict):
    seminar: str
    name: str
    research_theme: str
    academic_year: int


class MaterialSeed(TypedDict):
    seminar: str
    url: str
    type: MaterialType


class QASeed(TypedDict):
    seminar: str
    question: str
    answer: str | None


SEMINARS: list[SeminarSeed] = [
    {"name": "中村ゼミ", "capacity": 10},
    {"name": "福原ゼミ", "capacity": 8},
    {"name": "岡ゼミ", "capacity": 12},
    {"name": "高橋・浦木ゼミ", "capacity": 14},
    {"name": "林・清木ゼミ", "capacity": 10},
]

TEACHERS: list[TeacherSeed] = [
    {"seminar": "中村ゼミ", "name": "中村太郎", "research_theme": "機械学習・深層学習"},
    {
        "seminar": "福原ゼミ",
        "name": "福原花子",
        "research_theme": "データベース・分散システム",
    },
    {
        "seminar": "岡ゼミ",
        "name": "岡真一",
        "research_theme": "ロボティクス・制御工学",
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "name": "高橋修",
        "research_theme": "セキュリティ・暗号理論",
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "name": "浦木さやか",
        "research_theme": "ネットワークシステム",
    },
    {
        "seminar": "林・清木ゼミ",
        "name": "林大輔",
        "research_theme": "データマイニング",
    },
    {
        "seminar": "林・清木ゼミ",
        "name": "清木優子",
        "research_theme": "Webシステム開発",
    },
]

STUDENTS: list[StudentSeed] = [
    {
        "seminar": "中村ゼミ",
        "name": "山田太郎",
        "research_theme": "画像認識モデルの研究",
        "academic_year": CURRENT_ACADEMIC_YEAR,
    },
    {
        "seminar": "中村ゼミ",
        "name": "伊藤さくら",
        "research_theme": "強化学習によるゲームAI",
        "academic_year": CURRENT_ACADEMIC_YEAR - 1,
    },
    {
        "seminar": "福原ゼミ",
        "name": "渡辺健太",
        "research_theme": "分散データベースの性能評価",
        "academic_year": CURRENT_ACADEMIC_YEAR,
    },
    {
        "seminar": "岡ゼミ",
        "name": "小林愛",
        "research_theme": "自律移動ロボットの経路計画",
        "academic_year": CURRENT_ACADEMIC_YEAR,
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "name": "加藤翔太",
        "research_theme": "Webアプリケーションの脆弱性診断",
        "academic_year": CURRENT_ACADEMIC_YEAR,
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "name": "斎藤桃子",
        "research_theme": "無線ネットワークの経路最適化",
        "academic_year": CURRENT_ACADEMIC_YEAR - 1,
    },
    {
        "seminar": "林・清木ゼミ",
        "name": "吉田陽菜",
        "research_theme": "購買データのクラスタリング分析",
        "academic_year": CURRENT_ACADEMIC_YEAR,
    },
]

MATERIALS: list[MaterialSeed] = [
    {
        "seminar": "中村ゼミ",
        "url": "https://example.com/nakamura-slide.pdf",
        "type": MaterialType.slide,
    },
    {
        "seminar": "中村ゼミ",
        "url": "https://example.com/nakamura-intro.mp4",
        "type": MaterialType.video,
    },
    {
        "seminar": "福原ゼミ",
        "url": "https://example.com/fukuhara-guide.pdf",
        "type": MaterialType.pdf,
    },
    {
        "seminar": "岡ゼミ",
        "url": "https://example.com/oka-slide.pdf",
        "type": MaterialType.slide,
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "url": "https://example.com/takahashi-urakawa-intro.mp4",
        "type": MaterialType.video,
    },
    {
        "seminar": "林・清木ゼミ",
        "url": "https://example.com/hayashi-seiki-guide.pdf",
        "type": MaterialType.pdf,
    },
]

QA_PAIRS: list[QASeed] = [
    {
        "seminar": "中村ゼミ",
        "question": "プログラミング未経験でも大丈夫ですか？",
        "answer": "大丈夫です。基礎から丁寧に指導します。",
    },
    {
        "seminar": "福原ゼミ",
        "question": "週に何回ゼミがありますか？",
        "answer": None,
    },
    {
        "seminar": "岡ゼミ",
        "question": "研究テーマは自分で決められますか？",
        "answer": "相談しながら決めます。興味のある分野があればぜひ教えてください。",
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "question": "教員が2名いますが、どちらに相談すればいいですか？",
        "answer": None,
    },
]


async def _get_or_create_seminar(
    session: AsyncSession, data: SeminarSeed
) -> tuple[Seminar, bool]:
    result = await session.execute(select(Seminar).where(Seminar.name == data["name"]))
    seminar = result.scalar_one_or_none()
    if seminar is not None:
        return seminar, False

    seminar = Seminar(name=data["name"])
    session.add(seminar)
    await session.flush()
    return seminar, True


async def _get_or_create_user(
    session: AsyncSession,
    *,
    key: str,
    name: str,
    role: UserRole,
    research_theme: str | None,
) -> tuple[User, bool]:
    # keyは name とは独立した合成キー。同姓同名の別人が紛れ込んでも
    # google_id が衝突して同一人物として扱われてしまわないようにするため。
    google_id = f"seed-{role.value}-{key}"
    result = await session.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user, False

    user = User(
        google_id=google_id,
        email=f"{google_id}@example.com",
        name=name,
        role=role,
        research_theme=research_theme,
    )
    session.add(user)
    await session.flush()
    return user, True


async def _get_or_create_recruitment_term(
    session: AsyncSession, academic_year: int
) -> tuple[RecruitmentTerm, bool]:
    result = await session.execute(
        select(RecruitmentTerm).where(RecruitmentTerm.academic_year == academic_year)
    )
    term = result.scalar_one_or_none()
    if term is not None:
        return term, False

    # 開発中ずっと「募集中」として扱われるよう、期間は年度いっぱいまで広めに取る
    # (本来の募集期間は4〜5月の1ヶ月程度を想定しているが、シードデータは
    # 開発・デモ用途で使い続けられることを優先する)。
    term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date(academic_year, 4, 1),
        ends_at=date(academic_year, 12, 31),
        status=RecruitmentTermStatus.open,
    )
    session.add(term)
    await session.flush()
    return term, True


async def seed_all() -> None:
    async with async_session() as session:
        term, term_created = await _get_or_create_recruitment_term(
            session, CURRENT_ACADEMIC_YEAR
        )

        seminars_by_name: dict[str, Seminar] = {}
        seminar_created = 0
        recruitment_created = 0
        for seminar_data in SEMINARS:
            seminar, created = await _get_or_create_seminar(session, seminar_data)
            seminars_by_name[seminar.name] = seminar
            seminar_created += created

            recruitment_result = await session.execute(
                select(SeminarRecruitment).where(
                    SeminarRecruitment.term_id == term.id,
                    SeminarRecruitment.seminar_id == seminar.id,
                )
            )
            if recruitment_result.scalar_one_or_none() is None:
                session.add(
                    SeminarRecruitment(
                        term_id=term.id,
                        seminar_id=seminar.id,
                        capacity=seminar_data["capacity"],
                    )
                )
                recruitment_created += 1

        teacher_created = 0
        link_created = 0
        for teacher_data in TEACHERS:
            teacher, created = await _get_or_create_user(
                session,
                key=f"teacher-{teacher_data['name']}",
                name=teacher_data["name"],
                role=UserRole.teacher,
                research_theme=teacher_data["research_theme"],
            )
            teacher_created += created

            seminar = seminars_by_name[teacher_data["seminar"]]
            link_result = await session.execute(
                select(SeminarTeacher).where(
                    SeminarTeacher.seminar_id == seminar.id,
                    SeminarTeacher.teacher_id == teacher.id,
                )
            )
            if link_result.scalar_one_or_none() is None:
                session.add(
                    SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher.id)
                )
                link_created += 1

        student_created = 0
        member_created = 0
        for i, student_data in enumerate(STUDENTS):
            student, created = await _get_or_create_user(
                session,
                key=f"student-{i}",
                name=student_data["name"],
                role=UserRole.student,
                research_theme=student_data["research_theme"],
            )
            student_created += created

            seminar = seminars_by_name[student_data["seminar"]]
            member_result = await session.execute(
                select(SeminarMember).where(
                    SeminarMember.seminar_id == seminar.id,
                    SeminarMember.student_id == student.id,
                    SeminarMember.academic_year == student_data["academic_year"],
                )
            )
            if member_result.scalar_one_or_none() is None:
                session.add(
                    SeminarMember(
                        seminar_id=seminar.id,
                        student_id=student.id,
                        academic_year=student_data["academic_year"],
                    )
                )
                member_created += 1

        material_created = 0
        for material_data in MATERIALS:
            seminar = seminars_by_name[material_data["seminar"]]
            material_result = await session.execute(
                select(SeminarMaterial).where(
                    SeminarMaterial.seminar_id == seminar.id,
                    SeminarMaterial.url == material_data["url"],
                )
            )
            if material_result.scalar_one_or_none() is None:
                session.add(
                    SeminarMaterial(
                        seminar_id=seminar.id,
                        url=material_data["url"],
                        type=material_data["type"],
                    )
                )
                material_created += 1

        qa_created = 0
        for i, qa_data in enumerate(QA_PAIRS):
            seminar = seminars_by_name[qa_data["seminar"]]
            asker, _ = await _get_or_create_user(
                session,
                key=f"asker-{i}",
                name=f"質問者-{qa_data['seminar']}",
                role=UserRole.student,
                research_theme=None,
            )
            question_result = await session.execute(
                select(Question).where(
                    Question.seminar_id == seminar.id,
                    Question.content == qa_data["question"],
                )
            )
            question = question_result.scalar_one_or_none()
            if question is None:
                question = Question(
                    seminar_id=seminar.id,
                    user_id=asker.id,
                    content=qa_data["question"],
                )
                session.add(question)
                await session.flush()
                qa_created += 1

                answer_content = qa_data["answer"]
                if answer_content is not None:
                    teacher_name = next(
                        t["name"]
                        for t in TEACHERS
                        if t["seminar"] == qa_data["seminar"]
                    )
                    teacher, _ = await _get_or_create_user(
                        session,
                        key=f"teacher-{teacher_name}",
                        name=teacher_name,
                        role=UserRole.teacher,
                        research_theme=None,
                    )
                    session.add(
                        Answer(
                            question_id=question.id,
                            user_id=teacher.id,
                            content=answer_content,
                            source=AnswerSource.web,
                        )
                    )
                    question.status = QuestionStatus.answered

        await session.commit()

    print(
        f"recruitment_term: +{int(term_created)}, seminars: +{seminar_created} "
        f"(recruitments +{recruitment_created}), teachers: +{teacher_created} "
        f"(links +{link_created}), students: +{student_created} "
        f"(memberships +{member_created}), materials: +{material_created}, "
        f"questions: +{qa_created}"
    )


def main() -> None:
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
