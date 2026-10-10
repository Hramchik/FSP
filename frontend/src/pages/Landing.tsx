import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, session, Role } from '../api';
import { Field } from '../components/ui';
import { Mark } from '../components/Layout';

const DEMO = [
  { email: 'demo.employer@fsp.example', role: 'employer' as Role, title: 'Работодатель', note: 'ФСП Демо Тех — потребности и подборки' },
  { email: 'test.drive@fsp.example', role: 'candidate' as Role, title: 'Кандидат без категории', note: 'можно пройти тестирование с нуля' },
  { email: 'anna.belova@fsp.example', role: 'candidate' as Role, title: 'Кандидат с категорией', note: 'Backend / Senior, есть достижения ФСП' },
];

const POINTS = [
  ['1', 'Кандидат не пишет резюме «под вакансию»', 'Отрасль, специализация и заявленный грейд собираются опросом, а категорию присваивает адаптивный тест.'],
  ['2', 'Работодатель выбирает категорию, а не человека', 'Он описывает потребность, получает готовую подборку и видит, почему каждый кандидат в ней оказался.'],
  ['3', 'Первый шаг делает работодатель', 'Приглашение с вилкой зарплаты уходит конкретному человеку. Контакты раскрываются только после согласия кандидата.'],
];

export function Landing() {
  const [role, setRole] = useState<Role>('candidate');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; kind: 'ok' | 'danger' } | null>(null);
  const navigate = useNavigate();

  const go = (userRole: Role) => navigate(userRole === 'candidate' ? '/candidate' : '/employer');

  async function signIn(loginEmail = email, loginPassword = password) {
    setBusy(true); setMessage(null);
    try {
      const tokens = await api.post('/auth/login', { email: loginEmail, password: loginPassword });
      const me = await (async () => {
        session.save(tokens.access_token, tokens.refresh_token, role);
        return api.get('/auth/me');
      })();
      session.save(tokens.access_token, tokens.refresh_token, me.role as Role);
      go(me.role as Role);
    } catch (e) {
      setMessage({ text: e instanceof Error ? e.message : 'Ошибка', kind: 'danger' });
    } finally {
      setBusy(false);
    }
  }

  async function signUp() {
    setBusy(true); setMessage(null);
    try {
      const registered = await api.post('/auth/register', { email, password, role });
      // Local development returns the verification token instead of sending
      // mail, so registration can finish without an SMTP server.
      await api.post('/auth/verify-email', { token: registered.verification_token });
      await signIn();
    } catch (e) {
      setMessage({ text: e instanceof Error ? e.message : 'Ошибка', kind: 'danger' });
      setBusy(false);
    }
  }

  return (
    <div className="landing">
      <header>
        <div className="logo"><Mark size={34} /><div><b>ФСП Career</b><small>Федерация спортивного программирования</small></div></div>
        <span className="small" style={{ color: '#E5C9F2' }}>Обратный найм в ИТ</span>
      </header>

      <main>
        <div>
          <p className="eyebrow">Платформа-агрегатор ИТ-вакансий</p>
          <h1>Работодатель находит категорию<br />и выходит на человека сам</h1>
          <p className="lead">
            Соискатели распределяются по категориям «специализация + грейд» на основе
            подтверждаемого профиля: опрос, адаптивный тест и верифицированные достижения
            участника ФСП. Работодатель описывает потребность и получает подборку
            с объяснением, а не ленту откликов.
          </p>
          <div className="points">
            {POINTS.map(([number, title, text]) => (
              <div className="point" key={number}>
                <i>{number}</i>
                <div><b>{title}</b><span>{text}</span></div>
              </div>
            ))}
          </div>
        </div>

        <div className="auth">
          <div className="tabs" role="tablist">
            <button role="tab" aria-selected={role === 'candidate'} className={role === 'candidate' ? 'active' : ''}
              onClick={() => setRole('candidate')}>Я кандидат</button>
            <button role="tab" aria-selected={role === 'employer'} className={role === 'employer' ? 'active' : ''}
              onClick={() => setRole('employer')}>Я работодатель</button>
          </div>

          <Field label="E-mail">
            <input type="email" autoComplete="username" placeholder="you@company.ru"
              value={email} onChange={e => setEmail(e.target.value)} />
          </Field>
          <Field label="Пароль" hint="Минимум 8 символов">
            <input type="password" autoComplete="current-password" placeholder="••••••••"
              value={password} onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && signIn()} />
          </Field>

          <div className="row">
            <button className="btn wide" disabled={busy || !email || password.length < 8} onClick={signUp}>
              Регистрация
            </button>
            <button className="btn primary wide" disabled={busy || !email || !password} onClick={() => signIn()}>
              Войти
            </button>
          </div>

          {message && <div className={`note ${message.kind}`} style={{ marginTop: 12 }}>{message.text}</div>}

          <div className="demo-accounts">
            <p className="small muted" style={{ fontWeight: 600 }}>Демо-доступы (пароль DemoPass123!)</p>
            {DEMO.map(account => (
              <button key={account.email} onClick={() => { setRole(account.role); setEmail(account.email); setPassword('DemoPass123!'); signIn(account.email, 'DemoPass123!'); }}>
                <b>{account.title}</b> — {account.note}
              </button>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
