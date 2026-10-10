import React from 'react';
import { FORMAT_LABEL } from '../../api';

/** The employer-facing candidate card, shared by the shortlist and the bank. */
export function CandidateBody({ candidate, matched = [], missing = [] }: {
  candidate: any; matched?: string[]; missing?: string[];
}) {
  const matchedSet = new Set(matched);
  const missingSet = new Set(missing);
  const labelFor = (code: string, index: number) => candidate.skill_labels?.[index] ?? code;

  return (
    <div className="stack tight">
      <div className="row wrap">
        <span className="chip match">{candidate.category}</span>
        {candidate.theta != null && <span className="chip mono">θ {candidate.theta.toFixed(2)}</span>}
        {candidate.years_experience > 0 && <span className="chip">{candidate.years_experience} лет опыта</span>}
        {candidate.city && <span className="chip">{candidate.city}</span>}
        {candidate.work_format && <span className="chip">{FORMAT_LABEL[candidate.work_format] ?? candidate.work_format}</span>}
        {candidate.salary_expectation && <span className="chip">Ожидания: {candidate.salary_expectation}</span>}
      </div>

      {candidate.bio && <p className="small muted">{candidate.bio}</p>}

      {candidate.skills?.length > 0 && (
        <div className="chips">
          {candidate.skills.map((code: string, index: number) => (
            <span key={code} className={`chip${matchedSet.has(code) ? ' match' : ''}`}>{labelFor(code, index)}</span>
          ))}
          {missing.map(code => <span key={`miss-${code}`} className="chip miss">нет: {code}</span>)}
        </div>
      )}

      {(candidate.roles?.length > 0 || candidate.soft_skills?.length > 0) && (
        <p className="small muted">
          {candidate.roles?.length > 0 && <>Роли: {candidate.roles.join(', ')}. </>}
          {candidate.soft_skills?.length > 0 && <>Софт-скиллы: {candidate.soft_skills.join(', ')}.</>}
        </p>
      )}

      {candidate.fsp?.linked && candidate.fsp.count > 0 && (
        <div className="stack tight" style={{ padding: 12, background: '#FAF6FC', border: '1px solid #EADCF2', borderRadius: 12 }}>
          <div className="row wrap">
            <span className="chip fsp">ФСП · сила {candidate.fsp.strength}</span>
            <span className="chip">{candidate.fsp.podium_count} призовых</span>
            <span className="chip">Лучший уровень: {candidate.fsp.best_level}</span>
          </div>
          <ul className="reasons">
            {candidate.fsp.highlights.map((text: string) => <li key={text}><span>{text}</span><b>✓</b></li>)}
          </ul>
        </div>
      )}

      {candidate.contacts ? (
        <div className="note ok">
          <b>Контакты открыты</b> ({candidate.contacts.reason === 'invitation_accepted' ? 'кандидат принял приглашение' : 'кандидат откликнулся'}):{' '}
          {[candidate.contacts.email, candidate.contacts.phone, candidate.contacts.telegram, candidate.contacts.github]
            .filter(Boolean).join(' · ')}
        </div>
      ) : (
        <p className="faint">🔒 {candidate.contacts_locked_reason ?? 'Контакты скрыты до согласия кандидата'}</p>
      )}
    </div>
  );
}
