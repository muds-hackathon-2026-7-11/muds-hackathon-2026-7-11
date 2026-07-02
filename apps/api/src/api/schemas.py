import uuid

from pydantic import BaseModel, ConfigDict, Field


class SeminarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class QuestionCreate(BaseModel):
    seminar_id: uuid.UUID
    slack_user_id: str
    content: str = Field(min_length=1, max_length=2000)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seminar_id: uuid.UUID
    user_id: uuid.UUID
    content: str
