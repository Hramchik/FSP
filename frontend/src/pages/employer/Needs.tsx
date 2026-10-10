import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, dateRu, FORMAT_LABEL, GRADE_LABEL, Grade, salaryRange } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Field, Loader, Modal, SkillPicker, useToast } from '../../components/ui';
import { useEmployer } from './index';

const EMPTY = {
  title: '', text: '', specialization_code: 'backend', grade: 'senior',
  skills: [] as string[], city: '', work_format: '', salary_from: '', salary_to: '', require_fsp: false,
};

export function NeedsPage() {
  const { catalog, company } = useEmployer();
  const toast = useToast();
  const navigate = useNavigate();
  const [needs, setNeeds] = useState<any[] | null>(null);
  const [form, setForm] = useState({ ...EMPTY });
  const [editing, setEditing] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function load() { setNeeds(await api.get('/needs')); }
  useEffect(() => { load().catch(e => toast(e.message, 'err')); }, []);

  const set = (patch: Partial<typeof form>) => setForm(previous => ({ ...previous, ...patch }));

  function startNew() { setForm({ ...EMPTY }); setEditing(null); setOpen(true); }
  function startEdit(need: any) {
    setForm({
      title: need.title, text: need.text, specialization_code: need.specialization_code,
      grade: need.grade, skills: need.skills, city: need.city, work_format: need.work_format,
      salary_from: need.salary_from ?? '', salary_to: need.salary_to ?? '', require_fsp: need.require_fsp,
    });
    setEditing(need.id);
    setOpen(true);
  }

  async function save() {
    setBusy(true);
    try {
      const payload = {
        ...form,
        salary_from: form.salary_from === '' ? null : Number(form.salary_from),
        salary_to: form.salary_to === '' ? null : Number(form.salary_to),
      };
      const saved = editing
        ? await api.put(`/needs/${editing}`, payload)
        : await api.post('/needs', payload);
      setOpen(false);
      await load();
      toast(editing ? 'Потребность обновлена' : 'Потребность создана');
      if (!editing) await buildShortlist(saved.id);
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setBusy(false); }
  }

  async function buildShortlist(needId: number) {
    try {
      const shortlist = await api.post(`/needs/${needId}/shortlist`);
      navigate(`/employer/needs/${needId}/shortlist`, { state: { shortlistId: shortlist.shortlist_id } });
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
  }

  async function remove(needId: number) {
    await api.del(`/needs/${needId}`);
    await load();
    toast('Потребность удалена');
  }

  if (!needs) return <Loader />;
  const specializationName = (code: string) => catalog.specializations.find(s => s.code === code)?.name ?? code;

  return (
    <>
      <PageHead eyebrow="Работодатель" title="Потребности и подборки">
        Опишите, кто нужен — платформа подберёт не резюме, а категорию «специализация + грейд»
        и покажет людей внутри неё с объяснением, почему каждый из них попал в список.
      </PageHead>

      {!company.company_name && (
        <div className="note warn" style={{ marginBottom: 16 }}>
          Заполните название компании в «Профиле компании» — без него нельзя отправлять приглашения.
        </div>
      )}

      <div className="row" style={{ marginBottom: 18 }}>
        <button className="btn primary" onClick={startNew}>Описать потребность</button>
      </div>

      {needs.length === 0 && (
        <Card><Empty title="Потребностей пока нет">
          Нажмите «Описать потребность»: достаточно написать абзац своими словами — стек система
          распознает из текста сама.
        </Empty></Card>
      )}

      <div className="stack">
        {needs.map(need => (
          <Card key={need.id} title={need.title}
            action={<div className="row">
              <button className="btn sm" onClick={() => startEdit(need)}>Изменить</button>
              <button className="btn primary sm" onClick={() => buildShortlist(need.id)}>
                {need.shortlist_id ? 'Пересобрать подборку' : 'Собрать подборку'}
              </button>
            </div>}>
            <div className="row wrap" style={{ marginBottom: 10 }}>
              <span className="chip match">{specializationName(need.specialization_code)} · {GRADE_LABEL[need.grade as Grade]}</span>
              {need.city && <span className="chip">{need.city}</span>}
              {need.work_format && <span className="chip">{FORMAT_LABEL[need.work_format] ?? need.work_format}</span>}
              {(need.salary_from || need.salary_to) && <span className="chip">{salaryRange(need.salary_from, need.salary_to)}</span>}
              {need.require_fsp && <span className="chip fsp">Только с ФСП</span>}
            </div>
            {need.text && <p className="small muted">{need.text}</p>}
            {need.skill_labels.length > 0 && (
              <div className="chips" style={{ marginTop: 10 }}>
                {need.skill_labels.map((label: string) => <span className="chip" key={label}>{label}</span>)}
              </div>
            )}
            <div className="note info" style={{ marginTop: 12 }}>
              <b>Как будет искаться:</b>
              <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
                {need.routed_categories.map((line: string) => <li key={line}>{line}</li>)}
              </ul>
            </div>
            <div className="spread small muted" style={{ marginTop: 12 }}>
              <span>Создана {dateRu(need.created_at)}</span>
              <div className="row">
                {need.shortlist_id && (
                  <button className="btn ghost sm" onClick={() => navigate(`/employer/needs/${need.id}/shortlist`)}>
                    Открыть подборку
                  </button>
                )}
                <button className="btn ghost sm" onClick={() => remove(need.id)}>Удалить</button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {open && (
        <Modal title={editing ? 'Изменить потребность' : 'Новая потребность'} onClose={() => setOpen(false)}>
          <Field label="Название" hint="Для себя — например, «Senior Python в платформенную команду»">
            <input value={form.title} onChange={e => set({ title: e.target.value })} />
          </Field>
          <Field label="Кто нужен" hint="Опишите своими словами: стек из текста распознается автоматически">
            <textarea value={form.text} onChange={e => set({ text: e.target.value })}
              placeholder="Ищем сильного бэкендера на Python и FastAPI, нужен опыт с PostgreSQL и Kafka, высокие нагрузки…" />
          </Field>
          <div className="grid2">
            <Field label="Специализация">
              <select value={form.specialization_code} onChange={e => set({ specialization_code: e.target.value })}>
                {catalog.specializations.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
              </select>
            </Field>
            <Field label="Грейд" hint="Смежные грейды тоже попадут в подборку, с понижающим весом">
              <select value={form.grade} onChange={e => set({ grade: e.target.value })}>
                {catalog.grades.map(value => <option key={value} value={value}>{GRADE_LABEL[value as Grade]}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Требуемый стек">
            <SkillPicker all={catalog.skills} value={form.skills} onChange={skills => set({ skills })}
              suggestions={catalog.specializations.find(s => s.code === form.specialization_code)?.core_skills ?? []} />
          </Field>
          <div className="grid2">
            <Field label="Город"><input value={form.city} onChange={e => set({ city: e.target.value })} /></Field>
            <Field label="Формат работы">
              <select value={form.work_format} onChange={e => set({ work_format: e.target.value })}>
                <option value="">Не важно</option>
                {catalog.work_formats.map(value => <option key={value} value={value}>{FORMAT_LABEL[value] ?? value}</option>)}
              </select>
            </Field>
            <Field label="Вилка от, ₽"><input type="number" value={form.salary_from} onChange={e => set({ salary_from: e.target.value })} /></Field>
            <Field label="Вилка до, ₽"><input type="number" value={form.salary_to} onChange={e => set({ salary_to: e.target.value })} /></Field>
          </div>
          <label className="row" style={{ marginBottom: 16 }}>
            <input type="checkbox" checked={form.require_fsp} onChange={e => set({ require_fsp: e.target.checked })} />
            <span className="small">Только кандидаты с подтверждёнными достижениями ФСП</span>
          </label>
          <div className="row">
            <button className="btn primary" onClick={save} disabled={busy || !form.specialization_code}>
              {editing ? 'Сохранить' : 'Создать и собрать подборку'}
            </button>
            <button className="btn" onClick={() => setOpen(false)}>Отмена</button>
          </div>
        </Modal>
      )}
    </>
  );
}
