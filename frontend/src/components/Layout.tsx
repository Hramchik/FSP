import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { session } from '../api';

export type NavItem = { to: string; label: string; count?: number; group?: string };

export function Layout({ items, email, roleLabel, children }: {
  items: NavItem[]; email: string; roleLabel: string; children: React.ReactNode;
}) {
  const navigate = useNavigate();
  let lastGroup: string | undefined;

  return (
    <div className="shell">
      <nav className="sidebar">
        <div className="brand">
          <Mark />
          <div><b>ФСП Career</b><small>{roleLabel}</small></div>
        </div>
        {items.map(item => {
          const header = item.group && item.group !== lastGroup ? item.group : null;
          lastGroup = item.group ?? lastGroup;
          return (
            <React.Fragment key={item.to}>
              {header && <div className="sep">{header}</div>}
              <NavLink to={item.to} className={({ isActive }) => `navlink${isActive ? ' active' : ''}`} end>
                <span>{item.label}</span>
                {item.count ? <span className="count">{item.count}</span> : null}
              </NavLink>
            </React.Fragment>
          );
        })}
        <div className="foot">
          <b>{email}</b>
          <button className="btn ghost sm" style={{ paddingLeft: 0 }}
            onClick={() => { session.clear(); navigate('/'); }}>Выйти</button>
        </div>
      </nav>
      <main className="main">{children}</main>
    </div>
  );
}

export function PageHead({ eyebrow, title, children }: {
  eyebrow: string; title: string; children?: React.ReactNode;
}) {
  return (
    <header className="page-head">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}

/** Six nodes around a centre — a nod to the ФСП mark without copying it. */
export function Mark({ size = 30 }: { size?: number }) {
  const nodes = [0, 60, 120, 180, 240, 300].map(angle => {
    const radians = (angle * Math.PI) / 180;
    return { x: 16 + Math.cos(radians) * 10.5, y: 16 + Math.sin(radians) * 10.5 };
  });
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" style={{ flex: 'none' }}>
      {nodes.map((node, index) => (
        <line key={index} x1="16" y1="16" x2={node.x} y2={node.y} stroke="currentColor" strokeWidth="1.4" opacity=".55" />
      ))}
      {nodes.map((node, index) => (
        <circle key={index} cx={node.x} cy={node.y} r="2.6" fill="currentColor" opacity={index % 2 ? '.75' : '1'} />
      ))}
      <circle cx="16" cy="16" r="4" fill="currentColor" />
    </svg>
  );
}
