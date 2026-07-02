import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from api.models import MaterialType, QuestionStatus


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
