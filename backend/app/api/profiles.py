"""Candidate and employer profiles, résumé import/export and the FSP link."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import current_user, require_role
from app.domain import resume as resume_domain
from app.domain import skills as skills_vocab
from app.models.models import (
    CandidateProfile,
    CandidateSpecialization,
    EmployerProfile,
    FspLink,
    ResumeUpload,
    Specialization,
    TestAttempt,
    User,
    UserRole,
)
from app.schemas.candidate import (
    CandidateProfileIn,
    CandidateProfileOut,
    CandidateSettingsIn,
    EmployerProfileIn,
    EmployerProfileOut,
    FspLinkIn,
    ResumeParseOut,
)
from app.schemas.catalog import CatalogOut, SkillOut, SpecializationOut
from app.services import candidates as candidate_service
from app.services import fsp_registry, resume_files
from app.services.cards import GRADE_RU, salary_expectation_text

router = APIRouter(tags=["profiles"])

WORK_FORMATS = ["remote", "hybrid", "office"]
GRADES = ["junior", "middle", "senior", "lead"]


async def _candidate(db: AsyncSession, user_id: int) -> CandidateProfile:
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if not profile:
        raise HTTPException(404, "Профиль кандидата не найден")
    return profile


async def _categories(db: AsyncSession, candidate_id: int) -> list[dict]:
    rows = (
        await db.execute(
            select(CandidateSpecialization, Specialization)
            .join(Specialization, CandidateSpecialization.specialization_id == Specialization.id)
            .where(
                CandidateSpecialization.candidate_id == candidate_id,
                CandidateSpecialization.confirmed_grade.is_not(None),
            )
            .order_by(Specialization.name)
        )
    ).all()
    out = []
    for candidate_spec, specialization in rows:
        attempt = await db.scalar(
            select(TestAttempt)
            .where(
                TestAttempt.candidate_id == candidate_id,
                TestAttempt.specialization_id == specialization.id,
                TestAttempt.status == "finished",
            )
            .order_by(TestAttempt.finished_at.desc())
            .limit(1)
        )
        out.append(
            {
                "specialization": specialization.code,
                "specialization_name": specialization.name,
                "grade": candidate_spec.confirmed_grade,
                "theta": round(candidate_spec.theta, 3) if candidate_spec.theta is not None else None,
                "confirmed_at": attempt.finished_at.isoformat() if attempt and attempt.finished_at else None,
            }
        )
    return out


async def _candidate_out(db: AsyncSession, profile: CandidateProfile, user: User) -> CandidateProfileOut:
    categories = await _categories(db, profile.id)
    fsp = await fsp_registry.profile_for_candidate(db, profile.id)

    blocking: list[str] = []
    if not categories:
        blocking.append("Пройдите тестирование — без подтверждённой категории профиль не попадает в подборки")
    if not profile.consent_publication:
        blocking.append("Дайте согласие на публикацию профиля в настройках")
    if not profile.is_searchable:
        blocking.append("Включите видимость профиля для работодателей")
    if not (profile.skills or []):
        blocking.append("Добавьте стек — по нему считается соответствие потребности")

    return CandidateProfileOut(
        id=profile.id,
        email=user.email,
        is_email_verified=user.is_email_verified,
        display_name=profile.display_name,
        city=profile.city,
        work_format=profile.work_format,
        bio=profile.bio,
        phone=profile.phone,
        telegram=profile.telegram,
        github=profile.github,
        skills=list(profile.skills or []),
        skill_labels=skills_vocab.labels(profile.skills or []),
        roles=list(profile.roles or []),
        soft_skills=list(profile.soft_skills or []),
        years_experience=profile.years_experience or 0.0,
        salary_expectation_from=profile.salary_expectation_from,
        salary_expectation_to=profile.salary_expectation_to,
        settings=CandidateSettingsIn(
            is_searchable=profile.is_searchable,
            consent_publication=profile.consent_publication,
            show_fsp=profile.show_fsp,
            show_salary_expectation=profile.show_salary_expectation,
            show_city=profile.show_city,
            accepts_spot_tasks=profile.accepts_spot_tasks,
        ),
        completeness=candidate_service.completeness(profile),
        categories=categories,
        fsp=fsp,
        profile_ready=not blocking,
        blocking_reasons=blocking,
    )


@router.get("/catalog", response_model=CatalogOut)
async def catalog(db: AsyncSession = Depends(get_db)):
    """Reference data both cabinets are built from."""
    rows = (await db.scalars(select(Specialization).order_by(Specialization.id))).all()
    return CatalogOut(
        specializations=[
            SpecializationOut(
                code=row.code,
                name=row.name,
                core_skills=[
                    SkillOut(code=code, label=skills_vocab.label(code))
                    for code in sorted(skills_vocab.CORE_SKILLS.get(row.code, set()))
                ],
            )
            for row in rows
        ],
        grades=GRADES,
        skills=[SkillOut(code=code, label=label) for code, label in sorted(skills_vocab.SKILLS.items(), key=lambda kv: kv[1])],
        work_formats=WORK_FORMATS,
    )


@router.get("/me/candidate", response_model=CandidateProfileOut)
async def get_candidate(u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)):
    return await _candidate_out(db, await _candidate(db, u.id), u)


@router.put("/me/candidate", response_model=CandidateProfileOut)
async def put_candidate(
    data: CandidateProfileIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    profile = await _candidate(db, u.id)
    payload = data.model_dump()
    payload["skills"] = skills_vocab.normalize_many(payload["skills"])
    payload["roles"] = [r.strip() for r in payload["roles"] if r and r.strip()][:12]
    payload["soft_skills"] = [r.strip() for r in payload["soft_skills"] if r and r.strip()][:12]
    if payload["work_format"] not in WORK_FORMATS:
        payload["work_format"] = "remote"
    for field, value in payload.items():
        setattr(profile, field, value)
    profile.last_activity_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)
    return await _candidate_out(db, profile, u)


@router.put("/me/candidate/settings", response_model=CandidateProfileOut)
async def put_candidate_settings(
    data: CandidateSettingsIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    profile = await _candidate(db, u.id)
    # Being searchable without a publication consent would publish data the
    # candidate never agreed to publish, so the two switches are coupled.
    if data.is_searchable and not data.consent_publication:
        raise HTTPException(400, "Видимость профиля требует согласия на публикацию данных")
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return await _candidate_out(db, profile, u)


@router.post("/me/candidate/resume", response_model=ResumeParseOut)
async def upload_resume(
    file: UploadFile = File(...),
    apply: bool = False,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    """Parse an uploaded résumé into a draft profile.

    Nothing is written to the profile unless `apply=true`: a mis-parsed file
    must never become a silent claim about a person. The declared grade found
    in the text is returned as a hint only — the category still comes from the
    test.
    """
    profile = await _candidate(db, u.id)
    data = await file.read()
    try:
        text = resume_files.extract_text(data, file.filename or "")
    except resume_files.ResumeFileError as exc:
        raise HTTPException(400, str(exc))

    parsed = resume_domain.parse(text)
    db.add(ResumeUpload(candidate_id=profile.id, filename=(file.filename or "resume.pdf")[:260], parsed=parsed.as_dict()))

    applied = False
    if apply:
        if parsed.full_name:
            profile.display_name = parsed.full_name
        if parsed.city:
            profile.city = parsed.city
        if parsed.phone:
            profile.phone = parsed.phone[:64]
        if parsed.telegram:
            profile.telegram = parsed.telegram[:64]
        if parsed.github:
            profile.github = parsed.github[:120]
        if parsed.skills:
            profile.skills = parsed.skills
        if parsed.roles:
            profile.roles = parsed.roles
        if parsed.soft_skills:
            profile.soft_skills = parsed.soft_skills
        if parsed.years_experience:
            profile.years_experience = parsed.years_experience
        if parsed.summary and not profile.bio.strip():
            profile.bio = parsed.summary
        profile.resume_text = text[:200000]
        profile.last_activity_at = datetime.now(timezone.utc)
        applied = True

    await db.commit()
    return ResumeParseOut(
        parsed=parsed.as_dict(),
        applied=applied,
        message=("Данные перенесены в профиль — проверьте и при необходимости отредактируйте"
                 if applied else "Проверьте распознанные поля и подтвердите перенос"),
    )


@router.get("/me/candidate/profile.pdf")
async def candidate_profile_pdf(
    u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)
):
    """Standardized FSP profile PDF generated from the stored data."""
    profile = await _candidate(db, u.id)
    categories = await _categories(db, profile.id)
    fsp = await fsp_registry.profile_for_candidate(db, profile.id)
    primary = categories[0] if categories else None
    pdf = resume_files.build_profile_pdf(
        {
            "display_name": profile.display_name,
            "city": profile.city,
            "work_format": profile.work_format,
            "years_experience": profile.years_experience,
            "bio": profile.bio,
            "skills": profile.skills or [],
            "roles": profile.roles or [],
            "soft_skills": profile.soft_skills or [],
            "salary_expectation": salary_expectation_text(profile),
            "categories": categories,
            "category": (
                f"{primary['specialization_name']} · {GRADE_RU.get(primary['grade'], primary['grade'])}"
                if primary else None
            ),
            "contacts": {"email": u.email, "phone": profile.phone,
                         "telegram": profile.telegram, "github": profile.github},
            "fsp": fsp,
        }
    )
    filename = f"fsp-profile-{profile.id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/me/candidate/fsp-link", response_model=CandidateProfileOut)
async def link_fsp(
    data: FspLinkIn, u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)
):
    profile = await _candidate(db, u.id)
    try:
        fsp_id = fsp_registry.validate_id(data.fsp_id)
    except fsp_registry.FspRegistryError as exc:
        raise HTTPException(400, str(exc))

    taken = await db.scalar(select(FspLink).where(FspLink.fsp_id == fsp_id, FspLink.candidate_id != profile.id))
    if taken:
        raise HTTPException(409, "Этот ФСП ID уже привязан к другому профилю")

    link = await db.scalar(select(FspLink).where(FspLink.candidate_id == profile.id))
    if link:
        link.fsp_id = fsp_id
        link.linked_at = datetime.now(timezone.utc)
    else:
        db.add(FspLink(candidate_id=profile.id, fsp_id=fsp_id, verified_by="mock-registry"))
    await db.commit()
    await db.refresh(profile)
    return await _candidate_out(db, profile, u)


@router.delete("/me/candidate/fsp-link", response_model=CandidateProfileOut)
async def unlink_fsp(u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)):
    profile = await _candidate(db, u.id)
    link = await db.scalar(select(FspLink).where(FspLink.candidate_id == profile.id))
    if link:
        await db.delete(link)
        await db.commit()
    await db.refresh(profile)
    return await _candidate_out(db, profile, u)


@router.get("/me/employer", response_model=EmployerProfileOut)
async def get_employer(u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == u.id))
    if not profile:
        raise HTTPException(404, "Профиль работодателя не найден")
    return EmployerProfileOut(
        id=profile.id, email=u.email, is_email_verified=u.is_email_verified,
        company_name=profile.company_name, description=profile.description, contact=profile.contact,
        website=profile.website, industry=profile.industry, city=profile.city, team_size=profile.team_size,
    )


@router.put("/me/employer", response_model=EmployerProfileOut)
async def put_employer(
    data: EmployerProfileIn, u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)
):
    profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == u.id))
    if not profile:
        raise HTTPException(404, "Профиль работодателя не найден")
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return EmployerProfileOut(
        id=profile.id, email=u.email, is_email_verified=u.is_email_verified,
        company_name=profile.company_name, description=profile.description, contact=profile.contact,
        website=profile.website, industry=profile.industry, city=profile.city, team_size=profile.team_size,
    )
