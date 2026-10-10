import React, { useState } from 'react';
import { api } from '../../api';
import { PageHead } from '../../components/Layout';
import { Card, useToast } from '../../components/ui';
import { useCandidate } from './index';

const SWITCHES: { key: string; title: string; description: string }[] = [
  {
    key: 'consent_publication',
    title: 'Согласие на обработку и публикацию профиля',
    description: 'Без него профиль не показывается работодателям. Отзыв согласия сразу убирает вас из подборок (152-ФЗ).',
  },
  {
    key: 'is_searchable',
    title: 'Профиль виден работодателям',
    description: 'Выключите, если сейчас не ищете работу. Приглашения перестанут приходить, данные останутся.',
  },
  {
    key: 'show_fsp',
    title: 'Показывать достижения ФСП',
    description: 'Верифицированные результаты соревнований повышают позицию в подборке. Можно скрыть.',
  },
  {
    key: 'show_salary_expectation',
    title: 'Показывать зарплатные ожидания',
    description: 'Работодатель увидит ваш диапазон до того, как напишет.',
  },
  {
    key: 'show_city',
    title: 'Показывать город',
    description: 'Влияет на совпадение по локации в подборке.',
  },
  {
    key: 'accepts_spot_tasks',
    title: 'Получать регулярные задания',
    description: 'Короткая задача раз в неделю. Свежий ответ повышает актуальность профиля.',
  },
];

export function SettingsPage() {
  const { profile, reload } = useCandidate();
  const toast = useToast();
  const [settings, setSettings] = useState({ ...profile.settings });
  const [saving, setSaving] = useState(false);

  async function save(next: any) {
    setSaving(true);
    try {
      await api.put('/me/candidate/settings', next);
      setSettings(next);
      await reload();
      toast('Настройки сохранены');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Ошибка', 'err');
      setSettings({ ...profile.settings });
    } finally { setSaving(false); }
  }

  function toggle(key: string) {
    const next = { ...settings, [key]: !settings[key] };
    // Visibility without a publication consent would publish data the candidate
    // never agreed to publish, so the pair is kept consistent in the UI too.
    if (key === 'consent_publication' && !next.consent_publication) next.is_searchable = false;
    save(next);
  }

  return (
    <>
      <PageHead eyebrow="Кандидат" title="Приватность и видимость">
        Вы управляете тем, что видно работодателю. Контактные данные в этот список не входят:
        они закрыты всегда и раскрываются только после принятого приглашения или вашего отклика.
      </PageHead>

      <div className="stack">
        <Card>
          {SWITCHES.map(item => (
            <div className="switch" key={item.key}>
              <input type="checkbox" checked={!!settings[item.key]} disabled={saving}
                onChange={() => toggle(item.key)} id={`sw-${item.key}`} />
              <label htmlFor={`sw-${item.key}`}>
                <b>{item.title}</b>
                <span>{item.description}</span>
              </label>
            </div>
          ))}
        </Card>

        <div className="note info">
          <b>Как платформа обращается с контактами.</b> E-mail, телефон, Telegram и GitHub
          не попадают ни в подборку, ни в поиск по банку кандидатов. Каждое раскрытие
          записывается, и список компаний, получивших доступ, виден в разделе «Приглашения».
        </div>
      </div>
    </>
  );
}
