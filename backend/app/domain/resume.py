"""Résumé text → a structured draft profile.

The candidate may upload a PDF instead of filling the form. Extraction of the
text itself belongs to the service layer (pypdf); this module is the pure part:
given plain text, produce the fields that pre-fill the form. Everything is a
*draft* — the candidate confirms or edits before anything is saved, because a
mis-parsed résumé must never silently become a claim about a person.

Nothing here decides a grade. A résumé is a self-description, and the whole
point of the platform is that the category comes from the test instead.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.domain import skills as skills_vocab

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")
PHONE_RE = re.compile(r"(?:\+7|8|\+\d{1,3})[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")
TELEGRAM_RE = re.compile(r"(?:t\.me/|telegram[:\s]+@?|@)([A-Za-z][A-Za-z0-9_]{4,31})\b", re.I)
GITHUB_RE = re.compile(r"github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})", re.I)
# "Фамилия Имя Отчество" in Russian title case, optionally without a patronymic.
FIO_RE = re.compile(r"\b([А-ЯЁ][а-яё]{1,24})\s+([А-ЯЁ][а-яё]{1,24})(?:\s+([А-ЯЁ][а-яё]{2,24}(?:вич|вна|ична|мич)))?\b")

GRADE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(team\s*lead|teamlead|tech\s*lead|techlead|тимлид|руководитель\s+группы|lead)\b", re.I), "lead"),
    (re.compile(r"\b(senior|сеньор|синьор|ведущий|старший)\b", re.I), "senior"),
    (re.compile(r"\b(middle|мидл|миддл)\b", re.I), "middle"),
    (re.compile(r"\b(junior|джуниор|джун|стажёр|стажер|intern)\b", re.I), "junior"),
]

SPECIALIZATION_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("devops", ("devops", "девопс", "sre", "инфраструктур", "системный администратор", "платформенн")),
    ("qa", ("qa", "тестиров", "автотест", "quality assurance", "испытател")),
    ("data", ("data scien", "дата сайент", "аналитик данных", "machine learning", "машинн", "ml-инженер", "ml инженер", "data engineer", "дата инженер")),
    ("mobile", ("mobile", "мобильн", "android", "ios", "flutter", "react native")),
    ("frontend", ("frontend", "фронтенд", "фронт-энд", "верстальщик", "ui-разработ")),
    ("backend", ("backend", "бэкенд", "бекенд", "back-end", "серверн")),
]

ROLE_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("Разработка", ("разработ", "develop", "программист", "инженер-програм")),
    ("Код-ревью", ("ревью", "code review", "код-ревью")),
    ("Менторство", ("ментор", "наставни", "обучение джун", "mentor")),
    ("Архитектура", ("архитектур", "architect", "проектирование систем")),
    ("Тимлид", ("тимлид", "team lead", "руководство командой", "управление командой")),
    ("Аналитика", ("аналитик", "analyst", "сбор требований")),
    ("Эксплуатация", ("дежурств", "on-call", "oncall", "эксплуатац", "поддержк")),
]

SOFT_SKILL_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("Командная работа", ("команд", "teamwork", "совместн")),
    ("Коммуникация", ("коммуникаб", "коммуникац", "переговор", "communication")),
    ("Ответственность", ("ответствен", "самостоятельн", "proactive", "инициативн")),
    ("Наставничество", ("ментор", "наставни", "mentor")),
    ("Английский язык", ("английск", "english", "upper-intermediate", "intermediate", "b2", "c1")),
    ("Публичные выступления", ("доклад", "конференц", "спикер", "митап", "выступлен")),
]

EXPERIENCE_RE = [
    re.compile(r"опыт[^.\n]{0,40}?(\d{1,2})(?:[.,](\d))?\s*(?:\+)?\s*(?:год|года|лет)", re.I),
    re.compile(r"(\d{1,2})(?:[.,](\d))?\s*(?:\+)?\s*(?:год|года|лет)[^.\n]{0,30}опыт", re.I),
    re.compile(r"\b(\d{1,2})(?:[.,](\d))?\s*\+?\s*(?:years?|yrs?)\b", re.I),
]
YEAR_RANGE_RE = re.compile(r"\b(19[89]\d|20[0-4]\d)\s*[-–—]\s*(20[0-4]\d|наст|сейчас|present|now)", re.I)


@dataclass
class ParsedResume:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    telegram: str = ""
    github: str = ""
    city: str = ""
    specialization: str | None = None
    grade_hint: str | None = None
    years_experience: float = 0.0
    skills: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    summary: str = ""
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "telegram": self.telegram,
            "github": self.github,
            "city": self.city,
            "specialization": self.specialization,
            "grade_hint": self.grade_hint,
            "years_experience": self.years_experience,
            "skills": self.skills,
            "skill_labels": skills_vocab.labels(self.skills),
            "roles": self.roles,
            "soft_skills": self.soft_skills,
            "summary": self.summary,
            "warnings": self.warnings,
        }


CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Нижний Новгород",
    "Челябинск", "Самара", "Омск", "Ростов-на-Дону", "Уфа", "Красноярск", "Воронеж", "Пермь",
    "Волгоград", "Краснодар", "Саратов", "Тюмень", "Тольятти", "Ижевск", "Барнаул", "Иркутск",
    "Хабаровск", "Владивосток", "Ярославль", "Томск", "Калининград", "Сочи", "Иннополис",
]


def _find_name(text: str) -> str:
    """Prefer an explicit ФИО label, then fall back to the first title-case run."""
    labelled = re.search(r"(?:ФИО|Ф\.И\.О\.?|Имя)\s*[:\-–]\s*([^\n]{3,80})", text, re.I)
    if labelled:
        return re.sub(r"\s+", " ", labelled.group(1)).strip(" .,:;")
    # A résumé almost always opens with the name, so only scan the first lines.
    head = "\n".join(text.splitlines()[:8])
    match = FIO_RE.search(head)
    if match:
        return " ".join(part for part in match.groups() if part)
    return ""


def _find_experience(text: str) -> tuple[float, list[str]]:
    warnings: list[str] = []
    for pattern in EXPERIENCE_RE:
        match = pattern.search(text)
        if match:
            whole = int(match.group(1))
            fraction = int(match.group(2) or 0)
            if whole <= 60:
                return round(whole + fraction / 10.0, 1), warnings
    # No explicit statement: estimate from the longest employment range found.
    spans = YEAR_RANGE_RE.findall(text)
    if spans:
        total = 0
        for start, end in spans:
            end_year = 2026 if not end.isdigit() else int(end)
            total += max(0, end_year - int(start))
        if total:
            warnings.append("Стаж оценён по датам мест работы — проверьте значение")
            return float(min(total, 45)), warnings
    return 0.0, warnings


def _find_first(text: str, hints) -> str | None:
    low = text.lower().replace("ё", "е")
    for value, needles in hints:
        if any(needle.replace("ё", "е") in low for needle in needles):
            return value
    return None


def _find_all(text: str, hints) -> list[str]:
    low = text.lower().replace("ё", "е")
    return [value for value, needles in hints if any(n.replace("ё", "е") in low for n in needles)]


def parse(text: str) -> ParsedResume:
    """Best-effort structured draft. Never raises on messy input."""
    result = ParsedResume()
    if not text or not text.strip():
        result.warnings.append("Не удалось извлечь текст из файла — заполните профиль вручную")
        return result

    clean = re.sub(r"[ \t]+", " ", text)
    result.full_name = _find_name(clean)

    email = EMAIL_RE.search(clean)
    result.email = email.group(0) if email else ""
    phone = PHONE_RE.search(clean)
    result.phone = re.sub(r"\s+", " ", phone.group(0)).strip() if phone else ""
    # Addresses are removed first so that the "@" branch of TELEGRAM_RE cannot
    # pick up the domain of an e-mail that appears earlier on the line.
    without_emails = EMAIL_RE.sub(" ", clean)
    telegram = TELEGRAM_RE.search(without_emails)
    if telegram:
        result.telegram = "@" + telegram.group(1)
    github = GITHUB_RE.search(clean)
    result.github = github.group(1) if github else ""

    for city in CITIES:
        if re.search(r"(?<![А-Яа-яЁё])" + re.escape(city) + r"(?![А-Яа-яЁё])", clean, re.I):
            result.city = city
            break

    result.specialization = _find_first(clean, SPECIALIZATION_HINTS)
    for pattern, grade in GRADE_HINTS:
        if pattern.search(clean):
            result.grade_hint = grade
            break

    result.years_experience, warnings = _find_experience(clean)
    result.warnings.extend(warnings)

    result.skills = skills_vocab.extract(clean)
    result.roles = _find_all(clean, ROLE_HINTS)
    result.soft_skills = _find_all(clean, SOFT_SKILL_HINTS)

    about = re.search(r"(?:о себе|обо мне|summary|about)\s*[:\-–]?\s*\n?(.{40,600}?)(?:\n\s*\n|$)", clean, re.I | re.S)
    if about:
        result.summary = re.sub(r"\s+", " ", about.group(1)).strip()
    else:
        paragraph = next((p.strip() for p in re.split(r"\n\s*\n", clean) if 80 <= len(p.strip()) <= 600), "")
        result.summary = re.sub(r"\s+", " ", paragraph)

    if not result.full_name:
        result.warnings.append("ФИО не распознано — укажите его вручную")
    if not result.skills:
        result.warnings.append("Стек не распознан — добавьте навыки вручную")
    if result.grade_hint:
        result.warnings.append(
            f"В резюме указан уровень «{result.grade_hint}». Это самоописание: "
            "итоговый грейд определит тестирование"
        )
    return result
