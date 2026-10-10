import React, { useEffect, useState } from 'react';
import { api, dateRu, GRADE_LABEL, Grade } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Field, Loader, Modal, useToast } from '../../components/ui';
import { useEmployer } from './index';

const EMPTY = { title: '', prompt: '', kind: 'open', specialization_code: 'backend', grade: 'senior', is_active: true };

export function EmployerTasksPage() {
  const { catalog } = useEmployer();
  const toast = useToast();
  const [tasks, setTasks] = useState<any[] | null>(null);
  const [answers, setAnswers] = useState<Record<number, any[]>>({});
  const [form, setForm] = useState({ ...EMPTY });
  const [open, setOpen] = useState(false);

  async function load() { setTasks(await api.get('/spot-tasks')); }
  useEffect(() => { load().catch(e => toast(e.message, 'err')); }, []);
  const set = (patch: Partial<typeof form>) => setForm(previous => ({ ...previous, ...patch }));

  async function create() {
    try {
      await api.post('/spot-tasks', form);
      setOpen(false); setForm({ ...EMPTY });
      await load();
      toast('Задание создано');
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
  }

  async function showAnswers(taskId: number) {
    if (answers[taskId]) { setAnswers({ ...answers, [taskId]: [] }); return; }
    setAnswers({ ...answers, [taskId]: await api.get(`/spot-tasks/${taskId}/answers`) });
  }

  if (!tasks) return <Loader />;

  return (
    <>
      <PageHead eyebrow="Работодатель" title="Регулярные задания">
        Короткая задача, которую система периодически предлагает кандидатам нужной категории.
        Свежий ответ держит их профиль актуальным и даёт вам сигнал о человеке до первого контакта.
      </PageHead>

      <div className="row" style={{ marginBottom: 18 }}>
        <button className="btn primary" onClick={() => setOpen(true)}>Создать задание</button>
      </div>

      {tasks.length === 0 && (
        <Card><Empty title="Заданий пока нет">
          Открытое задание читает человек из вашей команды; сгенерированное собирается
          из откалиброванного банка лично под каждого кандидата и проверяется автоматически.
        </Empty></Card>
      )}

      <div className="stack">
        {tasks.map(task => (
          <Card key={task.id} title={task.title}
            action={<div className="row">
              <span className="badge">{task.kind === 'generated' ? 'Генерируется' : 'Открытое'}</span>
              <button className="btn sm" onClick={() => showAnswers(task.id)}>
                Ответы ({task.answered_count})
              </button>
            </div>}>
            <div className="row wrap" style={{ marginBottom: 10 }}>
              <span className="chip match">
                {catalog.specializations.find(s => s.code === task.specialization_code)?.name} · {GRADE_LABEL[task.grade as Grade]}
              </span>
              <span className="chip">Выдано {task.assigned_count}</span>
              <span className="chip">Создано {dateRu(task.created_at)}</span>
            </div>
            {task.prompt && <p className="small muted">{task.prompt}</p>}
            {answers[task.id]?.length > 0 && (
              <table className="table" style={{ marginTop: 12 }}>
                <thead><tr><th>Кандидат</th><th>Ответ</th><th>Когда</th></tr></thead>
                <tbody>
                  {answers[task.id].map(answer => (
                    <tr key={answer.id}>
                      <td><b>{answer.candidate_name}</b></td>
                      <td className="small">
                        {answer.answer_text}
                        {answer.is_correct !== null && (
                          <span className={`badge ${answer.is_correct ? 'ok' : 'danger'}`} style={{ marginLeft: 8 }}>
                            {answer.is_correct ? 'верно' : 'неверно'}
                          </span>
                        )}
                      </td>
                      <td className="small muted">{dateRu(answer.answered_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        ))}
      </div>

      {open && (
        <Modal title="Новое регулярное задание" onClose={() => setOpen(false)}>
          <Field label="Тип задания" hint="Сгенерированное нельзя передать другому кандидату: у каждого свои числа">
            <select value={form.kind} onChange={e => set({ kind: e.target.value })}>
              <option value="open">Открытый вопрос — читает человек</option>
              <option value="generated">Из банка заданий — проверяется автоматически</option>
            </select>
          </Field>
          <Field label="Название"><input value={form.title} onChange={e => set({ title: e.target.value })} /></Field>
          {form.kind === 'open' && (
            <Field label="Текст вопроса">
              <textarea value={form.prompt} onChange={e => set({ prompt: e.target.value })}
                placeholder="Опишите в 5–10 предложениях, как вы обеспечите идемпотентность платёжного запроса." />
            </Field>
          )}
          <div className="grid2">
            <Field label="Специализация">
              <select value={form.specialization_code} onChange={e => set({ specialization_code: e.target.value })}>
                {catalog.specializations.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
              </select>
            </Field>
            <Field label="Грейд">
              <select value={form.grade} onChange={e => set({ grade: e.target.value })}>
                {catalog.grades.map(value => <option key={value} value={value}>{GRADE_LABEL[value as Grade]}</option>)}
              </select>
            </Field>
          </div>
          <div className="row">
            <button className="btn primary" onClick={create}
              disabled={!form.title || (form.kind === 'open' && form.prompt.trim().length < 10)}>Создать</button>
            <button className="btn" onClick={() => setOpen(false)}>Отмена</button>
          </div>
        </Modal>
      )}
    </>
  );
}
