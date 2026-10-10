import React, { useEffect, useState } from 'react';
import { api, dateRu, salaryRange } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, Empty, Loader, StatusBadge, useToast } from '../../components/ui';

export function InvitationsPage() {
  const toast = useToast();
  const [invitations, setInvitations] = useState<any[] | null>(null);
  const [disclosures, setDisclosures] = useState<any[]>([]);

  async function load() {
    const [list, shared] = await Promise.all([
      api.get('/me/invitations'),
      api.get('/me/disclosures').catch(() => []),
    ]);
    setInvitations(list);
    setDisclosures(shared);
  }

  useEffect(() => { load().catch(e => toast(e.message, 'err')); }, []);

  async function decide(id: number, decision: 'accepted' | 'declined') {
    try {
      await api.post(`/me/invitations/${id}/decision`, { decision });
      await load();
      toast(decision === 'accepted'
        ? 'Приглашение принято — работодатель получил ваши контакты'
        : 'Приглашение отклонено');
    } catch (e) { toast(e instanceof Error ? e.message : 'Ошибка', 'err'); }
  }

  if (!invitations) return <Loader />;
  const open = invitations.filter(i => i.status === 'sent' || i.status === 'viewed');
  const closed = invitations.filter(i => i.status === 'accepted' || i.status === 'declined');

  return (
    <>
      <PageHead eyebrow="Кандидат" title="Приглашения от работодателей">
        Здесь первый шаг делает компания. В каждом приглашении обязательно указана вилка
        зарплаты — условия видны до начала общения, а контакты уходят работодателю
        только если вы согласитесь.
      </PageHead>

      {invitations.length === 0 && (
        <Card>
          <Empty title="Приглашений пока нет">
            Чтобы попасть в подборки, подтвердите категорию в разделе «Опрос и тестирование»
            и включите видимость профиля в «Приватности».
          </Empty>
        </Card>
      )}

      <div className="stack">
        {open.map(invitation => <InvitationCard key={invitation.id} invitation={invitation} onDecide={decide} />)}
        {closed.length > 0 && <h3 style={{ marginTop: 10 }}>История</h3>}
        {closed.map(invitation => <InvitationCard key={invitation.id} invitation={invitation} onDecide={decide} />)}

        {disclosures.length > 0 && (
          <Card title="Кому открыты мои контакты">
            <table className="table">
              <thead><tr><th>Компания</th><th>Основание</th><th>Когда</th></tr></thead>
              <tbody>
                {disclosures.map((row, index) => (
                  <tr key={index}>
                    <td><b>{row.employer}</b></td>
                    <td className="small muted">
                      {row.reason === 'invitation_accepted' ? 'Вы приняли приглашение' : 'Вы откликнулись на вакансию'}
                    </td>
                    <td className="small muted">{dateRu(row.disclosed_at)}</td>
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

function InvitationCard({ invitation, onDecide }: {
  invitation: any; onDecide: (id: number, decision: 'accepted' | 'declined') => void;
}) {
  const pending = invitation.status === 'sent' || invitation.status === 'viewed';
  return (
    <Card
      title={invitation.company_name}
      action={<StatusBadge status={invitation.status} />}
    >
      <div className="stack">
        <div className="row wrap">
          <span className="chip match">{salaryRange(invitation.salary_from, invitation.salary_to)}</span>
          {invitation.vacancy_title && <span className="chip">Вакансия: {invitation.vacancy_title}</span>}
          {invitation.employer?.city && <span className="chip">{invitation.employer.city}</span>}
          {invitation.employer?.team_size && <span className="chip">{invitation.employer.team_size}</span>}
        </div>

        <p>{invitation.offer_description}</p>

        {invitation.employer?.description && (
          <p className="small muted">О компании: {invitation.employer.description}</p>
        )}

        <div className="spread small muted">
          <span>Отправлено {dateRu(invitation.created_at)}</span>
          <span>{invitation.history.map((event: any) => event.status).join(' → ')}</span>
        </div>

        {pending ? (
          <div className="row">
            <button className="btn primary" onClick={() => onDecide(invitation.id, 'accepted')}>
              Принять и открыть контакты
            </button>
            <button className="btn" onClick={() => onDecide(invitation.id, 'declined')}>Отклонить</button>
          </div>
        ) : invitation.status === 'accepted' ? (
          <div className="note ok">
            Вы приняли приглашение. Связаться с вами можно через: <b>{invitation.contact_method}</b>
          </div>
        ) : (
          <div className="note info">Приглашение отклонено — контакты не передавались.</div>
        )}
      </div>
    </Card>
  );
}
