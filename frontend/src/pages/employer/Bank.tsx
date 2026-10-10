import React, { useEffect, useState } from 'react';
import { api, FORMAT_LABEL, GRADE_LABEL, Grade } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Field, Loader, SkillPicker, StatusBadge, useToast } from '../../components/ui';
import { CandidateBody } from './CandidateCard';
import { InviteDialog } from './InviteDialog';
import { useEmployer } from './index';

export function BankPage() {
  const { catalog, company } = useEmployer();
  const toast = useToast();
  const [query, setQuery] = useState({
    specialization_code: '', grades: [] as string[], skills: [] as string[],
    city: '', work_format: '', fsp_only: false, query: '', limit: 30, offset: 0,
  });
  const [result, setResult] = useState<any>(null);
  const [vacancies, setVacancies] = useState<any[]>([]);
  const [inviting, setInviting] = useState<any>(null);

  async function search(next = query) {
    try {
      setResult(await api.post('/candidates/search', {
        ...next,
        specialization_code: next.specialization_code || null,
      }));
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
  }

  useEffect(() => {
    search();
    api.get('/employer/vacancies').then(setVacancies).catch(() => {});
  }, []);

  const set = (patch: Partial<typeof query>) => {
    const next = { ...query, ...patch, offset: 0 };
    setQuery(next);
    return next;
  };

  return (
    <>
      <PageHead eyebrow="Работодатель" title="Банк кандидатов">
        Прямой поиск по всей базе — дополнение к подборке. Здесь тоже видны только люди
        с подтверждённой категорией и открытым профилем, а контакты по-прежнему закрыты.
      </PageHead>

      <div className="grid2" style={{ gridTemplateColumns: '300px 1fr', alignItems: 'start' }}>
        <Card title="Фильтры">
          <Field label="Свободный запрос" hint="Например: «нужен питонист с кафкой» — стек распознается из текста">
            <input value={query.query} onChange={e => setQuery({ ...query, query: e.target.value })}
              onKeyDown={e => e.key === 'Enter' && search()} />
          </Field>
          <Field label="Специализация">
            <select value={query.specialization_code}
              onChange={e => search(set({ specialization_code: e.target.value }))}>
              <option value="">Все</option>
              {catalog.specializations.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Грейд">
            <div className="chips">
              {catalog.grades.map(value => {
                const active = query.grades.includes(value);
                return (
                  <button key={value} type="button" className={`chip${active ? ' match' : ''}`}
                    onClick={() => search(set({
                      grades: active ? query.grades.filter(g => g !== value) : [...query.grades, value],
                    }))}>{GRADE_LABEL[value as Grade]}</button>
                );
              })}
            </div>
          </Field>
          <Field label="Навыки">
            <SkillPicker all={catalog.skills} value={query.skills}
              onChange={skills => search(set({ skills }))} />
          </Field>
          <Field label="Формат работы">
            <select value={query.work_format} onChange={e => search(set({ work_format: e.target.value }))}>
              <option value="">Любой</option>
              {catalog.work_formats.map(value => <option key={value} value={value}>{FORMAT_LABEL[value] ?? value}</option>)}
            </select>
          </Field>
          <Field label="Город"><input value={query.city} onChange={e => setQuery({ ...query, city: e.target.value })} /></Field>
          <label className="row" style={{ marginBottom: 14 }}>
            <input type="checkbox" checked={query.fsp_only} onChange={e => search(set({ fsp_only: e.target.checked }))} />
            <span className="small">Только с достижениями ФСП</span>
          </label>
          <button className="btn primary wide" onClick={() => search()}>Найти</button>
        </Card>

        <div className="stack">
          {!result ? <Loader /> : (
            <>
              <div className="stat" style={{ maxWidth: 200 }}><span>Найдено</span><b>{result.total}</b></div>
              {result.items.length === 0 && (
                <Card><Empty title="Никого не нашлось">Ослабьте фильтры или очистите свободный запрос.</Empty></Card>
              )}
              {result.items.map((candidate: any) => (
                <section className="card" key={candidate.candidate_id}>
                  <header className="card-head">
                    <div><h3>{candidate.display_name}</h3><span className="faint">{candidate.category}</span></div>
                    {candidate.invitation_status
                      ? <StatusBadge status={candidate.invitation_status} />
                      : <button className="btn primary sm" onClick={() => setInviting(candidate)}>Пригласить</button>}
                  </header>
                  <div className="card-pad"><CandidateBody candidate={candidate} /></div>
                </section>
              ))}
            </>
          )}
        </div>
      </div>

      {inviting && (
        <InviteDialog candidate={inviting} vacancies={vacancies}
          defaults={{ contact: company.contact || company.email }}
          onClose={() => setInviting(null)} onSent={() => search()} />
      )}
    </>
  );
}
