import io

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)


def override_db():
    with TestingSession() as session:
        yield session


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def register(role: str, email: str) -> dict:
    response = client.post(
        f"/api/auth/register/{role}",
        json={"email": email, "password": "correct-horse", "display_name": email.split("@")[0]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_teacher_student_class_publication_and_single_image(tmp_path):
    settings.upload_dir = tmp_path
    teacher = register("teacher", "teacher@example.com")
    student = register("student", "student@example.com")
    teacher_headers = auth(teacher["access_token"])
    student_headers = auth(student["access_token"])

    course = client.post("/api/courses", json={"title": "ریاضی نهم"}, headers=teacher_headers).json()
    group = client.post(
        f"/api/courses/{course['id']}/classes",
        json={"name": "کلاس ۹/الف"},
        headers=teacher_headers,
    ).json()
    invite = client.post(f"/api/classes/{group['id']}/invite", headers=teacher_headers).json()
    join_request = client.post(
        f"/api/class-invites/{invite['token']}/request", headers=student_headers
    ).json()

    before_approval = client.get(
        f"/api/student/questions?class_id={group['id']}", headers=student_headers
    )
    assert before_approval.status_code == 403
    approved = client.post(
        f"/api/classes/{group['id']}/join-requests/{join_request['id']}/approve",
        headers=teacher_headers,
    )
    assert approved.status_code == 200

    question = client.post(
        "/api/questions",
        json={
            "course_id": course["id"],
            "type": "essay",
            "body_markdown": "مساحت مربع را توضیح دهید.",
            "answer_data": {"model_answer_markdown": "ضلع × ضلع"},
            "default_points": "1.50",
        },
        headers=teacher_headers,
    ).json()

    image = Image.new("RGB", (16, 16), "navy")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    uploaded = client.put(
        f"/api/questions/{question['id']}/image",
        data={"alt_text": "مربع آبی"},
        files={"image": ("square.png", buffer.getvalue(), "image/png")},
        headers=teacher_headers,
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["has_image"] is True

    published = client.put(
        f"/api/questions/{question['id']}/publications",
        json={"targets": [{"class_id": group["id"], "answers_available": False}]},
        headers=teacher_headers,
    )
    assert published.status_code == 204
    visible = client.get(f"/api/student/questions?class_id={group['id']}", headers=student_headers)
    assert visible.status_code == 200
    assert visible.json()[0]["answer_data"] is None
    assert visible.json()[0]["has_image"] is True

    forbidden_answers = client.post(
        "/api/student/question-downloads",
        json={"class_id": group["id"], "question_ids": [question["id"]], "include_answers": True},
        headers=student_headers,
    )
    assert forbidden_answers.status_code == 403

    no_answers = client.post(
        "/api/student/question-downloads",
        json={"class_id": group["id"], "question_ids": [question["id"]], "include_answers": False},
        headers=student_headers,
    )
    assert no_answers.status_code == 200
    assert "data:image/png;base64" in no_answers.text
    assert "ضلع × ضلع" not in no_answers.text

    client.put(
        f"/api/questions/{question['id']}/publications",
        json={"targets": [{"class_id": group["id"], "answers_available": True}]},
        headers=teacher_headers,
    )
    with_answers = client.post(
        "/api/student/question-downloads",
        json={"class_id": group["id"], "question_ids": [question["id"]], "include_answers": True},
        headers=student_headers,
    )
    assert with_answers.status_code == 200
    assert "ضلع × ضلع" in with_answers.text
