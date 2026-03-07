"""Skill matching engine using fuzzy and semantic NLP techniques.

Matches candidate skills against job requirements using exact matching,
fuzzy string matching, and spaCy semantic similarity.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

import spacy
import structlog

logger = structlog.get_logger(__name__)

# Canonical skill variations mapping common aliases to normalized names.
SKILL_VARIATIONS: dict[str, list[str]] = {
    "python": ["python3", "python 3", "cpython", "python programming"],
    "javascript": ["js", "ecmascript", "es6", "es2015", "vanilla js"],
    "typescript": ["ts", "typescript programming"],
    "react": ["reactjs", "react.js", "react js"],
    "angular": ["angularjs", "angular.js", "angular 2+"],
    "vue": ["vuejs", "vue.js", "vue 3"],
    "node": ["nodejs", "node.js", "node js"],
    "express": ["expressjs", "express.js"],
    "django": ["django framework", "django python"],
    "flask": ["flask framework", "flask python"],
    "fastapi": ["fast api", "fastapi framework"],
    "sql": ["structured query language"],
    "postgresql": ["postgres", "psql", "pg"],
    "mongodb": ["mongo", "mongo db"],
    "mysql": ["my sql", "mariadb"],
    "redis": ["redis db", "redis cache"],
    "docker": ["docker container", "containerization"],
    "kubernetes": ["k8s", "kube"],
    "aws": ["amazon web services", "amazon aws"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure", "azure cloud"],
    "git": ["github", "gitlab", "git version control"],
    "ci/cd": ["cicd", "ci cd", "continuous integration", "continuous deployment"],
    "machine learning": ["ml", "machine-learning"],
    "deep learning": ["dl", "deep-learning"],
    "natural language processing": ["nlp", "text mining", "text analytics"],
    "computer vision": ["cv", "image recognition", "image processing"],
    "data science": ["data analytics", "data analysis"],
    "tensorflow": ["tf", "tensor flow"],
    "pytorch": ["torch", "py torch"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "pandas": ["pandas library", "python pandas"],
    "numpy": ["np", "numerical python"],
    "html": ["html5", "hypertext markup language"],
    "css": ["css3", "cascading style sheets", "stylesheets"],
    "rest": ["restful", "rest api", "restful api"],
    "graphql": ["graph ql", "gql"],
    "agile": ["scrum", "kanban", "agile methodology"],
    "devops": ["dev ops", "development operations"],
    "linux": ["unix", "ubuntu", "centos", "debian"],
    "java": ["java programming", "java se", "java ee"],
    "c++": ["cpp", "cplusplus", "c plus plus"],
    "c#": ["csharp", "c sharp", "dotnet", ".net"],
    "go": ["golang", "go programming"],
    "rust": ["rust programming", "rust lang"],
    "swift": ["swift programming", "swift language"],
    "kotlin": ["kotlin programming", "kotlin language"],
    "r": ["r programming", "r language", "r stats"],
}

# Skill category mapping for classification.
SKILL_CATEGORIES: dict[str, list[str]] = {
    "programming_languages": [
        "python", "javascript", "typescript", "java", "c++", "c#",
        "go", "rust", "swift", "kotlin", "r", "ruby", "php", "scala",
    ],
    "web_frameworks": [
        "react", "angular", "vue", "django", "flask", "fastapi",
        "express", "node", "next.js", "nuxt.js", "spring",
    ],
    "databases": [
        "sql", "postgresql", "mongodb", "mysql", "redis",
        "elasticsearch", "cassandra", "dynamodb", "sqlite",
    ],
    "cloud_devops": [
        "aws", "gcp", "azure", "docker", "kubernetes", "ci/cd",
        "terraform", "ansible", "jenkins", "linux", "devops",
    ],
    "data_ml": [
        "machine learning", "deep learning", "natural language processing",
        "computer vision", "data science", "tensorflow", "pytorch",
        "scikit-learn", "pandas", "numpy", "spark", "hadoop",
    ],
    "soft_skills": [
        "agile", "leadership", "communication", "teamwork",
        "problem solving", "project management", "mentoring",
    ],
}


class SkillMatcher:
    """Matches candidate skills against job requirements using fuzzy and semantic matching.

    Uses a combination of exact matching, fuzzy string matching (SequenceMatcher),
    and spaCy word-vector semantic similarity to determine whether a candidate
    possesses a required skill.

    Args:
        nlp: A loaded spaCy language model with word vectors.
    """

    def __init__(self, nlp: spacy.Language) -> None:
        self._nlp = nlp
        self._variation_index: dict[str, str] = self._build_variation_index()
        logger.info("skill_matcher.initialized", variation_count=len(self._variation_index))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_skill(self, candidate_skills: list[str], required_skill: str) -> bool:
        """Check whether a candidate possesses a required skill.

        Args:
            candidate_skills: List of skills the candidate claims.
            required_skill: The skill to search for.

        Returns:
            True if an exact, fuzzy, or semantic match is found.
        """
        norm_required = self._normalize_skill(required_skill)
        for skill in candidate_skills:
            norm_candidate = self._normalize_skill(skill)
            if norm_candidate == norm_required:
                return True
            if self._is_fuzzy_match(norm_candidate, norm_required):
                return True
            if self._is_semantic_match(norm_candidate, norm_required):
                return True
        return False

    def find_similar_skills(self, skill: str, threshold: float = 0.8) -> list[str]:
        """Find skills similar to the given one from the known variations.

        Args:
            skill: The skill to find matches for.
            threshold: Minimum similarity ratio (0-1).

        Returns:
            List of similar skill names above the threshold.
        """
        norm = self._normalize_skill(skill)
        similar: list[str] = []
        for canonical in SKILL_VARIATIONS:
            if canonical == norm:
                continue
            ratio = SequenceMatcher(None, norm, canonical).ratio()
            if ratio >= threshold:
                similar.append(canonical)
            else:
                sim = self._calculate_semantic_similarity(norm, canonical)
                if sim >= threshold:
                    similar.append(canonical)
        return similar

    def extract_skills(self, text: str) -> set[str]:
        """Extract recognised skills from free-form text.

        Args:
            text: Resume or job description text.

        Returns:
            Set of normalised skill names found in the text.
        """
        lower = text.lower()
        found: set[str] = set()
        for canonical, variations in SKILL_VARIATIONS.items():
            if self._word_present(canonical, lower):
                found.add(canonical)
                continue
            for variant in variations:
                if self._word_present(variant, lower):
                    found.add(canonical)
                    break
        return found

    @staticmethod
    def _word_present(term: str, text: str) -> bool:
        """Check if *term* appears in *text* as a whole word."""
        import re

        return bool(re.search(rf"\b{re.escape(term)}\b", text))

    def categorize_skills(self, skills: list[str]) -> dict[str, list[str]]:
        """Categorize a list of skills into predefined groups.

        Args:
            skills: List of skill names.

        Returns:
            Dict mapping category names to lists of matching skills.
        """
        result: dict[str, list[str]] = {cat: [] for cat in SKILL_CATEGORIES}
        result["other"] = []
        for skill in skills:
            norm = self._normalize_skill(skill)
            placed = False
            for category, members in SKILL_CATEGORIES.items():
                if norm in members:
                    result[category].append(skill)
                    placed = True
                    break
            if not placed:
                result["other"].append(skill)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_variation_index(self) -> dict[str, str]:
        """Build a reverse index from every variation to its canonical name."""
        index: dict[str, str] = {}
        for canonical, variants in SKILL_VARIATIONS.items():
            index[canonical] = canonical
            for v in variants:
                index[v] = canonical
        return index

    def _normalize_skill(self, skill: str) -> str:
        """Normalise a skill string to its canonical form."""
        cleaned = re.sub(r"[^\w\s/#+.]", "", skill.lower()).strip()
        return self._variation_index.get(cleaned, cleaned)

    def _is_fuzzy_match(self, skill_a: str, skill_b: str, threshold: float = 0.85) -> bool:
        """Return True if two skill strings are a fuzzy match."""
        return SequenceMatcher(None, skill_a, skill_b).ratio() >= threshold

    def _is_semantic_match(self, skill_a: str, skill_b: str, threshold: float = 0.8) -> bool:
        """Return True if two skills are semantically similar via word vectors."""
        return self._calculate_semantic_similarity(skill_a, skill_b) >= threshold

    def _calculate_semantic_similarity(self, text_a: str, text_b: str) -> float:
        """Calculate semantic similarity between two strings using spaCy vectors."""
        doc_a = self._nlp(text_a)
        doc_b = self._nlp(text_b)
        if not doc_a.has_vector or not doc_b.has_vector:
            return 0.0
        return float(doc_a.similarity(doc_b))
