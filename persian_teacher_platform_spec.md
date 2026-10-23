# سامانه مدیریت کلاس، محتوای آموزشی، بانک سؤال و آزمون‌ساز

> **Project specification / implementation brief**  
> Version: 1.1 · October 2026 · Primary product language: **Persian (fa-IR), RTL**

## 1. Product vision

Build a **simple, beautiful, Persian-first teaching and learning web app** with separate teacher and student accounts. Teachers manage courses, class groups, editable lecture notes, question banks and printable exams. They decide which notes and questions are published to students, and to which class groups. Students join a specific class through its invitation link, subject to teacher approval, and can view and download the material made available to that class. Teachers can author questions manually or import AI-generated questions from validated JSON or constrained Markdown. They can select and reorder questions, assign decimal point values, and export polished **A4 Persian PDFs with or without answers**.

### Success criteria

- Create a course and organize its content into subjects/topics.
- Register and sign in as either a teacher or a student through role-appropriate account flows.
- Let a teacher create multiple class groups for one course and manage each class roster independently.
- Let students open a class-specific invitation link, request access and join only after teacher approval.
- Write, edit, preview and download Markdown-based lecture notes.
- Create, duplicate, edit, filter and delete questions of several types.
- Publish selected notes and questions to all or selected classes while keeping drafts private.
- Let students browse and download available question sets, without answers by default and with answers only when the teacher permits it.
- Bulk-import agent-generated questions with validation and a preview/approval step.
- Build, save and reopen an exam with chosen questions, ordering and per-exam marks (`0.25`, `1.5`, `2.75`, etc.).
- Export student exam (no answers) and teacher copy (with answer key) as legible Persian PDFs.
- Deploy a working authenticated product on free services, within their current limits.

## 2. Recommended stack

| Layer | Technology | Reason |
|---|---|---|
| Web app | **React + Vite + TypeScript** | Small, fast and easy to deploy as a static site |
| UI framework | **Mantine** (`@mantine/core`, `@mantine/hooks`, `@mantine/notifications`, `@mantine/modals`) | Cohesive, polished components; first-class RTL support |
| Rich-text authoring | **Mantine RichTextEditor (`@mantine/tiptap`) + Tiptap** | Friendly writing UI; implement explicit Markdown import/export conversion |
| Routing | React Router | Straightforward page navigation |
| Server state | TanStack Query | API fetching, caching and mutation feedback |
| Forms | Mantine `useForm` + Zod (or equivalent schema validation) | Type-safe user-facing validation |
| Icons | Tabler Icons (`@tabler/icons-react`) | Visually consistent with Mantine |
| Backend | **Python + FastAPI + Pydantic** | Easy CRUD and JSON import APIs |
| Persistence | **PostgreSQL on Supabase**, SQLAlchemy 2, Alembic | Durable relational storage and migrations |
| Authentication | Supabase Auth or secure app-side authentication | Support teacher/student accounts, secure registration and role-based access |
| PDF | Server-rendered HTML/CSS → WeasyPrint; evaluate Chromium-based rendering if needed | Printable A4; verify RTL/math quality through actual tests |
| Math | KaTeX/MathJax in web preview; pre-render math to PDF-compatible HTML/SVG | Math in notes and exam PDFs |
| Hosting | **Render Static Site + Render Free Web Service + Supabase Free** | Simple GitHub-based deployments with free-tier constraints |

### Mantine RTL setup

- Set `<html lang="fa" dir="rtl">` in `frontend/index.html`.
- Wrap the application with `DirectionProvider` (RTL) and `MantineProvider`.
- Use **Vazirmatn** for UI and generated PDF output, embedding the font for PDF. Keep fonts legally sourced; don't commit restricted fonts.
- Use Persian navigation, field names, errors, toasts, empty states, confirmation dialogs and PDF labels; do not leave accidental English text.
- Check bidirectional text carefully for dates, email addresses, Latin formulas, code and numbers; set local `dir="ltr"` on those fragments when required.

```tsx
import { DirectionProvider, MantineProvider, createTheme } from '@mantine/core';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import '@mantine/tiptap/styles.css';

const theme = createTheme({ fontFamily: 'Vazirmatn, sans-serif', primaryColor: 'indigo' });

export function Root() {
  return (
    <DirectionProvider initialDirection="rtl">
      <MantineProvider theme={theme}>
        <App />
      </MantineProvider>
    </DirectionProvider>
  );
}
```

> `@mantine/tiptap` supplies a Tiptap UI, **not automatic Markdown persistence**. Implement Markdown conversion deliberately, and test round trips (Markdown → editor → Markdown) before relying on it for storage.

## 3. UX and screens

**Design direction:** calm, modern, teacher- and student-friendly academic dashboard; a restrained indigo/teal palette, generous whitespace, rounded cards and clear hierarchy. Mobile responsive, but optimize lecture authoring/exam assembly for desktop first. Use Mantine `AppShell`, `NavLink`, `Card`, `DataTable` equivalent (`Table` initially), `Drawer`, `Modal`, `Stepper`, `Badge`, `MultiSelect`, `NumberInput`, `Dropzone` (if used), `Notifications`.

**Teacher navigation (all Persian):**

- `داشبورد` — recent courses, notes and exams
- `دوره‌ها` — courses, create/edit/archive
- `کلاس‌ها` — class groups, invitation links, join requests and rosters
- `موضوعات` — topics within a course
- `جزوه‌ها` — author/import/preview/download
- `بانک سؤالات` — filter, create, edit, import and select
- `آزمون‌ساز` — assemble and score exams
- `آزمون‌های ذخیره‌شده` — reopen, duplicate, export
- `تنظیمات` — profile, exam header/defaults

**Student navigation (all Persian):**

- `داشبورد` — enrolled classes and recently published material
- `کلاس‌های من` — approved memberships and pending join requests
- `جزوه‌ها` — notes published to the student's classes
- `سؤالات` — available questions and permitted download variants
- `تنظیمات` — profile and account settings

**Public authentication screens:**

- `ورود` — sign in for both roles
- `ثبت‌نام دانش‌آموز` — student registration
- `ثبت‌نام معلم` — dedicated teacher registration portal with email verification and any configured teacher-verification step
- `پیوستن به کلاس` — class invitation landing page; preserves the target class through sign-up/sign-in

**Core flows:**

1. **Course → Topic → Note:** create a course, add a topic, author a lecture note, save and export to PDF.
2. **Course → Topic → Question:** select type, enter question, answers and default points; validate and save.
3. **Import:** upload/paste JSON or structured Markdown → validate → view questions and errors → choose destination topic → approve import.
4. **Exam:** choose course → filter/select questions → reorder → override points → preview → save → export student PDF and teacher PDF.
5. **Create class:** choose a course → create a named class group → generate/revoke a class-specific invitation link → review join requests → approve/reject/remove students.
6. **Publish content:** choose a note or one or more questions → select target classes → optionally permit answer downloads → publish/unpublish.
7. **Student joins and studies:** open invitation link → register/sign in → request to join → wait for approval → browse published notes/questions → download a question packet without answers or, when the teacher permits it, with answers.

Use search, empty states, save feedback, delete confirmation and loading/error states throughout. Avoid a complicated admin system.

## 4. Accounts, classes and content model

### 4.1 Accounts and roles

Every person has an authenticated account with exactly one primary role in v1: `teacher` or `student`. Store the role in an application-owned profile record, not only in client-editable authentication metadata. Teachers can create and edit teaching content; students have read-only access to content explicitly published to a class in which they have an approved membership.

The teacher registration portal collects at least name, email and password, verifies the email address, records acceptance of the terms/privacy notice and creates a teacher profile. If teacher verification is required for launch, use a small `pending → active/rejected` status workflow; a pending teacher cannot create classes or publish content. Student registration is separate and must not allow a student to self-assign the teacher role. Document the operational owner of teacher approvals before enabling verification in production.

### 4.2 Courses and class groups

A course is reusable academic content owned by one teacher. A course may contain multiple class groups—for example, five separately managed groups of the same course. A class has a teacher owner, course, name/section, optional school name, optional academic year and status.

Each class can have one active invitation token/link at a time. Store only a hash of the token, allow the teacher to rotate or revoke it, and optionally support an expiry date and maximum uses. Opening the link identifies the class but does not grant access. An authenticated student submits a join request; the owning teacher approves or rejects it. Approved students become class members. Teachers can view pending requests, approve/reject them, remove members and regenerate the link. Membership and request uniqueness must prevent duplicates for the same student/class.

### 4.3 Topics

A course has a title, optional description, teacher owner and status. Each course contains ordered topics; notes and questions belong to a course and topic. Course/topic deletion needs referential-integrity protection or a soft-delete/archive strategy. A student does not gain access to every course item merely by joining a class; publication is explicit.

### 4.4 Lecture notes

Each note has `title`, `course_id`, `topic_id`, `markdown_content`, timestamps and optional sort order. Notes start as private drafts. A teacher can publish a note to one or more class groups belonging to the same course and can later unpublish it. Support headings, emphasis, lists, tables, links, fenced code and inline/block LaTeX. Preview before save and before export. Markdown is the canonical stored format; sanitize rendered HTML. Support pasted Markdown and `.md` upload. Make images/attachments a later feature unless an object-storage strategy is defined.

### 4.5 Question bank types

| Type (API enum) | Persian UI | Answer model |
|---|---|---|
| `essay` | تشریحی | Model answer / rubric (Markdown) |
| `single_choice` | چهارگزینه‌ای | Exactly one option ID |
| `multiple_choice` | چندپاسخی | One or more correct option IDs |
| `fill_blank` | جای خالی | Ordered blanks with accepted answers |
| `true_false` | درست / نادرست | Boolean + optional explanation |
| `short_answer` | پاسخ کوتاه | One or more accepted short answers |
| `matching` | وصل‌کردنی | Pair mappings |
| `ordering` (optional) | مرتب‌سازی | Ordered item IDs |

Questions have: `id`, `course_id`, `topic_id`, `type`, `body_markdown`, optional `image_key`, `image_alt_text`, `options` (JSONB), `answer_data` (JSONB), `explanation_markdown`, `default_points` (NUMERIC), `difficulty`, `tags`, `created_at`, `updated_at`. Each question may have **at most one image**. Teachers can upload, replace or remove it and must provide useful Persian alternative text when an image is present. Questions remain private until explicitly published to one or more classes. Keep answers **separate** from the rendered question body so student views and no-answer exports can never accidentally reveal them. Question editing should have a live preview and a duplicate action.

Store question images in private object storage rather than the application filesystem. Accept only validated JPEG, PNG or WebP files within a configured size and pixel limit; verify the decoded file type, generate a safe storage key and strip unsafe metadata. Serve images through an authorized endpoint or short-lived signed URL so only the owning teacher or a student with access to an active publication can view them. Include the image in both permitted question PDF variants.

### 4.6 Student publication and downloads

Use explicit publication records for notes and questions rather than a single global `is_visible` flag. Each publication identifies the resource, target class, publishing teacher, publish time and status. A question publication also has `answers_available` (default `false`). This supports different visibility rules across five or more classes in one course without duplicating content.

Students can list and view only publications targeting classes where their membership is approved. They can download selected available questions as a polished PDF without answers. The “with answers” download option appears and succeeds only when every selected question is published with `answers_available = true`; enforce this again on the server. Downloads must not expose drafts, other classes, answer JSON, model answers or explanations through API payloads, HTML, PDF metadata or hidden text. Teachers can preview both variants before publishing.

### 4.7 Exam builder

An exam has `title`, `course_id`, optional instructions, date/duration/header settings and ordered question entries. Each entry stores a **DECIMAL / NUMERIC** `assigned_points`, not a float. Support fractional increments (e.g. `0.25`) and configurable precision; calculate totals using Python `Decimal`/PostgreSQL `NUMERIC`. Reordering by drag-and-drop (with accessible move-up/down controls) should not affect question bank order.

**Snapshot requirement:** save each selected question's printable body, options, answers and explanation as a snapshot in `exam_questions` at the time of adding/publishing. This keeps existing exams stable if bank questions later change. Decide explicitly whether a teacher can refresh a snapshot from the latest bank item.

### 4.8 Exam PDF variants

**Student copy (`بدون پاسخنامه`):** school/name fields, title, course, optional date/duration, total points, numbered questions, per-question points and space for essays; no answer keys, solution text or hidden answer metadata.

**Teacher copy (`همراه پاسخنامه`):** same question order, scores, clearly distinguished model answers/correct options and explanations; optional separate answer-key section.

Generate on demand; do not assume Render's local filesystem is persistent. A4 sizing, pagination, footer/page numbers, correct Persian shaping, embedded font, LTR snippets for math, and prevention of awkward page breaks should be validated against representative real PDFs.

## 5. AI import contracts

**Canonical interface: JSON.** Markdown remains useful for human-friendly notes and an optional constrained import format. No built-in LLM service or automatic question generation in v1.

### Sample JSON

```json
{
  "schema_version": "1.0",
  "course_id": "<existing-course-uuid>",
  "topic_id": "<existing-topic-uuid>",
  "questions": [
    {
      "type": "single_choice",
      "body_markdown": "حاصل $2 + 3$ چیست؟",
      "options": [
        {"id": "a", "text": "۴"},
        {"id": "b", "text": "۵"},
        {"id": "c", "text": "۶"},
        {"id": "d", "text": "۷"}
      ],
      "answer_data": {"correct_option_ids": ["b"]},
      "explanation_markdown": "چون $2 + 3 = 5$ است.",
      "default_points": "1.5",
      "difficulty": "easy",
      "tags": ["جمع", "اعداد"]
    },
    {
      "type": "essay",
      "body_markdown": "مراحل حل یک معادلهٔ خطی را توضیح دهید.",
      "options": null,
      "answer_data": {"model_answer_markdown": "ابتدا ..."},
      "explanation_markdown": null,
      "default_points": "2.25",
      "difficulty": "medium",
      "tags": ["معادلات"]
    }
  ]
}
```

Accept a numeric JSON points value too, but normalize immediately to `Decimal` from its string representation. Validate positive/zero score policy, unique option IDs, valid answer IDs, topic ownership and supported question types.

### Constrained Markdown alternative

```md
## سؤال: ۱
نوع: single_choice
موضوع: معادلات
بارم: 1.5

حاصل $2 + 3$ چیست؟

- [a] ۴
- [b] ۵
- [c] ۶
- [d] ۷

پاسخ: b
توضیح: حاصل برابر پنج است.
```

**Important:** define and test a strict grammar for Markdown imports rather than trying to parse all free-form Markdown. The import endpoint should produce per-item validation errors and a preview, and only write questions after explicit user approval. Enforce limits on import file size and question count; use transactions for approved batch insertion. Prevent duplicates via preview/confirmation rather than destructive implicit overwrites.

## 6. Database tables

- `users`: `id`, auth identity, email, `role` (`teacher`/`student`), `display_name`, `status`, email-verification/terms timestamps and audit timestamps. The backend controls role assignment.
- `courses`: `id`, `owner_id`, `title`, `description`, `status`, timestamps.
- `classes`: `id`, `course_id`, `owner_id`, `name`, `school_name`, `academic_year`, `status`, timestamps.
- `class_invites`: `id`, `class_id`, `token_hash`, `expires_at`, `max_uses`, `use_count`, `revoked_at`, timestamps. Never store or log the plain invitation token after creation.
- `class_join_requests`: `id`, `class_id`, `student_id`, `status` (`pending`/`approved`/`rejected`/`cancelled`), `reviewed_by`, `reviewed_at`, timestamps.
- `class_memberships`: `id`, `class_id`, `student_id`, `status` (`active`/`removed`), `joined_at`, `removed_at`, with one current membership per student/class.
- `topics`: `id`, `course_id`, `title`, `description`, `sort_order`.
- `lecture_notes`: `id`, `course_id`, `topic_id`, `title`, `markdown_content`, timestamps.
- `questions`: `id`, `course_id`, `topic_id`, `type`, `body_markdown`, `image_key` (nullable), `image_alt_text` (nullable), `options JSONB`, `answer_data JSONB`, `explanation_markdown`, `default_points NUMERIC(8,2)` (adjust precision if desired), `difficulty`, tags, timestamps. Enforce at most one image per question in the model and API.
- `note_publications`: `id`, `note_id`, `class_id`, `published_by`, `published_at`, `unpublished_at`, unique active publication per note/class.
- `question_publications`: `id`, `question_id`, `class_id`, `published_by`, `answers_available BOOLEAN DEFAULT FALSE`, `published_at`, `unpublished_at`, unique active publication per question/class.
- `exams`: `id`, `course_id`, `title`, `instructions`, `header_settings JSONB`, timestamps.
- `exam_questions`: `id`, `exam_id`, `source_question_id` (nullable reference), `position`, `assigned_points NUMERIC(8,2)`, `question_snapshot JSONB`.

Add indexes on common foreign keys, invitation-token hashes, join-request status, active memberships, publication class/resource pairs and question filters. Enforce that classes and publication targets belong to the same course as their content. Add ownership, role, membership and publication authorization to every query and mutation; authentication alone is insufficient. Use Alembic for migrations.

## 7. Suggested REST API

```text
POST   /api/auth/...                       # depends on chosen auth provider
POST   /api/auth/register/student
POST   /api/auth/register/teacher          # dedicated teacher registration flow
GET    /api/courses
POST   /api/courses
GET    /api/courses/{id}
PATCH  /api/courses/{id}
DELETE /api/courses/{id}
GET    /api/courses/{id}/classes
POST   /api/courses/{id}/classes
GET    /api/classes/{id}
PATCH  /api/classes/{id}
POST   /api/classes/{id}/invite            # create or rotate invitation link
DELETE /api/classes/{id}/invite            # revoke active invitation link
GET    /api/classes/{id}/join-requests
POST   /api/classes/{id}/join-requests/{request_id}/approve
POST   /api/classes/{id}/join-requests/{request_id}/reject
GET    /api/classes/{id}/students
DELETE /api/classes/{id}/students/{student_id}
GET    /api/class-invites/{token}           # safe public invitation summary
POST   /api/class-invites/{token}/request   # authenticated student requests access
GET    /api/me/classes                      # approved/pending classes for student
GET    /api/courses/{id}/topics
POST   /api/courses/{id}/topics
PATCH  /api/topics/{id}
DELETE /api/topics/{id}
GET    /api/notes?course_id=&topic_id=
POST   /api/notes
GET    /api/notes/{id}
PATCH  /api/notes/{id}
DELETE /api/notes/{id}
GET    /api/notes/{id}/pdf
PUT    /api/notes/{id}/publications         # teacher replaces selected class targets
GET    /api/questions?course_id=&topic_id=&type=&difficulty=&q=
POST   /api/questions
GET    /api/questions/{id}
PATCH  /api/questions/{id}
DELETE /api/questions/{id}
PUT    /api/questions/{id}/image            # upload or replace the single image
GET    /api/questions/{id}/image            # authorized image response or signed redirect
DELETE /api/questions/{id}/image
PUT    /api/questions/{id}/publications     # targets plus answers_available per class
POST   /api/question-imports/preview       # parse and validate, no DB write
POST   /api/question-imports/commit        # commit validated reviewed items
GET    /api/exams?course_id=
POST   /api/exams
GET    /api/exams/{id}
PATCH  /api/exams/{id}
DELETE /api/exams/{id}
GET    /api/exams/{id}/pdf?include_answers=false
GET    /api/exams/{id}/pdf?include_answers=true
GET    /api/student/notes?class_id=&topic_id=
GET    /api/student/notes/{id}
GET    /api/student/notes/{id}/pdf
GET    /api/student/questions?class_id=&topic_id=&type=&q=
POST   /api/student/question-downloads      # selected IDs; include_answers is authorized server-side
```

Pydantic models should validate per-question-type answer shapes. Use opaque, high-entropy invitation tokens and rate-limit invitation lookup, registration and join requests. Use pagination for list endpoints as the bank grows. Student response schemas must omit all answer fields unless the relevant publication permits answers. Return localized UI messages from frontend translation strings rather than relying on raw server exceptions.

## 8. Repository layout

```text
teacher-platform/
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── app/             # routes, theme, providers
│   │   ├── components/      # shared Mantine components
│   │   ├── features/        # auth, courses, classes, memberships, notes, questions, exams
│   │   ├── lib/             # API client and utilities
│   │   └── styles/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # configuration, auth
│   │   ├── db/              # session and models
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/        # import, Markdown, image storage, PDF
│   │   └── templates/       # print HTML/CSS
│   ├── alembic/
│   ├── requirements.txt
│   └── alembic.ini
├── docs/
│   ├── question-import-schema.json
│   └── examples/
├── .gitignore
└── README.md
```

## 9. Free deployment plan

### Supabase PostgreSQL

1. Create a free Supabase project and choose an appropriate EU region.
2. Configure authentication (if using Supabase Auth) and obtain the PostgreSQL **session pooler** connection string for Render IPv4 compatibility.
3. Store database credentials only in backend environment variables; require SSL.
4. Run Alembic migrations; seed a sample course and sample question set.
5. Set up a periodic **manual data export/backup** workflow. Free plans may pause inactive projects; check the current free-plan policies before launch.

### Render backend

1. Connect GitHub repo and create a **Web Service**, instance type **Free**, root directory `backend`.
2. Build command: `pip install -r requirements.txt`.
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Environment variables: `DATABASE_URL`, auth/JWT settings, `FRONTEND_ORIGIN`, other secrets (never commit `.env`).
5. Configure restricted CORS; confirm DB health, auth, migrations and PDF font dependencies in deployment.
6. Free services sleep when idle; expect cold starts. Do not store uploaded files or generated PDFs on ephemeral disk permanently.

### Render frontend

1. Create **Static Site**, GitHub repo, root directory `frontend`.
2. Build command: `npm ci && npm run build`; publish directory: `dist`.
3. Provide `VITE_API_BASE_URL` pointing to the backend's HTTPS URL.
4. Enable SPA fallback/rewrite to `/index.html` if using client-side routes; configure `FRONTEND_ORIGIN` on backend.
5. Test all pages, Persian RTL and real student/answer PDFs at deployed URLs.

**Budget:** target €0/month within the current free allowances, not a guaranteed permanent zero-cost SLA. Render free web-service sleep, monthly limits and Supabase project pausing/storage limits are acceptable for a hobby/MVP, not uninterrupted school-critical production service.

## 10. Security and quality

- Require login for private content read/write/export. Scope every teacher mutation to owned resources, and every student read/download to an active class membership and active publication.
- Enforce role permissions on the server. Never trust a role, teacher ID, class ID or `answers_available` decision supplied only by the client.
- Prevent privilege escalation through sign-up: student registration cannot create a teacher account, and any teacher-verification status is application-controlled.
- Store only hashed class invitation tokens; support expiry, rotation and revocation; rate-limit token lookup and join requests; do not expose student rosters publicly.
- Ensure approving, rejecting or removing a student affects only the selected class, even when the same course has several class groups.
- Sanitize Markdown/HTML and protect PDF rendering from untrusted content or remote resource fetching.
- Keep secret connection strings server-side, never in `VITE_*` variables.
- Enforce import limits, input validation, unique option IDs, one validated image per question and consistent exam totals.
- Add database migrations and tests for all answer types and decimal marks.
- Snapshot exam questions so later bank changes do not alter a saved exam.
- Verify **student views and PDFs contain no answer information** unless explicitly allowed for that class publication, including hidden text, serialized API fields and metadata.
- Ensure PDFs render Persian joining correctly, math correctly and do not clip RTL text. Test long essays, multi-page exams, options, tables and fractional marks.

## 11. Delivery phases

**Phase 1 — Accounts and working foundation:** Vite/React/Mantine RTL shell, teacher/student authentication and registration, server-controlled roles, FastAPI, Supabase, course/topic CRUD, deployed hello-world integration.

**Phase 2 — Classes and enrollment:** class-group CRUD, secure invitation links, join requests, teacher approval/rejection/removal and separate rosters per class.

**Phase 3 — Notes and publication:** Markdown persisted in DB, Mantine/Tiptap editor and conversion, import/preview, notes PDF, class-specific publish/unpublish and student note portal.

**Phase 4 — Question bank and student downloads:** type-specific manual forms, answer model, optional single-image upload/replace/remove, filtering/search, editing/duplication, JSON import preview/commit, constrained Markdown import, class-specific publication and question PDF downloads with answer authorization.

**Phase 5 — Exams:** select, reorder, decimal scoring, total, snapshots, save/reopen/duplicate.

**Phase 6 — Print and polish:** accurate student/teacher PDFs, exam header template, responsive layouts, validation, backups and end-to-end tests.

### Explicitly out of scope (v1)

Online exam taking; student submissions; automatic grading; analytics; attendance; payments; parent accounts; school-wide administrators/organizations; co-teaching or collaborative editing; internal LLM generation; sophisticated file storage; and complex background-job infrastructure.

## 12. Build acceptance test

A teacher registers through the teacher portal, verifies the account, logs in and creates `ریاضی پایه نهم` with five separate class groups. The teacher generates a link for one class. A student registers through that link and requests access; the teacher sees the request in the correct class and approves it. The student cannot access any material yet. The teacher adds topics `معادلات` and `هندسه`, authors a note with RTL text and math, imports a reviewed JSON question batch, manually edits a multiple-choice and an essay question, and publishes selected notes/questions only to that class. The student can view and download only those items and cannot see answers. After the teacher enables answers for one published question, the permitted answer variant becomes available without exposing answers for other questions or classes. The teacher also filters by topic, makes an exam from selected questions, gives them `0.25`, `1.5`, `2.75` marks, sees the correct sum, saves/reopens the exam, and successfully downloads both Persian A4 exam versions—one with answers and one without—from the deployed HTTPS site.

## 13. Official references

- Mantine RTL: https://mantine.dev/styles/rtl/
- Mantine Tiptap editor: https://mantine.dev/x/tiptap/
- FastAPI: https://fastapi.tiangolo.com/
- Render: https://render.com/docs
- Supabase: https://supabase.com/docs

---

**Implementation principle:** ship a reliable, approachable Persian teaching tool. Favor working end-to-end workflows and excellent exam PDF fidelity over extra features.
