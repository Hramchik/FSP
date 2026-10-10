import React, { useEffect, useState } from 'react';
import { api, dateRu, salaryRange } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Loader, StatusBadge, useToast } from '../../components/ui';
import { CandidateBody } from './CandidateCard';

const FLOW = ['sent', 'viewed', 'accepted'];

export function EmployerInvitationsPage() {
  const toast = useToast();
  const [invitations, setInvitations] = useState<any[] | null>(null);

  useEffect(() => {
    api.get('/employer/invitations').then(setInvitations).catch(e => toast(e.message, 'err'));
  }, []);

  if (!invitations) return <Loader />;
  const counts = FLOW.map(status => invitations.filter(i => i.status === status).length);
  const declined = invitations.filter(i => i.status === 'declined').length;

  return (
    <>
      <PageHead eyebrow="Работодатель" title="Отправленные приглашения">
        Статус обновляется на обеих сторонах. Контактные данные кандидата появляются в карточке
        в тот момент, когда он принимает приглашение.
      </PageHead>

      {invitations.length === 0 ? (
        <Card><Empty title="Приглашений ещё не было">
          Соберите подборку по потребности и пригласите кандидата — это основной сценарий платформы.
        </Empty></Card>
      ) : (
        <div className="stack">
          <div className="grid3">
            <div className="stat"><span>Отправлено</span><b>{counts[0]}</b></div>
            <div className="stat"><span>Просмотрено</span><b>{counts[1]}</b></div>
            <div className="stat"><span>Принято / отклонено</span><b>{counts[2]} / {declined}</b></div>
          </div>

          {invitations.map(invitation => (
            <section className="card" key={invitation.id}>
              <header className="card-head">
                <div>
                  <h3>{invitation.candidate?.display_name ?? 'Кандидат'}</h3>
                  <span className="faint">
                    {salaryRange(invitation.salary_from, invitation.salary_to)} · отправлено {dateRu(invitation.created_at)}
                  </span>
                </div>
                <StatusBadge status={invitation.status} />
              </header>
              <div className="card-pad stack">
                <p className="small muted">{invitation.offer_description}</p>
                <div className="legend">
                  {invitation.history.map((event: any, index: number) => (
                    <span key={index}><i className="sc-category" />{event.status} · {dateRu(event.created_at)}</span>
                  ))}
                </div>
                {invitation.candidate && <CandidateBody candidate={invitation.candidate} />}
              </div>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
