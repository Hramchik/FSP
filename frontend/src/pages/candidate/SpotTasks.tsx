import React, { useEffect, useState } from 'react';
import { api, dateRu } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Field, Loader, useToast } from '../../components/ui';

export function SpotTasksPage() {
  const toast = useToast();
  const [assignments, setAssignments] = useState<any[] | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});

  async function load() { setAssignments(await api.get('/me/spot-tasks')); }
  useEffect(() => { load().catch(e => toast(e.message, 'err')); }, []);

  async function send(id: number) {
    try {
      await api.post(`/me/spot-tasks/${id}/answer`, { answer: answers[id] ?? '' });
      await load();
      toast('Ответ отправлен — профиль отмечен как актуальный');
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
  }

  if (!assignments) return <Loader />;
  const pending = assignments.filter(a => a.status === 'assigned');
  const done = assignments.filter(a => a.status === 'answered');

  return (
    <>
      <PageHead eyebrow="Кандидат" title="Регулярные задания">
        Раз в неделю система предлагает короткую задачу от работодателя. Её не обязательно решать,
        но свежий ответ поднимает актуальность профиля в подборках. Задания с генерацией
        собираются лично под вас, открытые — читает человек из компании.
      </PageHead>

      {assignments.length === 0 && (
        <Card>
          <Empty title="Заданий пока нет">
            Задания выдаются по подтверждённой категории. Пройдите тест, и первая задача придёт сюда.
          </Empty>
        </Card>
      )}

      <div className="stack">
        {pending.map(assignment => (
          <Card key={assignment.id} title={assignment.title}
            action={<span className="badge live">{assignment.kind === 'generated' ? 'Сгенерировано лично' : 'Вопрос работодателя'}</span>}>
            <p className="small muted" style={{ marginBottom: 10 }}>
              {assignment.company_name} · выдано {dateRu(assignment.assigned_at)}
            </p>
            <div className="question" style={{ marginBottom: 14 }}>{assignment.prompt}</div>
            <Field label={assignment.kind === 'generated' ? 'Ответ (целое число)' : 'Ваш подход'}>
              {assignment.kind === 'generated'
                ? <input value={answers[assignment.id] ?? ''} onChange={e => setAnswers({ ...answers, [assignment.id]: e.target.value })} />
                : <textarea value={answers[assignment.id] ?? ''} onChange={e => setAnswers({ ...answers, [assignment.id]: e.target.value })} />}
            </Field>
            <button className="btn primary" onClick={() => send(assignment.id)}
              disabled={!(answers[assignment.id] ?? '').trim()}>Отправить</button>
          </Card>
        ))}

        {done.length > 0 && <h3 style={{ marginTop: 10 }}>Отвеченные</h3>}
        {done.map(assignment => (
          <Card key={assignment.id} title={assignment.title}
            action={assignment.is_correct === null
              ? <span className="badge">На стороне работодателя</span>
              : <span className={`badge ${assignment.is_correct ? 'ok' : 'danger'}`}>
                  {assignment.is_correct ? 'Верно' : 'Неверно'}
                </span>}>
            <p className="small muted">{assignment.company_name} · отвечено {dateRu(assignment.answered_at)}</p>
            <p className="small" style={{ marginTop: 10 }}><b>Ваш ответ:</b> {assignment.answer_text}</p>
          </Card>
        ))}
      </div>
    </>
  );
}
