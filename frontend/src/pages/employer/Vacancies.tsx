import React, { useEffect, useState } from 'react';
import { api, dateRu, FORMAT_LABEL, GRADE_LABEL, Grade, salaryRange } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Field, Loader, Modal, SkillPicker, StatusBadge, useToast } from '../../components/ui';
import { CandidateBody } from './CandidateCard';
import { useEmployer } from './index';

const EMPTY = {
  title: '', description: '', specialization_code: 'backend', grade: 'middle',
  skills: [] as string[], city: '', work_format: 'remote',
  salary_from: '', salary_to: '', is_published: true,
};

export function EmployerVacanciesPage() {
  const { catalog } = useEmployer();
  const toast = useToast();
  const [vacancies, setVacancies] = useState<any[] | null>(null);
  const [applications, setApplications] = useState<any[]>([]);
  const [form, setForm] = useState({ ...EMPTY });
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function load() {
    const [list, incoming] = await Promise.all([
      api.get('/employer/vacancies'),
      api.get('/employer/applications'),
    ]);
    setVacancies(list);
    setApplications(incoming);
  }

  useEffect(() => { load().catch(e => toast(e.message, 'err')); }, []);
  const set = (patch: Partial<typeof form>) => setForm(previous => ({ ...previous, ...patch }));

  async function create() {
    setBusy(true);
    try {
      await api.post('/vacancies', {
        ...form, salary_from: Number(form.salary_from), salary_to: Number(form.salary_to),
      });
      setOpen(false); setForm({ ...EMPTY });
      await load();
      toast('Вакансия опубликована');
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setBusy(false); }
  }

  async function decide(id: number, decision: 'accepted' | 'declined') {
    await api.post(`/employer/applications/${id}/decision`, { decision });
    await load();
    toast(decision === 'accepted' ? 'Отклик принят' : 'Отклик отклонён');
  }

  if (!vacancies) return <Loader />;

  return (
    <>
      <PageHead eyebrow="Работодатель" title="Вакансии и входящие отклики">
        Дополнительный сценарий: публикация вакансии даёт кандидату, который ещё не получил
        приглашение, возможность написать первым. Отклик открывает его контакты.
      </PageHead>

      <div className="row" style={{ marginBottom: 18 }}>
        <button className="btn primary" onClick={() => setOpen(true)}>Опубликовать вакансию</button>
      </div>

      <div className="stack">
        {vacancies.length === 0 && <Card><Empty title="Вакансий пока нет" /></Card>}

        {vacancies.map(vacancy => (
          <Card key={vacancy.id} title={vacancy.title}
            action={<div className="row">
              <span className="badge">{vacancy.applications_count} откликов</span>
              {!vacancy.is_published && <span className="badge warn">Снята</span>}
            </div>}>
            <div className="row wrap" style={{ marginBottom: 10 }}>
              <span className="chip match">{salaryRange(vacancy.salary_from, vacancy.salary_to)}</span>
              <span className="chip">{GRADE_LABEL[vacancy.grade as Grade]}</span>
              <span className="chip">{FORMAT_LABEL[vacancy.work_format] ?? vacancy.work_format}</span>
              {vacancy.city && <span className="chip">{vacancy.city}</span>}
            </div>
            <p className="small muted">{vacancy.description}</p>
          </Card>
        ))}

        {applications.length > 0 && (
          <>
            <h3 style={{ marginTop: 10 }}>Входящие отклики</h3>
            {applications.map(application => (
              <section className="card" key={application.id}>
                <header className="card-head">
                  <div>
                    <h3>{application.candidate?.display_name ?? 'Кандидат'}</h3>
                    <span className="faint">{application.vacancy_title} · {dateRu(application.created_at)}</span>
                  </div>
                  <div className="row">
                    <StatusBadge status={application.status} kind="application" />
                    {application.status === 'sent' && (
                      <>
                        <button className="btn primary sm" onClick={() => decide(application.id, 'accepted')}>Принять</button>
                        <button className="btn sm" onClick={() => decide(application.id, 'declined')}>Отклонить</button>
                      </>
                    )}
                  </div>
                </header>
                <div className="card-pad stack">
                  {application.message && <p className="small">«{application.message}»</p>}
                  {application.candidate && <CandidateBody candidate={application.candidate} />}
                </div>
              </section>
            ))}
          </>
        )}
      </div>

      {open && (
        <Modal title="Новая вакансия" onClose={() => setOpen(false)}>
          <Field label="Название"><input value={form.title} onChange={e => set({ title: e.target.value })} /></Field>
          <Field label="Описание" hint="Стек распознается из текста автоматически">
            <textarea value={form.description} onChange={e => set({ description: e.target.value })} />
          </Field>
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
          <Field label="Стек">
            <SkillPicker all={catalog.skills} value={form.skills} onChange={skills => set({ skills })}
              suggestions={catalog.specializations.find(s => s.code === form.specialization_code)?.core_skills ?? []} />
          </Field>
          <div className="grid2">
            <Field label="Город"><input value={form.city} onChange={e => set({ city: e.target.value })} /></Field>
            <Field label="Формат">
              <select value={form.work_format} onChange={e => set({ work_format: e.target.value })}>
                {catalog.work_formats.map(value => <option key={value} value={value}>{FORMAT_LABEL[value] ?? value}</option>)}
              </select>
            </Field>
            <Field label="Вилка от, ₽" hint="Обязательна — кандидат видит условия до общения">
              <input type="number" value={form.salary_from} onChange={e => set({ salary_from: e.target.value })} />
            </Field>
            <Field label="Вилка до, ₽">
              <input type="number" value={form.salary_to} onChange={e => set({ salary_to: e.target.value })} />
            </Field>
          </div>
          <div className="row">
            <button className="btn primary" onClick={create}
              disabled={busy || !form.title || form.description.length < 10 || !form.salary_from || !form.salary_to}>
              Опубликовать
            </button>
            <button className="btn" onClick={() => setOpen(false)}>Отмена</button>
          </div>
        </Modal>
      )}
    </>
  );
}
