# سامانه مدیریت دوره، بانک سؤال و آزمون‌ساز معلمان

> **Project specification / implementation brief**  
> Version: 1.0 · October 2026 · Primary product language: **Persian (fa-IR), RTL**

## 1. Product vision

Build a **simple, beautiful, Persian-first web app for teachers** to manage courses, topics, editable lecture notes, question banks and printable exams. Teachers can author questions manually or import AI-generated questions from validated JSON or constrained Markdown. They can select and reorder questions, assign decimal point values, and export polished **A4 Persian PDFs with or without answers**. Keep v1 intentionally small: one teacher/account initially, with ownership-ready models for later multi-teacher support.

### Success criteria

- Create a course and organize its content into subjects/topics.
- Write, edit, preview and download Markdown-based lecture notes.
- Create, duplicate, edit, filter and delete questions of several types.
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
| Authentication | Supabase Auth or secure app-side authentication | Protect teacher content and write APIs |
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

**Design direction:** calm, modern, teacher-friendly academic dashboard; a restrained indigo/teal palette, generous whitespace, rounded cards and clear hierarchy. Mobile responsive, but optimize lecture authoring/exam assembly for desktop first. Use Mantine `AppShell`, `NavLink`, `Card`, `DataTable` equivalent (`Table` initially), `Drawer`, `Modal`, `Stepper`, `Badge`, `MultiSelect`, `NumberInput`, `Dropzone` (if used), `Notifications`.

**Navigation (all Persian):**

- `داشبورد` — recent courses, notes and exams
- `دوره‌ها` — courses, create/edit/archive
- `موضوعات` — topics within a course
- `جزوه‌ها` — author/import/preview/download
- `بانک سؤالات` — filter, create, edit, import and select
- `آزمون‌ساز` — assemble and score exams
- `آزمون‌های ذخیره‌شده` — reopen, duplicate, export
- `تنظیمات` — profile, exam header/defaults

**Core flows:**

1. **Course → Topic → Note:** create a course, add a topic, author a lecture note, save and export to PDF.
2. **Course → Topic → Question:** select type, enter question, answers and default points; validate and save.
3. **Import:** upload/paste JSON or structured Markdown → validate → view questions and errors → choose destination topic → approve import.
4. **Exam:** choose course → filter/select questions → reorder → override points → preview → save → export student PDF and teacher PDF.

Use search, empty states, save feedback, delete confirmation and loading/error states throughout. Avoid a complicated admin system.

## 4. Content model

### 4.1 Courses and topics

A course has a title, optional description, teacher owner and status. Each course contains ordered topics; notes and questions belong to a course and topic. Course/topic deletion needs referential-integrity protection or a soft-delete/archive strategy.

### 4.2 Lecture notes

Each note has `title`, `course_id`, `topic_id`, `markdown_content`, timestamps and optional sort order. Support headings, emphasis, lists, tables, links, fenced code and inline/block LaTeX. Preview before save and before export. Markdown is the canonical stored format; sanitize rendered HTML. Support pasted Markdown and `.md` upload. Make images/attachments a later feature unless an object-storage strategy is defined.

### 4.3 Question bank types

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

Questions have: `id`, `course_id`, `topic_id`, `type`, `body_markdown`, `options` (JSONB), `answer_data` (JSONB), `explanation_markdown`, `default_points` (NUMERIC), `difficulty`, `tags`, `created_at`, `updated_at`. Keep answers **separate** from the rendered question body so student exports can never accidentally reveal them. Question editing should have a live preview and a duplicate action.

### 4.4 Exam builder

An exam has `title`, `course_id`, optional instructions, date/duration/header settings and ordered question entries. Each entry stores a **DECIMAL / NUMERIC** `assigned_points`, not a float. Support fractional increments (e.g. `0.25`) and configurable precision; calculate totals using Python `Decimal`/PostgreSQL `NUMERIC`. Reordering by drag-and-drop (with accessible move-up/down controls) should not affect question bank order.

**Snapshot requirement:** save each selected question's printable body, options, answers and explanation as a snapshot in `exam_questions` at the time of adding/publishing. This keeps existing exams stable if bank questions later change. Decide explicitly whether a teacher can refresh a snapshot from the latest bank item.

### 4.5 Exam PDF variants

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

- `users`: `id`, auth identity, email, timestamps.
- `courses`: `id`, `owner_id`, `title`, `description`, `status`, timestamps.
- `topics`: `id`, `course_id`, `title`, `description`, `sort_order`.
- `lecture_notes`: `id`, `course_id`, `topic_id`, `title`, `markdown_content`, timestamps.
- `questions`: `id`, `course_id`, `topic_id`, `type`, `body_markdown`, `options JSONB`, `answer_data JSONB`, `explanation_markdown`, `default_points NUMERIC(8,2)` (adjust precision if desired), `difficulty`, tags, timestamps.
- `exams`: `id`, `course_id`, `title`, `instructions`, `header_settings JSONB`, timestamps.
- `exam_questions`: `id`, `exam_id`, `source_question_id` (nullable reference), `position`, `assigned_points NUMERIC(8,2)`, `question_snapshot JSONB`.

Add indexes on common foreign keys and question filters. Add ownership authorization to every query and mutation; authentication alone is insufficient. Use Alembic for migrations.

## 7. Suggested REST API

```text
POST   /api/auth/...                       # depends on chosen auth provider
GET    /api/courses
POST   /api/courses
GET    /api/courses/{id}
PATCH  /api/courses/{id}
DELETE /api/courses/{id}
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
GET    /api/questions?course_id=&topic_id=&type=&difficulty=&q=
POST   /api/questions
GET    /api/questions/{id}
PATCH  /api/questions/{id}
DELETE /api/questions/{id}
POST   /api/question-imports/preview       # parse and validate, no DB write
POST   /api/question-imports/commit        # commit validated reviewed items
GET    /api/exams?course_id=
POST   /api/exams
GET    /api/exams/{id}
PATCH  /api/exams/{id}
DELETE /api/exams/{id}
GET    /api/exams/{id}/pdf?include_answers=false
GET    /api/exams/{id}/pdf?include_answers=true
```

Pydantic models should validate per-question-type answer shapes. Use pagination for list endpoints as the bank grows. Return localized UI messages from frontend translation strings rather than relying on raw server exceptions.

## 8. Repository layout

```text
teacher-platform/
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── app/             # routes, theme, providers
│   │   ├── components/      # shared Mantine components
│   │   ├── features/        # courses, topics, notes, questions, exams
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
│   │   ├── services/        # import, Markdown, PDF
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

- Require login for content read/write/export; scope every course, topic, note, question and exam to the authorized teacher.
- Sanitize Markdown/HTML and protect PDF rendering from untrusted content or remote resource fetching.
- Keep secret connection strings server-side, never in `VITE_*` variables.
- Enforce import limits, input validation, unique option IDs and consistent exam totals.
- Add database migrations and tests for all answer types and decimal marks.
- Snapshot exam questions so later bank changes do not alter a saved exam.
- Verify **student PDFs contain no answer information** (including hidden text / metadata).
- Ensure PDFs render Persian joining correctly, math correctly and do not clip RTL text. Test long essays, multi-page exams, options, tables and fractional marks.

## 11. Delivery phases

**Phase 1 — Working foundation:** Vite/React/Mantine RTL shell, authentication, FastAPI, Supabase, course/topic CRUD, deployed hello-world integration.

**Phase 2 — Notes:** Markdown persisted in DB, Mantine/Tiptap editor and conversion, import/preview, notes PDF.

**Phase 3 — Question bank:** type-specific manual forms, answer model, filtering/search, editing/duplication, JSON import preview/commit, constrained Markdown import.

**Phase 4 — Exams:** select, reorder, decimal scoring, total, snapshots, save/reopen/duplicate.

**Phase 5 — Print and polish:** accurate student/teacher PDFs, exam header template, responsive layouts, validation, backups and end-to-end tests.

### Explicitly out of scope (v1)

Student accounts; online exam taking; automatic grading; analytics; attendance; payments; collaborative editing; school-level roles; internal LLM generation; sophisticated file storage; and complex background-job infrastructure.

## 12. Build acceptance test

A teacher logs in, creates `ریاضی پایه نهم`, adds topics `معادلات` and `هندسه`, authors a note with RTL text and math, exports the note, imports a reviewed JSON batch, manually edits a multiple-choice and an essay question, filters by topic, makes an exam from selected questions, gives them `0.25`, `1.5`, `2.75` marks, sees the correct sum, saves/reopens the exam, and successfully downloads both Persian A4 versions — one with answers and one without — from the deployed HTTPS site.

## 13. Official references

- Mantine RTL: https://mantine.dev/styles/rtl/
- Mantine Tiptap editor: https://mantine.dev/x/tiptap/
- FastAPI: https://fastapi.tiangolo.com/
- Render: https://render.com/docs
- Supabase: https://supabase.com/docs

---

**Implementation principle:** ship a reliable, approachable Persian teaching tool. Favor working end-to-end workflows and excellent exam PDF fidelity over extra features.
