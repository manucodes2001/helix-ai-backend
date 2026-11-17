"""SQLite implementation of ResearchRepositoryProtocol using Unit-of-Work transactions."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger("repository")


class SQLiteResearchRepository:
    """Thread-safe SQLite repository managing all Helix AI datasets, caches, and audit logs."""

    def __init__(self, db_path: Path | str | None = None, schema_path: Path | None = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path) if db_path is not None else settings.DB_PATH
        self.schema_path = schema_path or settings.SCHEMA_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self.transaction() as conn:
            conn.executescript(schema_sql)

    def log_search_query(
        self,
        query_text: str,
        db_source: str = "pubmed",
        retmax: int = 10,
        total_found: int = 0,
        retrieved_count: int = 0,
        duplicates_skipped: int = 0,
        excluded_count: int = 0,
    ) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO search_queries
                    (query_text, db_source, retmax, total_found, retrieved_count, duplicates_skipped, excluded_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (query_text, db_source, retmax, total_found, retrieved_count, duplicates_skipped, excluded_count),
            )
            return int(cur.lastrowid)

    def get_recent_searches(self, limit: int = 15) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            rows = conn.execute("SELECT * FROM search_queries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def publication_exists(self, pmid: str) -> bool:
        with self.transaction() as conn:
            return conn.execute("SELECT 1 FROM publications WHERE pmid = ?", (pmid,)).fetchone() is not None

    def upsert_publication(self, record: dict[str, Any]) -> bool:
        pmid = str(record["pmid"]).strip()
        is_new = not self.publication_exists(pmid)
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO publications
                    (pmid, title, authors, journal, publication_year, abstract, doi, pubmed_url, source_query)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pmid) DO UPDATE SET
                    title = excluded.title,
                    authors = CASE WHEN excluded.authors != '' THEN excluded.authors ELSE publications.authors END,
                    journal = CASE WHEN excluded.journal != '' THEN excluded.journal ELSE publications.journal END,
                    publication_year = COALESCE(excluded.publication_year, publications.publication_year),
                    abstract = CASE WHEN excluded.abstract != '' THEN excluded.abstract ELSE publications.abstract END,
                    doi = COALESCE(excluded.doi, publications.doi),
                    pubmed_url = excluded.pubmed_url,
                    updated_at = datetime('now')
                """,
                (
                    pmid,
                    record.get("title", ""),
                    record.get("authors", ""),
                    record.get("journal", ""),
                    record.get("publication_year"),
                    record.get("abstract", ""),
                    record.get("doi"),
                    record.get("pubmed_url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"),
                    record.get("source_query", ""),
                ),
            )
        return is_new

    def get_publication(self, pmid: str) -> dict[str, Any] | None:
        with self.transaction() as conn:
            row = conn.execute("SELECT * FROM publications WHERE pmid = ?", (str(pmid),)).fetchone()
            return dict(row) if row else None

    def get_all_publications(self, query_filter: str | None = None) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            if query_filter:
                like_term = f"%{query_filter.strip()}%"
                rows = conn.execute(
                    """
                    SELECT * FROM publications
                    WHERE title LIKE ? OR abstract LIKE ? OR source_query LIKE ? OR pmid LIKE ?
                    ORDER BY publication_year DESC, pmid DESC
                    """,
                    (like_term, like_term, like_term, like_term),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM publications ORDER BY created_at DESC, pmid DESC").fetchall()
            return [dict(r) for r in rows]

    def geo_study_exists(self, gse_accession: str) -> bool:
        with self.transaction() as conn:
            return (
                conn.execute(
                    "SELECT 1 FROM geo_studies WHERE gse_accession = ?",
                    (gse_accession.upper(),),
                ).fetchone()
                is not None
            )

    def upsert_geo_study(self, record: dict[str, Any]) -> bool:
        gse = str(record["gse_accession"]).strip().upper()
        is_new = not self.geo_study_exists(gse)
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO geo_studies
                    (gse_accession, gds_uid, study_title, organism, platform, sample_count, study_summary, associated_pmids, geo_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(gse_accession) DO UPDATE SET
                    gds_uid = COALESCE(excluded.gds_uid, geo_studies.gds_uid),
                    study_title = excluded.study_title,
                    organism = CASE WHEN excluded.organism != '' THEN excluded.organism ELSE geo_studies.organism END,
                    platform = CASE WHEN excluded.platform != '' THEN excluded.platform ELSE geo_studies.platform END,
                    sample_count = COALESCE(excluded.sample_count, geo_studies.sample_count),
                    study_summary = CASE WHEN excluded.study_summary != '' THEN excluded.study_summary ELSE geo_studies.study_summary END,
                    associated_pmids = CASE WHEN excluded.associated_pmids != '' THEN excluded.associated_pmids ELSE geo_studies.associated_pmids END,
                    geo_url = excluded.geo_url,
                    updated_at = datetime('now')
                """,
                (
                    gse,
                    record.get("gds_uid"),
                    record.get("study_title", ""),
                    record.get("organism", ""),
                    record.get("platform", ""),
                    record.get("sample_count"),
                    record.get("study_summary", ""),
                    record.get("associated_pmids", ""),
                    record.get("geo_url", f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse}"),
                ),
            )
        return is_new

    def get_geo_study(self, gse_accession: str) -> dict[str, Any] | None:
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM geo_studies WHERE gse_accession = ?",
                (gse_accession.upper(),),
            ).fetchone()
            return dict(row) if row else None

    def get_all_geo_studies(self) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            rows = conn.execute("SELECT * FROM geo_studies ORDER BY created_at DESC, gse_accession ASC").fetchall()
            return [dict(r) for r in rows]

    def upsert_relationship(self, rel: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO pub_geo_relationships
                    (pmid, gse_accession, relationship_method, supporting_evidence, verification_status, confidence_score, uncertainty_indicator)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pmid, gse_accession, relationship_method) DO UPDATE SET
                    supporting_evidence = excluded.supporting_evidence,
                    verification_status = excluded.verification_status,
                    confidence_score = excluded.confidence_score,
                    uncertainty_indicator = excluded.uncertainty_indicator
                """,
                (
                    str(rel["pmid"]),
                    str(rel["gse_accession"]).upper(),
                    rel["relationship_method"],
                    rel.get("supporting_evidence", ""),
                    rel["verification_status"],
                    float(rel.get("confidence_score", 0.0)),
                    rel.get("uncertainty_indicator", "High"),
                ),
            )

    def get_relationships(self, pmid: str | None = None) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            if pmid:
                rows = conn.execute(
                    """
                    SELECT r.*, p.title AS publication_title, g.study_title, g.organism, g.platform, g.sample_count, g.geo_url
                    FROM pub_geo_relationships r
                    LEFT JOIN publications p ON r.pmid = p.pmid
                    LEFT JOIN geo_studies g ON r.gse_accession = g.gse_accession
                    WHERE r.pmid = ?
                    ORDER BY r.confidence_score DESC
                    """,
                    (str(pmid),),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT r.*, p.title AS publication_title, g.study_title, g.organism, g.platform, g.sample_count, g.geo_url
                    FROM pub_geo_relationships r
                    LEFT JOIN publications p ON r.pmid = p.pmid
                    LEFT JOIN geo_studies g ON r.gse_accession = g.gse_accession
                    ORDER BY r.confidence_score DESC, r.id DESC
                    """
                ).fetchall()
            return [dict(r) for r in rows]

    def save_extraction(
        self,
        pmid: str,
        extraction_model: str,
        raw_json: str,
        fields: list[dict[str, Any]],
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO extractions (pmid, extraction_model, raw_json, extracted_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(pmid) DO UPDATE SET
                    extraction_model = excluded.extraction_model,
                    raw_json = excluded.raw_json,
                    extracted_at = datetime('now')
                """,
                (str(pmid), extraction_model, raw_json),
            )
            for item in fields:
                conn.execute(
                    """
                    INSERT INTO extraction_fields
                        (pmid, field_name, extracted_value, supporting_passage, extraction_method, verification_status, verification_notes, grounding_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(pmid, field_name) DO UPDATE SET
                        extracted_value = excluded.extracted_value,
                        supporting_passage = excluded.supporting_passage,
                        extraction_method = excluded.extraction_method,
                        verification_status = excluded.verification_status,
                        verification_notes = excluded.verification_notes,
                        grounding_score = excluded.grounding_score,
                        created_at = datetime('now')
                    """,
                    (
                        str(pmid),
                        item["field_name"],
                        item["extracted_value"],
                        item.get("supporting_passage", ""),
                        item.get("extraction_method", extraction_model),
                        item.get("verification_status", "Unverified"),
                        item.get("verification_notes", ""),
                        float(item.get("grounding_score", 0.0)),
                    ),
                )

    def update_field_verification(
        self,
        pmid: str,
        field_name: str,
        verification_status: str,
        verification_notes: str,
        grounding_score: float,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE extraction_fields
                SET verification_status = ?, verification_notes = ?, grounding_score = ?
                WHERE pmid = ? AND field_name = ?
                """,
                (verification_status, verification_notes, float(grounding_score), str(pmid), field_name),
            )

    def get_extraction_fields(self, pmid: str | None = None) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            if pmid:
                rows = conn.execute(
                    """
                    SELECT ef.*, p.title AS publication_title, p.journal, p.publication_year, p.pubmed_url
                    FROM extraction_fields ef
                    JOIN publications p ON ef.pmid = p.pmid
                    WHERE ef.pmid = ?
                    ORDER BY ef.id ASC
                    """,
                    (str(pmid),),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT ef.*, p.title AS publication_title, p.journal, p.publication_year, p.pubmed_url
                    FROM extraction_fields ef
                    JOIN publications p ON ef.pmid = p.pmid
                    ORDER BY ef.pmid DESC, ef.id ASC
                    """
                ).fetchall()
            return [dict(r) for r in rows]

    def log_verification(
        self,
        entity_type: str,
        entity_id: str,
        status: str,
        details: str = "",
        pmid: str | None = None,
        field_name: str | None = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO verification_logs (entity_type, entity_id, pmid, field_name, status, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entity_type, str(entity_id), pmid, field_name, status, details),
            )

    def get_verification_logs(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            rows = conn.execute("SELECT * FROM verification_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def log_excluded_record(
        self,
        record_type: str,
        raw_identifier: str,
        exclusion_reason: str,
        source_context: str = "",
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO excluded_records (record_type, raw_identifier, exclusion_reason, source_context)
                VALUES (?, ?, ?, ?)
                """,
                (record_type, str(raw_identifier), exclusion_reason, source_context),
            )

    def get_excluded_records(self) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            rows = conn.execute("SELECT * FROM excluded_records ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def get_cached_response(self, cache_key: str) -> str | None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT response_payload, expires_at FROM api_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if not row:
                return None
            if row["expires_at"] <= now_iso:
                conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (cache_key,))
                return None
            return str(row["response_payload"])

    def set_cached_response(
        self,
        cache_key: str,
        endpoint: str,
        response_payload: str,
        ttl_hours: int = 72,
    ) -> None:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO api_cache (cache_key, endpoint, response_payload, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_payload = excluded.response_payload,
                    created_at = datetime('now'),
                    expires_at = excluded.expires_at
                """,
                (cache_key, endpoint, response_payload, expires_at),
            )

    def get_dashboard_stats(self) -> dict[str, Any]:
        with self.transaction() as conn:
            pub_count = conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0]
            geo_count = conn.execute("SELECT COUNT(*) FROM geo_studies").fetchone()[0]
            verified_links = conn.execute(
                "SELECT COUNT(*) FROM pub_geo_relationships WHERE verification_status = 'Verified relationship'"
            ).fetchone()[0]
            candidate_links = conn.execute(
                "SELECT COUNT(*) FROM pub_geo_relationships WHERE verification_status = 'Candidate relationship'"
            ).fetchone()[0]
            total_fields = conn.execute("SELECT COUNT(*) FROM extraction_fields").fetchone()[0]
            verified_fields = conn.execute(
                "SELECT COUNT(*) FROM extraction_fields WHERE verification_status = 'Verified'"
            ).fetchone()[0]
            unsupported_fields = conn.execute(
                "SELECT COUNT(*) FROM extraction_fields WHERE verification_status = 'Unsupported'"
            ).fetchone()[0]
            searches_count = conn.execute("SELECT COUNT(*) FROM search_queries").fetchone()[0]

            return {
                "publications_count": pub_count,
                "geo_studies_count": geo_count,
                "verified_geo_links": verified_links,
                "candidate_geo_links": candidate_links,
                "total_extracted_fields": total_fields,
                "verified_extracted_fields": verified_fields,
                "unsupported_extracted_fields": unsupported_fields,
                "searches_count": searches_count,
            }

    def get_master_research_dataset(self) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.pmid,
                    p.title AS publication_title,
                    p.authors,
                    p.journal,
                    p.publication_year,
                    p.doi,
                    p.pubmed_url,
                    p.source_query,
                    r.gse_accession,
                    g.study_title AS geo_study_title,
                    g.organism AS geo_organism,
                    g.platform AS geo_platform,
                    g.sample_count AS geo_sample_count,
                    r.relationship_method AS geo_link_method,
                    r.verification_status AS geo_link_status,
                    r.confidence_score AS geo_link_confidence,
                    ef.field_name,
                    ef.extracted_value,
                    ef.supporting_passage,
                    ef.extraction_method,
                    ef.verification_status AS claim_verification_status,
                    ef.grounding_score,
                    ef.verification_notes
                FROM publications p
                LEFT JOIN pub_geo_relationships r
                    ON p.pmid = r.pmid AND r.gse_accession != 'NONE'
                LEFT JOIN geo_studies g
                    ON r.gse_accession = g.gse_accession
                LEFT JOIN extraction_fields ef
                    ON p.pmid = ef.pmid
                ORDER BY p.publication_year DESC, p.pmid ASC, ef.id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]
