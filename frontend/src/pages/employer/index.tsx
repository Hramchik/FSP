import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { api, session } from '../../api';
import { Layout, NavItem } from '../../components/Layout';
import { Loader } from '../../components/ui';
import type { Catalog } from '../candidate/index';
import { CompanyPage } from './Company';
import { NeedsPage } from './Needs';
import { ShortlistPage } from './Shortlist';
import { BankPage } from './Bank';
import { EmployerInvitationsPage } from './Invitations';
import { EmployerVacanciesPage } from './Vacancies';
import { EmployerTasksPage } from './Tasks';

type Ctx = { company: any; catalog: Catalog; reload: () => Promise<void> };
const EmployerContext = createContext<Ctx | null>(null);
export const useEmployer = () => useContext(EmployerContext)!;

export function EmployerApp() {
  const [company, setCompany] = useState<any>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [counts, setCounts] = useState({ invitations: 0, applications: 0 });
  const [error, setError] = useState('');

  const reload = useCallback(async () => {
    const [profile, reference] = await Promise.all([api.get('/me/employer'), api.get('/catalog')]);
    setCompany(profile);
    setCatalog(reference);
  }, []);

  useEffect(() => {
    reload().catch(e => setError(e instanceof Error ? e.message : 'Ошибка'));
    Promise.all([
      api.get('/employer/invitations').catch(() => []),
      api.get('/employer/applications').catch(() => []),
    ]).then(([invitations, applications]) => setCounts({
      invitations: invitations.filter((i: any) => i.status === 'accepted').length,
      applications: applications.filter((a: any) => a.status === 'sent').length,
    }));
  }, [reload]);

  if (error) return <div className="main"><div className="note danger">{error}</div></div>;
  if (!company || !catalog) return <Loader />;
  if (session.role !== 'employer') return <Navigate to="/" replace />;

  const items: NavItem[] = [
    { to: '/employer', label: 'Потребности и подборки', group: 'Подбор' },
    { to: '/employer/bank', label: 'Банк кандидатов' },
    { to: '/employer/invitations', label: 'Приглашения', count: counts.invitations },
    { to: '/employer/vacancies', label: 'Вакансии и отклики', count: counts.applications, group: 'Дополнительно' },
    { to: '/employer/tasks', label: 'Регулярные задания' },
    { to: '/employer/company', label: 'Профиль компании' },
  ];

  return (
    <EmployerContext.Provider value={{ company, catalog, reload }}>
      <Layout items={items} email={company.email} roleLabel="Кабинет работодателя">
        <Routes>
          <Route index element={<NeedsPage />} />
          <Route path="needs/:needId/shortlist" element={<ShortlistPage />} />
          <Route path="bank" element={<BankPage />} />
          <Route path="invitations" element={<EmployerInvitationsPage />} />
          <Route path="vacancies" element={<EmployerVacanciesPage />} />
          <Route path="tasks" element={<EmployerTasksPage />} />
          <Route path="company" element={<CompanyPage />} />
          <Route path="*" element={<Navigate to="/employer" replace />} />
        </Routes>
      </Layout>
    </EmployerContext.Provider>
  );
}
