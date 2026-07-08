import asyncio
from datetime import datetime, timezone
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session
from api.models import (
    AnswerSource,
    ApplicationChoice,
    ApplicationForm,
    ApplicationStatus,
    MaterialType,
    Question,
    RecruitmentTerm,
    ResearchTag,
    Seminar,
    SeminarMaterial,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
    UserInterestTag,
    UserRole,
)
from api.recruitment_terms import get_or_create_recruitment_term
from api.services import record_answer

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
    # 興味分野タグ(research_tagsマスタのname)。プロフィール/マッチ用の仮データ。
    interest_tags: list[str]


class MaterialSeed(TypedDict):
    seminar: str
    url: str
    type: MaterialType


class QASeed(TypedDict):
    seminar: str
    question: str
    answer: str | None


class ApplicationChoiceSeed(TypedDict):
    seminar: str
    priority: int
    reason: str


class ApplicationSeed(TypedDict):
    name: str
    grade: str
    # 研究概要(users.research_theme)。マッチ度診断・プロフィール表示の仮データ。
    research_theme: str
    # 興味分野タグ(research_tagsマスタのname)。
    interest_tags: list[str]
    choices: list[ApplicationChoiceSeed]


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
        "interest_tags": ["画像認識", "深層学習"],
    },
    {
        "seminar": "中村ゼミ",
        "name": "伊藤さくら",
        "research_theme": "強化学習によるゲームAI",
        "academic_year": CURRENT_ACADEMIC_YEAR - 1,
        "interest_tags": ["強化学習", "深層学習"],
    },
    {
        "seminar": "福原ゼミ",
        "name": "渡辺健太",
        "research_theme": "分散データベースの性能評価",
        "academic_year": CURRENT_ACADEMIC_YEAR,
        "interest_tags": ["データベース", "最適化"],
    },
    {
        "seminar": "岡ゼミ",
        "name": "小林愛",
        "research_theme": "自律移動ロボットの経路計画",
        "academic_year": CURRENT_ACADEMIC_YEAR,
        "interest_tags": ["自律移動", "制御"],
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "name": "加藤翔太",
        "research_theme": "Webアプリケーションの脆弱性診断",
        "academic_year": CURRENT_ACADEMIC_YEAR,
        "interest_tags": ["認証", "Web開発"],
    },
    {
        "seminar": "高橋・浦木ゼミ",
        "name": "斎藤桃子",
        "research_theme": "無線ネットワークの経路最適化",
        "academic_year": CURRENT_ACADEMIC_YEAR - 1,
        "interest_tags": ["センサ", "最適化"],
    },
    {
        "seminar": "林・清木ゼミ",
        "name": "吉田陽菜",
        "research_theme": "購買データのクラスタリング分析",
        "academic_year": CURRENT_ACADEMIC_YEAR,
        "interest_tags": ["統計解析", "データ可視化"],
    },
    # 中村ゼミ所属を厚めに。研究はVR系がメインの傾向(デモ用の仮データ)。
    {
        "seminar": "中村ゼミ",
        "name": "藤井蓮",
        "research_theme": "VR空間での没入型学習コンテンツの研究",
        "academic_year": CURRENT_ACADEMIC_YEAR,
        "interest_tags": ["VR/AR", "VRコンテンツ制作"],
    },
    {
        "seminar": "中村ゼミ",
        "name": "岡田結衣",
        "research_theme": "メタバース上での協調作業を支援するインタフェースの研究",
        "academic_year": CURRENT_ACADEMIC_YEAR,
        "interest_tags": ["メタバース", "VR/AR"],
    },
    {
        "seminar": "中村ゼミ",
        "name": "松本大和",
        "research_theme": "VRリハビリテーションの効果測定と可視化",
        "academic_year": CURRENT_ACADEMIC_YEAR - 1,
        "interest_tags": ["VR/AR", "データ可視化"],
    },
    {
        "seminar": "中村ゼミ",
        "name": "中島美咲",
        "research_theme": "ARによる現実空間への情報重畳と操作支援",
        "academic_year": CURRENT_ACADEMIC_YEAR,
        "interest_tags": ["VR/AR", "UI/UX"],
    },
    {
        "seminar": "中村ゼミ",
        "name": "前田悠斗",
        "research_theme": "VRコンテンツ制作パイプラインの自動化",
        "academic_year": CURRENT_ACADEMIC_YEAR - 1,
        "interest_tags": ["VRコンテンツ制作", "メタバース"],
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

# 応募状況(GET /seminars/stats)のグラフ用の、提出済み志望データ。
# 学年別グラフを埋めるため B1〜B4 を各ゼミに散らしてある。
# 研究概要(research_theme)は中村ゼミ(第1志望)をメインに厚く用意し、
# 他ゼミ第1志望は空にしている(タグ・応募データはグラフ用に全ゼミ付与)。
APPLICATIONS: list[ApplicationSeed] = [
    # --- B1(1年生) ---
    {
        "name": "応募一花",
        "grade": "B1",
        "research_theme": (
            "スマホで撮った写真を自動で仕分けするような、"
            "画像認識AIの仕組みを基礎から学びたい。"
        ),
        "interest_tags": ["深層学習", "画像認識"],
        "choices": [
            {
                "seminar": "中村ゼミ",
                "priority": 1,
                "reason": "AIを基礎から学びたいため。",
            },
            {
                "seminar": "福原ゼミ",
                "priority": 2,
                "reason": "データの扱いにも興味があるため。",
            },
        ],
    },
    {
        "name": "応募一輝",
        "grade": "B1",
        "research_theme": "",
        "interest_tags": ["自律移動", "制御"],
        "choices": [
            {"seminar": "岡ゼミ", "priority": 1, "reason": "ロボットを作りたいため。"},
            {
                "seminar": "高橋・浦木ゼミ",
                "priority": 2,
                "reason": "ネットワークにも触れたいため。",
            },
        ],
    },
    {
        "name": "応募一葉",
        "grade": "B1",
        "research_theme": "",
        "interest_tags": ["Web開発", "UI/UX"],
        "choices": [
            {
                "seminar": "林・清木ゼミ",
                "priority": 1,
                "reason": "Web開発を学びたいため。",
            },
        ],
    },
    # --- B2(2年生) ---
    {
        "name": "応募二郎",
        "grade": "B2",
        "research_theme": "",
        "interest_tags": ["データベース", "統計解析"],
        "choices": [
            {
                "seminar": "福原ゼミ",
                "priority": 1,
                "reason": "データベースを深く学びたいため。",
            },
            {
                "seminar": "中村ゼミ",
                "priority": 2,
                "reason": "分析にも興味があるため。",
            },
        ],
    },
    {
        "name": "応募二菜",
        "grade": "B2",
        "research_theme": "",
        "interest_tags": ["暗号", "認証"],
        "choices": [
            {
                "seminar": "高橋・浦木ゼミ",
                "priority": 1,
                "reason": "暗号技術を学びたいため。",
            },
            {
                "seminar": "林・清木ゼミ",
                "priority": 2,
                "reason": "Web技術にも関心があるため。",
            },
        ],
    },
    {
        "name": "応募二葉",
        "grade": "B2",
        "research_theme": (
            "文章や画像を作る生成AIやLLMを、"
            "学習支援ツールに応用することに関心がある。"
        ),
        "interest_tags": ["生成AI", "LLM"],
        "choices": [
            {
                "seminar": "中村ゼミ",
                "priority": 1,
                "reason": "生成AIを研究したいため。",
            },
            {
                "seminar": "岡ゼミ",
                "priority": 3,
                "reason": "ロボットへの応用も見たいため。",
            },
        ],
    },
    # --- B3(3年生) ---
    {
        "name": "応募太郎",
        "grade": "B3",
        "research_theme": (
            "気象や株価などの時系列データを、"
            "深層学習で予測する研究に取り組みたい。"
        ),
        "interest_tags": ["深層学習", "時系列解析"],
        "choices": [
            {
                "seminar": "中村ゼミ",
                "priority": 1,
                "reason": "機械学習を深く学びたいため。",
            },
            {
                "seminar": "福原ゼミ",
                "priority": 2,
                "reason": "データ基盤にも関心があるため。",
            },
            {
                "seminar": "岡ゼミ",
                "priority": 3,
                "reason": "ロボティクスにも触れたいため。",
            },
        ],
    },
    {
        "name": "応募花子",
        "grade": "B3",
        "research_theme": (
            "画像認識モデルの認識精度を、"
            "データ拡張やモデル改良で高める研究をしたい。"
        ),
        "interest_tags": ["画像認識", "深層学習"],
        "choices": [
            {
                "seminar": "中村ゼミ",
                "priority": 1,
                "reason": "画像認識の研究をしたいため。",
            },
            {"seminar": "岡ゼミ", "priority": 2, "reason": "制御にも興味があるため。"},
        ],
    },
    {
        "name": "応募次郎",
        "grade": "B3",
        "research_theme": "",
        "interest_tags": ["データベース", "最適化"],
        "choices": [
            {
                "seminar": "福原ゼミ",
                "priority": 1,
                "reason": "分散システムを学びたいため。",
            },
            {"seminar": "中村ゼミ", "priority": 2, "reason": "AIも学びたいため。"},
            {
                "seminar": "高橋・浦木ゼミ",
                "priority": 3,
                "reason": "セキュリティにも興味があるため。",
            },
        ],
    },
    {
        "name": "応募健",
        "grade": "B3",
        "research_theme": "",
        "interest_tags": ["自律移動", "センサ"],
        "choices": [
            {
                "seminar": "岡ゼミ",
                "priority": 1,
                "reason": "自律移動ロボットに関心があるため。",
            },
            {
                "seminar": "福原ゼミ",
                "priority": 2,
                "reason": "データベースも学びたいため。",
            },
        ],
    },
    # --- B4(4年生) ---
    {
        "name": "応募さくら",
        "grade": "B4",
        "research_theme": (
            "深層学習を使って大規模データから有用なパターンを見つける、"
            "データマイニングの研究を深めたい。"
        ),
        "interest_tags": ["深層学習", "データ可視化"],
        "choices": [
            {
                "seminar": "中村ゼミ",
                "priority": 1,
                "reason": "深層学習を継続したいため。",
            },
            {
                "seminar": "林・清木ゼミ",
                "priority": 2,
                "reason": "データマイニングも学びたいため。",
            },
        ],
    },
    {
        "name": "応募舞",
        "grade": "B4",
        "research_theme": "",
        "interest_tags": ["認証", "Web開発"],
        "choices": [
            {
                "seminar": "高橋・浦木ゼミ",
                "priority": 1,
                "reason": "脆弱性診断を研究したいため。",
            },
            {
                "seminar": "中村ゼミ",
                "priority": 2,
                "reason": "機械学習にも興味があるため。",
            },
        ],
    },
    {
        "name": "応募翔",
        "grade": "B4",
        "research_theme": "",
        "interest_tags": ["統計解析", "マーケティング"],
        "choices": [
            {
                "seminar": "林・清木ゼミ",
                "priority": 1,
                "reason": "データマイニングを研究したいため。",
            },
            {
                "seminar": "福原ゼミ",
                "priority": 2,
                "reason": "データ基盤も学びたいため。",
            },
        ],
    },
    {
        "name": "応募葵",
        "grade": "B4",
        "research_theme": "",
        "interest_tags": ["制御", "エッジAI"],
        "choices": [
            {
                "seminar": "岡ゼミ",
                "priority": 1,
                "reason": "制御工学を研究したいため。",
            },
            {
                "seminar": "高橋・浦木ゼミ",
                "priority": 3,
                "reason": "組込みにも興味があるため。",
            },
        ],
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
    grade: str | None = None,
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
        grade=grade,
    )
    session.add(user)
    await session.flush()
    return user, True


async def _link_interest_tags(
    session: AsyncSession, *, user: User, tag_names: list[str]
) -> int:
    """ユーザーに興味分野タグ(research_tagsマスタ)を紐付ける。追加した数を返す。

    マスタに無い名前は無視する(タグマスタはmigrationで投入済みの想定)。
    """
    linked = 0
    for name in tag_names:
        tag = (
            await session.execute(select(ResearchTag).where(ResearchTag.name == name))
        ).scalar_one_or_none()
        if tag is None:
            continue
        exists = (
            await session.execute(
                select(UserInterestTag).where(
                    UserInterestTag.user_id == user.id,
                    UserInterestTag.tag_id == tag.id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(UserInterestTag(user_id=user.id, tag_id=tag.id))
            linked += 1
    return linked


async def seed_all() -> None:
    async with async_session() as session:
        term, term_created = await get_or_create_recruitment_term(
            session, CURRENT_ACADEMIC_YEAR
        )
        # 所属ゼミ生は term_id で持つ。過年度の「過去の所属」も表現できるよう、
        # STUDENTS に登場する年度分の募集ラウンドを用意しておく。
        terms_by_year: dict[int, RecruitmentTerm] = {CURRENT_ACADEMIC_YEAR: term}
        for year in {s["academic_year"] for s in STUDENTS}:
            if year not in terms_by_year:
                past_term, _ = await get_or_create_recruitment_term(session, year)
                terms_by_year[year] = past_term

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
                        target_grades=["B1", "B2", "B3", "B4"],
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
        tag_link_created = 0
        for i, student_data in enumerate(STUDENTS):
            student, created = await _get_or_create_user(
                session,
                key=f"student-{i}",
                name=student_data["name"],
                role=UserRole.student,
                research_theme=student_data["research_theme"],
            )
            student_created += created
            tag_link_created += await _link_interest_tags(
                session, user=student, tag_names=student_data["interest_tags"]
            )

            seminar = seminars_by_name[student_data["seminar"]]
            member_term = terms_by_year[student_data["academic_year"]]
            member_result = await session.execute(
                select(SeminarMember).where(
                    SeminarMember.seminar_id == seminar.id,
                    SeminarMember.student_id == student.id,
                    SeminarMember.term_id == member_term.id,
                )
            )
            if member_result.scalar_one_or_none() is None:
                session.add(
                    SeminarMember(
                        seminar_id=seminar.id,
                        student_id=student.id,
                        term_id=member_term.id,
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
                    await record_answer(
                        session,
                        question=question,
                        user_id=teacher.id,
                        content=answer_content,
                        source=AnswerSource.web,
                    )

        application_created = 0
        choice_created = 0
        for i, app_data in enumerate(APPLICATIONS):
            applicant, _ = await _get_or_create_user(
                session,
                key=f"applicant-{i}",
                name=app_data["name"],
                role=UserRole.student,
                research_theme=app_data["research_theme"],
                grade=app_data["grade"],
            )
            tag_link_created += await _link_interest_tags(
                session, user=applicant, tag_names=app_data["interest_tags"]
            )
            form_result = await session.execute(
                select(ApplicationForm).where(
                    ApplicationForm.term_id == term.id,
                    ApplicationForm.student_id == applicant.id,
                )
            )
            form = form_result.scalar_one_or_none()
            if form is None:
                form = ApplicationForm(
                    term_id=term.id,
                    student_id=applicant.id,
                    status=ApplicationStatus.submitted,
                    submitted_at=datetime.now(timezone.utc),
                )
                session.add(form)
                await session.flush()
                application_created += 1

            for choice_data in app_data["choices"]:
                seminar = seminars_by_name[choice_data["seminar"]]
                choice_result = await session.execute(
                    select(ApplicationChoice).where(
                        ApplicationChoice.application_form_id == form.id,
                        ApplicationChoice.seminar_id == seminar.id,
                    )
                )
                if choice_result.scalar_one_or_none() is None:
                    session.add(
                        ApplicationChoice(
                            application_form_id=form.id,
                            seminar_id=seminar.id,
                            priority=choice_data["priority"],
                            reason=choice_data["reason"],
                        )
                    )
                    choice_created += 1

        await session.commit()

    print(
        f"recruitment_term: +{int(term_created)}, seminars: +{seminar_created} "
        f"(recruitments +{recruitment_created}), teachers: +{teacher_created} "
        f"(links +{link_created}), students: +{student_created} "
        f"(memberships +{member_created}), materials: +{material_created}, "
        f"questions: +{qa_created}, applications: +{application_created} "
        f"(choices +{choice_created}), interest_tags: +{tag_link_created}"
    )


def main() -> None:
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
