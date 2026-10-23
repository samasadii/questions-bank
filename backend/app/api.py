import base64
import html
import io
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from .config import settings
from .deps import CurrentUser, Db, require_role
from .models import (
    ClassGroup,
    ClassInvite,
    ClassJoinRequest,
    ClassMembership,
    Course,
    LectureNote,
    MembershipStatus,
    NotePublication,
    Question,
    QuestionPublication,
    RequestStatus,
    Role,
    Topic,
    User,
    UserStatus,
)
from .schemas import (
    ClassCreate,
    ClassMemberOut,
    ClassOut,
    CourseCreate,
    CourseOut,
    InviteOut,
    InviteSummary,
    JoinRequestOut,
    LoginInput,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    PublicationUpdate,
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
    RegisterInput,
    TokenOut,
    TopicCreate,
    TopicOut,
    UserOut,
)
from .security import create_access_token, hash_password, new_invite_token, token_digest, verify_password


router = APIRouter(prefix="/api")


def owned_course(db: Db, user: User, course_id: str) -> Course:
    course = db.scalar(select(Course).where(Course.id == course_id, Course.owner_id == user.id))
    if not course:
        raise HTTPException(status_code=404, detail="دوره پیدا نشد")
    return course


def owned_class(db: Db, user: User, class_id: str) -> ClassGroup:
    group = db.scalar(select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.owner_id == user.id))
    if not group:
        raise HTTPException(status_code=404, detail="کلاس پیدا نشد")
    return group


def active_membership(db: Db, user: User, class_id: str) -> ClassMembership | None:
    return db.scalar(
        select(ClassMembership).where(
            ClassMembership.class_id == class_id,
            ClassMembership.student_id == user.id,
            ClassMembership.status == MembershipStatus.active,
        )
    )


def validate_topic(db: Db, course_id: str, topic_id: str | None) -> None:
    if topic_id and not db.scalar(select(Topic).where(Topic.id == topic_id, Topic.course_id == course_id)):
        raise HTTPException(status_code=400, detail="موضوع باید متعلق به همان دوره باشد")


def auth_response(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/auth/register/teacher", response_model=TokenOut, status_code=201)
def register_teacher(payload: RegisterInput, db: Db) -> TokenOut:
    return register(payload, Role.teacher, db)


@router.post("/auth/register/student", response_model=TokenOut, status_code=201)
def register_student(payload: RegisterInput, db: Db) -> TokenOut:
    return register(payload, Role.student, db)


def register(payload: RegisterInput, role: Role, db: Db) -> TokenOut:
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="این ایمیل قبلاً ثبت شده است")
    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role=role,
        status=UserStatus.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return auth_response(user)


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginInput, db: Db) -> TokenOut:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ایمیل یا گذرواژه نادرست است")
    return auth_response(user)


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.get("/courses", response_model=list[CourseOut])
def list_courses(db: Db, user: CurrentUser) -> list[Course]:
    require_role(user, Role.teacher)
    return list(db.scalars(select(Course).where(Course.owner_id == user.id).order_by(Course.created_at.desc())))


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, db: Db, user: CurrentUser) -> Course:
    require_role(user, Role.teacher)
    course = Course(owner_id=user.id, **payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/courses/{course_id}/classes", response_model=list[ClassOut])
def list_classes(course_id: str, db: Db, user: CurrentUser) -> list[ClassGroup]:
    require_role(user, Role.teacher)
    owned_course(db, user, course_id)
    return list(db.scalars(select(ClassGroup).where(ClassGroup.course_id == course_id)))


@router.post("/courses/{course_id}/classes", response_model=ClassOut, status_code=201)
def create_class(course_id: str, payload: ClassCreate, db: Db, user: CurrentUser) -> ClassGroup:
    require_role(user, Role.teacher)
    owned_course(db, user, course_id)
    group = ClassGroup(course_id=course_id, owner_id=user.id, **payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.post("/classes/{class_id}/invite", response_model=InviteOut)
def rotate_invite(class_id: str, db: Db, user: CurrentUser) -> InviteOut:
    require_role(user, Role.teacher)
    owned_class(db, user, class_id)
    for invite in db.scalars(select(ClassInvite).where(ClassInvite.class_id == class_id, ClassInvite.revoked_at.is_(None))):
        invite.revoked_at = datetime.utcnow()
    token = new_invite_token()
    db.add(ClassInvite(class_id=class_id, token_hash=token_digest(token)))
    db.commit()
    return InviteOut(token=token, join_path=f"/join/{token}")


@router.delete("/classes/{class_id}/invite", status_code=204)
def revoke_invite(class_id: str, db: Db, user: CurrentUser) -> Response:
    require_role(user, Role.teacher)
    owned_class(db, user, class_id)
    for invite in db.scalars(select(ClassInvite).where(ClassInvite.class_id == class_id, ClassInvite.revoked_at.is_(None))):
        invite.revoked_at = datetime.utcnow()
    db.commit()
    return Response(status_code=204)


def resolve_invite(token: str, db: Db) -> tuple[ClassInvite, ClassGroup]:
    invite = db.scalar(
        select(ClassInvite).where(ClassInvite.token_hash == token_digest(token), ClassInvite.revoked_at.is_(None))
    )
    if not invite:
        raise HTTPException(status_code=404, detail="پیوند دعوت معتبر نیست")
    group = db.get(ClassGroup, invite.class_id)
    if not group or group.status != "active":
        raise HTTPException(status_code=404, detail="کلاس فعال نیست")
    return invite, group


@router.get("/class-invites/{token}", response_model=InviteSummary)
def invite_summary(token: str, db: Db) -> InviteSummary:
    _, group = resolve_invite(token, db)
    course = db.get(Course, group.course_id)
    teacher = db.get(User, group.owner_id)
    return InviteSummary(
        class_id=group.id,
        class_name=group.name,
        course_title=course.title,
        teacher_name=teacher.display_name,
    )


@router.post("/class-invites/{token}/request", response_model=JoinRequestOut, status_code=201)
def request_join(token: str, db: Db, user: CurrentUser) -> ClassJoinRequest:
    require_role(user, Role.student)
    _, group = resolve_invite(token, db)
    if active_membership(db, user, group.id):
        raise HTTPException(status_code=409, detail="شما عضو این کلاس هستید")
    request = db.scalar(
        select(ClassJoinRequest).where(
            ClassJoinRequest.class_id == group.id,
            ClassJoinRequest.student_id == user.id,
        )
    )
    if request:
        if request.status == RequestStatus.pending:
            raise HTTPException(status_code=409, detail="درخواست شما در انتظار بررسی است")
        request.status = RequestStatus.pending
        request.reviewed_at = None
        request.reviewed_by = None
    else:
        request = ClassJoinRequest(class_id=group.id, student_id=user.id)
        db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("/classes/{class_id}/join-requests", response_model=list[JoinRequestOut])
def list_join_requests(class_id: str, db: Db, user: CurrentUser) -> list[JoinRequestOut]:
    require_role(user, Role.teacher)
    owned_class(db, user, class_id)
    rows = db.execute(
        select(ClassJoinRequest, User)
        .join(User, User.id == ClassJoinRequest.student_id)
        .where(ClassJoinRequest.class_id == class_id)
        .order_by(ClassJoinRequest.created_at.desc())
    ).all()
    return [
        JoinRequestOut.model_validate(request).model_copy(
            update={"student_name": student.display_name, "student_email": student.email}
        )
        for request, student in rows
    ]


@router.post("/classes/{class_id}/join-requests/{request_id}/approve", response_model=JoinRequestOut)
def approve_join(class_id: str, request_id: str, db: Db, user: CurrentUser) -> ClassJoinRequest:
    require_role(user, Role.teacher)
    owned_class(db, user, class_id)
    request = db.scalar(
        select(ClassJoinRequest).where(ClassJoinRequest.id == request_id, ClassJoinRequest.class_id == class_id)
    )
    if not request:
        raise HTTPException(status_code=404, detail="درخواست پیدا نشد")
    request.status = RequestStatus.approved
    request.reviewed_by = user.id
    request.reviewed_at = datetime.utcnow()
    membership = db.scalar(
        select(ClassMembership).where(
            ClassMembership.class_id == class_id, ClassMembership.student_id == request.student_id
        )
    )
    if membership:
        membership.status = MembershipStatus.active
        membership.removed_at = None
    else:
        db.add(ClassMembership(class_id=class_id, student_id=request.student_id))
    db.commit()
    db.refresh(request)
    return request


@router.post("/classes/{class_id}/join-requests/{request_id}/reject", response_model=JoinRequestOut)
def reject_join(class_id: str, request_id: str, db: Db, user: CurrentUser) -> ClassJoinRequest:
    require_role(user, Role.teacher)
    owned_class(db, user, class_id)
    request = db.scalar(
        select(ClassJoinRequest).where(ClassJoinRequest.id == request_id, ClassJoinRequest.class_id == class_id)
    )
    if not request:
        raise HTTPException(status_code=404, detail="درخواست پیدا نشد")
    request.status = RequestStatus.rejected
    request.reviewed_by = user.id
    request.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return request


@router.get("/classes/{class_id}/students", response_model=list[ClassMemberOut])
def list_students(class_id: str, db: Db, user: CurrentUser) -> list[ClassMemberOut]:
    require_role(user, Role.teacher)
    owned_class(db, user, class_id)
    rows = db.execute(
        select(ClassMembership, User)
        .join(User, User.id == ClassMembership.student_id)
        .where(
            ClassMembership.class_id == class_id,
            ClassMembership.status == MembershipStatus.active,
        )
    ).all()
    return [
        ClassMemberOut(
            student_id=student.id,
            display_name=student.display_name,
            email=student.email,
            joined_at=membership.joined_at,
        )
        for membership, student in rows
    ]


@router.delete("/classes/{class_id}/students/{student_id}", status_code=204)
def remove_student(class_id: str, student_id: str, db: Db, user: CurrentUser) -> Response:
    require_role(user, Role.teacher)
    owned_class(db, user, class_id)
    membership = db.scalar(
        select(ClassMembership).where(
            ClassMembership.class_id == class_id,
            ClassMembership.student_id == student_id,
            ClassMembership.status == MembershipStatus.active,
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="دانش‌آموز عضو این کلاس نیست")
    membership.status = MembershipStatus.removed
    membership.removed_at = datetime.utcnow()
    db.commit()
    return Response(status_code=204)


@router.post("/courses/{course_id}/topics", response_model=TopicOut, status_code=201)
def create_topic(course_id: str, payload: TopicCreate, db: Db, user: CurrentUser) -> Topic:
    require_role(user, Role.teacher)
    owned_course(db, user, course_id)
    topic = Topic(course_id=course_id, **payload.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.post("/notes", response_model=NoteOut, status_code=201)
def create_note(payload: NoteCreate, db: Db, user: CurrentUser) -> LectureNote:
    require_role(user, Role.teacher)
    owned_course(db, user, payload.course_id)
    validate_topic(db, payload.course_id, payload.topic_id)
    note = LectureNote(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes", response_model=list[NoteOut])
def list_notes(course_id: str, db: Db, user: CurrentUser) -> list[LectureNote]:
    require_role(user, Role.teacher)
    owned_course(db, user, course_id)
    return list(db.scalars(select(LectureNote).where(LectureNote.course_id == course_id)))


@router.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: str, payload: NoteUpdate, db: Db, user: CurrentUser) -> LectureNote:
    require_role(user, Role.teacher)
    note = db.get(LectureNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="جزوه پیدا نشد")
    owned_course(db, user, note.course_id)
    changes = payload.model_dump(exclude_unset=True)
    if "topic_id" in changes:
        validate_topic(db, note.course_id, changes["topic_id"])
    for key, value in changes.items():
        setattr(note, key, value)
    db.commit()
    db.refresh(note)
    return note


@router.put("/notes/{note_id}/publications", status_code=204)
def publish_note(note_id: str, payload: PublicationUpdate, db: Db, user: CurrentUser) -> Response:
    require_role(user, Role.teacher)
    note = db.get(LectureNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="جزوه پیدا نشد")
    owned_course(db, user, note.course_id)
    class_ids = {target.class_id for target in payload.targets}
    for class_id in class_ids:
        group = owned_class(db, user, class_id)
        if group.course_id != note.course_id:
            raise HTTPException(status_code=400, detail="کلاس و جزوه باید متعلق به یک دوره باشند")
    db.execute(delete(NotePublication).where(NotePublication.note_id == note_id))
    db.flush()
    db.add_all([NotePublication(note_id=note_id, class_id=class_id, published_by=user.id) for class_id in class_ids])
    db.commit()
    return Response(status_code=204)


@router.post("/questions", response_model=QuestionOut, status_code=201)
def create_question(payload: QuestionCreate, db: Db, user: CurrentUser) -> Question:
    require_role(user, Role.teacher)
    owned_course(db, user, payload.course_id)
    validate_topic(db, payload.course_id, payload.topic_id)
    question = Question(**payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(course_id: str, db: Db, user: CurrentUser) -> list[Question]:
    require_role(user, Role.teacher)
    owned_course(db, user, course_id)
    return list(db.scalars(select(Question).where(Question.course_id == course_id)))


@router.patch("/questions/{question_id}", response_model=QuestionOut)
def update_question(question_id: str, payload: QuestionUpdate, db: Db, user: CurrentUser) -> Question:
    require_role(user, Role.teacher)
    question = owned_question(db, user, question_id)
    changes = payload.model_dump(exclude_unset=True)
    if "topic_id" in changes:
        validate_topic(db, question.course_id, changes["topic_id"])
    for key, value in changes.items():
        setattr(question, key, value)
    db.commit()
    db.refresh(question)
    return question


@router.put("/questions/{question_id}/publications", status_code=204)
def publish_question(question_id: str, payload: PublicationUpdate, db: Db, user: CurrentUser) -> Response:
    require_role(user, Role.teacher)
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="سؤال پیدا نشد")
    owned_course(db, user, question.course_id)
    unique_targets = {target.class_id: target for target in payload.targets}
    for target in unique_targets.values():
        group = owned_class(db, user, target.class_id)
        if group.course_id != question.course_id:
            raise HTTPException(status_code=400, detail="کلاس و سؤال باید متعلق به یک دوره باشند")
    db.execute(delete(QuestionPublication).where(QuestionPublication.question_id == question_id))
    db.flush()
    db.add_all([
        QuestionPublication(
            question_id=question_id,
            class_id=target.class_id,
            published_by=user.id,
            answers_available=target.answers_available,
        )
        for target in unique_targets.values()
    ])
    db.commit()
    return Response(status_code=204)


ALLOWED_IMAGE_TYPES = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"), "WEBP": ("image/webp", ".webp")}


def owned_question(db: Db, user: User, question_id: str) -> Question:
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="سؤال پیدا نشد")
    owned_course(db, user, question.course_id)
    return question


@router.put("/questions/{question_id}/image", response_model=QuestionOut)
async def upload_question_image(
    question_id: str,
    db: Db,
    user: CurrentUser,
    image: UploadFile = File(...),
    alt_text: str = Form(..., min_length=2, max_length=300),
) -> Question:
    require_role(user, Role.teacher)
    question = owned_question(db, user, question_id)
    content = await image.read(settings.max_image_bytes + 1)
    if len(content) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="حجم تصویر بیش از حد مجاز است")
    try:
        decoded = Image.open(io.BytesIO(content))
        decoded.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="فایل تصویر معتبر نیست")
    image_format = decoded.format
    if image_format not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="فقط JPEG، PNG یا WebP مجاز است")
    if decoded.width * decoded.height > settings.max_image_pixels:
        raise HTTPException(status_code=400, detail="ابعاد تصویر بیش از حد مجاز است")
    _, extension = ALLOWED_IMAGE_TYPES[image_format]
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    new_key = f"questions/{question.id}/{secrets.token_hex(12)}{extension}"
    destination = settings.upload_dir / new_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    safe_mode = "RGB" if image_format == "JPEG" else decoded.mode
    if decoded.mode != safe_mode:
        decoded = decoded.convert(safe_mode)
    decoded.save(destination, format=image_format)
    old_path = settings.upload_dir / question.image_key if question.image_key else None
    question.image_key = new_key
    question.image_alt_text = alt_text.strip()
    db.commit()
    if old_path and old_path.exists():
        old_path.unlink()
    db.refresh(question)
    return question


def may_view_question(db: Db, user: User, question: Question) -> bool:
    if user.role == Role.teacher:
        course = db.get(Course, question.course_id)
        return bool(course and course.owner_id == user.id)
    return bool(db.scalar(
        select(QuestionPublication)
        .join(ClassMembership, ClassMembership.class_id == QuestionPublication.class_id)
        .where(
            QuestionPublication.question_id == question.id,
            ClassMembership.student_id == user.id,
            ClassMembership.status == MembershipStatus.active,
        )
    ))


@router.get("/questions/{question_id}/image")
def get_question_image(question_id: str, db: Db, user: CurrentUser) -> FileResponse:
    question = db.get(Question, question_id)
    if not question or not question.image_key or not may_view_question(db, user, question):
        raise HTTPException(status_code=404, detail="تصویر پیدا نشد")
    path = settings.upload_dir / question.image_key
    if not path.is_file():
        raise HTTPException(status_code=404, detail="تصویر پیدا نشد")
    return FileResponse(path)


@router.delete("/questions/{question_id}/image", status_code=204)
def delete_question_image(question_id: str, db: Db, user: CurrentUser) -> Response:
    require_role(user, Role.teacher)
    question = owned_question(db, user, question_id)
    path = settings.upload_dir / question.image_key if question.image_key else None
    question.image_key = None
    question.image_alt_text = None
    db.commit()
    if path and path.exists():
        path.unlink()
    return Response(status_code=204)


class StudentQuestionOut(QuestionOut):
    answers_available: bool


@router.get("/student/questions", response_model=list[StudentQuestionOut])
def student_questions(class_id: str, db: Db, user: CurrentUser) -> list[dict]:
    require_role(user, Role.student)
    if not active_membership(db, user, class_id):
        raise HTTPException(status_code=403, detail="عضویت فعال در این کلاس ندارید")
    rows = db.execute(
        select(Question, QuestionPublication.answers_available)
        .join(QuestionPublication, QuestionPublication.question_id == Question.id)
        .where(QuestionPublication.class_id == class_id)
    ).all()
    result = []
    for question, answers_available in rows:
        data = QuestionOut.model_validate(question).model_dump()
        data["answers_available"] = answers_available
        if not answers_available:
            data["answer_data"] = None
            data["explanation_markdown"] = None
        result.append(data)
    return result


class DownloadRequest(BaseModel):
    class_id: str
    question_ids: list[str] = Field(min_length=1, max_length=100)
    include_answers: bool = False


@router.post("/student/question-downloads")
def download_questions(payload: DownloadRequest, db: Db, user: CurrentUser) -> HTMLResponse:
    require_role(user, Role.student)
    if not active_membership(db, user, payload.class_id):
        raise HTTPException(status_code=403, detail="عضویت فعال در این کلاس ندارید")
    rows = db.execute(
        select(Question, QuestionPublication)
        .join(QuestionPublication, QuestionPublication.question_id == Question.id)
        .where(
            QuestionPublication.class_id == payload.class_id,
            Question.id.in_(set(payload.question_ids)),
        )
    ).all()
    if len(rows) != len(set(payload.question_ids)):
        raise HTTPException(status_code=404, detail="یک یا چند سؤال در این کلاس منتشر نشده است")
    if payload.include_answers and any(not publication.answers_available for _, publication in rows):
        raise HTTPException(status_code=403, detail="پاسخ همه سؤال‌های انتخاب‌شده منتشر نشده است")
    blocks = []
    for index, (question, _) in enumerate(rows, 1):
        image_html = ""
        if question.image_key:
            path = settings.upload_dir / question.image_key
            if path.is_file():
                mime = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(path.suffix, "image/jpeg")
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                image_html = f'<img src="data:{mime};base64,{encoded}" alt="{html.escape(question.image_alt_text or "")}">'
        answer_html = ""
        if payload.include_answers:
            answer_html = f'<section class="answer"><strong>پاسخ:</strong><pre>{html.escape(str(question.answer_data or ""))}</pre><p>{html.escape(question.explanation_markdown or "")}</p></section>'
        blocks.append(f'<article><h2>{index}. {html.escape(question.body_markdown)}</h2>{image_html}{answer_html}</article>')
    document = f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>سؤالات کلاس</title>
    <style>@page{{size:A4;margin:18mm}}body{{font-family:Tahoma,sans-serif;line-height:1.9}}article{{break-inside:avoid;margin-bottom:2rem}}img{{display:block;max-width:100%;max-height:90mm;margin:1rem auto}}.answer{{border-right:4px solid #16877c;padding:.5rem 1rem;background:#f1fbf9}}pre{{white-space:pre-wrap}}</style>
    </head><body><h1>سؤالات کلاس</h1>{''.join(blocks)}</body></html>"""
    headers = {"Content-Disposition": 'attachment; filename="questions.html"'}
    return HTMLResponse(document, headers=headers)


@router.get("/student/notes", response_model=list[NoteOut])
def student_notes(class_id: str, db: Db, user: CurrentUser) -> list[LectureNote]:
    require_role(user, Role.student)
    if not active_membership(db, user, class_id):
        raise HTTPException(status_code=403, detail="عضویت فعال در این کلاس ندارید")
    return list(db.scalars(
        select(LectureNote)
        .join(NotePublication, NotePublication.note_id == LectureNote.id)
        .where(NotePublication.class_id == class_id)
    ))


@router.get("/me/classes", response_model=list[ClassOut])
def my_classes(db: Db, user: CurrentUser) -> list[ClassGroup]:
    require_role(user, Role.student)
    return list(db.scalars(
        select(ClassGroup)
        .join(ClassMembership, ClassMembership.class_id == ClassGroup.id)
        .where(
            ClassMembership.student_id == user.id,
            ClassMembership.status == MembershipStatus.active,
        )
    ))
