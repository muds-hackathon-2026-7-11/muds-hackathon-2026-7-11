import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from api.models import (
    MaterialType,
    QuestionStatus,
    RecruitmentTermStatus,
    UserRole,
)


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
    slack_user_id: str | None


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
    research_theme: str | None


class SeminarMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    type: MaterialType


class SeminarMemberOut(BaseModel):
    id: uuid.UUID
    name: str
    research_theme: str | None


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
    is_recruiting: bool = True


class SeminarRecruitmentOut(BaseModel):
    """募集ラウンドでのゼミ別設定。未設定のゼミは値が null。"""

    seminar_id: uuid.UUID
    seminar_name: str
    capacity: int | None
    is_recruiting: bool | None


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
    is_recruiting: bool | None = None


class TeacherRecruitmentOut(BaseModel):
    seminar_id: uuid.UUID
    seminar_name: str
    capacity: int | None
    is_recruiting: bool | None


# --- マッチ度診断 (#59) ---


class MatchOut(BaseModel):
    seminar_id: uuid.UUID
    score: int | None
    feedback: dict | None
    # score を出せない場合(研究テーマ/ゼミ紹介が未設定など)の説明。
    message: str | None = None
