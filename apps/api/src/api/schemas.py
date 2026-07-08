import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.models import (
    ApplicationStatus,
    MaterialType,
    QuestionStatus,
    RecruitmentTermStatus,
    UserRole,
)


class ResearchTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str


class CurrentSeminarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class MeOut(BaseModel):
    """認証済みユーザー自身の情報(GET /me)。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    student_id: str | None
    grade: str | None
    research_theme: str | None
    interest_tags: list[ResearchTagOut]
    slack_user_id: str | None
    # 現在の年度に所属しているゼミ(学生のみ。無ければNone)。
    current_seminar: CurrentSeminarOut | None


class MeUpdateIn(BaseModel):
    """本人の研究概要・興味分野タグの更新(PATCH /me)。"""

    research_theme: str | None = Field(default=None, max_length=2000)
    interest_tag_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)


class UserExistsOut(BaseModel):
    """メールアドレスが事前登録済みか(ログイン許可判定用)。"""

    exists: bool


class SeminarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    photo_url: str | None
    capacity: int | None
    recruitment_start: date | None
    recruitment_end: date | None


class TeacherOut(BaseModel):
    id: uuid.UUID
    name: str
    photo_url: str | None
    research_theme: str | None
    interest_tags: list[ResearchTagOut]


class SeminarMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    type: MaterialType


class SeminarMemberOut(BaseModel):
    id: uuid.UUID
    name: str
    research_theme: str | None
    interest_tags: list[ResearchTagOut]


class SeminarDetailOut(SeminarOut):
    teachers: list[TeacherOut]
    materials: list[SeminarMaterialOut]
    current_members: list[SeminarMemberOut]


class PriorityCounts(BaseModel):
    """第1〜第3志望それぞれの人数。"""

    first: int
    second: int
    third: int


class SeminarStatsOut(BaseModel):
    """ゼミごとの応募状況（現在の募集ラウンド基準）。"""

    id: uuid.UUID
    name: str
    capacity: int | None
    applicant_count: int
    priority_counts: PriorityCounts
    # 学年(users.grade)別の志望人数。grade未設定は "不明"。
    grade_counts: dict[str, int]
    # 倍率 = applicant_count / capacity。定員が未設定/0 の場合は null。
    ratio: float | None
    # 現在の所属ゼミ生数（継続者）。
    continuing_count: int
    # 対象学年(#99)。未設定(募集ラウンドの設定行が無い)ならnull。
    target_grades: list[str] | None


class QuestionCreate(BaseModel):
    seminar_id: uuid.UUID
    slack_user_id: str
    content: str = Field(min_length=1, max_length=2000)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seminar_id: uuid.UUID
    content: str
    status: QuestionStatus
    created_at: datetime


class AnswerOut(BaseModel):
    id: uuid.UUID
    content: str
    answerer_name: str
    created_at: datetime


class QuestionWithAnswersOut(QuestionOut):
    answers: list[AnswerOut]


class ApplicationChoiceIn(BaseModel):
    seminar_id: uuid.UUID
    priority: int = Field(ge=1, le=3)
    reason: str = Field(max_length=400)


class ApplicationUpsertIn(BaseModel):
    choices: list[ApplicationChoiceIn] = Field(max_length=3)


class ApplicationChoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seminar_id: uuid.UUID
    priority: int
    reason: str
    match_score: int | None
    match_feedback: dict | None


class ApplicationFormOut(BaseModel):
    id: uuid.UUID | None
    status: ApplicationStatus
    submitted_at: datetime | None
    choices: list[ApplicationChoiceOut]
    # 現在アクティブな募集期間の内容ならtrue。falseは過去期間の閲覧専用表示
    # (提出期間外でも直近の提出内容は見えるが、編集・再提出はできない)。
    is_editable: bool


# --- 運営: 募集ラウンド・定員設定 (#57) ---


class RecruitmentTermCreate(BaseModel):
    academic_year: int
    starts_at: date
    ends_at: date
    status: RecruitmentTermStatus = RecruitmentTermStatus.preparing


class RecruitmentTermUpdate(BaseModel):
    starts_at: date | None = None
    ends_at: date | None = None
    status: RecruitmentTermStatus | None = None


class RecruitmentTermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    academic_year: int
    starts_at: date
    ends_at: date
    status: RecruitmentTermStatus


class SeminarRecruitmentUpsert(BaseModel):
    capacity: int = Field(ge=0)
    # 募集対象学年(#99)。空リストは「募集していない」を意味する。
    # このエンドポイントは全置換なので必須にする(省略時に暗黙で
    # 閉じる/開くのどちらかにフォールバックすると、teacher.py側の
    # 「省略時は既存値据え置き」という別の省略時挙動と食い違うため)。
    target_grades: list[Literal["B1", "B2", "B3", "B4"]]


class SeminarRecruitmentOut(BaseModel):
    """募集ラウンドでのゼミ別設定。未設定のゼミは値が null。"""

    seminar_id: uuid.UUID
    seminar_name: str
    capacity: int | None
    target_grades: list[str] | None


# --- 教員向け応募者管理 (#58) ---


class PastSeminarOut(BaseModel):
    seminar_name: str
    academic_year: int


class ApplicantOut(BaseModel):
    student_id: str | None
    name: str
    grade: str | None
    priority: int
    reason: str
    past_seminars: list[PastSeminarOut]


class SeminarApplicantsOut(BaseModel):
    seminar_id: uuid.UUID
    seminar_name: str
    applicants: list[ApplicantOut]


class TeacherRecruitmentUpdate(BaseModel):
    capacity: int = Field(ge=0)
    # Noneなら据え置き(現状の対象学年を変更しない)。
    target_grades: list[Literal["B1", "B2", "B3", "B4"]] | None = None


class TeacherRecruitmentOut(BaseModel):
    seminar_id: uuid.UUID
    seminar_name: str
    capacity: int | None
    target_grades: list[str] | None


# --- マッチ度診断 (#59) ---


class MatchOut(BaseModel):
    seminar_id: uuid.UUID
    score: int | None
    feedback: dict | None
    # score を出せない場合(研究テーマ/ゼミ紹介が未設定など)の説明。
    message: str | None = None


# --- 運営: 教員・ゼミ管理 (#62) ---
# 新規の一括投入はCSV(#40/#45)が担うため、ここは個別の編集・担当の付け外しが中心。


class AdminSeminarCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    photo_url: str | None = None


class AdminSeminarUpdate(BaseModel):
    # 送られたフィールドのみ更新する(未指定は据え置き)。ルーター側で
    # model_dump(exclude_unset=True) を使うため、既定値は「未指定」を表す。
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    photo_url: str | None = None


class AdminSeminarTeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class SeminarMaterialCreate(BaseModel):
    url: str = Field(min_length=1)
    type: MaterialType


class AdminSeminarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    photo_url: str | None
    teachers: list[AdminSeminarTeacherOut]
    materials: list[SeminarMaterialOut]


class AdminTeacherCreate(BaseModel):
    # 教員ユーザーを1名追加する(作成はここ、一括はCSV #40)。
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=255)
    research_theme: str | None = None
    photo_url: str | None = None

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        # import系と揃えて小文字正規化し、最低限の形式チェックを行う。
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("有効なメールアドレスを入力してください。")
        return normalized


class AdminTeacherUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    research_theme: str | None = None
    photo_url: str | None = None
    is_active: bool | None = None


class AdminTeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    research_theme: str | None
    photo_url: str | None
    is_active: bool


# --- 配属結果CSVインポート (#61) ---


class AssignmentImportError(BaseModel):
    # CSVの行番号(ヘッダを除いた1始まり)と理由。
    row: int
    reason: str


class AssignmentImportResult(BaseModel):
    created: int  # 新規に作成した配属レコード数
    existing: int  # 既に存在していた(スキップした)数
    errors: list[AssignmentImportError]
