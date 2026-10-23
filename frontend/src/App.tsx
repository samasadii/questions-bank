import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react';
import {
  ActionIcon, AppShell, Badge, Box, Burger, Button, Card, Container, Divider,
  FileInput, Group, Modal, NavLink, NumberInput, Paper, PasswordInput, Select,
  SimpleGrid, Stack, Switch, Table, Text, TextInput, Textarea, ThemeIcon, Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconBook2, IconBooks, IconCheck, IconClipboardText, IconCopy, IconDoorEnter,
  IconHome, IconLink, IconLogout, IconPhoto, IconPlus, IconSchool, IconTrash,
  IconUsers, IconX,
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  API_BASE, api, ClassGroup, ClassMember, Course, downloadQuestions, getToken,
  JoinRequest, Note, Question, Role, setToken, User,
} from './api';

type TeacherSection = 'dashboard' | 'courses' | 'classes' | 'notes' | 'questions' | 'students';

function report(error: unknown) {
  notifications.show({ color: 'red', title: 'خطا', message: error instanceof Error ? error.message : 'خطایی رخ داد' });
}

function notify(title: string, message: string) {
  notifications.show({ color: 'teal', title, message });
}

function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <Paper className="empty-state" withBorder>
    <ThemeIcon size={48} radius="xl" variant="light"><IconClipboardText size={25} /></ThemeIcon>
    <Title order={3}>{title}</Title><Text c="dimmed" ta="center">{description}</Text>{action}
  </Paper>;
}

function PageTitle({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <Group justify="space-between" align="flex-start" mb="xl" gap="lg">
    <div><Title order={1}>{title}</Title><Text c="dimmed" mt={4}>{description}</Text></div>{action}
  </Group>;
}

function QuestionImage({ question }: { question: Question }) {
  const [source, setSource] = useState<string>();
  useEffect(() => {
    if (!question.has_image) return;
    let objectUrl: string | undefined;
    fetch(`${API_BASE}/api/questions/${question.id}/image`, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then(response => { if (!response.ok) throw new Error(); return response.blob(); })
      .then(blob => { objectUrl = URL.createObjectURL(blob); setSource(objectUrl); })
      .catch(() => setSource(undefined));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [question.id, question.has_image]);
  return source ? <img className="question-image" src={source} alt={question.image_alt_text ?? ''} /> : null;
}

function Auth({ onAuth }: { onAuth: (user: User) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [role, setRole] = useState<Role>('teacher');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true);
    try {
      const path = mode === 'login' ? '/auth/login' : `/auth/register/${role}`;
      const body = mode === 'login' ? { email, password } : { email, password, display_name: name };
      const result = await api<{ access_token: string; user: User }>(path, { method: 'POST', body: JSON.stringify(body) });
      setToken(result.access_token); onAuth(result.user);
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  return <main className="auth-page"><Card className="auth-card" shadow="xl" padding="xl">
    <Text className="eyebrow">سامانه آموزشی فارسی</Text><Title order={1}>هم‌درس</Title>
    <Text c="dimmed" mb="xl">کلاس، جزوه و بانک سؤال؛ همه در یک جای آرام و منظم.</Text>
    <Group grow className="auth-tabs"><Button variant={mode === 'login' ? 'filled' : 'subtle'} onClick={() => setMode('login')}>ورود</Button><Button variant={mode === 'register' ? 'filled' : 'subtle'} onClick={() => setMode('register')}>ثبت‌نام</Button></Group>
    <form onSubmit={submit}><Stack mt="lg">
      {mode === 'register' && <><Group grow><Button variant={role === 'teacher' ? 'filled' : 'light'} onClick={() => setRole('teacher')}>معلم هستم</Button><Button variant={role === 'student' ? 'filled' : 'light'} onClick={() => setRole('student')}>دانش‌آموز هستم</Button></Group><TextInput required label="نام و نام خانوادگی" value={name} onChange={e => setName(e.currentTarget.value)} /></>}
      <TextInput required type="email" label="ایمیل" value={email} onChange={e => setEmail(e.currentTarget.value)} />
      <PasswordInput required minLength={8} label="گذرواژه" value={password} onChange={e => setPassword(e.currentTarget.value)} />
      <Button type="submit" size="md" loading={busy}>{mode === 'login' ? 'ورود به حساب' : 'ساخت حساب'}</Button>
    </Stack></form>
  </Card></main>;
}

function CoursePicker({ courses, value, onChange, label = 'دوره' }: { courses: Course[]; value: string | null; onChange: (value: string | null) => void; label?: string }) {
  return <Select searchable clearable label={label} placeholder="یک دوره انتخاب کنید" value={value} onChange={onChange} data={courses.map(course => ({ value: course.id, label: course.title }))} />;
}

function DashboardSection({ courses, classes, goTo }: { courses: Course[]; classes: ClassGroup[]; goTo: (section: TeacherSection) => void }) {
  const cards = [
    { label: 'دوره‌ها', value: courses.length, icon: IconBooks, color: 'indigo', section: 'courses' as const },
    { label: 'کلاس‌ها', value: classes.length, icon: IconSchool, color: 'teal', section: 'classes' as const },
    { label: 'مدیریت دانش‌آموزان', value: 'مشاهده', icon: IconUsers, color: 'cyan', section: 'students' as const },
  ];
  return <><PageTitle title="داشبورد" description="از اینجا همه بخش‌های آموزش را سریع مدیریت کنید." />
    <SimpleGrid cols={{ base: 1, sm: 3 }}>{cards.map(item => <Card key={item.label} withBorder className="metric-card" onClick={() => goTo(item.section)}><Group justify="space-between"><ThemeIcon color={item.color} size={46} radius="lg" variant="light"><item.icon size={25} /></ThemeIcon><Text className="metric-value">{item.value}</Text></Group><Text fw={700} mt="lg">{item.label}</Text><Text size="sm" c="dimmed">برای مدیریت کلیک کنید</Text></Card>)}</SimpleGrid>
    <Paper withBorder p="xl" mt="xl" className="welcome-panel"><Text className="eyebrow">شروع سریع</Text><Title order={2}>جریان کار پیشنهادی</Title><SimpleGrid cols={{ base: 1, md: 4 }} mt="lg">{['یک دوره بسازید', 'کلاس‌ها را به دوره اضافه کنید', 'پیوند عضویت را بفرستید', 'محتوا را برای کلاس منتشر کنید'].map((step, index) => <Group key={step} align="flex-start" wrap="nowrap"><div className="step-number">{index + 1}</div><Text fw={600}>{step}</Text></Group>)}</SimpleGrid></Paper>
  </>;
}

function CoursesSection({ courses, reload }: { courses: Course[]; reload: () => Promise<void> }) {
  const [opened, setOpened] = useState(false); const [title, setTitle] = useState(''); const [description, setDescription] = useState('');
  async function create() { try { await api('/courses', { method: 'POST', body: JSON.stringify({ title, description: description || null }) }); setTitle(''); setDescription(''); setOpened(false); await reload(); notify('دوره ساخته شد', 'اکنون می‌توانید کلاس‌های این دوره را اضافه کنید.'); } catch (error) { report(error); } }
  return <><PageTitle title="دوره‌ها" description="محتوای آموزشی را در دوره‌ها سازمان‌دهی کنید." action={<Button leftSection={<IconPlus size={18} />} onClick={() => setOpened(true)}>دوره جدید</Button>} />
    {courses.length ? <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>{courses.map(course => <Card key={course.id} withBorder className="course-card"><ThemeIcon size={44} radius="lg" variant="light"><IconBooks size={23} /></ThemeIcon><Title order={3} mt="md">{course.title}</Title><Text c="dimmed" mt="xs" lineClamp={3}>{course.description || 'برای این دوره هنوز توضیحی ثبت نشده است.'}</Text><Badge mt="lg" variant="light" color="teal">فعال</Badge></Card>)}</SimpleGrid> : <EmptyState title="هنوز دوره‌ای ندارید" description="اولین دوره را بسازید تا بتوانید کلاس و محتوا به آن اضافه کنید." action={<Button onClick={() => setOpened(true)}>ساخت اولین دوره</Button>} />}
    <Modal opened={opened} onClose={() => setOpened(false)} title="ساخت دوره جدید" centered><Stack><TextInput autoFocus label="عنوان دوره" placeholder="مثلاً ریاضی پایه نهم" value={title} onChange={e => setTitle(e.currentTarget.value)} /><Textarea label="توضیح کوتاه" value={description} onChange={e => setDescription(e.currentTarget.value)} /><Button onClick={create} disabled={!title.trim()}>ساخت دوره</Button></Stack></Modal>
  </>;
}

function ClassesSection({ courses, onChanged }: { courses: Course[]; onChanged: () => Promise<void> }) {
  const [courseId, setCourseId] = useState<string | null>(courses[0]?.id ?? null); const [classes, setClasses] = useState<ClassGroup[]>([]); const [opened, setOpened] = useState(false); const [name, setName] = useState(''); const [year, setYear] = useState(''); const [schoolName, setSchoolName] = useState('');
  async function load(id: string | null) { setCourseId(id); setClasses(id ? await api<ClassGroup[]>(`/courses/${id}/classes`) : []); }
  useEffect(() => { if (courseId) void load(courseId); }, []);
  async function create() { if (!courseId) return; try { await api(`/courses/${courseId}/classes`, { method: 'POST', body: JSON.stringify({ name, academic_year: year || null, school_name: schoolName || null }) }); setName(''); setYear(''); setSchoolName(''); setOpened(false); await load(courseId); await onChanged(); notify('کلاس ساخته شد', 'برای این کلاس می‌توانید پیوند اختصاصی بسازید.'); } catch (error) { report(error); } }
  async function copyInvite(group: ClassGroup) { try { const result = await api<{ join_path: string }>(`/classes/${group.id}/invite`, { method: 'POST' }); await navigator.clipboard.writeText(`${location.origin}${result.join_path}`); notify('پیوند کپی شد', `پیوند عضویت ${group.name} آماده ارسال است.`); } catch (error) { report(error); } }
  return <><PageTitle title="کلاس‌ها" description="هر دوره می‌تواند چند کلاس مستقل با پیوند عضویت جدا داشته باشد." action={<Button leftSection={<IconPlus size={18} />} disabled={!courseId} onClick={() => setOpened(true)}>کلاس جدید</Button>} />
    <Paper withBorder p="lg" mb="xl"><CoursePicker courses={courses} value={courseId} onChange={value => void load(value)} /></Paper>
    {classes.length ? <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>{classes.map(group => <Card key={group.id} withBorder className="course-card"><Group justify="space-between"><ThemeIcon size={42} radius="lg" color="teal" variant="light"><IconSchool size={22} /></ThemeIcon><Badge variant="light">فعال</Badge></Group><Title order={3} mt="md">{group.name}</Title><Text size="sm" c="dimmed">{[group.school_name, group.academic_year].filter(Boolean).join(' · ') || 'بدون نام مدرسه و سال تحصیلی'}</Text><Button mt="lg" fullWidth variant="light" leftSection={<IconLink size={17} />} onClick={() => copyInvite(group)}>ساخت و کپی پیوند عضویت</Button></Card>)}</SimpleGrid> : <EmptyState title="کلاسی برای این دوره نیست" description="یک کلاس بسازید؛ بعد برای همان کلاس پیوند عضویت اختصاصی ایجاد کنید." />}
    <Modal opened={opened} onClose={() => setOpened(false)} title="افزودن کلاس" centered><Stack><TextInput autoFocus label="نام کلاس" placeholder="مثلاً کلاس ۹/الف" value={name} onChange={e => setName(e.currentTarget.value)} /><TextInput label="نام مدرسه" placeholder="مثلاً دبیرستان فرهنگ" value={schoolName} onChange={e => setSchoolName(e.currentTarget.value)} /><TextInput label="سال تحصیلی" value={year} onChange={e => setYear(e.currentTarget.value)} /><Button onClick={create} disabled={!name.trim()}>افزودن کلاس</Button></Stack></Modal>
  </>;
}

function NotesSection({ courses }: { courses: Course[] }) {
  const [courseId, setCourseId] = useState<string | null>(courses[0]?.id ?? null); const [classId, setClassId] = useState<string | null>(null); const [classes, setClasses] = useState<ClassGroup[]>([]); const [notes, setNotes] = useState<Note[]>([]); const [selected, setSelected] = useState<Note | null>(null); const [title, setTitle] = useState(''); const [markdown, setMarkdown] = useState('');
  async function load(id: string | null, preserveNote?: string) { setCourseId(id); if (!id) { setNotes([]); setClasses([]); setSelected(null); return; } const [items, courseClasses] = await Promise.all([api<Note[]>(`/notes?course_id=${id}`), api<ClassGroup[]>(`/courses/${id}/classes`)]); setNotes(items); setClasses(courseClasses); setClassId(current => current && courseClasses.some(group => group.id === current) ? current : courseClasses[0]?.id ?? null); const retained = items.find(note => note.id === preserveNote); if (retained) { setSelected(retained); setTitle(retained.title); setMarkdown(retained.markdown_content); } else { setSelected(null); } }
  useEffect(() => { if (courseId) void load(courseId); }, []);
  function choose(note: Note) { setSelected(note); setTitle(note.title); setMarkdown(note.markdown_content); }
  async function save() { if (!selected) return; try { await api<Note>(`/notes/${selected.id}`, { method: 'PATCH', body: JSON.stringify({ title, markdown_content: markdown }) }); await load(courseId, selected.id); notify('جزوه ذخیره شد', 'تغییرات Markdown با موفقیت ثبت شد.'); } catch (error) { report(error); } }
  async function setVisibility(visible: boolean) { if (!selected || !classId) return; const targets = (selected.publications ?? []).filter(item => item.class_id !== classId); if (visible) targets.push({ class_id: classId }); try { await api(`/notes/${selected.id}/publications`, { method: 'PUT', body: JSON.stringify({ targets }) }); await load(courseId, selected.id); } catch (error) { report(error); } }
  const noteVisible = Boolean(selected?.publications?.some(item => item.class_id === classId));
  return <><PageTitle title="جزوه‌ها" description="جزوه‌های موجود در پایگاه داده را ویرایش، پیش‌نمایش و برای کلاس‌ها منتشر کنید." /><Paper withBorder p="lg" mb="lg"><SimpleGrid cols={{ base: 1, sm: 2 }}><CoursePicker courses={courses} value={courseId} onChange={value => void load(value)} /><Select label="کلاس برای تنظیم نمایش" placeholder="یک کلاس انتخاب کنید" value={classId} onChange={setClassId} data={classes.map(group => ({ value: group.id, label: group.name }))} /></SimpleGrid></Paper>
    {!notes.length ? <EmptyState title="جزوه‌ای در پایگاه داده نیست" description="در این مرحله جزوه‌ها فقط از پایگاه داده اضافه می‌شوند. پس از اضافه‌شدن، ویرایشگر اینجا فعال است." /> : <div className="notes-layout"><Paper withBorder p="sm" className="notes-list"><Text fw={800} p="sm">جزوه‌های دوره</Text>{notes.map(note => <NavLink key={note.id} label={note.title} active={selected?.id === note.id} onClick={() => choose(note)} leftSection={<IconBook2 size={18} />} />)}</Paper><Paper withBorder p="lg">{selected ? <Stack><Group justify="space-between"><Title order={3}>ویرایش جزوه</Title><Group><Switch disabled={!classId} checked={noteVisible} onChange={event => void setVisibility(event.currentTarget.checked)} label="نمایش برای کلاس" /><Button onClick={save}>ذخیره تغییرات</Button></Group></Group><TextInput label="عنوان" value={title} onChange={e => setTitle(e.currentTarget.value)} /><div className="markdown-grid"><Textarea label="Markdown" autosize minRows={18} value={markdown} onChange={e => setMarkdown(e.currentTarget.value)} /><Box><Text size="sm" fw={600} mb={6}>پیش‌نمایش</Text><div className="markdown-preview"><ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown></div></Box></div></Stack> : <EmptyState title="یک جزوه انتخاب کنید" description="برای بازکردن ویرایشگر روی نام جزوه کلیک کنید." />}</Paper></div>}
  </>;
}

const questionTypes = [{ value: 'essay', label: 'تشریحی' }, { value: 'single_choice', label: 'چهارگزینه‌ای' }, { value: 'multiple_choice', label: 'چندپاسخی' }, { value: 'fill_blank', label: 'جای خالی' }, { value: 'true_false', label: 'درست / نادرست' }, { value: 'short_answer', label: 'پاسخ کوتاه' }];

function answerText(question: Question): string {
  if (!question.answer_data) return 'پاسخی ثبت نشده است.';
  const answer = question.answer_data.answer ?? question.answer_data.model_answer_markdown ?? question.answer_data.correct_option_ids;
  return Array.isArray(answer) ? answer.join('، ') : String(answer ?? JSON.stringify(question.answer_data));
}

function QuestionsSection({ courses }: { courses: Course[] }) {
  const [courseId, setCourseId] = useState<string | null>(courses[0]?.id ?? null); const [classId, setClassId] = useState<string | null>(null); const [classes, setClasses] = useState<ClassGroup[]>([]); const [questions, setQuestions] = useState<Question[]>([]); const [opened, setOpened] = useState(false); const [type, setType] = useState('essay'); const [body, setBody] = useState(''); const [answer, setAnswer] = useState(''); const [explanation, setExplanation] = useState(''); const [points, setPoints] = useState<string | number>('1'); const [image, setImage] = useState<File | null>(null); const [alt, setAlt] = useState('');
  async function load(id: string | null, preserveClass?: string | null) { setCourseId(id); if (!id) { setClasses([]); setQuestions([]); setClassId(null); return; } const [courseClasses, courseQuestions] = await Promise.all([api<ClassGroup[]>(`/courses/${id}/classes`), api<Question[]>(`/questions?course_id=${id}`)]); setClasses(courseClasses); setQuestions(courseQuestions); setClassId(preserveClass && courseClasses.some(group => group.id === preserveClass) ? preserveClass : courseClasses[0]?.id ?? null); }
  useEffect(() => { if (courseId) void load(courseId); }, []);
  async function createQuestion() { if (!courseId) return; try { const question = await api<Question>('/questions', { method: 'POST', body: JSON.stringify({ course_id: courseId, type, body_markdown: body, answer_data: { answer }, explanation_markdown: explanation || null, default_points: String(points) }) }); if (image) { const data = new FormData(); data.append('image', image); data.append('alt_text', alt); await api(`/questions/${question.id}/image`, { method: 'PUT', body: data }); } setOpened(false); setBody(''); setAnswer(''); setExplanation(''); setImage(null); setAlt(''); await load(courseId, classId); notify('سؤال اضافه شد', 'سؤال و پاسخ در بانک سؤال ذخیره شدند.'); } catch (error) { report(error); } }
  async function setPublication(question: Question, visible: boolean, answersVisible?: boolean) { if (!classId || !courseId) return; const existing = question.publications ?? []; const current = existing.find(item => item.class_id === classId); const targets = existing.filter(item => item.class_id !== classId); if (visible) targets.push({ class_id: classId, answers_available: answersVisible ?? current?.answers_available ?? false }); try { await api(`/questions/${question.id}/publications`, { method: 'PUT', body: JSON.stringify({ targets }) }); await load(courseId, classId); } catch (error) { report(error); } }
  return <><PageTitle title="بانک سؤال" description="دوره و کلاس را انتخاب کنید، سؤال‌ها را ببینید و دسترسی دانش‌آموزان را تعیین کنید." action={<Button leftSection={<IconPlus size={18} />} disabled={!courseId} onClick={() => setOpened(true)}>افزودن سؤال</Button>} /><Paper withBorder p="lg" mb="xl"><SimpleGrid cols={{ base: 1, sm: 2 }}><CoursePicker courses={courses} value={courseId} onChange={value => void load(value)} /><Select label="کلاس برای تنظیم نمایش" placeholder="یک کلاس انتخاب کنید" value={classId} onChange={setClassId} data={classes.map(group => ({ value: group.id, label: group.name }))} /></SimpleGrid></Paper>
    {!questions.length ? <EmptyState title="سؤالی در این دوره نیست" description="با دکمه افزودن سؤال، سؤال و پاسخ را خیلی سریع وارد بانک کنید." action={<Button leftSection={<IconPlus size={17} />} onClick={() => setOpened(true)}>اولین سؤال</Button>} /> : <Stack>{questions.map((question, index) => { const publication = question.publications?.find(item => item.class_id === classId); return <Card key={question.id} withBorder className="question-card"><Group justify="space-between" align="flex-start"><Group align="flex-start" wrap="nowrap"><div className="question-number">{index + 1}</div><div><Badge variant="light">{questionTypes.find(item => item.value === question.type)?.label ?? question.type}</Badge><Text fw={700} size="lg" mt="xs">{question.body_markdown}</Text></div></Group><Text fw={700} c="dimmed">{question.default_points ?? 1} نمره</Text></Group><QuestionImage question={question} /><Paper className="answer-box" mt="md" p="md"><Text size="xs" fw={800} c="teal">پاسخ</Text><Text mt={4}>{answerText(question)}</Text>{question.explanation_markdown && <Text size="sm" c="dimmed" mt="xs">{question.explanation_markdown}</Text>}</Paper><Divider my="md" /><Group justify="space-between"><Text size="sm" c="dimmed">نمایش برای کلاس انتخاب‌شده</Text><Group><Switch disabled={!classId} checked={Boolean(publication)} onChange={event => void setPublication(question, event.currentTarget.checked)} label="قابل مشاهده" /><Switch disabled={!publication} checked={publication?.answers_available ?? false} onChange={event => void setPublication(question, true, event.currentTarget.checked)} label="نمایش پاسخ" /></Group></Group></Card>; })}</Stack>}
    <Modal opened={opened} onClose={() => setOpened(false)} title="افزودن سؤال" size="lg" centered><Stack><Select label="نوع سؤال" data={questionTypes} value={type} onChange={value => setType(value ?? 'essay')} /><Textarea autoFocus minRows={4} label="متن سؤال" placeholder="صورت سؤال را وارد کنید…" value={body} onChange={e => setBody(e.currentTarget.value)} /><Textarea minRows={3} label="پاسخ" placeholder="پاسخ صحیح یا پاسخ نمونه…" value={answer} onChange={e => setAnswer(e.currentTarget.value)} /><Textarea label="توضیح پاسخ (اختیاری)" value={explanation} onChange={e => setExplanation(e.currentTarget.value)} /><NumberInput label="نمره پیش‌فرض" min={0} decimalScale={2} value={points} onChange={setPoints} /><FileInput label="یک تصویر (اختیاری)" accept="image/png,image/jpeg,image/webp" value={image} onChange={setImage} leftSection={<IconPhoto size={17} />} />{image && <TextInput required label="توضیح تصویر" value={alt} onChange={e => setAlt(e.currentTarget.value)} />}<Button onClick={createQuestion} disabled={!body.trim() || !answer.trim() || Boolean(image && alt.trim().length < 2)}>ذخیره سؤال</Button></Stack></Modal>
  </>;
}

function StudentsSection({ courses }: { courses: Course[] }) {
  const [courseId, setCourseId] = useState<string | null>(courses[0]?.id ?? null); const [classId, setClassId] = useState<string | null>(null); const [classes, setClasses] = useState<ClassGroup[]>([]); const [members, setMembers] = useState<ClassMember[]>([]); const [requests, setRequests] = useState<JoinRequest[]>([]); const selectedClass = classes.find(group => group.id === classId);
  async function loadClasses(id: string | null) { setCourseId(id); setClassId(null); setMembers([]); setRequests([]); if (!id) { setClasses([]); return; } const items = await api<ClassGroup[]>(`/courses/${id}/classes`); setClasses(items); if (items[0]) await loadClass(items[0].id); }
  async function loadClass(id: string | null) { setClassId(id); if (!id) { setMembers([]); setRequests([]); return; } const [students, waiting] = await Promise.all([api<ClassMember[]>(`/classes/${id}/students`), api<JoinRequest[]>(`/classes/${id}/join-requests`)]); setMembers(students); setRequests(waiting); }
  useEffect(() => { if (courseId) void loadClasses(courseId); }, []);
  async function review(requestId: string, action: 'approve' | 'reject') { if (!classId) return; try { await api(`/classes/${classId}/join-requests/${requestId}/${action}`, { method: 'POST' }); await loadClass(classId); } catch (error) { report(error); } }
  async function remove(studentId: string) { if (!classId) return; try { await api(`/classes/${classId}/students/${studentId}`, { method: 'DELETE' }); await loadClass(classId); } catch (error) { report(error); } }
  async function copyInvite() { if (!classId || !selectedClass) return; try { const result = await api<{ join_path: string }>(`/classes/${classId}/invite`, { method: 'POST' }); await navigator.clipboard.writeText(`${location.origin}${result.join_path}`); notify('پیوند کپی شد', `پیوند ${selectedClass.name} آماده ارسال است.`); } catch (error) { report(error); } }
  const pending = requests.filter(request => request.status === 'pending');
  return <><PageTitle title="مدیریت دانش‌آموزان" description="کلاس را انتخاب کنید، فهرست اعضا و درخواست‌های در انتظار را مدیریت کنید." action={<Button leftSection={<IconCopy size={17} />} disabled={!classId} onClick={copyInvite}>ساخت پیوند کلاس</Button>} /><Paper withBorder p="lg" mb="xl"><SimpleGrid cols={{ base: 1, sm: 2 }}><CoursePicker courses={courses} value={courseId} onChange={value => void loadClasses(value)} /><Select label="کلاس" placeholder="یک کلاس انتخاب کنید" value={classId} onChange={value => void loadClass(value)} data={classes.map(group => ({ value: group.id, label: group.name }))} /></SimpleGrid></Paper><SimpleGrid cols={{ base: 1, lg: 2 }}>
    <Paper withBorder p="lg"><Group justify="space-between" mb="md"><Title order={3}>دانش‌آموزان کلاس</Title><Badge variant="light">{members.length} نفر</Badge></Group>{members.length ? <Table.ScrollContainer minWidth={440}><Table verticalSpacing="md"><Table.Thead><Table.Tr><Table.Th>نام</Table.Th><Table.Th>ایمیل</Table.Th><Table.Th></Table.Th></Table.Tr></Table.Thead><Table.Tbody>{members.map(member => <Table.Tr key={member.student_id}><Table.Td fw={600}>{member.display_name}</Table.Td><Table.Td dir="ltr">{member.email}</Table.Td><Table.Td><ActionIcon color="red" variant="subtle" aria-label="حذف از کلاس" onClick={() => remove(member.student_id)}><IconTrash size={18} /></ActionIcon></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer> : <EmptyState title="هنوز دانش‌آموزی نیست" description="پیوند کلاس را برای دانش‌آموزان بفرستید و درخواست‌ها را تأیید کنید." />}</Paper>
    <Paper withBorder p="lg"><Group justify="space-between" mb="md"><Title order={3}>فهرست انتظار</Title><Badge color="orange" variant="light">{pending.length} درخواست</Badge></Group>{pending.length ? <Stack>{pending.map(request => <Card key={request.id} bg="gray.0"><Group justify="space-between"><div><Text fw={700}>{request.student_name}</Text><Text size="sm" c="dimmed" dir="ltr">{request.student_email}</Text></div><Group gap="xs"><ActionIcon color="teal" variant="light" aria-label="تأیید" onClick={() => review(request.id, 'approve')}><IconCheck size={18} /></ActionIcon><ActionIcon color="red" variant="light" aria-label="رد" onClick={() => review(request.id, 'reject')}><IconX size={18} /></ActionIcon></Group></Group></Card>)}</Stack> : <EmptyState title="درخواستی در انتظار نیست" description="درخواست‌های عضویت این کلاس اینجا نمایش داده می‌شوند." />}</Paper>
  </SimpleGrid></>;
}

const navItems: { key: TeacherSection; label: string; icon: typeof IconHome }[] = [
  { key: 'dashboard', label: 'داشبورد', icon: IconHome }, { key: 'courses', label: 'دوره‌ها', icon: IconBooks },
  { key: 'classes', label: 'کلاس‌ها', icon: IconSchool }, { key: 'notes', label: 'جزوه‌ها', icon: IconBook2 },
  { key: 'questions', label: 'بانک سؤال', icon: IconClipboardText }, { key: 'students', label: 'مدیریت دانش‌آموزان', icon: IconUsers },
];

function TeacherApp({ user, logout }: { user: User; logout: () => void }) {
  const [section, setSection] = useState<TeacherSection>('dashboard'); const [mobileOpened, setMobileOpened] = useState(false); const [courses, setCourses] = useState<Course[]>([]); const [allClasses, setAllClasses] = useState<ClassGroup[]>([]);
  async function loadCourses() { const items = await api<Course[]>('/courses'); setCourses(items); const grouped = await Promise.all(items.map(course => api<ClassGroup[]>(`/courses/${course.id}/classes`))); setAllClasses(grouped.flat()); }
  useEffect(() => { void loadCourses().catch(report); }, []);
  function navigate(next: TeacherSection) { setSection(next); setMobileOpened(false); }
  const content = useMemo(() => { if (section === 'dashboard') return <DashboardSection courses={courses} classes={allClasses} goTo={navigate} />; if (section === 'courses') return <CoursesSection courses={courses} reload={loadCourses} />; if (section === 'classes') return <ClassesSection courses={courses} onChanged={loadCourses} />; if (section === 'notes') return <NotesSection courses={courses} />; if (section === 'questions') return <QuestionsSection courses={courses} />; return <StudentsSection courses={courses} />; }, [section, courses, allClasses]);
  return <AppShell header={{ height: 68 }} navbar={{ width: 270, breakpoint: 'md', collapsed: { mobile: !mobileOpened } }} padding="xl"><AppShell.Header><Group h="100%" px="lg" justify="space-between"><Group><Burger opened={mobileOpened} onClick={() => setMobileOpened(value => !value)} hiddenFrom="md" size="sm" /><div className="logo">هـ</div><div><Text fw={800}>هم‌درس</Text><Text size="xs" c="dimmed">پنل معلم</Text></div></Group><Group><Text visibleFrom="sm" size="sm" c="dimmed">{user.display_name}</Text><Button variant="subtle" color="gray" leftSection={<IconLogout size={18} />} onClick={logout}>خروج</Button></Group></Group></AppShell.Header><AppShell.Navbar p="md"><Stack gap={4} className="nav-stack">{navItems.map(item => <NavLink key={item.key} active={section === item.key} label={item.label} leftSection={<item.icon size={20} />} onClick={() => navigate(item.key)} />)}</Stack><Divider my="md" /><Paper p="md" className="sidebar-help"><Text fw={700} size="sm">به کمک نیاز دارید؟</Text><Text size="xs" c="dimmed" mt={4}>ابتدا دوره و کلاس را بسازید، سپس محتوا را منتشر کنید.</Text></Paper></AppShell.Navbar><AppShell.Main><Container size="xl" py="md">{content}</Container></AppShell.Main></AppShell>;
}

function StudentApp({ user, logout }: { user: User; logout: () => void }) {
  const [classes, setClasses] = useState<ClassGroup[]>([]); const [token, setInviteToken] = useState(location.pathname.startsWith('/join/') ? location.pathname.split('/').pop() ?? '' : ''); const [questions, setQuestions] = useState<Question[]>([]); const [notes, setNotes] = useState<Note[]>([]); const [activeClass, setActiveClass] = useState('');
  const load = () => api<ClassGroup[]>('/me/classes').then(setClasses).catch(report); useEffect(() => { void load(); }, []);
  async function join() { try { await api(`/class-invites/${token}/request`, { method: 'POST' }); notify('درخواست ارسال شد', 'پس از تأیید معلم، کلاس نمایش داده می‌شود.'); } catch (error) { report(error); } }
  async function open(group: ClassGroup) { setActiveClass(group.id); try { const [availableQuestions, availableNotes] = await Promise.all([api<Question[]>(`/student/questions?class_id=${group.id}`), api<Note[]>(`/student/notes?class_id=${group.id}`)]); setQuestions(availableQuestions); setNotes(availableNotes); } catch (error) { report(error); } }
  return <AppShell header={{ height: 68 }} padding="xl"><AppShell.Header><Group h="100%" px="xl" justify="space-between"><Group><div className="logo">هـ</div><div><Text fw={800}>هم‌درس</Text><Text size="xs" c="dimmed">پنل دانش‌آموز</Text></div></Group><Button variant="subtle" color="gray" leftSection={<IconLogout size={18} />} onClick={logout}>خروج</Button></Group></AppShell.Header><AppShell.Main><Container size="lg" py="xl"><PageTitle title={`سلام ${user.display_name}`} description="کلاس‌ها و محتوای منتشرشده برای شما" /><Paper withBorder p="lg" mb="xl"><Group align="flex-end"><TextInput className="grow" label="کد یا پیوند دعوت" value={token} onChange={e => setInviteToken(e.currentTarget.value)} /><Button leftSection={<IconDoorEnter size={18} />} onClick={join} disabled={!token}>ارسال درخواست</Button></Group></Paper><SimpleGrid cols={{ base: 1, md: 3 }}>{classes.map(group => <Card key={group.id} withBorder className="course-card"><ThemeIcon variant="light" color="teal" size={44}><IconSchool /></ThemeIcon><Title order={3} mt="md">{group.name}</Title><Button mt="lg" variant="light" onClick={() => open(group)}>مشاهده محتوا</Button></Card>)}</SimpleGrid>{activeClass && <SimpleGrid cols={{ base: 1, lg: 2 }} mt="xl"><Paper withBorder p="lg"><Title order={2}>جزوه‌ها</Title>{notes.map(note => <Card key={note.id} bg="gray.0" mt="md"><Title order={4}>{note.title}</Title><div className="markdown-preview compact"><ReactMarkdown remarkPlugins={[remarkGfm]}>{note.markdown_content}</ReactMarkdown></div></Card>)}</Paper><Paper withBorder p="lg"><Title order={2}>سؤال‌ها</Title>{questions.map((question, index) => <Card key={question.id} bg="gray.0" mt="md"><Text fw={700}>{index + 1}. {question.body_markdown}</Text><QuestionImage question={question} /></Card>)}{!!questions.length && <Group mt="lg"><Button onClick={() => downloadQuestions(activeClass, questions.map(question => question.id), false)}>دانلود بدون پاسخ</Button><Button variant="light" onClick={() => downloadQuestions(activeClass, questions.map(question => question.id), true)} disabled={questions.some(question => !question.answers_available)}>دانلود با پاسخ</Button></Group>}</Paper></SimpleGrid>}</Container></AppShell.Main></AppShell>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true);
  useEffect(() => { api<User>('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false)); }, []);
  const logout = () => { setToken(null); setUser(null); };
  if (loading) return <main className="center"><Text>در حال بارگذاری…</Text></main>;
  if (!user) return <Auth onAuth={setUser} />;
  return user.role === 'teacher' ? <TeacherApp user={user} logout={logout} /> : <StudentApp user={user} logout={logout} />;
}
