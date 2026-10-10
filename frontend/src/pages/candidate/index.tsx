import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { api, session } from '../../api';
import { Layout, NavItem } from '../../components/Layout';
import { Loader } from '../../components/ui';
import { CandidateProfilePage } from './Profile';
import { TestingPage } from './Testing';
import { InvitationsPage } from './Invitations';
import { VacanciesPage } from './Vacancies';
import { SpotTasksPage } from './SpotTasks';
import { SettingsPage } from './Settings';

export type Catalog = {
  specializations: { code: string; name: string; core_skills: { code: string; label: string }[] }[];
  grades: string[];
  skills: { code: string; label: string }[];
  work_formats: string[];
};

type Ctx = {
  profile: any;
  catalog: Catalog;
  reload: () => Promise<void>;
  setProfile: (next: any) => void;
};

const CandidateContext = createContext<Ctx | null>(null);
export const useCandidate = () => useContext(CandidateContext)!;

export function CandidateApp() {
  const [profile, setProfile] = useState<any>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [counts, setCounts] = useState({ invitations: 0, tasks: 0 });
  const [error, setError] = useState('');

  const reload = useCallback(async () => {
    const [me, reference] = await Promise.all([api.get('/me/candidate'), api.get('/catalog')]);
    setProfile(me);
    setCatalog(reference);
  }, []);

  useEffect(() => {
    reload().catch(e => setError(e instanceof Error ? e.message : 'Ошибка'));
    // Badge counts are informational, so a failure here must not block the cabinet.
    Promise.all([api.get('/me/invitations').catch(() => []), api.get('/me/spot-tasks').catch(() => [])])
      .then(([invitations, tasks]) => setCounts({
        invitations: invitations.filter((i: any) => i.status !== 'accepted' && i.status !== 'declined').length,
        tasks: tasks.filter((t: any) => t.status === 'assigned').length,
      }));
  }, [reload]);

  if (error) return <div className="main"><div className="note danger">{error}</div></div>;
  if (!profile || !catalog) return <Loader />;
  if (session.role !== 'candidate') return <Navigate to="/" replace />;

  const items: NavItem[] = [
    { to: '/candidate', label: 'Профиль и резюме', group: 'Мой профиль' },
    { to: '/candidate/testing', label: 'Опрос и тестирование' },
    { to: '/candidate/settings', label: 'Приватность' },
    { to: '/candidate/invitations', label: 'Приглашения', count: counts.invitations, group: 'Работа' },
    { to: '/candidate/tasks', label: 'Регулярные задания', count: counts.tasks },
    { to: '/candidate/vacancies', label: 'Вакансии и отклики' },
  ];

  return (
    <CandidateContext.Provider value={{ profile, catalog, reload, setProfile }}>
      <Layout items={items} email={profile.email} roleLabel="Кабинет кандидата">
        <Routes>
          <Route index element={<CandidateProfilePage />} />
          <Route path="testing" element={<TestingPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="invitations" element={<InvitationsPage />} />
          <Route path="tasks" element={<SpotTasksPage />} />
          <Route path="vacancies" element={<VacanciesPage />} />
          <Route path="*" element={<Navigate to="/candidate" replace />} />
        </Routes>
      </Layout>
    </CandidateContext.Provider>
  );
}
