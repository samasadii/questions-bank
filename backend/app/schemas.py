from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from .models import RequestStatus, Role, UserStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: str
    email: EmailStr
    display_name: str
    role: Role
    status: UserStatus


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class CourseOut(ORMModel):
    id: str
    owner_id: str
    title: str
    description: str | None
    status: str


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    academic_year: str | None = Field(default=None, max_length=30)
    term: str | None = Field(default=None, max_length=50)


class ClassOut(ORMModel):
    id: str
    course_id: str
    owner_id: str
    name: str
    academic_year: str | None
    term: str | None
    status: str


class InviteOut(BaseModel):
    token: str
    join_path: str


class InviteSummary(BaseModel):
    class_id: str
    class_name: str
    course_title: str
    teacher_name: str


class JoinRequestOut(ORMModel):
    id: str
    class_id: str
    student_id: str
    status: RequestStatus
    created_at: datetime
    student_name: str | None = None
    student_email: str | None = None


class ClassMemberOut(BaseModel):
    student_id: str
    display_name: str
    email: EmailStr
    joined_at: datetime


class TopicCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    sort_order: int = 0


class TopicOut(ORMModel):
    id: str
    course_id: str
    title: str
    description: str | None
    sort_order: int


class NoteCreate(BaseModel):
    course_id: str
    topic_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    markdown_content: str = ""


class NoteOut(ORMModel):
    id: str
    course_id: str
    topic_id: str | None
    title: str
    markdown_content: str


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    markdown_content: str | None = None
    topic_id: str | None = None


QuestionType = Literal[
    "essay", "single_choice", "multiple_choice", "fill_blank",
    "true_false", "short_answer", "matching", "ordering"
]


class QuestionCreate(BaseModel):
    course_id: str
    topic_id: str | None = None
    type: QuestionType
    body_markdown: str = Field(min_length=1)
    options: list[dict[str, Any]] | None = None
    answer_data: dict[str, Any] | None = None
    explanation_markdown: str | None = None
    default_points: Decimal = Field(default=Decimal("1.00"), ge=0)
    difficulty: str | None = None
    tags: list[str] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    topic_id: str | None = None
    type: QuestionType | None = None
    body_markdown: str | None = Field(default=None, min_length=1)
    options: list[dict[str, Any]] | None = None
    answer_data: dict[str, Any] | None = None
    explanation_markdown: str | None = None
    default_points: Decimal | None = Field(default=None, ge=0)
    difficulty: str | None = None
    tags: list[str] | None = None


class QuestionOut(ORMModel):
    id: str
    course_id: str
    topic_id: str | None
    type: str
    body_markdown: str
    image_alt_text: str | None
    has_image: bool = False
    options: list[dict[str, Any]] | None
    answer_data: dict[str, Any] | None
    explanation_markdown: str | None
    default_points: Decimal
    difficulty: str | None
    tags: list[str]

    @model_validator(mode="before")
    @classmethod
    def image_flag(cls, value: Any) -> Any:
        if hasattr(value, "image_key"):
            data = {column.name: getattr(value, column.name) for column in value.__table__.columns}
            data["has_image"] = bool(value.image_key)
            return data
        return value


class PublicationTarget(BaseModel):
    class_id: str
    answers_available: bool = False


class PublicationUpdate(BaseModel):
    targets: list[PublicationTarget]
