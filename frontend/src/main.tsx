import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import './styles.css';

const API = 'http://localhost:8000/api/v1';

type Role = 'candidate' | 'employer';
type Grade = 'junior' | 'middle' | 'senior' | 'lead';
type SpecializationStatus = {
  specialization: string;
  specialization_name: string;
  declared_grade: Grade;
  confirmed_grade: Grade | null;
  theta: number | null;
  grade_change_allowed_at: string | null;
};

const SPECIALIZATIONS = [
  ['backend', 'Бэкенд-разработка'],
  ['frontend', 'Фронтенд-разработка'],
  ['mobile', 'Мобильная разработка'],
  ['data', 'Данные и ML'],
  ['devops', 'DevOps и инфраструктура'],
  ['qa', 'Тестирование'],
] as const;

async function api(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access');
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(API + path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === 'string'
      ? data.detail
      : data.detail?.[0]?.msg || 'Ошибка запроса';
    throw new Error(detail);
  }
  return data;
}

function App() {
  const [role, setRole] = useState<Role>('candidate');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const nav = useNavigate();

  async function register() {
    try {
      const d = await api('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, role }),
      });
      await api('/auth/verify-email', {
        method: 'POST',
        body: JSON.stringify({ token: d.verification_token }),
      });
      setMessage('Почта подтверждена. Теперь можно войти.');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Ошибка');
    }
  }

  async function login() {
    try {
      const d = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem('access', d.access_token);
      localStorage.setItem('role', role);
      nav(role === 'candidate' ? '/candidate' : '/employer');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Ошибка');
    }
  }

  return (
    <div className="app">
      <header><b>FSP Career</b><span>Обратный найм IT · DAY 2</span></header>
      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">DAY 2 · TESTING</p>
            <h1>Платформа, где работодатель ищет кандидата</h1>
            <p>Кандидат проходит опрос и адаптивный тест. Категория определяется по латентной способности θ, а не по простому проценту правильных ответов.</p>
          </div>
          <div className="card auth">
            <div className="tabs">
              <button className={role === 'candidate' ? 'active' : ''} onClick={() => setRole('candidate')}>Кандидат</button>
              <button className={role === 'employer' ? 'active' : ''} onClick={() => setRole('employer')}>Работодатель</button>
            </div>
            <input placeholder="E-mail" value={email} onChange={e => setEmail(e.target.value)} />
            <input placeholder="Пароль (8+ символов)" type="password" value={password} onChange={e => setPassword(e.target.value)} />
            <div className="row">
              <button onClick={register}>Регистрация</button>
              <button className="primary" onClick={login}>Войти</button>
            </div>
            {message && <div className="notice">{message}</div>}
          </div>
        </section>
      </main>
    </div>
  );
}

function CandidateDashboard() {
  const [industry, setIndustry] = useState('IT');
  const [specialization, setSpecialization] = useState('backend');
  const [grade, setGrade] = useState<Grade>('middle');
  const [surveySaved, setSurveySaved] = useState(false);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [item, setItem] = useState<any>(null);
  const [answer, setAnswer] = useState('');
  const [progress, setProgress] = useState(0);
  const [theta, setTheta] = useState(0);
  const [se, setSe] = useState(1);
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState('');
  const [specializationStatuses, setSpecializationStatuses] = useState<SpecializationStatus[]>([]);

  async function loadSpecializations() {
    try {
      const d = await api('/me/testing/specializations');
      setSpecializationStatuses(d);
    } catch {
      // The dashboard can still be used before any specialization is saved.
    }
  }

  useEffect(() => {
    loadSpecializations();
  }, []);

  const selectedStatus = specializationStatuses.find(s => s.specialization === specialization);

  async function saveSurvey() {
    try {
      await api('/survey', { method: 'POST', body: JSON.stringify({ industry: industry.trim(), specialization, declared_grade: grade }) });
      setSurveySaved(true);
      await loadSpecializations();
      setMessage('Опрос сохранён для выбранной специализации. Теперь можно начать тест.');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Ошибка');
    }
  }

  async function startTest() {
    try {
      const a = await api('/test/attempts', { method: 'POST', body: JSON.stringify({ specialization, grade }) });
      setAttemptId(a.id);
      setTheta(a.theta);
      setSe(a.se);
      setProgress(0);
      setResult(null);
      await nextItem(a.id);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Ошибка');
    }
  }

  async function nextItem(id = attemptId) {
    if (!id) return;
    try {
      const d = await api(`/test/attempts/${id}/next`);
      setItem(d);
      setAnswer('');
      setProgress(d.progress);
      setMessage('');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Тест завершён или недоступен');
    }
  }

  async function submitAnswer() {
    if (!item) return;
    try {
      const d = await api(`/test/items/${item.item_id}/answer`, {
        method: 'POST',
        body: JSON.stringify({ answer }),
      });
      setTheta(d.theta);
      setSe(d.se);
      setProgress(d.progress);
      setItem(null);
      if (d.finished) {
        const finish = await api(`/test/attempts/${attemptId}/finish`, { method: 'POST' });
        setResult(finish);
      } else {
        await nextItem(attemptId);
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Ошибка');
    }
  }

  return (
    <div className="app">
      <header><b>FSP Career</b><span>Кабинет кандидата · Day 2</span></header>
      <main className="dashboard">
        <p className="eyebrow">CANDIDATE · TESTING</p>
        <h1>Опрос и адаптивный тест</h1>
        <div className="grid">
          <div className="panel">
            <h3>1. Опрос</h3>
            <label>Отрасль</label>
            <input value={industry} onChange={e => { setIndustry(e.target.value); setSurveySaved(false); }} placeholder="Например: IT" />
            <label>Специализация</label>
            <select value={specialization} onChange={e => { setSpecialization(e.target.value); setSurveySaved(false); }}>
              {SPECIALIZATIONS.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
            </select>
            <label>Заявленный грейд</label>
            <select value={grade} onChange={e => { setGrade(e.target.value as Grade); setSurveySaved(false); }}>
              <option value="junior">Junior</option>
              <option value="middle">Middle</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead</option>
            </select>
            <button className="primary wide" onClick={saveSurvey}>Сохранить опрос</button>
            {surveySaved && <p className="ok">✓ Опрос сохранён для этой специализации</p>}
            {specializationStatuses.length > 0 && (
              <div className="specialization-list">
                <h4>Мои специализации</h4>
                {specializationStatuses.map(s => (
                  <div className="specialization-status" key={s.specialization}>
                    <b>{s.specialization_name}</b>
                    <span>{s.confirmed_grade ? `Подтверждён: ${s.confirmed_grade}` : `Заявлен: ${s.declared_grade}`}</span>
                    {s.theta !== null && <span>θ {s.theta.toFixed(2)}</span>}
                    {s.confirmed_grade && s.grade_change_allowed_at && <small>Смена грейда: {new Date(s.grade_change_allowed_at).toLocaleDateString('ru-RU')}</small>}
                  </div>
                ))}
              </div>
            )}
            <h3>2. Тест</h3>
            <p>8–15 заданий. Если стандартной точности недостаточно, система может добавить до 5 заданий. Следующее выбирается по максимуму информации Фишера.</p>
            {selectedStatus?.confirmed_grade && selectedStatus.grade_change_allowed_at && (
              <p className="muted">Для этой специализации подтверждён {selectedStatus.confirmed_grade}. Сменить грейд можно после {new Date(selectedStatus.grade_change_allowed_at).toLocaleDateString('ru-RU')}.</p>
            )}
            <button className="primary wide" onClick={startTest}>Начать тест по этой специализации</button>
          </div>

          <div className="panel">
            {!attemptId && !result && <div className="empty"><h2>Готовы?</h2><p>Сначала выберите специализацию и грейд, сохраните опрос и запустите тест.</p></div>}
            {item && (
              <div>
                <div className="test-meta"><b>Задание {progress + 1}</b><span>θ {theta.toFixed(2)} · SE {se.toFixed(2)}</span></div>
                <div className="question">{item.prompt}</div>
                <input className="answer" placeholder="Ваш ответ" value={answer} onChange={e => setAnswer(e.target.value)} />
                <button className="primary wide" disabled={!answer.trim()} onClick={submitAnswer}>Ответить</button>
                <p className="muted">Эталонный ответ хранится только в генераторе на сервере и не передаётся в браузер.</p>
              </div>
            )}
            {attemptId && !item && !result && <div className="empty"><h2>Подготовка следующего задания…</h2></div>}
            {result && (
              <div className="result">
                <p className="eyebrow">РЕЗУЛЬТАТ</p>
                <h2>{result.grade ? `Категория: ${result.specialization ?? specialization} / ${result.grade}` : 'Категория пока не подтверждена'}</h2>
                <div className="stats"><span>θ <b>{result.theta.toFixed(2)}</b></span><span>SE <b>{result.se.toFixed(2)}</b></span></div>
                <p>{result.grade ? 'Результат засчитан. Для этой специализации следующая смена подтверждённого грейда доступна через 90 дней.' : result.recommended_grade ? `Результат выше заявленного грейда. Рекомендуется уровень ${result.recommended_grade}.` : result.se > 0.45 ? 'Точность результата пока недостаточна для подтверждения грейда.' : 'Результат ниже заявленного грейда. Можно пройти тест на уровень ниже для этой специализации.'}</p>
              </div>
            )}
            {message && <div className="notice">{message}</div>}
          </div>
        </div>
      </main>
    </div>
  );
}

function EmployerPlaceholder() {
  return <div className="app"><header><b>FSP Career</b><span>Кабинет работодателя · Day 2</span></header><main className="dashboard"><p className="eyebrow">EMPLOYER</p><h1>Потребность компании</h1><div className="panel"><h3>Следующий этап</h3><p>Механика подбора и shortlist реализуются в Day 3 согласно SPEC.</p></div></main></div>;
}

function RouterApp() {
  return <Routes><Route path="/" element={<App />} /><Route path="/candidate" element={<CandidateDashboard />} /><Route path="/employer" element={<EmployerPlaceholder />} /></Routes>;
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode><BrowserRouter><RouterApp /></BrowserRouter></React.StrictMode>
);
