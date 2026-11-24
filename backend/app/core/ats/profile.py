"""Candidate-profile extraction from free résumé text.

Turns parsed résumé text into the structured ``candidate_profile`` the
:class:`~app.core.ats.scorer.ResumeScorer` consumes (``skills``, ``experience``,
``education``). Before this module the scoring paths always passed empty
experience/education lists, so every résumé lost those factors entirely.

Experience entries come from date ranges such as ``Jan 2019 - Mar 2022``, ``2016 - 2018``,
``01/2018 - 07/2019`` or ``Jan 2020 - Present`` (hyphen, en/em dash or ``to``).
Education entries come from lines carrying a degree keyword matched on word boundaries.
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING, Any

from app.core.documents.parser import SECTION_HEADERS, extract_sections

if TYPE_CHECKING:
    from app.core.ats.skill_matcher import SkillMatcher

_EXPERIENCE_SECTIONS = ("experience", "work experience", "professional experience", "employment")
_EDUCATION_SECTIONS = ("education", "academic background")

_MONTHS: dict[str, int] = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
)
_YEAR = r"(?:19|20)\d{2}"
_DATE = rf"(?:{_MONTH}\s+{_YEAR}|(?:0?[1-9]|1[0-2])/{_YEAR}|{_YEAR})"
_RANGE_RE = re.compile(
    rf"\b(?P<start>{_DATE})\s*(?:-|\u2013|\u2014|to)\s*(?P<end>{_DATE}|present|current)\b",
    re.IGNORECASE,
)
_MONTH_NAME_RE = re.compile(rf"^(?P<mon>[a-z]+)\.?\s+(?P<year>{_YEAR})$", re.IGNORECASE)
_NUMERIC_RE = re.compile(rf"^(?P<mon>\d{{1,2}})/(?P<year>{_YEAR})$")

_ABBREVIATED_DEGREES = r"b\.s\.|b\.sc\.?|bsc|b\.a\.|m\.s\.|m\.sc\.?|msc|mba|ph\.d\.?|phd"
# Inside an education section every degree keyword counts.
_DEGREE_RE = re.compile(
    r"(?<![A-Za-z])(?:"
    r"bachelor(?:'?s)?|(?<!scrum\s)master(?:'?s)?|associate(?:'?s)?|doctor(?:ate)?"
    rf"|{_ABBREVIATED_DEGREES}"
    r")(?![A-Za-z])",
    re.IGNORECASE,
)
# Scanning the whole text, "Associate Engineer", "Doctor" or "Master Electrician" are job
# titles, so Master/Associate/Doctor then need degree context ("of", "in", "degree", "'s").
_STRICT_DEGREE_RE = re.compile(
    r"(?<![A-Za-z])(?:"
    r"bachelor(?:'?s)?|(?:master|associate)(?:'?s)?(?=\s+(?:of|in|degree)\b)"
    r"|(?:master|associate)'s|doctorate|doctor(?=\s+of\b)"
    rf"|{_ABBREVIATED_DEGREES}"
    r")(?![A-Za-z])",
    re.IGNORECASE,
)
_INSTITUTION_RE = re.compile(
    r"\b(?:university|college|institute|school|academy|polytechnic)\b", re.IGNORECASE
)
# Title/company separators on a role line, in priority order.
_ROLE_SEPARATORS = (" at ", "|", ",", " - ")
_EDU_SPLIT_RE = re.compile(r"\s*[|,;]\s*|\s+[-\u2013\u2014]\s+|\s+at\s+")
_EDGE_CHARS = " \t,;|-\u2013\u2014()[]\u2022\u00b7*"


def extract_candidate_profile(
    resume_text: str, skill_matcher: SkillMatcher
) -> dict[str, list[Any]]:
    """Build the scorer's candidate profile from résumé text.

    Args:
        resume_text: Plain résumé text.
        skill_matcher: Used for canonical skill extraction.

    Returns:
        ``{"skills": [...], "experience": [...], "education": [...]}`` where experience
        entries carry ``title``, ``company``, ``duration_years`` and ``description``, and
        education entries carry ``degree`` and ``institution``.
    """
    sections = extract_sections(resume_text)
    return {
        "skills": sorted(skill_matcher.extract_skills(resume_text)),
        "experience": _extract_experience(resume_text, sections),
        "education": _extract_education(resume_text, sections),
    }


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


def _extract_experience(text: str, sections: dict[str, str]) -> list[dict[str, Any]]:
    section_text = "\n".join(sections[k] for k in _EXPERIENCE_SECTIONS if k in sections)
    whole_text = not section_text.strip()
    lines = [ln.strip() for ln in (text if whole_text else section_text).split("\n")]
    # Without an experience section, dated lines under an education header are schooling.
    education_lines: set[str] = set()
    if whole_text:
        for key in _EDUCATION_SECTIONS:
            education_lines.update(ln.strip() for ln in sections.get(key, "").split("\n"))
        education_lines.discard("")

    # (range_line_index, header_line_index, title, company, duration_years)
    found: list[tuple[int, int, str, str, float]] = []
    range_lines: set[int] = set()
    for idx, line in enumerate(lines):
        match = _RANGE_RE.search(line)
        if match is None:
            continue
        # Without an experience section, a dated degree line is education, not a job.
        if whole_text and (line in education_lines or _STRICT_DEGREE_RE.search(line)):
            continue
        duration = _duration_years(match.group("start"), match.group("end"))
        if duration is None:
            continue
        range_lines.add(idx)
        header_idx, role = idx, _clean(line[: match.start()] + " " + line[match.end() :])
        if not role:
            prev = _previous_non_empty(lines, idx)
            if prev is not None and prev not in range_lines:
                header_idx, role = prev, _clean(lines[prev])
        title, company = _split_role(role)
        found.append((idx, header_idx, title, company, duration))

    entries: list[dict[str, Any]] = []
    for pos, (idx, _header, title, company, duration) in enumerate(found):
        stop = found[pos + 1][1] if pos + 1 < len(found) else len(lines)
        # A role's description never runs past the next section header (whole-text mode).
        stop = next(
            (j for j in range(idx + 1, stop) if lines[j].lower().rstrip(":") in SECTION_HEADERS),
            stop,
        )
        body = [ln.lstrip("-*\u2022\u00b7 ").strip() for ln in lines[idx + 1 : stop]]
        entries.append(
            {
                "title": title,
                "company": company,
                "duration_years": duration,
                "description": "\n".join(b for b in body if b),
            }
        )
    return entries


def _duration_years(start: str, end: str) -> float | None:
    """Return the span in years (month resolution), or None when unparseable/inverted."""
    begin = _parse_month(start)
    if end.strip().lower() in ("present", "current"):
        today = date.today()
        finish: tuple[int, int] | None = (today.year, today.month)
    else:
        finish = _parse_month(end)
    if begin is None or finish is None:
        return None
    months = (finish[0] * 12 + finish[1]) - (begin[0] * 12 + begin[1])
    if months < 0:
        return None
    return round(months / 12, 4)


def _parse_month(token: str) -> tuple[int, int] | None:
    """Parse ``Mon YYYY`` / ``MM/YYYY`` / ``YYYY`` into ``(year, month)``."""
    token = token.strip()
    if m := _MONTH_NAME_RE.match(token):
        month = _MONTHS.get(m.group("mon").lower()[:3])
        return (int(m.group("year")), month) if month else None
    if m := _NUMERIC_RE.match(token):
        return int(m.group("year")), int(m.group("mon"))
    if re.fullmatch(_YEAR, token):
        return int(token), 1
    return None


def _split_role(role: str) -> tuple[str, str]:
    for sep in _ROLE_SEPARATORS:
        if sep in role:
            title, company = role.split(sep, 1)
            return _clean(title), _clean(company)
    return role, ""


def _previous_non_empty(lines: list[str], idx: int) -> int | None:
    for prev in range(idx - 1, -1, -1):
        if lines[prev]:
            return prev
    return None


def _clean(value: str) -> str:
    return re.sub(r"\s{2,}", " ", value).strip(_EDGE_CHARS)


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


def _extract_education(text: str, sections: dict[str, str]) -> list[dict[str, str]]:
    section_text = "\n".join(sections[k] for k in _EDUCATION_SECTIONS if k in sections)
    lines = [ln.strip() for ln in (section_text or text).split("\n")]
    degree_re = _DEGREE_RE if section_text.strip() else _STRICT_DEGREE_RE

    entries: list[dict[str, str]] = []
    for idx, line in enumerate(lines):
        if not degree_re.search(line):
            continue
        undated = _clean(_RANGE_RE.sub(" ", line))
        parts = [p for p in (_clean(s) for s in _EDU_SPLIT_RE.split(undated)) if p]
        if not parts:
            continue
        degree_pos = next((i for i, p in enumerate(parts) if degree_re.search(p)), 0)
        entries.append(
            {
                "degree": parts[degree_pos],
                "institution": _institution(parts, degree_pos, lines, idx),
            }
        )
    return entries


def _institution(parts: list[str], degree_pos: int, lines: list[str], idx: int) -> str:
    """Pick the institution: a named school on the line, else on an adjacent line."""
    others = [p for i, p in enumerate(parts) if i != degree_pos]
    for part in others:
        if _INSTITUTION_RE.search(part):
            return part
    for near in (idx - 1, idx + 1):
        if 0 <= near < len(lines):
            candidate = lines[near]
            if candidate and _INSTITUTION_RE.search(candidate) and not _DEGREE_RE.search(candidate):
                return _clean(_RANGE_RE.sub(" ", candidate))
    return others[0] if len(others) == 1 else ""
