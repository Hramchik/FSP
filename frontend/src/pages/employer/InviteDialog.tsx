import React, { useState } from 'react';
import { api, salaryRange } from '../../api';
import { Field, Modal, useToast } from '../../components/ui';

export function InviteDialog({ candidate, needId, vacancies, defaults, onClose, onSent }: {
  candidate: any;
  needId?: number;
  vacancies: any[];
  defaults: { contact: string; salaryFrom?: number | null; salaryTo?: number | null };
  onClose: () => void;
  onSent: () => void;
}) {
  const toast = useToast();
  const [form, setForm] = useState({
    offer_description: '',
    salary_from: defaults.salaryFrom ?? '',
    salary_to: defaults.salaryTo ?? '',
    contact_method: defaults.contact ?? '',
    vacancy_id: '' as string,
  });
  const [busy, setBusy] = useState(false);
  const set = (patch: Partial<typeof form>) => setForm(previous => ({ ...previous, ...patch }));

  async function send() {
    setBusy(true);
    try {
      await api.post('/invitations', {
        candidate_id: candidate.candidate_id,
        need_id: needId ?? null,
        vacancy_id: form.vacancy_id ? Number(form.vacancy_id) : null,
        offer_description: form.offer_description,
        salary_from: Number(form.salary_from),
        salary_to: Number(form.salary_to),
        contact_method: form.contact_method,
      });
      toast('Приглашение отправлено');
      onSent();
      onClose();
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setBusy(false); }
  }

  const valid = form.offer_description.trim().length >= 10 &&
    Number(form.salary_from) > 0 && Number(form.salary_to) >= Number(form.salary_from) &&
    form.contact_method.trim().length >= 3;

  return (
    <Modal title={`Приглашение: ${candidate.display_name}`} onClose={onClose}>
      <div className="note info" style={{ marginBottom: 14 }}>
        Кандидат увидит условия до начала общения. Ваши контакты он получит сразу,
        свои — передаст только если примет приглашение.
      </div>

      <Field label="Предложение" hint="Что за команда, над чем работа, что ждёте от человека">
        <textarea value={form.offer_description} onChange={e => set({ offer_description: e.target.value })}
          placeholder="Платформенная команда из шести человек, Python/FastAPI, Kafka, Kubernetes. Удалённо, гибкий график." />
      </Field>

      <div className="grid2">
        <Field label="Зарплата от, ₽"><input type="number" value={form.salary_from} onChange={e => set({ salary_from: e.target.value })} /></Field>
        <Field label="Зарплата до, ₽"><input type="number" value={form.salary_to} onChange={e => set({ salary_to: e.target.value })} /></Field>
      </div>
      <p className="faint" style={{ marginTop: -6, marginBottom: 14 }}>
        Вилка обязательна: {salaryRange(Number(form.salary_from) || null, Number(form.salary_to) || null)}
      </p>

      <Field label="Как с вами связаться"><input value={form.contact_method} onChange={e => set({ contact_method: e.target.value })} /></Field>

      {vacancies.length > 0 && (
        <Field label="Привязать к вакансии" hint="Необязательно — приглашение работает и без опубликованной вакансии">
          <select value={form.vacancy_id} onChange={e => set({ vacancy_id: e.target.value })}>
            <option value="">Без вакансии</option>
            {vacancies.map(vacancy => <option key={vacancy.id} value={vacancy.id}>{vacancy.title}</option>)}
          </select>
        </Field>
      )}

      <div className="row">
        <button className="btn primary" onClick={send} disabled={busy || !valid}>Отправить приглашение</button>
        <button className="btn" onClick={onClose}>Отмена</button>
      </div>
    </Modal>
  );
}
