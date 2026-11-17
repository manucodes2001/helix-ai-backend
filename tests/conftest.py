"""Shared offline test doubles implementing Helix AI protocols."""

from __future__ import annotations

from typing import Any

from domain.enums import ExtractionFieldName
from domain.models import UNAVAILABLE_LABEL

SAMPLE_PUBMED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>24925914</PMID>
      <Article>
        <Journal>
          <JournalIssue><PubDate><Year>2014</Year></PubDate></JournalIssue>
          <Title>Science (New York, N.Y.)</Title>
        </Journal>
        <ArticleTitle>Single-cell RNA-seq highlights intratumoral heterogeneity in primary glioblastoma.</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Human cancers are complex ecosystems composed of cells with distinct phenotypes.</AbstractText>
          <AbstractText Label="RESULTS">We used single-cell RNA-seq to profile 430 cells from five primary glioblastomas (GSE57872) and uncovered inherent intratumoral heterogeneity in EGFR and PDGFRA signaling.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Patel</LastName><ForeName>Anoop P</ForeName></Author>
          <Author><LastName>Tirosh</LastName><ForeName>Itay</ForeName></Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1126/science.1254257</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

SAMPLE_GEO_ESUMMARY = {
    "uids": ["200057872"],
    "200057872": {
        "uid": "200057872",
        "accession": "GSE57872",
        "title": "Single-cell RNA-seq highlights intratumoral heterogeneity in primary glioblastoma",
        "taxon": "Homo sapiens",
        "gpl": "11154",
        "n_samples": 430,
        "summary": "Single-cell transcriptomic profiling of 430 cells across five primary human glioblastoma tumors.",
        "pubmedids": ["24925914"],
    },
}


class FakeNCBIClient:
    """In-memory implementation of LiteratureClientProtocol for fast unit/integration tests."""

    def esearch(self, db: str, term: str, retstart: int = 0, retmax: int = 10, sort: str = "relevance", use_cache: bool = True) -> dict[str, Any]:
        if db == "pubmed":
            return {"count": 1, "idlist": ["24925914"], "retstart": retstart, "retmax": retmax}
        if db == "gds" and "GSE57872" in term:
            return {"count": 1, "idlist": ["200057872"], "retstart": retstart, "retmax": retmax}
        return {"count": 0, "idlist": [], "retstart": retstart, "retmax": retmax}

    def efetch_pubmed_xml(self, pmids: list[str], use_cache: bool = True) -> str:
        return SAMPLE_PUBMED_XML

    def esummary(self, db: str, ids: list[str], use_cache: bool = True) -> dict[str, Any]:
        if db == "pubmed":
            return {
                "uids": ["24925914"],
                "24925914": {
                    "uid": "24925914",
                    "title": "Single-cell RNA-seq highlights intratumoral heterogeneity in primary glioblastoma.",
                },
            }
        if db == "gds":
            return SAMPLE_GEO_ESUMMARY
        return {}

    def elink(self, dbfrom: str, db: str, ids: list[str], linkname: str | None = None, use_cache: bool = True) -> list[dict[str, Any]]:
        if "24925914" in [str(i) for i in ids]:
            return [{"source_id": "24925914", "linkname": "pubmed_gds", "target_ids": ["200057872"]}]
        return []


class FakeLLMExtractor:
    """In-memory implementation of StructuredExtractorProtocol."""

    model = "gpt-4o-mini-mock"

    def __init__(self, inject_hallucination: bool = False) -> None:
        self.inject_hallucination = inject_hallucination

    def extract_scientific_fields(self, pmid: str, title: str, abstract: str) -> dict[str, Any]:
        passage = (
            "We used single-cell RNA-seq to profile 430 cells from five primary glioblastomas (GSE57872) "
            "and uncovered inherent intratumoral heterogeneity in EGFR and PDGFRA signaling."
        )
        payload = {
            fname: {"value": UNAVAILABLE_LABEL, "supporting_passage": "", "is_available": False}
            for fname in ExtractionFieldName.ordered_names()
        }
        payload["disease_or_condition"] = {
            "value": "Primary glioblastoma",
            "supporting_passage": passage,
            "is_available": True,
        }
        payload["experimental_methodology"] = {
            "value": "Single-cell RNA-seq",
            "supporting_passage": passage,
            "is_available": True,
        }
        payload["genes_or_biomarkers"] = {
            "value": "EGFR, PDGFRA",
            "supporting_passage": passage,
            "is_available": True,
        }
        payload["dataset_accession_references"] = {
            "value": "GSE57872",
            "supporting_passage": passage,
            "is_available": True,
        }
        if self.inject_hallucination:
            payload["sample_information"] = {
                "value": "9999 patient biopsies across 12 hospitals",
                "supporting_passage": "We analyzed 9999 patient biopsies across 12 hospitals.",
                "is_available": True,
            }
        else:
            payload["sample_information"] = {
                "value": "430 cells from five primary glioblastomas",
                "supporting_passage": passage,
                "is_available": True,
            }
        return payload
