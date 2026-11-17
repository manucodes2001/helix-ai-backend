"""Engine 1: PubMed Literature Retrieval, Pagination & Deduplication."""

from __future__ import annotations

from typing import Any

from domain.models import Publication, SearchBatchResult
from interfaces.literature_client import LiteratureClientProtocol
from interfaces.repository import ResearchRepositoryProtocol
from services.ncbi_service import PubMedXMLParser
from utils.logging_config import get_logger
from utils.validators import IdentifierValidator

logger = get_logger("pubmed_engine")


class PubMedEngine:
    """Retrieves genuine PubMed records, deduplicates on PMID, and persists metadata."""

    def __init__(
        self,
        repository: ResearchRepositoryProtocol,
        client: LiteratureClientProtocol,
    ) -> None:
        self.repository = repository
        self.client = client

    def search_and_fetch(
        self,
        query: str,
        max_results: int = 10,
        page: int = 1,
        page_size: int | None = None,
        use_cache: bool = True,
    ) -> SearchBatchResult:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            raise ValueError("Research query cannot be empty.")

        effective_size = max(1, min(int(page_size or max_results), 100))
        safe_page = max(1, int(page))
        retstart = (safe_page - 1) * effective_size

        search_res = self.client.esearch(
            db="pubmed",
            term=cleaned_query,
            retstart=retstart,
            retmax=effective_size,
            sort="relevance",
            use_cache=use_cache,
        )
        total_found = int(search_res.get("count", 0))
        raw_pmids = search_res.get("idlist", [])

        valid_pmids: list[str] = []
        excluded_count = 0
        for raw_id in raw_pmids:
            if IdentifierValidator.is_valid_pmid(raw_id):
                valid_pmids.append(IdentifierValidator.validate_pmid(raw_id))
            else:
                excluded_count += 1
                self.repository.log_excluded_record(
                    record_type="pubmed_search_id",
                    raw_identifier=str(raw_id),
                    exclusion_reason="Invalid PMID returned from esearch",
                    source_context=cleaned_query,
                )

        if not valid_pmids:
            self.repository.log_search_query(
                query_text=cleaned_query,
                db_source="pubmed",
                retmax=effective_size,
                total_found=total_found,
                retrieved_count=0,
                duplicates_skipped=0,
                excluded_count=excluded_count,
            )
            return SearchBatchResult(
                query=cleaned_query,
                total_found=total_found,
                page=safe_page,
                page_size=effective_size,
                publications=[],
                newly_inserted=0,
                duplicates_skipped=0,
                excluded_count=excluded_count,
            )

        xml_payload = self.client.efetch_pubmed_xml(valid_pmids, use_cache=use_cache)
        parsed_records, parse_excluded = PubMedXMLParser.parse(xml_payload, source_query=cleaned_query)

        for ex in parse_excluded:
            excluded_count += 1
            self.repository.log_excluded_record(
                record_type=ex["record_type"],
                raw_identifier=ex["raw_identifier"],
                exclusion_reason=ex["exclusion_reason"],
                source_context=ex["source_context"],
            )

        newly_inserted = 0
        duplicates_skipped = 0
        stored_publications: list[Publication] = []
        seen_in_batch: set[str] = set()

        for record in parsed_records:
            pmid = record["pmid"]
            if pmid in seen_in_batch:
                duplicates_skipped += 1
                continue
            seen_in_batch.add(pmid)

            is_new = self.repository.upsert_publication(record)
            if is_new:
                newly_inserted += 1
            else:
                duplicates_skipped += 1

            stored = self.repository.get_publication(pmid) or record
            stored_publications.append(Publication.from_dict(stored))

        self.repository.log_search_query(
            query_text=cleaned_query,
            db_source="pubmed",
            retmax=effective_size,
            total_found=total_found,
            retrieved_count=len(stored_publications),
            duplicates_skipped=duplicates_skipped,
            excluded_count=excluded_count,
        )

        return SearchBatchResult(
            query=cleaned_query,
            total_found=total_found,
            page=safe_page,
            page_size=effective_size,
            publications=stored_publications,
            newly_inserted=newly_inserted,
            duplicates_skipped=duplicates_skipped,
            excluded_count=excluded_count,
        )

    def fetch_by_pmids(self, pmids: list[str], source_query: str = "direct_pmid_lookup") -> list[Publication]:
        clean_pmids = [IdentifierValidator.validate_pmid(p) for p in pmids if IdentifierValidator.is_valid_pmid(p)]
        if not clean_pmids:
            return []
        xml_payload = self.client.efetch_pubmed_xml(clean_pmids)
        records, excluded = PubMedXMLParser.parse(xml_payload, source_query=source_query)
        for ex in excluded:
            self.repository.log_excluded_record(**ex)
        results: list[Publication] = []
        for rec in records:
            self.repository.upsert_publication(rec)
            stored = self.repository.get_publication(rec["pmid"]) or rec
            results.append(Publication.from_dict(stored))
        return results
