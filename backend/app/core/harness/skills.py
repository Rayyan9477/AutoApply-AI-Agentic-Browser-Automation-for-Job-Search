"""Domain-skill registry: versioned, scored, PII-gated institutional memory.

Distilled site knowledge is shared across users, so a PII gate runs before storage,
skills are versioned per domain, feedback adjusts a running score, and skills that fall
below a threshold auto-retire. ``load_skills`` returns the active, highest-scored skills
for a domain to inject into the agent's system prompt.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SkillStatus
from app.models.harness import DomainSkill, SkillFeedback

logger = structlog.get_logger(__name__)

RETIRE_THRESHOLD = -3
_VERSION_RETRIES = 3  # retry the read-max+insert on a concurrent version collision

_PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),  # email
    re.compile(r"\b\+?\d[\d\-\s().]{7,}\d\b"),  # phone
    re.compile(r"(?:sk-|ghp_|xox[baprs]-|AKIA|Bearer\s)[A-Za-z0-9_\-]{8,}"),  # keys/tokens
    # street address (capitalized street name required, to avoid matching skill prose)
    re.compile(
        r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s+){1,3}"
        r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Lane|Dr|Drive)\b"
    ),
]


def _contains_person_name(content: str) -> bool:
    """True if spaCy NER finds a full personal name (>=2 tokens).

    DomainSkills are shared across tenants, so a distilled run summary that leaked a candidate's
    name must not be stored. Requires >=2 tokens so single-word tech terms don't false-positive;
    falls back to the regex gate only if the model is unavailable.
    """
    try:
        from app.core.ats.nlp import get_nlp

        doc = get_nlp()(content)
    except Exception:
        return False
    return any(ent.label_ == "PERSON" and len(ent.text.split()) >= 2 for ent in doc.ents)


def pii_clean(content: str) -> bool:
    """Return True if ``content`` has no detectable PII/secrets (pre-storage gate)."""
    if any(pattern.search(content) for pattern in _PII_PATTERNS):
        return False
    return not _contains_person_name(content)


async def record_skill(
    db: AsyncSession,
    domain: str,
    content: str,
    *,
    meta: dict[str, Any] | None = None,
    created_by: str = "distiller",
) -> DomainSkill | None:
    """Store a new skill version for ``domain``. Returns None if it fails the PII gate."""
    if not pii_clean(content):
        logger.warning("skill.pii_rejected", domain=domain)
        return None
    # Content dedup: the distiller runs after every apply, so an unchanged site keeps producing
    # the same guidance. If it already exists ACTIVE for the domain, return it instead of piling
    # up identical rows (unbounded growth). Distinct guidance still coexists (that's by design).
    duplicate = (
        await db.execute(
            select(DomainSkill).where(
                DomainSkill.domain == domain,
                DomainSkill.content == content,
                DomainSkill.status == SkillStatus.ACTIVE,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        logger.info("skill.duplicate_skipped", domain=domain, version=duplicate.version)
        return duplicate
    # SELECT max(version)+INSERT races the uq_domain_skill_version constraint under
    # concurrent distillation; retry on the resulting IntegrityError.
    for _ in range(_VERSION_RETRIES):
        max_version = (
            await db.execute(
                select(func.max(DomainSkill.version)).where(DomainSkill.domain == domain)
            )
        ).scalar()
        skill = DomainSkill(
            domain=domain,
            version=(max_version or 0) + 1,
            content=content,
            meta=meta or {},
            pii_checked=True,
            created_by=created_by,
            status=SkillStatus.ACTIVE,
        )
        db.add(skill)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(skill)
        logger.info("skill.recorded", domain=domain, version=skill.version)
        return skill
    logger.warning("skill.version_race_exhausted", domain=domain)
    return None


async def add_feedback(
    db: AsyncSession,
    skill_id: str,
    delta: int,
    *,
    reason: str | None = None,
    run_id: str | None = None,
) -> DomainSkill | None:
    """Record a +/- feedback signal; auto-retire the skill if its score drops too low."""
    skill = await db.get(DomainSkill, skill_id)
    if skill is None:
        return None
    db.add(SkillFeedback(skill_id=skill_id, delta=delta, reason=reason, run_id=run_id))
    skill.score += delta
    if skill.score <= RETIRE_THRESHOLD:
        skill.status = SkillStatus.RETIRED
        logger.info("skill.auto_retired", skill_id=skill_id, score=skill.score)
    await db.commit()
    await db.refresh(skill)
    return skill


async def load_skills(db: AsyncSession, domain: str, *, limit: int = 5) -> list[DomainSkill]:
    """Return the active, highest-scored skills for ``domain`` (for prompt injection)."""
    rows = (
        (
            await db.execute(
                select(DomainSkill)
                .where(DomainSkill.domain == domain, DomainSkill.status == SkillStatus.ACTIVE)
                .order_by(DomainSkill.score.desc(), DomainSkill.version.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


def build_skill_guidance(skills: list[DomainSkill]) -> str:
    """Render active domain skills into a system-message addendum for the apply agent.

    Returns "" when there are no skills, so the caller can append unconditionally.
    """
    if not skills:
        return ""
    lines = ["Learned guidance for this site (from past runs — treat as hints, verify live):"]
    lines.extend(f"- {skill.content.strip()}" for skill in skills if skill.content.strip())
    return "\n".join(lines) if len(lines) > 1 else ""
