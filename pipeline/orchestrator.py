"""Application Facade & Dependency Injection Factory for Helix AI."""

from __future__ import annotations

from pathlib import Path

from config.settings import Settings, get_settings
from database.repository import SQLiteResearchRepository
from domain.enums import RelationshipStatus
from domain.exceptions import ConfigurationError
from domain.models import PipelineRunSummary
from engines.cross_reference_engine import CrossReferenceEngine
from engines.extraction_engine import ExtractionEngine
from engines.geo_engine import GEOEngine
from engines.pubmed_engine import PubMedEngine
from engines.verification_engine import VerificationEngine
from interfaces.literature_client import LiteratureClientProtocol
from interfaces.llm_extractor import StructuredExtractorProtocol
from interfaces.repository import ResearchRepositoryProtocol
from services.export_service import ExportService
from services.ncbi_service import NCBIService
from services.openai_service import OpenAIService


class HelixResearchPipeline:
    """Facade coordinating Engines 1-4 for end-to-end literature-to-dataset intelligence."""

    def __init__(
        self,
        repository: ResearchRepositoryProtocol,
        pubmed_engine: PubMedEngine,
        geo_engine: GEOEngine,
        cross_reference_engine: CrossReferenceEngine,
        extraction_engine: ExtractionEngine,
        verification_engine: VerificationEngine,
        export_service: ExportService,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository
        self.pubmed = pubmed_engine
        self.geo = geo_engine
        self.xref = cross_reference_engine
        self.extraction = extraction_engine
        self.verification = verification_engine
        self.export = export_service

    def execute_query(
        self,
        query: str,
        max_results: int = 10,
        page: int = 1,
        link_geo: bool = True,
        run_extraction: bool = False,
        remote_id_verify: bool = False,
    ) -> PipelineRunSummary:
        batch = self.pubmed.search_and_fetch(
            query=query,
            max_results=max_results,
            page=page,
            page_size=max_results,
        )
        geo_links = 0
        verified_links = 0
        extracted_papers = 0
        errors: list[str] = []

        for pub in batch.publications:
            if link_geo:
                try:
                    rels = self.xref.link_publication(pub.pmid)
                    geo_links += sum(1 for r in rels if r.gse_accession != "NONE")
                    verified_links += sum(1 for r in rels if r.verification_status == RelationshipStatus.VERIFIED)
                except Exception as exc:
                    errors.append(f"GEO Cross-Reference failed for PMID {pub.pmid}: {exc}")

            if run_extraction:
                try:
                    self.extraction.extract_for_publication(pub.pmid)
                    self.verification.verify_publication_extractions(
                        pmid=pub.pmid,
                        remote_pmid_check=remote_id_verify,
                    )
                    extracted_papers += 1
                except ConfigurationError as exc:
                    errors.append(str(exc))
                    run_extraction = False
                except Exception as exc:
                    errors.append(f"AI Extraction/Verification failed for PMID {pub.pmid}: {exc}")

        return PipelineRunSummary(
            query=query.strip(),
            total_pubmed_hits=batch.total_found,
            retrieved_publications=len(batch.publications),
            newly_inserted_publications=batch.newly_inserted,
            duplicates_skipped=batch.duplicates_skipped,
            geo_links_discovered=geo_links,
            verified_geo_links=verified_links,
            extracted_publications=extracted_papers,
            errors=errors,
        )


def create_default_pipeline(
    db_path: Path | str | None = None,
    repository: ResearchRepositoryProtocol | None = None,
    ncbi_client: LiteratureClientProtocol | None = None,
    llm_extractor: StructuredExtractorProtocol | None = None,
    settings: Settings | None = None,
) -> HelixResearchPipeline:
    """Composition root assembling all Helix AI engines with clean dependency injection."""
    active_settings = settings or get_settings()
    repo = repository or SQLiteResearchRepository(db_path=db_path or active_settings.DB_PATH)
    client = ncbi_client or NCBIService(repository=repo, settings=active_settings)
    extractor = llm_extractor or OpenAIService(settings=active_settings)

    pubmed_engine = PubMedEngine(repository=repo, client=client)
    geo_engine = GEOEngine(repository=repo, client=client)
    xref_engine = CrossReferenceEngine(repository=repo, client=client, geo_engine=geo_engine)
    extraction_engine = ExtractionEngine(repository=repo, extractor=extractor)
    verification_engine = VerificationEngine(repository=repo, client=client)
    export_service = ExportService(repository=repo, settings=active_settings)

    return HelixResearchPipeline(
        repository=repo,
        pubmed_engine=pubmed_engine,
        geo_engine=geo_engine,
        cross_reference_engine=xref_engine,
        extraction_engine=extraction_engine,
        verification_engine=verification_engine,
        export_service=export_service,
        settings=active_settings,
    )
