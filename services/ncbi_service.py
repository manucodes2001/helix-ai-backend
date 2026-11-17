"""Rate-limited, cached, retry-enabled NCBI E-utilities client and dedicated XML/JSON parsers."""

from __future__ import annotations

import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

try:
    from Bio import Entrez
except ImportError:  # pragma: no cover
    Entrez = None

from config.settings import Settings, get_settings
from database.repository import SQLiteResearchRepository
from domain.exceptions import NCBIAPIError
from interfaces.repository import ResearchRepositoryProtocol
from utils.logging_config import get_logger
from utils.validators import IdentifierValidator

logger = get_logger("ncbi_service")


class PubMedXMLParser:
    """Stateless XML parser converting PubMed efetch XML into validated publication dicts."""

    @staticmethod
    def _collect_text(element: ET.Element | None) -> str:
        if element is None:
            return ""
        return re.sub(r"\s+", " ", "".join(element.itertext())).strip()

    @classmethod
    def parse(cls, xml_text: str, source_query: str = "") -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        valid_records: list[dict[str, Any]] = []
        excluded: list[dict[str, str]] = []

        if not xml_text or not xml_text.strip():
            return valid_records, excluded

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            excluded.append(
                {
                    "record_type": "pubmed_xml_batch",
                    "raw_identifier": "XML_PARSE_ERROR",
                    "exclusion_reason": f"Malformed PubMed XML response: {exc}",
                    "source_context": source_query,
                }
            )
            return valid_records, excluded

        for article_node in root.findall(".//PubmedArticle"):
            pmid_raw = cls._collect_text(article_node.find(".//MedlineCitation/PMID"))
            if not IdentifierValidator.is_valid_pmid(pmid_raw):
                excluded.append(
                    {
                        "record_type": "pubmed_article",
                        "raw_identifier": pmid_raw or "MISSING_PMID",
                        "exclusion_reason": "Missing or invalid PMID format",
                        "source_context": source_query,
                    }
                )
                continue

            pmid = IdentifierValidator.validate_pmid(pmid_raw)
            title = cls._collect_text(article_node.find(".//Article/ArticleTitle"))
            if not title:
                excluded.append(
                    {
                        "record_type": "pubmed_article",
                        "raw_identifier": pmid,
                        "exclusion_reason": "Missing publication title",
                        "source_context": source_query,
                    }
                )
                continue

            authors_list: list[str] = []
            for author_node in article_node.findall(".//Article/AuthorList/Author"):
                last_name = cls._collect_text(author_node.find("LastName"))
                fore_name = cls._collect_text(author_node.find("ForeName"))
                collective = cls._collect_text(author_node.find("CollectiveName"))
                if last_name and fore_name:
                    authors_list.append(f"{fore_name} {last_name}")
                elif last_name:
                    authors_list.append(last_name)
                elif collective:
                    authors_list.append(collective)

            journal = (
                cls._collect_text(article_node.find(".//Article/Journal/Title"))
                or cls._collect_text(article_node.find(".//MedlineCitation/MedlineJournalInfo/MedlineTA"))
            )
            year_text = (
                cls._collect_text(article_node.find(".//Article/Journal/JournalIssue/PubDate/Year"))
                or cls._collect_text(article_node.find(".//Article/ArticleDate/Year"))
            )
            if not year_text:
                medline_date = cls._collect_text(article_node.find(".//Article/Journal/JournalIssue/PubDate/MedlineDate"))
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", medline_date)
                year_text = year_match.group(1) if year_match else ""
            publication_year = int(year_text) if year_text.isdigit() else None

            abstract_parts: list[str] = []
            for abs_node in article_node.findall(".//Article/Abstract/AbstractText"):
                label = (abs_node.attrib.get("Label") or "").strip()
                segment = cls._collect_text(abs_node)
                if not segment:
                    continue
                if label and label.upper() != "UNLABELLED":
                    abstract_parts.append(f"{label}: {segment}")
                else:
                    abstract_parts.append(segment)

            doi: str | None = None
            for id_node in article_node.findall(".//PubmedData/ArticleIdList/ArticleId"):
                if id_node.attrib.get("IdType") == "doi":
                    doi = IdentifierValidator.validate_doi(cls._collect_text(id_node))
                    if doi:
                        break

            valid_records.append(
                {
                    "pmid": pmid,
                    "title": title.rstrip("."),
                    "authors": ", ".join(authors_list),
                    "journal": journal,
                    "publication_year": publication_year,
                    "abstract": " ".join(abstract_parts).strip(),
                    "doi": doi,
                    "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source_query": source_query,
                }
            )

        return valid_records, excluded


class GEOESummaryParser:
    """Stateless JSON parser converting NCBI GDS esummary payloads into GEO study dicts."""

    @staticmethod
    def parse(summary_result: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        valid_studies: list[dict[str, Any]] = []
        excluded: list[dict[str, str]] = []

        for uid in summary_result.get("uids", []):
            doc = summary_result.get(str(uid))
            if not isinstance(doc, dict):
                continue

            raw_acc = str(doc.get("accession", "")).strip().upper()
            if not IdentifierValidator.is_valid_gse(raw_acc):
                excluded.append(
                    {
                        "record_type": "geo_record",
                        "raw_identifier": raw_acc or str(uid),
                        "exclusion_reason": "Record is not a valid GEO Series (GSE) accession",
                        "source_context": f"gds_uid:{uid}",
                    }
                )
                continue

            gse_accession = IdentifierValidator.validate_gse(raw_acc)
            study_title = str(doc.get("title", "")).strip()
            if not study_title:
                excluded.append(
                    {
                        "record_type": "geo_record",
                        "raw_identifier": gse_accession,
                        "exclusion_reason": "Missing GEO study title",
                        "source_context": f"gds_uid:{uid}",
                    }
                )
                continue

            gpl_raw = str(doc.get("gpl", "")).strip()
            platform = ", ".join(
                p.strip() if p.strip().upper().startswith("GPL") else f"GPL{p.strip()}"
                for p in gpl_raw.split(";")
                if p.strip()
            )

            n_samples_raw = doc.get("n_samples")
            try:
                sample_count = int(n_samples_raw) if n_samples_raw is not None and str(n_samples_raw).strip() != "" else None
            except (ValueError, TypeError):
                sample_count = None

            associated_pmids_list = [
                str(p).strip()
                for p in (doc.get("pubmedids") or [])
                if IdentifierValidator.is_valid_pmid(str(p).strip())
            ]

            valid_studies.append(
                {
                    "gse_accession": gse_accession,
                    "gds_uid": str(uid),
                    "study_title": study_title,
                    "organism": str(doc.get("taxon", "")).strip(),
                    "platform": platform,
                    "sample_count": sample_count,
                    "study_summary": str(doc.get("summary", "")).strip(),
                    "associated_pmids": ", ".join(associated_pmids_list),
                    "geo_url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_accession}",
                }
            )

        return valid_studies, excluded


class EntrezELinkParser:
    """Stateless JSON parser for Entrez ELink linksets."""

    @staticmethod
    def parse(raw_json: str) -> list[dict[str, Any]]:
        if not raw_json or not raw_json.strip():
            return []
        data = json.loads(raw_json)
        links: list[dict[str, Any]] = []
        for linkset in data.get("linksets", []):
            source_ids = [str(x) for x in linkset.get("ids", [])]
            source_id = source_ids[0] if source_ids else ""
            for ldb in linkset.get("linksetdbs", []):
                linkname = str(ldb.get("linkname", ""))
                target_ids = [str(x) for x in ldb.get("links", [])]
                if source_id and target_ids:
                    links.append({"source_id": source_id, "linkname": linkname, "target_ids": target_ids})
        return links


class NCBIService:
    """Concrete NCBI E-utilities client with rate limiting, exponential retries, and SQLite caching."""

    _RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        repository: ResearchRepositoryProtocol | None = None,
        settings: Settings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or SQLiteResearchRepository(db_path=self.settings.DB_PATH)
        self.session = session or requests.Session()
        self._last_request_ts: float = 0.0

        if Entrez is not None:
            Entrez.email = self.settings.NCBI_EMAIL
            Entrez.tool = self.settings.NCBI_TOOL
            if self.settings.has_ncbi_key:
                Entrez.api_key = self.settings.NCBI_API_KEY

    def _respect_rate_limit(self) -> None:
        min_interval = 1.0 / self.settings.ncbi_rate_limit_per_sec
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_ts = time.monotonic()

    @staticmethod
    def _build_cache_key(endpoint: str, params: dict[str, Any]) -> str:
        filtered = {k: str(v) for k, v in sorted(params.items()) if k not in {"api_key", "email", "tool"}}
        digest = hashlib.sha256(json.dumps(filtered, sort_keys=True).encode("utf-8")).hexdigest()
        return f"{endpoint}:{digest}"

    def _request(self, endpoint: str, params: dict[str, Any], use_cache: bool = True) -> str:
        cache_key = self._build_cache_key(endpoint, params)
        if use_cache:
            cached = self.repository.get_cached_response(cache_key)
            if cached is not None:
                return cached

        full_params: dict[str, Any] = {
            **params,
            "tool": self.settings.NCBI_TOOL,
            "email": self.settings.NCBI_EMAIL,
        }
        if self.settings.has_ncbi_key:
            full_params["api_key"] = self.settings.NCBI_API_KEY

        url = f"{self.settings.NCBI_BASE_URL}/{endpoint}"
        last_exc: Exception | None = None

        for attempt in range(1, self.settings.NCBI_MAX_RETRIES + 1):
            self._respect_rate_limit()
            try:
                response = self.session.get(url, params=full_params, timeout=self.settings.NCBI_TIMEOUT_SEC)
                if response.status_code in self._RETRYABLE_STATUS:
                    raise NCBIAPIError(f"Transient HTTP {response.status_code} from {endpoint}")
                response.raise_for_status()
                text = response.text
                if use_cache and text:
                    self.repository.set_cached_response(
                        cache_key=cache_key,
                        endpoint=endpoint,
                        response_payload=text,
                        ttl_hours=self.settings.CACHE_TTL_HOURS,
                    )
                return text
            except Exception as exc:
                last_exc = exc
                logger.warning("NCBI %s attempt %d/%d failed: %s", endpoint, attempt, self.settings.NCBI_MAX_RETRIES, exc)
                if attempt < self.settings.NCBI_MAX_RETRIES:
                    time.sleep(self.settings.NCBI_BACKOFF_FACTOR ** attempt)

        raise NCBIAPIError(f"NCBI request to '{endpoint}' failed after {self.settings.NCBI_MAX_RETRIES} retries: {last_exc}")

    def esearch(
        self,
        db: str,
        term: str,
        retstart: int = 0,
        retmax: int = 10,
        sort: str = "relevance",
        use_cache: bool = True,
    ) -> dict[str, Any]:
        raw = self._request(
            "esearch.fcgi",
            {"db": db, "term": term, "retstart": retstart, "retmax": retmax, "sort": sort, "retmode": "json"},
            use_cache=use_cache,
        )
        result = json.loads(raw).get("esearchresult", {})
        return {
            "count": int(result.get("count", 0)),
            "idlist": [str(x) for x in result.get("idlist", [])],
            "retstart": int(result.get("retstart", retstart)),
            "retmax": int(result.get("retmax", retmax)),
        }

    def efetch_pubmed_xml(self, pmids: list[str], use_cache: bool = True) -> str:
        if not pmids:
            return "<PubmedArticleSet></PubmedArticleSet>"
        return self._request(
            "efetch.fcgi",
            {"db": "pubmed", "id": ",".join(str(p) for p in pmids), "retmode": "xml"},
            use_cache=use_cache,
        )

    def esummary(self, db: str, ids: list[str], use_cache: bool = True) -> dict[str, Any]:
        if not ids:
            return {}
        raw = self._request(
            "esummary.fcgi",
            {"db": db, "id": ",".join(str(i) for i in ids), "retmode": "json"},
            use_cache=use_cache,
        )
        return json.loads(raw).get("result", {})

    def elink(
        self,
        dbfrom: str,
        db: str,
        ids: list[str],
        linkname: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        if not ids:
            return []
        params: dict[str, Any] = {"dbfrom": dbfrom, "db": db, "id": ",".join(str(i) for i in ids), "retmode": "json"}
        if linkname:
            params["linkname"] = linkname
        return EntrezELinkParser.parse(self._request("elink.fcgi", params, use_cache=use_cache))
