from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, LargeBinary, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    teacher = "teacher"
    student = "student"


class UserStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    rejected = "rejected"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class MembershipStatus(str, enum.Enum):
    active = "active"
    removed = "removed"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role), index=True)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClassGroup(Base):
    __tablename__ = "classes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    academic_year: Mapped[str | None] = mapped_column(String(30))
    # Keep the existing physical column name for local database compatibility.
    school_name: Mapped[str | None] = mapped_column("term", String(120))
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClassInvite(Base):
    __tablename__ = "class_invites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClassJoinRequest(Base):
    __tablename__ = "class_join_requests"
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_join_request_class_student"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.pending)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClassMembership(Base):
    __tablename__ = "class_memberships"
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_membership_class_student"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[MembershipStatus] = mapped_column(Enum(MembershipStatus), default=MembershipStatus.active)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(default=0)


class LectureNote(Base):
    __tablename__ = "lecture_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    markdown_content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NoteImage(Base):
    __tablename__ = "note_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    note_id: Mapped[str] = mapped_column(ForeignKey("lecture_notes.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    alt_text: Mapped[str | None] = mapped_column(String(500))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContentImport(Base):
    __tablename__ = "content_imports"
    __table_args__ = (UniqueConstraint("source_path", name="uq_content_import_source_path"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_path: Mapped[str] = mapped_column(String(500), index=True)
    source_hash: Mapped[str] = mapped_column(String(64))
    note_id: Mapped[str] = mapped_column(ForeignKey("lecture_notes.id"), unique=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    body_markdown: Mapped[str] = mapped_column(Text)
    image_key: Mapped[str | None] = mapped_column(String(255))
    image_alt_text: Mapped[str | None] = mapped_column(String(300))
    options: Mapped[list | None] = mapped_column(JSON)
    answer_data: Mapped[dict | None] = mapped_column(JSON)
    explanation_markdown: Mapped[str | None] = mapped_column(Text)
    default_points: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("1.00"))
    difficulty: Mapped[str | None] = mapped_column(String(20))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotePublication(Base):
    __tablename__ = "note_publications"
    __table_args__ = (UniqueConstraint("note_id", "class_id", name="uq_note_publication"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    note_id: Mapped[str] = mapped_column(ForeignKey("lecture_notes.id"), index=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    published_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QuestionPublication(Base):
    __tablename__ = "question_publications"
    __table_args__ = (UniqueConstraint("question_id", "class_id", name="uq_question_publication"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), index=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    published_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    answers_available: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
