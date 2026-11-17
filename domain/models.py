"""Strongly-typed OOP domain entities and value objects for Helix AI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from domain.enums import ClaimVerificationStatus, RelationshipStatus

UNAVAILABLE_LABEL = "Unavailable in source text"


@dataclass(slots=True)
class Publication:
    """Dataset A domain entity representing a peer-reviewed PubMed publication."""

    pmid: str
    title: str
    authors: str = ""
    journal: str = ""
    publication_year: int | None = None
    abstract: str = ""
    doi: str | None = None
    pubmed_url: str = ""
    source_query: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.pubmed_url and self.pmid:
            self.pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @property
    def has_abstract(self) -> bool:
        return bool((self.abstract or "").strip())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Publication:
        return cls(
            pmid=str(data["pmid"]),
            title=str(data.get("title", "")),
            authors=str(data.get("authors", "")),
            journal=str(data.get("journal", "")),
            publication_year=data.get("publication_year"),
            abstract=str(data.get("abstract", "")),
            doi=data.get("doi"),
            pubmed_url=str(data.get("pubmed_url", "")),
            source_query=str(data.get("source_query", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


@dataclass(slots=True)
class GEOStudy:
    """Dataset B domain entity representing an NCBI GEO Series (GSE) study."""

    gse_accession: str
    study_title: str
    gds_uid: str | None = None
    organism: str = ""
    platform: str = ""
    sample_count: int | None = None
    study_summary: str = ""
    associated_pmids: str = ""
    geo_url: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.gse_accession = self.gse_accession.strip().upper()
        if not self.geo_url and self.gse_accession:
            self.geo_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={self.gse_accession}"

    @property
    def pmid_list(self) -> list[str]:
        return [p.strip() for p in self.associated_pmids.split(",") if p.strip()]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GEOStudy:
        return cls(
            gse_accession=str(data["gse_accession"]).upper(),
            gds_uid=data.get("gds_uid"),
            study_title=str(data.get("study_title", "")),
            organism=str(data.get("organism", "")),
            platform=str(data.get("platform", "")),
            sample_count=data.get("sample_count"),
            study_summary=str(data.get("study_summary", "")),
            associated_pmids=str(data.get("associated_pmids", "")),
            geo_url=str(data.get("geo_url", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


@dataclass(slots=True)
class PubGeoRelationship:
    """Dataset C domain entity modeling an evidence-graded PubMed <-> GEO link."""

    pmid: str
    gse_accession: str
    relationship_method: str
    supporting_evidence: str
    verification_status: RelationshipStatus
    confidence_score: float
    uncertainty_indicator: str
    publication_title: str = ""
    study_title: str = ""
    organism: str = ""
    platform: str = ""
    sample_count: int | None = None
    geo_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verification_status"] = self.verification_status.value
        return d


@dataclass(slots=True)
class ExtractedField:
    """Dataset D field-level scientific extraction with verbatim source provenance."""

    pmid: str
    field_name: str
    extracted_value: str
    supporting_passage: str = ""
    extraction_method: str = ""
    verification_status: ClaimVerificationStatus = ClaimVerificationStatus.UNVERIFIED
    verification_notes: str = ""
    grounding_score: float = 0.0
    publication_title: str = ""
    journal: str = ""
    publication_year: int | None = None
    pubmed_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verification_status"] = self.verification_status.value
        return d


@dataclass(slots=True)
class IdentifierCheckResult:
    """Audit output for PMID or GSE identifier existence and title correspondence."""

    identifier: str
    exists: bool
    title_matches: bool
    status: ClaimVerificationStatus
    details: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass(slots=True)
class SearchBatchResult:
    """Structured return object from a paginated PubMed literature search."""

    query: str
    total_found: int
    page: int
    page_size: int
    publications: list[Publication] = field(default_factory=list)
    newly_inserted: int = 0
    duplicates_skipped: int = 0
    excluded_count: int = 0


@dataclass(slots=True)
class PipelineRunSummary:
    """Aggregated telemetry returned by HelixResearchPipeline.execute_query()."""

    query: str
    total_pubmed_hits: int
    retrieved_publications: int
    newly_inserted_publications: int
    duplicates_skipped: int
    geo_links_discovered: int
    verified_geo_links: int
    extracted_publications: int
    errors: list[str] = field(default_factory=list)
