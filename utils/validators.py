"""Object-oriented biomedical identifier validators and accession extractors."""

from __future__ import annotations

import re

from domain.exceptions import IdentifierValidationError


class IdentifierValidator:
    """Validates and extracts PubMed (PMID), GEO (GSE/GPL/GSM), and DOI identifiers."""

    PMID_PATTERN = re.compile(r"^[1-9]\d{0,8}$")
    GSE_PATTERN = re.compile(r"^GSE[1-9]\d{0,7}$", re.IGNORECASE)
    GPL_PATTERN = re.compile(r"^GPL[1-9]\d{0,7}$", re.IGNORECASE)
    GSM_PATTERN = re.compile(r"^GSM[1-9]\d{0,8}$", re.IGNORECASE)
    DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

    GSE_TEXT_REGEX = re.compile(r"\b(GSE[1-9]\d{1,7})\b", re.IGNORECASE)
    PMID_TEXT_REGEX = re.compile(r"\bPMID\s*[:#]?\s*([1-9]\d{4,8})\b", re.IGNORECASE)

    @classmethod
    def validate_pmid(cls, pmid: str | int | None) -> str:
        if pmid is None:
            raise IdentifierValidationError("PMID cannot be None.")
        cleaned = str(pmid).strip()
        if cleaned.lower().startswith("pmid:"):
            cleaned = cleaned.split(":", 1)[1].strip()
        if not cls.PMID_PATTERN.match(cleaned):
            raise IdentifierValidationError(f"Invalid PMID format: '{pmid}'")
        return cleaned

    @classmethod
    def is_valid_pmid(cls, pmid: str | int | None) -> bool:
        try:
            cls.validate_pmid(pmid)
            return True
        except IdentifierValidationError:
            return False

    @classmethod
    def validate_gse(cls, gse_accession: str | None) -> str:
        if gse_accession is None:
            raise IdentifierValidationError("GSE accession cannot be None.")
        cleaned = str(gse_accession).strip().upper()
        if not cls.GSE_PATTERN.match(cleaned):
            raise IdentifierValidationError(f"Invalid GEO Series accession: '{gse_accession}'")
        return cleaned

    @classmethod
    def is_valid_gse(cls, gse_accession: str | None) -> bool:
        try:
            cls.validate_gse(gse_accession)
            return True
        except IdentifierValidationError:
            return False

    @classmethod
    def validate_doi(cls, doi: str | None) -> str | None:
        if not doi:
            return None
        cleaned = str(doi).strip()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        if cls.DOI_PATTERN.match(cleaned):
            return cleaned
        return None

    @classmethod
    def extract_gse_mentions(cls, text: str, context_window: int = 120) -> list[dict[str, str]]:
        if not text:
            return []
        seen: set[str] = set()
        mentions: list[dict[str, str]] = []
        for match in cls.GSE_TEXT_REGEX.finditer(text):
            gse = match.group(1).upper()
            if gse in seen:
                continue
            seen.add(gse)
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            snippet = text[start:end].strip().replace("\n", " ")
            mentions.append({"gse_accession": gse, "context_snippet": snippet})
        return mentions

    @classmethod
    def extract_pmid_mentions(cls, text: str) -> list[str]:
        if not text:
            return []
        seen: set[str] = set()
        results: list[str] = []
        for match in cls.PMID_TEXT_REGEX.finditer(text):
            pmid = match.group(1)
            if pmid not in seen and cls.is_valid_pmid(pmid):
                seen.add(pmid)
                results.append(pmid)
        return results
