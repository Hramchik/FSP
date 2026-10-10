import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, FORMAT_LABEL, GRADE_LABEL, Grade } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Field, Loader, Reasons, ScoreBar, SkillPicker, StatusBadge, useToast } from '../../components/ui';
import { CandidateBody } from './CandidateCard';
import { InviteDialog } from './InviteDialog';
import { useEmployer } from './index';

const DEFAULT_REFINEMENT = {
  min_score: null as number | null, grades: [] as string[], skills: [] as string[],
  city: '', work_format: '', fsp_only: false, hide_invited: false, sort: 'score',
};

export function ShortlistPage() {
  const { needId } = useParams();
  const { catalog, company } = useEmployer();
  const toast = useToast();
  const navigate = useNavigate();

  const [need, setNeed] = useState<any>(null);
  const [shortlist, setShortlist] = useState<any>(null);
  const [refinement, setRefinement] = useState({ ...DEFAULT_REFINEMENT });
  const [vacancies, setVacancies] = useState<any[]>([]);
  const [inviting, setInviting] = useState<any>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const loaded = await api.get(`/needs/${needId}`);
    setNeed(loaded);
    if (!loaded.shortlist_id) {
      const built = await api.post(`/needs/${needId}/shortlist`);
      setShortlist(built);
      setRefinement({ ...DEFAULT_REFINEMENT, ...built.refinement });
    } else {
      const existing = await api.get(`/shortlists/${loaded.shortlist_id}`);
      setShortlist(existing);
      setRefinement({ ...DEFAULT_REFINEMENT, ...existing.refinement });
    }
    setVacancies(await api.get('/employer/vacancies').catch(() => []));
  }

  useEffect(() => { load().catch(e => toast(e.message, 'err')); }, [needId]);

  async function applyRefinement(next: typeof refinement) {
    setBusy(true);
    try {
      setRefinement(next);
      setShortlist(await api.post(`/shortlists/${shortlist.shortlist_id}/refine`, next));
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
    finally { setBusy(false); }
  }

  async function reset() {
    setBusy(true);
    try {
      setRefinement({ ...DEFAULT_REFINEMENT });
      setShortlist(await api.post(`/shortlists/${shortlist.shortlist_id}/reset`));
    } finally { setBusy(false); }
  }

  async function rebuild() {
    setBusy(true);
    try {
      const built = await api.post(`/needs/${needId}/shortlist`);
      setShortlist(built);
      setRefinement({ ...DEFAULT_REFINEMENT });
      toast('Подборка пересобрана по текущему составу банка');
    } finally { setBusy(false); }
  }

  if (!need || !shortlist) return <Loader />;
  const narrowed = shortlist.total_shown < shortlist.total_in_pool;

  return (
    <>
      <PageHead eyebrow="Подборка" title={need.title}>
        Список собран по категориям, а не по резюме. Позиция внутри категории определяется
        силой подтверждённого профиля — результатом теста и достижениями ФСП.
      </PageHead>

      <div className="grid2" style={{ gridTemplateColumns: '300px 1fr', alignItems: 'start' }}>
        <div className="stack">
          <Card title="Как собрана выдача">
            <ul className="reasons" style={{ marginBottom: 12 }}>
              {shortlist.routed_categories.map((line: string) => <li key={line}><span>{line}</span><b>→</b></li>)}
            </ul>
            <div className="legend">
              {Object.entries(shortlist.weights).map(([key, value]) => (
                <span key={key}><i className={`sc-${key}`} />макс. {String(value)}</span>
              ))}
            </div>
            <p className="faint" style={{ marginTop: 10 }}>Версия весов: {shortlist.weights_version}</p>
          </Card>

          <Card title="Уточнить запрос">
            <p className="faint" style={{ marginBottom: 12 }}>
              Фильтры сужают уже полученную подборку и не пересобирают её — можно вернуться
              к исходному списку одной кнопкой.
            </p>
            <Field label={`Минимальный балл: ${refinement.min_score ?? 0}`}>
              <input type="range" min={0} max={100} step={5} value={refinement.min_score ?? 0}
                onChange={e => setRefinement({ ...refinement, min_score: Number(e.target.value) || null })}
                onMouseUp={() => applyRefinement(refinement)}
                onTouchEnd={() => applyRefinement(refinement)} />
            </Field>
            <Field label="Грейды">
              <div className="chips">
                {catalog.grades.map(value => {
                  const active = refinement.grades.includes(value);
                  return (
                    <button key={value} type="button" className={`chip${active ? ' match' : ''}`}
                      onClick={() => applyRefinement({
                        ...refinement,
                        grades: active ? refinement.grades.filter(g => g !== value) : [...refinement.grades, value],
                      })}>{GRADE_LABEL[value as Grade]}</button>
                  );
                })}
              </div>
            </Field>
            <Field label="Обязательные навыки">
              <SkillPicker all={catalog.skills} value={refinement.skills}
                suggestions={catalog.specializations.find(s => s.code === need.specialization_code)?.core_skills ?? []}
                onChange={skills => applyRefinement({ ...refinement, skills })} />
            </Field>
            <Field label="Формат работы">
              <select value={refinement.work_format}
                onChange={e => applyRefinement({ ...refinement, work_format: e.target.value })}>
                <option value="">Любой</option>
                {catalog.work_formats.map(value => <option key={value} value={value}>{FORMAT_LABEL[value] ?? value}</option>)}
              </select>
            </Field>
            <Field label="Сортировка">
              <select value={refinement.sort} onChange={e => applyRefinement({ ...refinement, sort: e.target.value })}>
                <option value="score">По общему баллу</option>
                <option value="proof">По подтверждению тестом</option>
                <option value="fsp">По достижениям ФСП</option>
                <option value="experience">По опыту</option>
              </select>
            </Field>
            <label className="row" style={{ marginBottom: 8 }}>
              <input type="checkbox" checked={refinement.fsp_only}
                onChange={e => applyRefinement({ ...refinement, fsp_only: e.target.checked })} />
              <span className="small">Только с достижениями ФСП</span>
            </label>
            <label className="row" style={{ marginBottom: 14 }}>
              <input type="checkbox" checked={refinement.hide_invited}
                onChange={e => applyRefinement({ ...refinement, hide_invited: e.target.checked })} />
              <span className="small">Скрыть уже приглашённых</span>
            </label>
            <div className="row">
              <button className="btn sm" onClick={reset} disabled={busy}>Сбросить фильтры</button>
              <button className="btn sm" onClick={rebuild} disabled={busy}>Пересобрать</button>
            </div>
          </Card>

          <button className="btn ghost sm" onClick={() => navigate('/employer')}>← Ко всем потребностям</button>
        </div>

        <div className="stack">
          <div className="spread">
            <div className="row wrap">
              <div className="stat" style={{ minWidth: 120 }}><span>В подборке</span><b>{shortlist.total_shown}</b></div>
              <div className="stat" style={{ minWidth: 120 }}><span>Всего найдено</span><b>{shortlist.total_in_pool}</b></div>
            </div>
            {narrowed && <span className="badge warn">Фильтры сужают выдачу</span>}
          </div>

          {shortlist.items.length === 0 && (
            <Card><Empty title="Под эти условия никто не подошёл">
              {shortlist.total_in_pool > 0
                ? 'Сбросьте фильтры, чтобы вернуться к исходной подборке.'
                : 'В банке пока нет кандидатов с подтверждённой категорией по этой специализации.'}
            </Empty></Card>
          )}

          {shortlist.items.map((item: any) => (
            <section className="card" key={item.candidate.candidate_id}>
              <header className="card-head">
                <div className="row">
                  <span className={`rank${item.rank <= 3 ? ' top' : ''}`}>{item.rank}</span>
                  <div>
                    <h3>{item.candidate.display_name}</h3>
                    <span className="faint">{item.category}</span>
                  </div>
                </div>
                <div className="row">
                  <div style={{ textAlign: 'right' }}>
                    <div className="score">{item.score.toFixed(1)}<small> / 100</small></div>
                  </div>
                  {item.candidate.invitation_status
                    ? <StatusBadge status={item.candidate.invitation_status} />
                    : <button className="btn primary sm" onClick={() => setInviting(item.candidate)}>Пригласить</button>}
                </div>
              </header>
              <div className="card-pad stack">
                <ScoreBar components={item.components} />
                <CandidateBody candidate={item.candidate}
                  matched={item.matched_skills} missing={item.missing_skills} />
                <button className="btn ghost sm" style={{ justifySelf: 'start' }}
                  onClick={() => setExpanded(expanded === item.candidate.candidate_id ? null : item.candidate.candidate_id)}>
                  {expanded === item.candidate.candidate_id ? 'Скрыть обоснование' : 'Почему этот кандидат здесь'}
                </button>
                {expanded === item.candidate.candidate_id && <Reasons items={item.reasons} />}
              </div>
            </section>
          ))}
        </div>
      </div>

      {inviting && (
        <InviteDialog candidate={inviting} needId={Number(needId)} vacancies={vacancies}
          defaults={{ contact: company.contact || company.email, salaryFrom: need.salary_from, salaryTo: need.salary_to }}
          onClose={() => setInviting(null)}
          onSent={() => load()} />
      )}
    </>
  );
}
