"""PDF in, PDF out.

Reading: pypdf pulls the text layer out of an uploaded résumé; the structured
parsing itself is `app.domain.resume`, which stays pure and testable.
Writing: reportlab renders the standardized FSP profile. Both halves are kept
here so that the API layer never touches a file format directly.
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.domain import skills as skills_vocab

MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# FSP brand palette, identical to the one the web client uses.
FSP_MAGENTA = colors.HexColor("#FF0053")
FSP_PURPLE = colors.HexColor("#520978")
FSP_DARK = colors.HexColor("#1C1D22")
FSP_MUTED = colors.HexColor("#6B6B76")

# Any of these ships a Cyrillic-capable TTF; the Docker image installs the first.
_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
]
_REGULAR, _BOLD = "Helvetica", "Helvetica-Bold"
for regular, bold in _FONT_CANDIDATES:
    if os.path.exists(regular) and os.path.exists(bold):
        pdfmetrics.registerFont(TTFont("FSPSans", regular))
        pdfmetrics.registerFont(TTFont("FSPSans-Bold", bold))
        _REGULAR, _BOLD = "FSPSans", "FSPSans-Bold"
        break


class ResumeFileError(ValueError):
    pass


def extract_text(data: bytes, filename: str) -> str:
    """Text layer of a PDF, or the decoded body of a plain-text upload."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ResumeFileError("Файл больше 8 МБ")
    lowered = (filename or "").lower()
    if lowered.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    if not lowered.endswith(".pdf") and not data[:5] == b"%PDF-":
        raise ResumeFileError("Поддерживаются PDF и TXT")

    from pypdf import PdfReader  # imported lazily: only an upload needs it

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages[:12]]
    except Exception as exc:  # a corrupt upload is a user error, not a 500
        raise ResumeFileError("Не удалось прочитать PDF-файл") from exc
    text = "\n".join(pages).strip()
    if not text:
        raise ResumeFileError(
            "В PDF нет текстового слоя (похоже на скан). Заполните профиль вручную или загрузите текстовый PDF"
        )
    return text


def _styles():
    base = ParagraphStyle("base", fontName=_REGULAR, fontSize=10, leading=14, textColor=FSP_DARK, alignment=TA_LEFT)
    return {
        "base": base,
        "name": ParagraphStyle("name", parent=base, fontName=_BOLD, fontSize=22, leading=26),
        "sub": ParagraphStyle("sub", parent=base, fontSize=11, leading=15, textColor=FSP_PURPLE),
        "muted": ParagraphStyle("muted", parent=base, fontSize=9, leading=12, textColor=FSP_MUTED),
        "h": ParagraphStyle("h", parent=base, fontName=_BOLD, fontSize=11, leading=15, textColor=FSP_MAGENTA,
                            spaceBefore=10, spaceAfter=4),
    }


def _escape(value: str) -> str:
    return (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_profile_pdf(profile: dict) -> bytes:
    """Standardized FSP profile PDF.

    `profile` is assembled by the API layer; contacts are included only when
    the candidate generates the document for themselves.
    """
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Профиль ФСП — {profile.get('display_name') or 'кандидат'}",
        author="FSP Career",
    )
    flow = [
        Paragraph("ПРОФИЛЬ КАНДИДАТА · ФСП CAREER", styles["muted"]),
        Spacer(1, 4),
        Paragraph(_escape(profile.get("display_name") or "Имя не указано"), styles["name"]),
        Spacer(1, 2),
    ]

    category = profile.get("category") or "категория не подтверждена"
    headline = [category]
    if profile.get("years_experience"):
        headline.append(f"опыт {profile['years_experience']:g} лет")
    if profile.get("city"):
        headline.append(profile["city"])
    if profile.get("work_format"):
        headline.append(profile["work_format"])
    flow.append(Paragraph(_escape(" · ".join(headline)), styles["sub"]))
    flow.append(Spacer(1, 8))
    flow.append(HRFlowable(width="100%", thickness=1.2, color=FSP_MAGENTA, spaceAfter=6))

    def section(title: str, body: str):
        if body:
            flow.append(Paragraph(title, styles["h"]))
            flow.append(Paragraph(_escape(body), styles["base"]))

    contacts = profile.get("contacts") or {}
    section("Контакты", " · ".join(v for v in [contacts.get("email"), contacts.get("phone"),
                                               contacts.get("telegram"), contacts.get("github")] if v))
    section("О себе", profile.get("bio") or "")

    for row in profile.get("categories") or []:
        flow.append(Paragraph("Подтверждённые категории", styles["h"]))
        break
    for row in profile.get("categories") or []:
        line = f"{row['specialization_name']} — {row['grade']}"
        if row.get("theta") is not None:
            line += f" (θ {row['theta']:+.2f})"
        if row.get("confirmed_at"):
            line += f", подтверждено {row['confirmed_at'][:10]}"
        flow.append(Paragraph("• " + _escape(line), styles["base"]))

    section("Стек", ", ".join(skills_vocab.labels(profile.get("skills") or [])))
    section("Роли в команде", ", ".join(profile.get("roles") or []))
    section("Софт-скиллы", ", ".join(profile.get("soft_skills") or []))

    salary = profile.get("salary_expectation")
    if salary:
        section("Зарплатные ожидания", salary)

    fsp = profile.get("fsp") or {}
    if fsp.get("linked") and fsp.get("count"):
        flow.append(Paragraph("Достижения ФСП (верифицировано)", styles["h"]))
        flow.append(Paragraph(
            _escape(f"ФСП ID {fsp.get('fsp_id')} · сила профиля {fsp.get('strength', 0):.0f} из 100"),
            styles["muted"]))
        for highlight in fsp.get("highlights") or []:
            flow.append(Paragraph("• " + _escape(highlight), styles["base"]))

    flow.append(Spacer(1, 12))
    flow.append(HRFlowable(width="100%", thickness=0.6, color=FSP_MUTED, spaceAfter=4))
    flow.append(Paragraph(
        f"Сформировано платформой ФСП Career {datetime.now(timezone.utc).strftime('%d.%m.%Y')}. "
        "Категория присвоена по результатам адаптивного тестирования, достижения получены из реестра ФСП.",
        styles["muted"]))

    doc.build(flow)
    return buffer.getvalue()
