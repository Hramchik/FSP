import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { session } from './api';
import { ToastHost } from './components/ui';
import { Landing } from './pages/Landing';
import { CandidateApp } from './pages/candidate/index';
import { EmployerApp } from './pages/employer/index';
import './styles.css';

function Protected({ role, children }: { role: 'candidate' | 'employer'; children: React.ReactNode }) {
  if (!session.access) return <Navigate to="/" replace />;
  if (session.role !== role) return <Navigate to={session.role === 'candidate' ? '/candidate' : '/employer'} replace />;
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={session.access
        ? <Navigate to={session.role === 'employer' ? '/employer' : '/candidate'} replace />
        : <Landing />} />
      <Route path="/candidate/*" element={<Protected role="candidate"><CandidateApp /></Protected>} />
      <Route path="/employer/*" element={<Protected role="employer"><EmployerApp /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ToastHost><App /></ToastHost>
    </BrowserRouter>
  </React.StrictMode>,
);
