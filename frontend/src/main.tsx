import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  BrowserRouter,
  Routes,
  Route,
  useNavigate,
} from 'react-router-dom';
import './styles.css';

const API = 'http://localhost:8000/api/v1';

function App() {
  const [role, setRole] = useState<'candidate' | 'employer'>('candidate');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const nav = useNavigate();

  async function register() {
    const r = await fetch(API + '/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        role,
      }),
    });

    const d = await r.json();

    if (!r.ok) {
      setMessage(
        typeof d.detail === 'string'
          ? d.detail
          : d.detail?.[0]?.msg || 'Ошибка'
      );
      return;
    }

    const v = await fetch(API + '/auth/verify-email', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token: d.verification_token,
      }),
    });

    setMessage(
      v.ok
        ? 'Почта подтверждена. Теперь можно войти.'
        : 'Не удалось подтвердить почту'
    );
  }

  async function login() {
    const r = await fetch(API + '/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
      }),
    });

    const d = await r.json();

    if (!r.ok) {
      setMessage(
        typeof d.detail === 'string'
          ? d.detail
          : d.detail?.[0]?.msg || 'Ошибка'
      );
      return;
    }

    localStorage.setItem('access', d.access_token);
    localStorage.setItem('role', role);

    nav(role === 'candidate' ? '/candidate' : '/employer');
  }

  return (
    <div className="app">
      <header>
        <b>FSP Career</b>
        <span>Обратный найм IT</span>
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">DAY 1 · MVP</p>

            <h1>
              Платформа, где работодатель ищет кандидата
            </h1>

            <p>
              Кандидат проходит верифицируемый путь профилирования,
              работодатель получает анонимную базу и сам инициирует контакт.
            </p>
          </div>

          <div className="card auth">
            <div className="tabs">
              <button
                className={role === 'candidate' ? 'active' : ''}
                onClick={() => setRole('candidate')}
              >
                Кандидат
              </button>

              <button
                className={role === 'employer' ? 'active' : ''}
                onClick={() => setRole('employer')}
              >
                Работодатель
              </button>
            </div>

            <input
              placeholder="E-mail"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <input
              placeholder="Пароль (8+ символов)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <div className="row">
              <button onClick={register}>
                Регистрация
              </button>

              <button className="primary" onClick={login}>
                Войти
              </button>
            </div>

            {message && (
              <div className="notice">
                {message}
              </div>
            )}
          </div>
        </section>

        <section className="cards">
          <article>
            <h3>Кандидат</h3>
            <p>
              Профиль · специализация · грейд · тест · ФСП ID · приглашения
            </p>
          </article>

          <article>
            <h3>Работодатель</h3>
            <p>
              Потребность · подборка · объяснимое ранжирование · приглашение
            </p>
          </article>

          <article>
            <h3>Безопасность</h3>
            <p>
              Контакты не выдаются до принятия приглашения.
            </p>
          </article>
        </section>
      </main>
    </div>
  );
}

function Placeholder({ role }: { role: 'candidate' | 'employer' }) {
  return (
    <div className="app">
      <header>
        <b>FSP Career</b>

        <span>
          {role === 'candidate'
            ? 'Кабинет кандидата'
            : 'Кабинет работодателя'}
        </span>
      </header>

      <main>
        <div className="dashboard">
          <p className="eyebrow">DAY 1 SCAFFOLD</p>

          <h1>
            {role === 'candidate'
              ? 'Мой профиль'
              : 'Потребность компании'}
          </h1>

          <div className="grid">
            <div className="panel">
              <h3>Навигация</h3>

              <p>Профиль</p>

              <p>
                {role === 'candidate'
                  ? 'Опрос и тестирование'
                  : 'Подбор кандидатов'}
              </p>

              <p>Приглашения</p>
            </div>

            <div className="panel">
              <h3>
                {role === 'candidate'
                  ? 'Профиль пока не заполнен'
                  : 'Опишите потребность'}
              </h3>

              <p>
                Каркас кабинета готов. Механики тестирования
                и подбора подключаются в дни 2–3 согласно рабочему ТЗ.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function RouterApp() {
  return (
    <Routes>
      <Route path="/" element={<App />} />
      <Route
        path="/candidate"
        element={<Placeholder role="candidate" />}
      />
      <Route
        path="/employer"
        element={<Placeholder role="employer" />}
      />
    </Routes>
  );
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <RouterApp />
    </BrowserRouter>
  </React.StrictMode>
);