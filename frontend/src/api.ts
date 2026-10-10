/** Single HTTP layer: auth headers, error translation, typed helpers. */

export const API =
  (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000/api/v1';

const ACCESS = 'fsp.access';
const REFRESH = 'fsp.refresh';
const ROLE = 'fsp.role';

export type Role = 'candidate' | 'employer';
export type Grade = 'junior' | 'middle' | 'senior' | 'lead';

export const GRADE_LABEL: Record<Grade, string> = {
  junior: 'Junior', middle: 'Middle', senior: 'Senior', lead: 'Lead',
};
export const FORMAT_LABEL: Record<string, string> = {
  remote: 'Удалённо', hybrid: 'Гибрид', office: 'Офис',
};

export const session = {
  get access() { return localStorage.getItem(ACCESS); },
  get role() { return localStorage.getItem(ROLE) as Role | null; },
  save(access: string, refresh: string, role: Role) {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
    localStorage.setItem(ROLE, role);
  },
  clear() { [ACCESS, REFRESH, ROLE].forEach(k => localStorage.removeItem(k)); },
};

/** Backend messages are already in Russian; these cover transport and legacy cases. */
const TRANSLATIONS: [RegExp, string][] = [
  [/Failed to fetch|NetworkError|Load failed/i, 'Нет связи с API. Проверьте, что контейнер api запущен на :8000.'],
  [/active test attempt already exists/i, 'Уже есть незавершённая попытка теста — прервите её, чтобы начать новую.'],
  [/Complete the survey for this specialization first/i, 'Сначала сохраните опрос по этой специализации.'],
  [/Attempt grade must match the declared grade/i, 'Грейд теста должен совпадать с заявленным в опросе.'],
  [/At least \d+ answered items are required/i, 'Чтобы завершить тест, нужно ответить минимум на 8 заданий.'],
  [/Grade change .*not available yet/i, 'Смена грейда по этой специализации пока недоступна (90 дней с последнего подтверждения).'],
  [/Stop rule reached/i, 'Тест завершён: достигнуто правило остановки.'],
  [/Testing pool is not calibrated/i, 'Банк заданий по этой специализации не откалиброван.'],
  [/Email already registered/i, 'Этот e-mail уже зарегистрирован.'],
  [/Invalid credentials/i, 'Неверный e-mail или пароль.'],
  [/Email is not verified/i, 'Подтвердите e-mail, прежде чем входить.'],
  [/Wrong role/i, 'Этот раздел доступен другой роли.'],
  [/Authentication required|Invalid token|Access token required/i, 'Сессия истекла — войдите заново.'],
];

function humanize(message: string) {
  for (const [pattern, text] of TRANSLATIONS) if (pattern.test(message)) return text;
  return message;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(humanize(message));
    this.status = status;
  }
}

async function request(path: string, options: RequestInit = {}, retry = true): Promise<any> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const token = session.access;
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(API + path, { ...options, headers });
  } catch (e) {
    throw new ApiError(e instanceof Error ? e.message : 'Failed to fetch', 0);
  }

  // One transparent refresh keeps a long test session from dying mid-way.
  if (response.status === 401 && retry && localStorage.getItem(REFRESH)) {
    const refreshed = await fetch(API + '/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: localStorage.getItem(REFRESH) }),
    });
    if (refreshed.ok) {
      const tokens = await refreshed.json();
      session.save(tokens.access_token, tokens.refresh_token, session.role as Role);
      return request(path, options, false);
    }
    session.clear();
  }

  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof data.detail === 'string'
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((d: any) => d.msg).join('; ')
          : 'Ошибка запроса';
    throw new ApiError(detail, response.status);
  }
  return data;
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, body?: unknown) =>
    request(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: (path: string, body: unknown) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  del: (path: string) => request(path, { method: 'DELETE' }),
  upload: (path: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request(path, { method: 'POST', body: form });
  },
  /** Downloads keep the auth header, so they cannot be a plain <a href>. */
  async download(path: string, filename: string) {
    const response = await fetch(API + path, { headers: { Authorization: `Bearer ${session.access}` } });
    if (!response.ok) throw new ApiError('Не удалось сформировать файл', response.status);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  },
};

export function money(value?: number | null) {
  return value == null ? '' : value.toLocaleString('ru-RU') + ' ₽';
}
export function salaryRange(from?: number | null, to?: number | null) {
  if (from && to) return `${from.toLocaleString('ru-RU')} — ${to.toLocaleString('ru-RU')} ₽`;
  if (from) return `от ${money(from)}`;
  if (to) return `до ${money(to)}`;
  return 'не указана';
}
export function dateRu(value?: string | null) {
  return value ? new Date(value).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' }) : '';
}
