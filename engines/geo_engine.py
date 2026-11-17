"""Engine 2A: NCBI GEO Dataset Discovery & Metadata Persistence."""

from __future__ import annotations

from domain.models import GEOStudy
from interfaces.literature_client import LiteratureClientProtocol
from interfaces.repository import ResearchRepositoryProtocol
from services.ncbi_service import GEOESummaryParser
from utils.logging_config import get_logger
from utils.validators import IdentifierValidator

logger = get_logger("geo_engine")


class GEOEngine:
    """Queries NCBI GEO (GDS database) and stores validated GSE study entities."""

    def __init__(
        self,
        repository: ResearchRepositoryProtocol,
        client: LiteratureClientProtocol,
    ) -> None:
        self.repository = repository
        self.client = client

    def fetch_by_accession(self, gse_accession: str, use_cache: bool = True) -> GEOStudy | None:
        if not IdentifierValidator.is_valid_gse(gse_accession):
            self.repository.log_excluded_record(
                record_type="geo_accession",
                raw_identifier=str(gse_accession),
                exclusion_reason="Invalid GSE accession format",
                source_context="GEOEngine.fetch_by_accession",
            )
            return None

        clean_gse = IdentifierValidator.validate_gse(gse_accession)
        search_res = self.client.esearch(
            db="gds",
            term=f"{clean_gse}[ACCN] AND gse[ETYP]",
            retmax=5,
            use_cache=use_cache,
        )
        uids = search_res.get("idlist", [])
        if not uids:
            return None

        studies = self.fetch_by_gds_uids(uids, use_cache=use_cache)
        for study in studies:
            if study.gse_accession == clean_gse:
                return study
        return studies[0] if studies else None

    def fetch_by_gds_uids(self, gds_uids: list[str], use_cache: bool = True) -> list[GEOStudy]:
        clean_uids = [str(u).strip() for u in gds_uids if str(u).strip().isdigit()]
        if not clean_uids:
            return []

        summary_result = self.client.esummary(db="gds", ids=clean_uids, use_cache=use_cache)
        valid_studies, excluded = GEOESummaryParser.parse(summary_result)

        for ex in excluded:
            self.repository.log_excluded_record(**ex)

        stored: list[GEOStudy] = []
        for study in valid_studies:
            self.repository.upsert_geo_study(study)
            row = self.repository.get_geo_study(study["gse_accession"]) or study
            stored.append(GEOStudy.from_dict(row))
        return stored

    def search_geo_studies(self, query: str, max_results: int = 10, use_cache: bool = True) -> list[GEOStudy]:
        cleaned = (query or "").strip()
        if not cleaned:
            return []
        search_res = self.client.esearch(
            db="gds",
            term=f"({cleaned}) AND gse[ETYP]",
            retmax=max_results,
            use_cache=use_cache,
        )
        return self.fetch_by_gds_uids(search_res.get("idlist", []), use_cache=use_cache)
