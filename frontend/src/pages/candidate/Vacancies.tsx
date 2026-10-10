import React, { useEffect, useState } from 'react';
import { api, dateRu, FORMAT_LABEL, GRADE_LABEL, Grade, salaryRange } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Loader, StatusBadge, useToast } from '../../components/ui';
import { useCandidate } from './index';

export function VacanciesPage() {
  const { catalog } = useCandidate();
  const toast = useToast();
  const [vacancies, setVacancies] = useState<any[] | null>(null);
  const [applications, setApplications] = useState<any[]>([]);
  const [specialization, setSpecialization] = useState('');

  async function load() {
    const query = specialization ? `?specialization=${specialization}` : '';
    const [list, mine] = await Promise.all([api.get(`/vacancies${query}`), api.get('/me/applications')]);
    setVacancies(list);
    setApplications(mine);
  }

  useEffect(() => { load().catch(e => toast(e.message, 'err')); }, [specialization]);

  async function apply(id: number) {
    try {
      await api.post(`/vacancies/${id}/apply`, { message: '' });
      await load();
      toast('Отклик отправлен — работодатель получил доступ к вашим контактам');
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
  }

  if (!vacancies) return <Loader />;

  return (
    <>
      <PageHead eyebrow="Кандидат" title="Вакансии и мои отклики">
        Основной сценарий платформы — приглашение от работодателя. Этот раздел
        дополнительный: он нужен, если вы хотите проявить инициативу сами, не дожидаясь приглашения.
      </PageHead>

      <div className="stack">
        <div className="row wrap">
          <select style={{ maxWidth: 280 }} value={specialization} onChange={e => setSpecialization(e.target.value)}>
            <option value="">Все специализации</option>
            {catalog.specializations.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
          </select>
        </div>

        {vacancies.length === 0 && <Card><Empty title="Опубликованных вакансий нет" /></Card>}

        {vacancies.map(vacancy => (
          <Card key={vacancy.id} title={vacancy.title}
            action={vacancy.my_application_status
              ? <StatusBadge status={vacancy.my_application_status} kind="application" />
              : <button className="btn primary sm" onClick={() => apply(vacancy.id)}>Откликнуться</button>}>
            <div className="row wrap" style={{ marginBottom: 10 }}>
              <span className="chip match">{salaryRange(vacancy.salary_from, vacancy.salary_to)}</span>
              <span className="chip">{vacancy.company_name}</span>
              <span className="chip">{GRADE_LABEL[vacancy.grade as Grade]}</span>
              <span className="chip">{FORMAT_LABEL[vacancy.work_format] ?? vacancy.work_format}</span>
              {vacancy.city && <span className="chip">{vacancy.city}</span>}
            </div>
            <p className="small">{vacancy.description}</p>
            {vacancy.skill_labels?.length > 0 && (
              <div className="chips" style={{ marginTop: 10 }}>
                {vacancy.skill_labels.map((label: string) => <span className="chip" key={label}>{label}</span>)}
              </div>
            )}
          </Card>
        ))}

        {applications.length > 0 && (
          <Card title="Мои отклики">
            <table className="table">
              <thead><tr><th>Вакансия</th><th>Компания</th><th>Статус</th><th>Отправлен</th></tr></thead>
              <tbody>
                {applications.map(application => (
                  <tr key={application.id}>
                    <td><b>{application.vacancy_title}</b></td>
                    <td className="small muted">{application.company_name}</td>
                    <td><StatusBadge status={application.status} kind="application" /></td>
                    <td className="small muted">{dateRu(application.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </>
  );
}
