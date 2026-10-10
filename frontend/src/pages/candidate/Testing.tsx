import React, { useEffect, useState } from 'react';
import { api, dateRu, GRADE_LABEL, Grade } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Field, useToast } from '../../components/ui';
import { useCandidate } from './index';

type SpecStatus = {
  specialization: string; specialization_name: string;
  declared_grade: Grade; confirmed_grade: Grade | null;
  theta: number | null; grade_change_allowed_at: string | null;
};

export function TestingPage() {
  const { catalog, reload } = useCandidate();
  const toast = useToast();

  const [industry, setIndustry] = useState('IT');
  const [specialization, setSpecialization] = useState(catalog.specializations[0]?.code ?? 'backend');
  const [grade, setGrade] = useState<Grade>('middle');
  const [statuses, setStatuses] = useState<SpecStatus[]>([]);

  const [attempt, setAttempt] = useState<any>(null);
  const [item, setItem] = useState<any>(null);
  const [answer, setAnswer] = useState('');
  const [progress, setProgress] = useState(0);
  const [theta, setTheta] = useState(0);
  const [se, setSe] = useState(1);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function loadStatuses() {
    try { setStatuses(await api.get('/me/testing/specializations')); } catch { /* none yet */ }
  }

  useEffect(() => {
    loadStatuses();
    // A reload must not lose a running attempt, so pick it back up on mount.
    api.get('/test/attempts/active').then(async (active: any) => {
      if (!active) return;
      setAttempt(active);
      setTheta(active.theta); setSe(active.se); setProgress(active.answered_count);
      if (active.specialization) setSpecialization(active.specialization);
      setGrade(active.requested_grade);
      await nextItem(active.id);
      toast(`Продолжаем незавершённый тест: отвечено ${active.answered_count}`);
    }).catch(() => {});
  }, []);

  const current = statuses.find(s => s.specialization === specialization);
  const surveyMatches = current?.declared_grade === grade;
  const cooldownBlocks = !!(current?.confirmed_grade && current.confirmed_grade !== grade &&
    current.grade_change_allowed_at && new Date(current.grade_change_allowed_at) > new Date());

  async function saveSurvey() {
    setBusy(true);
    try {
      await api.post('/survey', { industry: industry.trim(), specialization, declared_grade: grade });
      await loadStatuses();
      toast('Опрос сохранён — можно начинать тест');
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setBusy(false); }
  }

  async function startTest() {
    setBusy(true);
    try {
      const started = await api.post('/test/attempts', { specialization, grade });
      setAttempt(started); setResult(null);
      setTheta(started.theta); setSe(started.se); setProgress(started.answered_count ?? 0);
      await nextItem(started.id);
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setBusy(false); }
  }

  async function nextItem(attemptId: number) {
    try {
      const next = await api.get(`/test/attempts/${attemptId}/next`);
      setItem(next); setAnswer(''); setProgress(next.progress);
    } catch {
      setItem(null);
    }
  }

  async function submit() {
    if (!item || !attempt) return;
    setBusy(true);
    try {
      const outcome = await api.post(`/test/items/${item.item_id}/answer`, { answer });
      setTheta(outcome.theta); setSe(outcome.se); setProgress(outcome.progress); setItem(null);
      if (outcome.finished) {
        setResult(await api.post(`/test/attempts/${attempt.id}/finish`));
        setAttempt(null);
        await Promise.all([loadStatuses(), reload()]);
      } else {
        await nextItem(attempt.id);
      }
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setBusy(false); }
  }

  async function abandon() {
    if (!attempt) return;
    await api.post(`/test/attempts/${attempt.id}/abandon`);
    setAttempt(null); setItem(null); setProgress(0); setTheta(0); setSe(1);
    await loadStatuses();
    toast('Попытка прервана — грейд не засчитан');
  }

  const minItems = item?.min_items ?? 8;
  const maxItems = item?.max_items ?? 15;

  return (
    <>
      <PageHead eyebrow="Кандидат" title="Опрос и адаптивное тестирование">
        Опрос фиксирует отрасль, специализацию и заявленный грейд. Тест проверяет его на деле:
        следующее задание выбирается по максимуму информации Фишера, а грейд подтверждается
        только когда оценка уверенно отделена от границы соседнего уровня.
      </PageHead>

      <div className="grid2" style={{ gridTemplateColumns: '360px 1fr', alignItems: 'start' }}>
        <div className="stack">
          <Card title="1. Опрос">
            <Field label="Отрасль"><input value={industry} onChange={e => setIndustry(e.target.value)} /></Field>
            <Field label="Специализация">
              <select value={specialization} onChange={e => setSpecialization(e.target.value)} disabled={!!attempt}>
                {catalog.specializations.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
              </select>
            </Field>
            <Field label="Заявленный грейд" hint="Тест может подтвердить его, порекомендовать выше или предложить уровень ниже">
              <select value={grade} onChange={e => setGrade(e.target.value as Grade)} disabled={!!attempt}>
                {catalog.grades.map(value => <option key={value} value={value}>{GRADE_LABEL[value as Grade]}</option>)}
              </select>
            </Field>
            <button className="btn wide" onClick={saveSurvey} disabled={busy || !!attempt}>Сохранить опрос</button>
            {cooldownBlocks && (
              <div className="note warn" style={{ marginTop: 12 }}>
                Для этой специализации подтверждён {GRADE_LABEL[current!.confirmed_grade!]}.
                Сменить грейд можно после {dateRu(current!.grade_change_allowed_at)}.
              </div>
            )}
          </Card>

          <Card title="2. Тест">
            <p className="small muted" style={{ marginBottom: 12 }}>
              От {minItems} до {maxItems} заданий, в сложных случаях — до 20. Условия генерируются
              индивидуально из (шаблон, seed), эталонный ответ не покидает сервер.
            </p>
            {!attempt && (
              <button className="btn primary wide" onClick={startTest} disabled={busy || !surveyMatches || cooldownBlocks}>
                Начать тест
              </button>
            )}
            {!surveyMatches && !attempt && (
              <p className="faint" style={{ marginTop: 8 }}>Сохраните опрос для выбранной пары «специализация + грейд».</p>
            )}
            {attempt && <button className="btn danger wide" onClick={abandon}>Прервать попытку</button>}
          </Card>

          <Card title="Мои специализации">
            {statuses.length === 0
              ? <p className="faint">Пока ни одна специализация не сохранена.</p>
              : <div className="stack tight">
                  {statuses.map(status => (
                    <div key={status.specialization} style={{ padding: '10px 12px', border: '1px solid var(--line)', borderRadius: 12 }}>
                      <div className="spread">
                        <b className="small">{status.specialization_name}</b>
                        {status.confirmed_grade
                          ? <span className="badge ok">{GRADE_LABEL[status.confirmed_grade]}</span>
                          : <span className="badge warn">заявлен {GRADE_LABEL[status.declared_grade]}</span>}
                      </div>
                      {status.theta !== null && <div className="faint mono">θ {status.theta.toFixed(2)}</div>}
                      {status.confirmed_grade && status.grade_change_allowed_at &&
                        <div className="faint">Смена грейда с {dateRu(status.grade_change_allowed_at)}</div>}
                    </div>
                  ))}
                </div>}
          </Card>
        </div>

        <div className="stack">
          {item && (
            <Card title={`Задание ${progress + 1}`} action={<span className="chip mono">θ {theta.toFixed(2)} · SE {se.toFixed(2)}</span>}>
              <div className="progressbar" style={{ marginBottom: 16 }}>
                <i style={{ width: `${Math.min(100, (progress / maxItems) * 100)}%` }} />
              </div>
              <div className="question">{item.prompt}</div>
              <Field label="Ваш ответ">
                <input autoFocus value={answer} onChange={e => setAnswer(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && answer.trim() && submit()} placeholder="Целое число" />
              </Field>
              <button className="btn primary wide" onClick={submit} disabled={busy || !answer.trim()}>Ответить</button>
              <p className="faint" style={{ marginTop: 10 }}>
                Условие сгенерировано лично для вас: у другого кандидата будут другие числа,
                поэтому ответами нельзя обменяться.
              </p>
            </Card>
          )}

          {attempt && !item && <Card><Empty title="Готовим следующее задание…" /></Card>}

          {result && (
            <Card title="Результат">
              <p className="eyebrow">{result.grade ? 'Категория присвоена' : 'Категория не подтверждена'}</p>
              <h2 style={{ margin: '8px 0 14px' }}>
                {result.grade ? `${result.specialization} · ${GRADE_LABEL[result.grade as Grade]}` : 'Грейд не подтверждён'}
              </h2>
              <div className="grid2" style={{ marginBottom: 14 }}>
                <div className="stat"><span>Оценка θ</span><b>{result.theta.toFixed(2)}</b></div>
                <div className="stat"><span>Стандартная ошибка</span><b>{result.se.toFixed(2)}</b></div>
              </div>
              <div className={`note ${result.grade ? 'ok' : result.recommended_grade ? 'info' : 'warn'}`}>
                {result.grade
                  ? `Результат засчитан. Следующая смена подтверждённого грейда доступна с ${dateRu(result.grade_change_allowed_at)}.`
                  : result.recommended_grade
                    ? `Результат выше заявленного уровня — рекомендуем пройти тест на ${GRADE_LABEL[result.recommended_grade as Grade]}.`
                    : result.se > 0.45
                      ? 'Точности пока не хватает для подтверждения. Можно пройти тест заново.'
                      : 'Результат ниже заявленного уровня. Грейд принудительно не понижается — пройдите тест на уровень ниже.'}
              </div>
            </Card>
          )}

          {!item && !attempt && !result && (
            <Card>
              <Empty title="Тест ещё не запущен">
                Сохраните опрос слева и нажмите «Начать тест». Результат сразу станет категорией,
                по которой вас найдут работодатели.
              </Empty>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
