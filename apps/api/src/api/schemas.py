import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from api.models import MaterialType, QuestionStatus, UserRole


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
