from __future__ import annotations

import argparse
import hashlib
import mimetypes
import re
from pathlib import Path

from sqlalchemy import delete, select

from app.db import Base, SessionLocal, engine
from app.models import ContentImport, Course, LectureNote, NoteImage, Role, Topic, User, uuid_str


COURSE_TITLES = {
    (7, "biology"): "زیست شناسی هفتم",
    (9, "biology"): "زیست شناسی نهم",
    (7, "geology"): "زمین شناسی هفتم",
    (9, "geology"): "زمین شناسی نهم",
}
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^)]*[\"'])?\)")
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def strip_frontmatter(source: str) -> str:
    if source.startswith("---\n"):
        closing = source.find("\n---\n", 4)
        if closing >= 0:
            return source[closing + 5 :].lstrip()
    return source


def grade_for(path: Path) -> int:
    lowered = str(path).lower()
    if "haftom" in lowered or "هفتم" in lowered:
        return 7
    if "nohom" in lowered or "نهم" in lowered:
        return 9
    raise ValueError(f"Could not infer grade 7 or 9 from {path}")


def chapter_for(path: Path, source: str) -> int:
    match = re.match(r"(\d+)", path.name)
    if match:
        return int(match.group(1))
    heading = HEADING_RE.search(source)
    if heading:
        number = re.search(r"فصل\s+([۰-۹0-9]+)", heading.group(1))
        if number:
            return int(number.group(1).translate(PERSIAN_DIGITS))
    raise ValueError(f"Could not infer chapter number from {path}")


def title_for(source: str, path: Path) -> str:
    match = HEADING_RE.search(source)
    return match.group(1).strip() if match else path.stem.replace("-", " ")


def content_hash(source: bytes, image_paths: list[Path]) -> str:
    digest = hashlib.sha256(source)
    for path in image_paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def resolve_image(note_path: Path, raw_target: str, content_root: Path) -> Path:
    target = raw_target.split("#", 1)[0].split("?", 1)[0]
    candidate = (note_path.parent / target).resolve()
    if content_root.resolve() not in candidate.parents or not candidate.is_file():
        raise ValueError(f"Missing or unsafe image reference {raw_target!r} in {note_path}")
    return candidate


def clear_application_content(session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != "users":
            session.execute(delete(table))
    session.commit()


def ensure_courses(session, teacher: User) -> dict[tuple[int, str], Course]:
    courses: dict[tuple[int, str], Course] = {}
    for key, title in COURSE_TITLES.items():
        course = session.scalar(select(Course).where(Course.owner_id == teacher.id, Course.title == title))
        if not course:
            subject = "زیست‌شناسی" if key[1] == "biology" else "زمین‌شناسی"
            course = Course(
                owner_id=teacher.id,
                title=title,
                description=f"جزوه‌های {subject} پایهٔ {'هفتم' if key[0] == 7 else 'نهم'}",
            )
            session.add(course)
            session.flush()
        courses[key] = course
    return courses


def import_note(session, note_path: Path, content_root: Path, courses: dict[tuple[int, str], Course]) -> str:
    raw_bytes = note_path.read_bytes()
    source = strip_frontmatter(raw_bytes.decode("utf-8"))
    grade = grade_for(note_path)
    chapter = chapter_for(note_path, source)
    subject = "geology" if chapter in {6, 7} else "biology"
    course = courses[(grade, subject)]
    source_key = note_path.relative_to(content_root).as_posix()

    refs: list[tuple[str, str, Path]] = []
    for match in IMAGE_RE.finditer(source):
        refs.append((match.group(0), match.group(1).strip(), resolve_image(note_path, match.group(2), content_root)))
    fingerprint = content_hash(raw_bytes, [item[2] for item in refs])
    imported = session.scalar(select(ContentImport).where(ContentImport.source_path == source_key))
    if imported and imported.source_hash == fingerprint:
        return "skipped"

    topic = session.scalar(
        select(Topic).where(Topic.course_id == course.id, Topic.sort_order == chapter)
    )
    if not topic:
        topic = Topic(course_id=course.id, title=f"فصل {chapter}", sort_order=chapter)
        session.add(topic)
        session.flush()

    note = session.get(LectureNote, imported.note_id) if imported else None
    if not note:
        note = LectureNote(course_id=course.id, topic_id=topic.id, title=title_for(source, note_path))
        session.add(note)
        session.flush()
    else:
        session.execute(delete(NoteImage).where(NoteImage.note_id == note.id))
        note.course_id = course.id
        note.topic_id = topic.id
        note.title = title_for(source, note_path)

    rewritten = source
    replacements: dict[str, str] = {}
    for full_match, alt_text, image_path in refs:
        image_id = uuid_str()
        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        data = image_path.read_bytes()
        if not mime_type.startswith("image/") or len(data) > MAX_IMAGE_BYTES:
            raise ValueError(f"Unsupported or oversized image: {image_path}")
        session.add(NoteImage(
            id=image_id,
            note_id=note.id,
            filename=image_path.name,
            mime_type=mime_type,
            alt_text=alt_text or None,
            data=data,
        ))
        replacements[full_match] = f"![{alt_text}](/api/notes/{note.id}/images/{image_id})"
    for original, replacement in replacements.items():
        rewritten = rewritten.replace(original, replacement)
    note.markdown_content = rewritten

    if imported:
        imported.note_id = note.id
        imported.source_hash = fingerprint
    else:
        session.add(ContentImport(source_path=source_key, source_hash=fingerprint, note_id=note.id))
    return "updated" if imported else "created"


def main() -> None:
    parser = argparse.ArgumentParser(description="Import local Markdown lecture notes and images into the database.")
    parser.add_argument("--content-dir", type=Path, default=Path(__file__).resolve().parents[2] / "content")
    parser.add_argument("--teacher-email", required=True, help="Teacher account that will own the four courses.")
    parser.add_argument("--reset", action="store_true", help="Delete all classes, courses, notes and questions first; users remain.")
    args = parser.parse_args()
    content_root = args.content_dir.resolve()
    note_paths = sorted(content_root.glob("lecture-notes/*/chapters/*.md"))
    if not note_paths:
        raise SystemExit(f"No chapter Markdown files found under {content_root}")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        teacher = session.scalar(select(User).where(User.email == args.teacher_email.lower(), User.role == Role.teacher))
        if not teacher:
            raise SystemExit(f"Teacher account not found: {args.teacher_email}")
        if args.reset:
            clear_application_content(session)
        courses = ensure_courses(session, teacher)
        totals = {"created": 0, "updated": 0, "skipped": 0}
        try:
            for path in note_paths:
                totals[import_note(session, path, content_root, courses)] += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
    print(
        f"Imported {len(note_paths)} notes for {args.teacher_email}: "
        f"{totals['created']} created, {totals['updated']} updated, {totals['skipped']} unchanged."
    )


if __name__ == "__main__":
    main()
