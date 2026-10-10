import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

/* ---------- toast ---------- */

type Toast = { text: string; kind: 'ok' | 'err' } | null;
const ToastContext = createContext<(text: string, kind?: 'ok' | 'err') => void>(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastHost({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<Toast>(null);
  const push = useCallback((text: string, kind: 'ok' | 'err' = 'ok') => setToast({ text, kind }), []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(timer);
  }, [toast]);
  return (
    <ToastContext.Provider value={push}>
      {children}
      {toast && <div className={`toast ${toast.kind}`} role="status">{toast.text}</div>}
    </ToastContext.Provider>
  );
}

/* ---------- form primitives ---------- */

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <span className="hint">{hint}</span>}
    </label>
  );
}

export function Card({ title, action, children, pad = true }: {
  title?: string; action?: React.ReactNode; children: React.ReactNode; pad?: boolean;
}) {
  return (
    <section className="card">
      {title && <header className="card-head"><h3>{title}</h3>{action}</header>}
      <div className={pad ? 'card-pad' : ''}>{children}</div>
    </section>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return <div className="empty"><h3>{title}</h3>{children && <p className="small">{children}</p>}</div>;
}

export function Loader({ text = 'Загрузка…' }: { text?: string }) {
  return <div className="loader">{text}</div>;
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <header className="card-head">
          <h3>{title}</h3>
          <button className="btn ghost sm" onClick={onClose} aria-label="Закрыть">✕</button>
        </header>
        <div className="card-pad">{children}</div>
      </div>
    </div>
  );
}

/* ---------- skill picker ---------- */

export type SkillOption = { code: string; label: string };

export function SkillPicker({ all, value, onChange, suggestions = [] }: {
  all: SkillOption[]; value: string[]; onChange: (next: string[]) => void; suggestions?: SkillOption[];
}) {
  const [query, setQuery] = useState('');
  const chosen = new Set(value);
  const pool = query.trim()
    ? all.filter(s => !chosen.has(s.code) && s.label.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 8)
    : suggestions.filter(s => !chosen.has(s.code)).slice(0, 10);
  const labelOf = (code: string) => all.find(s => s.code === code)?.label ?? code;

  return (
    <div className="stack tight">
      <div className="chips">
        {value.length === 0 && <span className="faint">Навыки не выбраны</span>}
        {value.map(code => (
          <button key={code} type="button" className="chip match"
            onClick={() => onChange(value.filter(c => c !== code))} title="Убрать">
            {labelOf(code)} ✕
          </button>
        ))}
      </div>
      <input placeholder="Найти навык — например, Kafka" value={query} onChange={e => setQuery(e.target.value)} />
      {pool.length > 0 && (
        <div className="chips">
          {pool.map(s => (
            <button key={s.code} type="button" className="chip"
              onClick={() => { onChange([...value, s.code]); setQuery(''); }}>+ {s.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- editable string list ---------- */

export function TagListEditor({ value, onChange, placeholder }: {
  value: string[]; onChange: (next: string[]) => void; placeholder: string;
}) {
  const [draft, setDraft] = useState('');
  const add = () => {
    const text = draft.trim();
    if (text && !value.includes(text)) onChange([...value, text]);
    setDraft('');
  };
  return (
    <div className="stack tight">
      <div className="chips">
        {value.length === 0 && <span className="faint">Пока пусто</span>}
        {value.map(item => (
          <button key={item} type="button" className="chip" onClick={() => onChange(value.filter(v => v !== item))}>
            {item} ✕
          </button>
        ))}
      </div>
      <div className="row">
        <input placeholder={placeholder} value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }} />
        <button type="button" className="btn sm" onClick={add}>Добавить</button>
      </div>
    </div>
  );
}

/* ---------- score explainability ---------- */

const COMPONENT_LABEL: Record<string, string> = {
  category: 'Категория',
  skills: 'Стек',
  proof: 'Подтверждение тестом',
  fsp: 'Достижения ФСП',
  activity: 'Актуальность профиля',
};
const ORDER = ['category', 'skills', 'proof', 'fsp', 'activity'];

export function ScoreBar({ components }: { components: Record<string, number> }) {
  const total = ORDER.reduce((sum, key) => sum + (components[key] ?? 0), 0) || 1;
  return (
    <div className="stack tight">
      <div className="scorebar" aria-hidden="true">
        {ORDER.map(key => {
          const value = components[key] ?? 0;
          return value > 0
            ? <i key={key} className={`sc-${key}`} style={{ width: `${(value / total) * 100}%` }} />
            : null;
        })}
      </div>
      <div className="legend">
        {ORDER.map(key => (components[key] ?? 0) > 0 && (
          <span key={key}><i className={`sc-${key}`} />{COMPONENT_LABEL[key]} {components[key].toFixed(1)}</span>
        ))}
      </div>
    </div>
  );
}

export function Reasons({ items }: { items: { code: string; text: string; contribution: number }[] }) {
  return (
    <ul className="reasons">
      {items.map((reason, index) => (
        <li key={`${reason.code}-${index}`}><span>{reason.text}</span><b>+{reason.contribution.toFixed(1)}</b></li>
      ))}
    </ul>
  );
}

/* ---------- status badges ---------- */

const INVITATION_STATUS: Record<string, { text: string; kind: string }> = {
  sent: { text: 'Отправлено', kind: 'live' },
  viewed: { text: 'Просмотрено', kind: '' },
  accepted: { text: 'Принято', kind: 'ok' },
  declined: { text: 'Отклонено', kind: 'danger' },
};
const APPLICATION_STATUS: Record<string, { text: string; kind: string }> = {
  sent: { text: 'Отправлен', kind: 'live' },
  viewed: { text: 'Просмотрен', kind: '' },
  accepted: { text: 'Принят', kind: 'ok' },
  declined: { text: 'Отклонён', kind: 'danger' },
};

export function StatusBadge({ status, kind = 'invitation' }: { status: string; kind?: 'invitation' | 'application' }) {
  const map = kind === 'invitation' ? INVITATION_STATUS : APPLICATION_STATUS;
  const entry = map[status] ?? { text: status, kind: '' };
  return <span className={`badge ${entry.kind}`}>{entry.text}</span>;
}
