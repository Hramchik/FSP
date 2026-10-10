import React, { useRef, useState } from 'react';
import { api, dateRu, FORMAT_LABEL, GRADE_LABEL, Grade } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Field, Modal, SkillPicker, TagListEditor, useToast } from '../../components/ui';
import { useCandidate } from './index';

export function CandidateProfilePage() {
  const { profile, catalog, reload } = useCandidate();
  const toast = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({
    display_name: profile.display_name, city: profile.city, work_format: profile.work_format,
    bio: profile.bio, phone: profile.phone, telegram: profile.telegram, github: profile.github,
    skills: profile.skills as string[], roles: profile.roles as string[],
    soft_skills: profile.soft_skills as string[], years_experience: profile.years_experience,
    salary_expectation_from: profile.salary_expectation_from ?? '',
    salary_expectation_to: profile.salary_expectation_to ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [parsed, setParsed] = useState<any>(null);
  const [fspId, setFspId] = useState(profile.fsp?.fsp_id ?? '');

  const set = (patch: Partial<typeof form>) => setForm(previous => ({ ...previous, ...patch }));

  async function save() {
    setSaving(true);
    try {
      await api.put('/me/candidate', {
        ...form,
        years_experience: Number(form.years_experience) || 0,
        salary_expectation_from: form.salary_expectation_from === '' ? null : Number(form.salary_expectation_from),
        salary_expectation_to: form.salary_expectation_to === '' ? null : Number(form.salary_expectation_to),
      });
      await reload();
      toast('Профиль сохранён');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Ошибка', 'err');
    } finally {
      setSaving(false);
    }
  }

  async function uploadResume(file: File) {
    try {
      const result = await api.upload('/me/candidate/resume', file);
      setParsed(result.parsed);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Ошибка', 'err');
    }
  }

  async function applyParsed() {
    const file = fileInput.current?.files?.[0];
    if (!file) return;
    try {
      const form = new FormData();
      form.append('file', file);
      await fetch(`${(import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000/api/v1'}/me/candidate/resume?apply=true`, {
        method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('fsp.access')}` }, body: form,
      });
      setParsed(null);
      await reload();
      window.location.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Ошибка', 'err');
    }
  }

  async function linkFsp() {
    try {
      await api.post('/me/candidate/fsp-link', { fsp_id: fspId });
      await reload();
      toast('ФСП ID привязан');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Ошибка', 'err');
    }
  }

  const percent = Math.round((profile.completeness ?? 0) * 100);
  const suggestions = catalog.specializations
    .find(s => s.code === profile.categories?.[0]?.specialization)?.core_skills ?? [];

  return (
    <>
      <PageHead eyebrow="Кандидат" title="Профиль и резюме">
        Профиль — это то, что увидит работодатель в подборке. Грейд в нём не самоописание:
        его подтверждает тестирование, а достижения приходят из реестра ФСП.
      </PageHead>

      {profile.blocking_reasons.length > 0 && (
        <div className="note warn" style={{ marginBottom: 16 }}>
          <b>Профиль ещё не участвует в подборках:</b>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
            {profile.blocking_reasons.map((reason: string) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
      )}

      <div className="stack">
        <div className="grid3">
          <div className="stat"><span>Заполненность</span><b>{percent}%</b></div>
          <div className="stat"><span>Категории</span><b>{profile.categories.length}</b></div>
          <div className="stat"><span>Сила профиля ФСП</span><b>{profile.fsp?.strength ?? 0}</b></div>
        </div>

        <Card title="Подтверждённые категории"
          action={<a className="btn ghost sm" href="/candidate/testing">Пройти тест</a>}>
          {profile.categories.length === 0
            ? <p className="muted small">Категории пока нет. Она присваивается по результатам адаптивного теста и определяет, в какие подборки вы попадёте.</p>
            : <div className="stack tight">
                {profile.categories.map((category: any) => (
                  <div className="spread" key={category.specialization}
                    style={{ padding: '10px 12px', border: '1px solid var(--line)', borderRadius: 12, background: '#FAF8FC' }}>
                    <div>
                      <b>{category.specialization_name} · {GRADE_LABEL[category.grade as Grade]}</b>
                      <div className="faint">Подтверждено {dateRu(category.confirmed_at)}</div>
                    </div>
                    <span className="chip mono">θ {category.theta?.toFixed(2)}</span>
                  </div>
                ))}
              </div>}
        </Card>

        <Card title="Импорт и экспорт"
          action={<button className="btn sm" onClick={() => api.download('/me/candidate/profile.pdf', 'fsp-profile.pdf').catch(() => toast('Не удалось сформировать PDF', 'err'))}>
            Скачать PDF-профиль
          </button>}>
          <p className="small muted" style={{ marginBottom: 10 }}>
            Загрузите резюме в PDF — система распознает ФИО, контакты, стек, роли, софт-скиллы и стаж.
            Ничего не записывается в профиль без вашего подтверждения.
          </p>
          <input ref={fileInput} type="file" accept=".pdf,.txt,.md"
            onChange={e => e.target.files?.[0] && uploadResume(e.target.files[0])} />
        </Card>

        <Card title="Основное">
          <div className="grid2">
            <Field label="ФИО"><input value={form.display_name} onChange={e => set({ display_name: e.target.value })} /></Field>
            <Field label="Город"><input value={form.city} onChange={e => set({ city: e.target.value })} /></Field>
            <Field label="Формат работы">
              <select value={form.work_format} onChange={e => set({ work_format: e.target.value })}>
                {catalog.work_formats.map(value => <option key={value} value={value}>{FORMAT_LABEL[value] ?? value}</option>)}
              </select>
            </Field>
            <Field label="Опыт, лет">
              <input type="number" min={0} max={60} step={0.5} value={form.years_experience}
                onChange={e => set({ years_experience: e.target.value as any })} />
            </Field>
          </div>
          <Field label="О себе" hint="Короткое описание, которое увидит работодатель в карточке">
            <textarea value={form.bio} onChange={e => set({ bio: e.target.value })} />
          </Field>
        </Card>

        <Card title="Контакты"
          action={<span className="badge">Скрыты до вашего согласия</span>}>
          <p className="small muted" style={{ marginBottom: 12 }}>
            Работодатель не видит эти данные в подборке. Они раскрываются только после того,
            как вы примете приглашение или откликнетесь на вакансию сами.
          </p>
          <div className="grid3">
            <Field label="Телефон"><input value={form.phone} onChange={e => set({ phone: e.target.value })} /></Field>
            <Field label="Telegram"><input value={form.telegram} placeholder="@username" onChange={e => set({ telegram: e.target.value })} /></Field>
            <Field label="GitHub"><input value={form.github} placeholder="username" onChange={e => set({ github: e.target.value })} /></Field>
          </div>
        </Card>

        <Card title="Стек и роли">
          <Field label="Навыки" hint="По ним считается соответствие потребности работодателя">
            <SkillPicker all={catalog.skills} value={form.skills} suggestions={suggestions}
              onChange={skills => set({ skills })} />
          </Field>
          <Field label="Роли в команде">
            <TagListEditor value={form.roles} onChange={roles => set({ roles })} placeholder="Например: Код-ревью" />
          </Field>
          <Field label="Софт-скиллы">
            <TagListEditor value={form.soft_skills} onChange={soft_skills => set({ soft_skills })} placeholder="Например: Наставничество" />
          </Field>
        </Card>

        <Card title="Зарплатные ожидания">
          <div className="grid2">
            <Field label="От, ₽"><input type="number" min={0} value={form.salary_expectation_from}
              onChange={e => set({ salary_expectation_from: e.target.value as any })} /></Field>
            <Field label="До, ₽"><input type="number" min={0} value={form.salary_expectation_to}
              onChange={e => set({ salary_expectation_to: e.target.value as any })} /></Field>
          </div>
        </Card>

        <Card title="ФСП ID" action={profile.fsp?.linked ? <span className="chip fsp">Привязан</span> : null}>
          <p className="small muted" style={{ marginBottom: 12 }}>
            Привязка к идентификатору участника ФСП подтягивает результаты соревнований из реестра.
            Если истории нет — это нормально: профиль работает и без неё.
          </p>
          <div className="row">
            <input placeholder="FSP-000000" value={fspId} onChange={e => setFspId(e.target.value)} />
            <button className="btn purple" onClick={linkFsp} disabled={!fspId}>Привязать</button>
            {profile.fsp?.linked && (
              <button className="btn danger" onClick={async () => { await api.del('/me/candidate/fsp-link'); setFspId(''); await reload(); }}>
                Отвязать
              </button>
            )}
          </div>
          {profile.fsp?.linked && profile.fsp.count > 0 && (
            <div className="stack tight" style={{ marginTop: 14 }}>
              <div className="row wrap">
                <span className="chip fsp">Сила профиля {profile.fsp.strength}</span>
                <span className="chip">{profile.fsp.count} результатов</span>
                <span className="chip">Лучший уровень: {profile.fsp.best_level}</span>
              </div>
              <ul className="reasons">
                {profile.fsp.highlights.map((text: string) => <li key={text}><span>{text}</span><b>✓</b></li>)}
              </ul>
            </div>
          )}
          {profile.fsp?.linked && profile.fsp.count === 0 && (
            <div className="note info" style={{ marginTop: 12 }}>
              По этому ФСП ID в реестре пока нет зачтённых результатов.
            </div>
          )}
        </Card>

        <div className="row">
          <button className="btn primary" onClick={save} disabled={saving}>
            {saving ? 'Сохраняем…' : 'Сохранить профиль'}
          </button>
        </div>
      </div>

      {parsed && (
        <Modal title="Распознано из резюме" onClose={() => setParsed(null)}>
          <div className="stack tight">
            <ParsedRow label="ФИО" value={parsed.full_name} />
            <ParsedRow label="Город" value={parsed.city} />
            <ParsedRow label="Телефон" value={parsed.phone} />
            <ParsedRow label="Telegram" value={parsed.telegram} />
            <ParsedRow label="GitHub" value={parsed.github} />
            <ParsedRow label="Стаж" value={parsed.years_experience ? `${parsed.years_experience} лет` : ''} />
            <ParsedRow label="Стек" value={parsed.skill_labels?.join(', ')} />
            <ParsedRow label="Роли" value={parsed.roles?.join(', ')} />
            <ParsedRow label="Софт-скиллы" value={parsed.soft_skills?.join(', ')} />
          </div>
          {parsed.warnings?.length > 0 && (
            <div className="note warn" style={{ marginTop: 14 }}>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {parsed.warnings.map((warning: string) => <li key={warning}>{warning}</li>)}
              </ul>
            </div>
          )}
          <div className="row" style={{ marginTop: 16 }}>
            <button className="btn primary" onClick={applyParsed}>Перенести в профиль</button>
            <button className="btn" onClick={() => setParsed(null)}>Отмена</button>
          </div>
        </Modal>
      )}
    </>
  );
}

function ParsedRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="spread" style={{ borderBottom: '1px solid var(--line)', padding: '7px 0' }}>
      <span className="small muted">{label}</span>
      <b className="small" style={{ textAlign: 'right' }}>{value || <span className="faint">не распознано</span>}</b>
    </div>
  );
}
