export type Role = 'teacher' | 'student';
export type User = { id: string; email: string; display_name: string; role: Role; status: string };
export type Course = { id: string; owner_id: string; title: string; description?: string; status: string };
export type ClassGroup = { id: string; course_id: string; name: string; academic_year?: string; school_name?: string; status: string };
export type JoinRequest = { id: string; student_name?: string; student_email?: string; status: string };
export type Publication = { class_id: string; answers_available: boolean };
export type Question = {
  id: string;
  course_id: string;
  body_markdown: string;
  type: string;
  has_image: boolean;
  image_alt_text?: string;
  answer_data?: Record<string, unknown> | null;
  explanation_markdown?: string | null;
  default_points?: string;
  answers_available?: boolean;
  publications?: Publication[];
};
export type Note = { id: string; title: string; markdown_content: string; publications?: { class_id: string }[] };
export type ClassMember = { student_id: string; display_name: string; email: string; joined_at: string };

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export function getToken() { return localStorage.getItem('token'); }
export function setToken(token: string | null) {
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_BASE}/api${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? 'خطایی رخ داد');
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function downloadQuestions(classId: string, ids: string[], includeAnswers: boolean) {
  const token = getToken();
  const response = await fetch(`${API_BASE}/api/student/question-downloads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ class_id: classId, question_ids: ids, include_answers: includeAnswers }),
  });
  if (!response.ok) throw new Error((await response.json()).detail ?? 'دانلود ناموفق بود');
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = includeAnswers ? 'questions-with-answers.html' : 'questions.html';
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function downloadNotePdf(noteId: string, title: string) {
  const token = getToken();
  const response = await fetch(`${API_BASE}/api/notes/${noteId}/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error((await response.json()).detail ?? 'دانلود جزوه ناموفق بود');
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${title}.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}
