import React, { useState } from 'react';
import { api } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Field, useToast } from '../../components/ui';
import { useEmployer } from './index';

export function CompanyPage() {
  const { company, reload } = useEmployer();
  const toast = useToast();
  const [form, setForm] = useState({
    company_name: company.company_name, description: company.description, contact: company.contact,
    website: company.website, industry: company.industry, city: company.city, team_size: company.team_size,
  });
  const [saving, setSaving] = useState(false);
  const set = (patch: Partial<typeof form>) => setForm(previous => ({ ...previous, ...patch }));

  async function save() {
    setSaving(true);
    try {
      await api.put('/me/employer', form);
      await reload();
      toast('Профиль компании сохранён');
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setSaving(false); }
  }

  return (
    <>
      <PageHead eyebrow="Работодатель" title="Профиль компании">
        Название и описание компании кандидат видит в приглашении — до того, как решит
        раскрывать контакты. Без заполненного названия приглашения не отправляются.
      </PageHead>

      <div className="stack">
        <Card title="Организация">
          <div className="grid2">
            <Field label="Название"><input value={form.company_name} onChange={e => set({ company_name: e.target.value })} /></Field>
            <Field label="Направление деятельности"><input value={form.industry} placeholder="Финтех, e-commerce…" onChange={e => set({ industry: e.target.value })} /></Field>
            <Field label="Город"><input value={form.city} onChange={e => set({ city: e.target.value })} /></Field>
            <Field label="Размер команды"><input value={form.team_size} placeholder="120 человек" onChange={e => set({ team_size: e.target.value })} /></Field>
          </div>
          <Field label="Чем занимается команда" hint="Этот текст увидит кандидат в приглашении">
            <textarea value={form.description} onChange={e => set({ description: e.target.value })} />
          </Field>
        </Card>

        <Card title="Контакты для связи">
          <div className="grid2">
            <Field label="Контакт для кандидатов" hint="E-mail или мессенджер, который попадёт в приглашение">
              <input value={form.contact} onChange={e => set({ contact: e.target.value })} />
            </Field>
            <Field label="Сайт"><input value={form.website} onChange={e => set({ website: e.target.value })} /></Field>
          </div>
        </Card>

        <div><button className="btn primary" onClick={save} disabled={saving}>Сохранить</button></div>
      </div>
    </>
  );
}
