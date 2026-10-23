import { FormEvent, useEffect, useState } from 'react';
import {
  AppShell, Badge, Button, Card, Checkbox, Container, FileInput, Group, PasswordInput,
  SegmentedControl, Select, SimpleGrid, Stack, Text, TextInput, Textarea, Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconBook2, IconDoorEnter, IconLogout, IconPhoto, IconUsers } from '@tabler/icons-react';
import { API_BASE, api, ClassGroup, ClassMember, Course, downloadQuestions, getToken, JoinRequest, Note, Question, Role, setToken, User } from './api';

function report(error: unknown) {
  notifications.show({ color: 'red', title: 'خطا', message: error instanceof Error ? error.message : 'خطایی رخ داد' });
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
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const path = mode === 'login' ? '/auth/login' : `/auth/register/${role}`;
      const body = mode === 'login' ? { email, password } : { email, password, display_name: name };
      const result = await api<{ access_token: string; user: User }>(path, { method: 'POST', body: JSON.stringify(body) });
      setToken(result.access_token);
      onAuth(result.user);
    } catch (error) { report(error); }
  }
  return <main className="auth-page"><Card className="auth-card" shadow="xl" padding="xl">
    <Text className="eyebrow">سامانه آموزشی فارسی</Text><Title order={1}>هم‌درس</Title>
    <Text c="dimmed" mb="xl">کلاس، جزوه و بانک سؤال؛ همه در یک جای آرام و منظم.</Text>
    <SegmentedControl fullWidth value={mode} onChange={v => setMode(v as typeof mode)} data={[{ label: 'ورود', value: 'login' }, { label: 'ثبت‌نام', value: 'register' }]} />
    <form onSubmit={submit}><Stack mt="lg">
      {mode === 'register' && <><SegmentedControl fullWidth value={role} onChange={v => setRole(v as Role)} data={[{ label: 'معلم هستم', value: 'teacher' }, { label: 'دانش‌آموز هستم', value: 'student' }]} /><TextInput required label="نام و نام خانوادگی" value={name} onChange={e => setName(e.currentTarget.value)} /></>}
      <TextInput required type="email" label="ایمیل" value={email} onChange={e => setEmail(e.currentTarget.value)} />
      <PasswordInput required minLength={8} label="گذرواژه" value={password} onChange={e => setPassword(e.currentTarget.value)} />
      <Button type="submit" size="md">{mode === 'login' ? 'ورود به حساب' : role === 'teacher' ? 'ثبت‌نام معلم' : 'ثبت‌نام دانش‌آموز'}</Button>
    </Stack></form>
  </Card></main>;
}

function TeacherDashboard({ user }: { user: User }) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [classes, setClasses] = useState<Record<string, ClassGroup[]>>({});
  const [requests, setRequests] = useState<Record<string, JoinRequest[]>>({});
  const [members, setMembers] = useState<Record<string, ClassMember[]>>({});
  const [title, setTitle] = useState('');
  const [className, setClassName] = useState('');
  const [activeCourse, setActiveCourse] = useState<string>();
  const [questionText, setQuestionText] = useState('');
  const [questionId, setQuestionId] = useState('');
  const [image, setImage] = useState<File | null>(null);
  const [alt, setAlt] = useState('');
  const [publishClass, setPublishClass] = useState<string | null>(null);
  const [answersAvailable, setAnswersAvailable] = useState(false);
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const load = () => api<Course[]>('/courses').then(setCourses).catch(report);
  useEffect(() => { void load(); }, []);
  async function loadClasses(courseId: string) {
    setActiveCourse(courseId); const items = await api<ClassGroup[]>(`/courses/${courseId}/classes`); setClasses(v => ({ ...v, [courseId]: items }));
  }
  async function addCourse() { try { await api('/courses', { method: 'POST', body: JSON.stringify({ title }) }); setTitle(''); load(); } catch (e) { report(e); } }
  async function addClass() { if (!activeCourse) return; try { await api(`/courses/${activeCourse}/classes`, { method: 'POST', body: JSON.stringify({ name: className }) }); setClassName(''); loadClasses(activeCourse); } catch (e) { report(e); } }
  async function invite(group: ClassGroup) { try { const result = await api<{ join_path: string }>(`/classes/${group.id}/invite`, { method: 'POST' }); await navigator.clipboard.writeText(`${location.origin}${result.join_path}`); notifications.show({ title: 'پیوند آماده است', message: 'پیوند دعوت در حافظه کپی شد.' }); } catch (e) { report(e); } }
  async function loadRequests(group: ClassGroup) { try { setRequests(v => ({ ...v, [group.id]: [] })); const items = await api<JoinRequest[]>(`/classes/${group.id}/join-requests`); setRequests(v => ({ ...v, [group.id]: items })); } catch (e) { report(e); } }
  async function approve(groupId: string, requestId: string) { try { await api(`/classes/${groupId}/join-requests/${requestId}/approve`, { method: 'POST' }); const group = Object.values(classes).flat().find(c => c.id === groupId); if (group) loadRequests(group); } catch (e) { report(e); } }
  async function reject(groupId: string, requestId: string) { try { await api(`/classes/${groupId}/join-requests/${requestId}/reject`, { method: 'POST' }); const group = Object.values(classes).flat().find(c => c.id === groupId); if (group) loadRequests(group); } catch (e) { report(e); } }
  async function loadMembers(group: ClassGroup) { try { const items = await api<ClassMember[]>(`/classes/${group.id}/students`); setMembers(v => ({ ...v, [group.id]: items })); } catch (e) { report(e); } }
  async function removeMember(group: ClassGroup, studentId: string) { try { await api(`/classes/${group.id}/students/${studentId}`, { method: 'DELETE' }); loadMembers(group); } catch (e) { report(e); } }
  async function addQuestion() { if (!activeCourse) return; try { const q = await api<Question>('/questions', { method: 'POST', body: JSON.stringify({ course_id: activeCourse, type: 'essay', body_markdown: questionText, default_points: '1.00' }) }); setQuestionId(q.id); setQuestionText(''); notifications.show({ title: 'سؤال ذخیره شد', message: 'اکنون می‌توانید یک تصویر به آن اضافه کنید.' }); } catch (e) { report(e); } }
  async function upload() { if (!questionId || !image) return; const data = new FormData(); data.append('image', image); data.append('alt_text', alt); try { await api(`/questions/${questionId}/image`, { method: 'PUT', body: data }); notifications.show({ title: 'تصویر ذخیره شد', message: 'تصویر یکتای سؤال ثبت شد.' }); } catch (e) { report(e); } }
  async function publishQuestion() { if (!questionId || !publishClass) return; try { await api(`/questions/${questionId}/publications`, { method: 'PUT', body: JSON.stringify({ targets: [{ class_id: publishClass, answers_available: answersAvailable }] }) }); notifications.show({ title: 'سؤال منتشر شد', message: answersAvailable ? 'دانش‌آموزان این کلاس پاسخ را هم می‌بینند.' : 'پاسخ برای دانش‌آموزان پنهان است.' }); } catch (e) { report(e); } }
  async function addNote() { if (!activeCourse || !publishClass) return; try { const note = await api<Note>('/notes', { method: 'POST', body: JSON.stringify({ course_id: activeCourse, title: noteTitle, markdown_content: noteContent }) }); await api(`/notes/${note.id}/publications`, { method: 'PUT', body: JSON.stringify({ targets: [{ class_id: publishClass }] }) }); setNoteTitle(''); setNoteContent(''); notifications.show({ title: 'جزوه منتشر شد', message: 'جزوه فقط برای کلاس انتخاب‌شده در دسترس است.' }); } catch (e) { report(e); } }
  const classOptions = activeCourse ? (classes[activeCourse] ?? []).map(group => ({ value: group.id, label: group.name })) : [];
  return <Container size="lg" py="xl"><Group justify="space-between" mb="xl"><div><Text c="dimmed">خوش آمدید، {user.display_name}</Text><Title>میز کار معلم</Title></div><Badge size="lg" variant="light">معلم</Badge></Group>
    <SimpleGrid cols={{ base: 1, md: 2 }}><Card withBorder padding="lg"><Group><IconBook2 /><Title order={3}>دوره تازه</Title></Group><TextInput mt="md" label="عنوان دوره" value={title} onChange={e => setTitle(e.currentTarget.value)} /><Button mt="md" onClick={addCourse} disabled={!title}>ساخت دوره</Button></Card>
    <Card withBorder padding="lg"><Group><IconUsers /><Title order={3}>کلاس تازه</Title></Group><Text c="dimmed" size="sm">ابتدا یک دوره را از پایین انتخاب کنید.</Text><TextInput mt="md" label="نام کلاس" value={className} onChange={e => setClassName(e.currentTarget.value)} /><Button mt="md" onClick={addClass} disabled={!activeCourse || !className}>ساخت کلاس</Button></Card></SimpleGrid>
    <Title order={2} mt="xl" mb="md">دوره‌های من</Title><SimpleGrid cols={{ base: 1, md: 2 }}>{courses.map(course => <Card key={course.id} withBorder className={activeCourse === course.id ? 'selected' : ''}><Title order={3}>{course.title}</Title><Text c="dimmed">{course.description || 'بدون توضیح'}</Text><Button variant="light" mt="md" onClick={() => loadClasses(course.id)}>مدیریت کلاس‌ها</Button>{classes[course.id]?.map(group => <Card key={group.id} mt="md" bg="gray.0"><Group justify="space-between"><Text fw={700}>{group.name}</Text><Group><Button size="xs" variant="subtle" onClick={() => invite(group)}>کپی پیوند</Button><Button size="xs" variant="subtle" onClick={() => loadRequests(group)}>درخواست‌ها</Button><Button size="xs" variant="subtle" onClick={() => loadMembers(group)}>دانش‌آموزان</Button></Group></Group>{requests[group.id]?.map(r => <Group key={r.id} justify="space-between" mt="xs"><Text size="sm">{r.student_name} · {r.student_email}</Text>{r.status === 'pending' && <Group gap="xs"><Button size="xs" onClick={() => approve(group.id, r.id)}>تأیید</Button><Button size="xs" color="red" variant="light" onClick={() => reject(group.id, r.id)}>رد</Button></Group>}</Group>)}{members[group.id]?.map(member => <Group key={member.student_id} justify="space-between" mt="xs"><Text size="sm">{member.display_name} · {member.email}</Text><Button size="xs" color="red" variant="subtle" onClick={() => removeMember(group, member.student_id)}>حذف از کلاس</Button></Group>)}</Card>)}</Card>)}</SimpleGrid>
    <SimpleGrid cols={{ base: 1, md: 2 }} mt="xl"><Card withBorder padding="lg"><Group><IconPhoto /><Title order={3}>ثبت و انتشار سؤال</Title></Group><Textarea mt="md" label="متن سؤال" value={questionText} onChange={e => setQuestionText(e.currentTarget.value)} /><Button mt="md" onClick={addQuestion} disabled={!activeCourse || !questionText}>ذخیره سؤال</Button>{questionId && <Stack mt="lg"><FileInput accept="image/png,image/jpeg,image/webp" label="یک تصویر (اختیاری)" value={image} onChange={setImage} /><TextInput label="متن جایگزین تصویر" value={alt} onChange={e => setAlt(e.currentTarget.value)} /><Button variant="light" onClick={upload} disabled={!image || alt.length < 2}>بارگذاری یا جایگزینی تصویر</Button><Select label="انتشار برای کلاس" data={classOptions} value={publishClass} onChange={setPublishClass} /><Checkbox label="دانش‌آموز پاسخ را هم ببیند" checked={answersAvailable} onChange={e => setAnswersAvailable(e.currentTarget.checked)} /><Button color="teal" onClick={publishQuestion} disabled={!publishClass}>انتشار سؤال</Button></Stack>}</Card>
    <Card withBorder padding="lg"><Group><IconBook2 /><Title order={3}>جزوه کلاس</Title></Group><TextInput mt="md" label="عنوان جزوه" value={noteTitle} onChange={e => setNoteTitle(e.currentTarget.value)} /><Textarea minRows={7} mt="md" label="متن جزوه (Markdown)" value={noteContent} onChange={e => setNoteContent(e.currentTarget.value)} /><Select mt="md" label="انتشار برای کلاس" data={classOptions} value={publishClass} onChange={setPublishClass} /><Button mt="md" color="teal" onClick={addNote} disabled={!activeCourse || !publishClass || !noteTitle}>ذخیره و انتشار</Button></Card></SimpleGrid>
  </Container>;
}

function StudentDashboard({ user }: { user: User }) {
  const [classes, setClasses] = useState<ClassGroup[]>([]); const [token, setInviteToken] = useState(location.pathname.startsWith('/join/') ? location.pathname.split('/').pop() ?? '' : ''); const [questions, setQuestions] = useState<Question[]>([]); const [notes, setNotes] = useState<Note[]>([]); const [activeClass, setActiveClass] = useState('');
  const load = () => api<ClassGroup[]>('/me/classes').then(setClasses).catch(report); useEffect(() => { void load(); }, []);
  async function join() { try { await api(`/class-invites/${token}/request`, { method: 'POST' }); notifications.show({ title: 'درخواست ارسال شد', message: 'پس از تأیید معلم، کلاس نمایش داده می‌شود.' }); } catch (e) { report(e); } }
  async function open(group: ClassGroup) { setActiveClass(group.id); try { const [availableQuestions, availableNotes] = await Promise.all([api<Question[]>(`/student/questions?class_id=${group.id}`), api<Note[]>(`/student/notes?class_id=${group.id}`)]); setQuestions(availableQuestions); setNotes(availableNotes); } catch (e) { report(e); } }
  return <Container size="lg" py="xl"><Group justify="space-between"><div><Text c="dimmed">خوش آمدید، {user.display_name}</Text><Title>کلاس‌های من</Title></div><Badge size="lg" color="teal">دانش‌آموز</Badge></Group><Card withBorder my="xl"><Group><IconDoorEnter /><Title order={3}>پیوستن به کلاس</Title></Group><TextInput mt="md" label="کد دعوت" value={token} onChange={e => setInviteToken(e.currentTarget.value)} /><Button mt="md" onClick={join} disabled={!token}>ارسال درخواست</Button></Card><SimpleGrid cols={{ base: 1, md: 3 }}>{classes.map(group => <Card key={group.id} withBorder><Title order={3}>{group.name}</Title><Button mt="md" variant="light" onClick={() => open(group)}>مشاهده محتوا</Button></Card>)}</SimpleGrid>{activeClass && <SimpleGrid cols={{ base: 1, md: 2 }} mt="xl"><Card withBorder><Title order={2}>جزوه‌های منتشرشده</Title>{notes.map(note => <Card key={note.id} bg="gray.0" mt="sm"><Text fw={700}>{note.title}</Text><Text mt="xs" className="note-content">{note.markdown_content}</Text></Card>)}</Card><Card withBorder><Title order={2}>سؤال‌های منتشرشده</Title>{questions.map((q, i) => <Card key={q.id} bg="gray.0" mt="sm"><Text fw={700}>{i + 1}. {q.body_markdown}</Text><QuestionImage question={q} /></Card>)}{!!questions.length && <Group mt="lg"><Button onClick={() => downloadQuestions(activeClass, questions.map(q => q.id), false)}>دانلود بدون پاسخ</Button><Button variant="light" onClick={() => downloadQuestions(activeClass, questions.map(q => q.id), true)} disabled={questions.some(q => !q.answers_available)}>دانلود با پاسخ</Button></Group>}</Card></SimpleGrid>}</Container>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true);
  useEffect(() => { api<User>('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false)); }, []);
  if (loading) return <main className="center"><Text>در حال بارگذاری…</Text></main>;
  if (!user) return <Auth onAuth={setUser} />;
  return <AppShell header={{ height: 64 }}><AppShell.Header><Group h="100%" px="xl" justify="space-between"><Group><div className="logo">هـ</div><Text fw={800}>هم‌درس</Text></Group><Button variant="subtle" color="gray" leftSection={<IconLogout size={18} />} onClick={() => { setToken(null); setUser(null); }}>خروج</Button></Group></AppShell.Header><AppShell.Main>{user.role === 'teacher' ? <TeacherDashboard user={user} /> : <StudentDashboard user={user} />}</AppShell.Main></AppShell>;
}
