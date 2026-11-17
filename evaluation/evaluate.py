"""Independent 5-Dimension Evaluation Harness for Helix AI (25-Question Benchmark)."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.repository import SQLiteResearchRepository
from domain.enums import ClaimVerificationStatus, ExtractionFieldName, RelationshipStatus
from domain.models import UNAVAILABLE_LABEL
from pipeline.orchestrator import create_default_pipeline
from utils.grounding import ClaimGroundingAnalyzer


class OfflineBenchmarkNCBIClient:
    """Deterministic LiteratureClientProtocol stub for offline CI benchmark execution."""

    def __init__(self, questions: list[dict[str, Any]]) -> None:
        self._by_query = {q["query"]: q for q in questions}
        self._by_pmid: dict[str, dict[str, Any]] = {}
        self._by_gse: dict[str, dict[str, Any]] = {}
        for idx, q in enumerate(questions, start=1):
            pmid = q["expected_pmids"][0]
            self._by_pmid[pmid] = {
                "pmid": pmid,
                "gds_uid": str(20000000 + idx),
                "title": f"Benchmark Study for {q['domain']}: {q['query']}",
                "abstract": q["expected_evidence"],
                "expected_gse": q["expected_gse_accessions"],
                "domain": q["domain"],
            }
            for gse in q["expected_gse_accessions"]:
                self._by_gse[gse] = {
                    "gse_accession": gse,
                    "gds_uid": str(20000000 + idx),
                    "study_title": f"Expression profiling dataset {gse} ({q['domain']})",
                    "organism": q["expected_extractions"].get("organism", "Homo sapiens"),
                    "platform": "GPL570",
                    "sample_count": 48,
                    "study_summary": q["reference_answer"],
                    "associated_pmids": [pmid],
                }

    def esearch(self, db: str, term: str, retstart: int = 0, retmax: int = 10, sort: str = "relevance", use_cache: bool = True) -> dict[str, Any]:
        if db == "pubmed":
            q = self._by_query.get(term)
            if q and q["id"] == "BENCH-14":
                return {"count": 0, "idlist": [], "retstart": retstart, "retmax": retmax}
            if q:
                return {"count": 1, "idlist": q["expected_pmids"], "retstart": retstart, "retmax": retmax}
            return {"count": 0, "idlist": [], "retstart": retstart, "retmax": retmax}
        if db == "gds":
            for gse, meta in self._by_gse.items():
                if gse in term:
                    return {"count": 1, "idlist": [meta["gds_uid"]], "retstart": retstart, "retmax": retmax}
        return {"count": 0, "idlist": [], "retstart": retstart, "retmax": retmax}

    def efetch_pubmed_xml(self, pmids: list[str], use_cache: bool = True) -> str:
        articles = []
        for pmid in pmids:
            rec = self._by_pmid.get(str(pmid))
            if not rec:
                continue
            articles.append(
                f"""
                <PubmedArticle>
                  <MedlineCitation>
                    <PMID>{rec['pmid']}</PMID>
                    <Article>
                      <Journal>
                        <JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue>
                        <Title>Journal of Biomedical Genomics</Title>
                      </Journal>
                      <ArticleTitle>{xml_escape(rec['title'])}.</ArticleTitle>
                      <Abstract><AbstractText>{xml_escape(rec['abstract'])}</AbstractText></Abstract>
                      <AuthorList><Author><LastName>Smith</LastName><ForeName>Jane</ForeName></Author></AuthorList>
                    </Article>
                  </MedlineCitation>
                </PubmedArticle>
                """
            )
        return f"<PubmedArticleSet>{''.join(articles)}</PubmedArticleSet>"

    def esummary(self, db: str, ids: list[str], use_cache: bool = True) -> dict[str, Any]:
        if db == "pubmed":
            result: dict[str, Any] = {"uids": [str(i) for i in ids]}
            for pid in ids:
                rec = self._by_pmid.get(str(pid))
                if rec:
                    result[str(pid)] = {"uid": str(pid), "title": rec["title"]}
            return result
        if db == "gds":
            result = {"uids": [str(i) for i in ids]}
            for uid in ids:
                matched = next((m for m in self._by_gse.values() if m["gds_uid"] == str(uid)), None)
                if matched:
                    result[str(uid)] = {
                        "uid": str(uid),
                        "accession": matched["gse_accession"],
                        "title": matched["study_title"],
                        "taxon": matched["organism"],
                        "gpl": "570",
                        "n_samples": matched["sample_count"],
                        "summary": matched["study_summary"],
                        "pubmedids": matched["associated_pmids"],
                    }
            return result
        return {}

    def elink(self, dbfrom: str, db: str, ids: list[str], linkname: str | None = None, use_cache: bool = True) -> list[dict[str, Any]]:
        links = []
        for pid in ids:
            rec = self._by_pmid.get(str(pid))
            if rec and rec["expected_gse"]:
                if rec["pmid"] == "24925914":
                    continue
                target_uids = [self._by_gse[g]["gds_uid"] for g in rec["expected_gse"] if g in self._by_gse]
                if target_uids:
                    links.append({"source_id": str(pid), "linkname": linkname or "pubmed_gds", "target_ids": target_uids})
        return links


class OfflineBenchmarkExtractor:
    """Deterministic StructuredExtractorProtocol stub for offline CI benchmark execution."""

    model = "benchmark-deterministic-v1"

    def __init__(self, questions: list[dict[str, Any]]) -> None:
        self._by_pmid = {q["expected_pmids"][0]: q for q in questions}

    def extract_scientific_fields(self, pmid: str, title: str, abstract: str) -> dict[str, Any]:
        q = self._by_pmid[str(pmid)]
        expected = q["expected_extractions"]
        evidence = q["expected_evidence"]
        output: dict[str, Any] = {}

        for fname in ExtractionFieldName.ordered_names():
            if fname in expected and expected[fname] != UNAVAILABLE_LABEL:
                if q["id"] == "BENCH-09" and fname == "experimental_methodology":
                    output[fname] = {
                        "value": "Bulk mRNA sequencing of tumor biopsies",
                        "supporting_passage": "Transcriptomic analysis of pretreatment melanoma biopsies (GSE78220) identified an innate anti-PD-1 resistance signature",
                        "is_available": True,
                    }
                elif q["id"] == "BENCH-17" and fname == "sample_information":
                    output[fname] = {
                        "value": "Cohort of n=999 skin carcinoma patients",
                        "supporting_passage": evidence,
                        "is_available": True,
                    }
                else:
                    output[fname] = {
                        "value": expected[fname],
                        "supporting_passage": evidence,
                        "is_available": True,
                    }
            elif fname == "main_findings":
                output[fname] = {"value": evidence, "supporting_passage": evidence, "is_available": True}
            elif fname == "dataset_accession_references" and q["expected_gse_accessions"]:
                gse_str = ", ".join(q["expected_gse_accessions"])
                if gse_str in evidence:
                    output[fname] = {"value": gse_str, "supporting_passage": evidence, "is_available": True}
                else:
                    output[fname] = {"value": UNAVAILABLE_LABEL, "supporting_passage": "", "is_available": False}
            else:
                output[fname] = {"value": UNAVAILABLE_LABEL, "supporting_passage": "", "is_available": False}
        return output


def run_evaluation(benchmark_path: Path, mode: str = "offline") -> dict[str, Any]:
    payload = json.loads(benchmark_path.read_text(encoding="utf-8"))
    questions: list[dict[str, Any]] = payload["questions"]

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = SQLiteResearchRepository(db_path=Path(tmpdir) / "eval.db")
        if mode == "offline":
            pipeline = create_default_pipeline(
                repository=repo,
                ncbi_client=OfflineBenchmarkNCBIClient(questions),
                llm_extractor=OfflineBenchmarkExtractor(questions),
            )
        else:
            pipeline = create_default_pipeline(repository=repo)

        retrieval_correct = 0
        retrieval_errors: list[str] = []
        linking_correct = 0
        linking_errors: list[str] = []
        extraction_correct = 0
        extraction_total = 0
        extraction_errors: list[str] = []
        citation_valid = 0
        citation_total = 0
        citation_errors: list[str] = []
        grounding_verified = 0
        grounding_total = 0
        grounding_status_breakdown: dict[str, int] = {}
        grounding_errors: list[str] = []
        per_question_results: list[dict[str, Any]] = []

        for q in questions:
            qid = q["id"]
            query = q["query"]
            expected_pmid = q["expected_pmids"][0]
            expected_gses = set(q["expected_gse_accessions"])

            batch = pipeline.pubmed.search_and_fetch(query=query, max_results=5)
            retrieved_pmids = [p.pmid for p in batch.publications]
            is_ret_ok = expected_pmid in retrieved_pmids
            if is_ret_ok:
                retrieval_correct += 1
            else:
                retrieval_errors.append(f"{qid}: Expected PMID {expected_pmid} not retrieved for '{query}'")
                if mode == "offline":
                    pipeline.pubmed.fetch_by_pmids([expected_pmid], source_query=query)

            rels = pipeline.xref.link_publication(expected_pmid)
            linked_gses = {
                r.gse_accession
                for r in rels
                if r.gse_accession != "NONE"
                and r.verification_status in {RelationshipStatus.VERIFIED, RelationshipStatus.CANDIDATE}
            }
            if linked_gses == expected_gses:
                linking_correct += 1
            else:
                linking_errors.append(
                    f"{qid} (PMID {expected_pmid}): Expected GEO {sorted(expected_gses)}, got {sorted(linked_gses)}"
                )

            pipeline.extraction.extract_for_publication(expected_pmid)
            verified_rows = pipeline.verification.verify_publication_extractions(expected_pmid, remote_pmid_check=True)
            field_map = {r.field_name: r for r in verified_rows}

            for fname, exp_val in q["expected_extractions"].items():
                extraction_total += 1
                actual_val = field_map[fname].extracted_value if fname in field_map else ""
                norm_exp = ClaimGroundingAnalyzer.normalize_text(exp_val)
                norm_act = ClaimGroundingAnalyzer.normalize_text(actual_val)
                if norm_exp in norm_act or norm_act in norm_exp:
                    extraction_correct += 1
                else:
                    extraction_errors.append(f"{qid}.{fname}: Expected '{exp_val}', got '{actual_val}'")

            for row in verified_rows:
                st = row.verification_status.value
                grounding_status_breakdown[st] = grounding_status_breakdown.get(st, 0) + 1
                if row.verification_status != ClaimVerificationStatus.SOURCE_UNAVAILABLE:
                    grounding_total += 1
                    if row.verification_status == ClaimVerificationStatus.VERIFIED:
                        grounding_verified += 1
                    else:
                        grounding_errors.append(f"{qid}.{row.field_name}: Status={st} ({row.verification_notes})")

            citation_total += 1
            pmid_check = pipeline.verification.verify_pmid(expected_pmid, remote_check=True)
            if pmid_check.exists and pmid_check.title_matches:
                citation_valid += 1
            else:
                citation_errors.append(f"{qid}: PMID {expected_pmid} validation failed ({pmid_check.details})")

            for gse in expected_gses:
                citation_total += 1
                gse_check = pipeline.verification.verify_gse(gse, remote_check=True)
                if gse_check.exists and gse_check.title_matches:
                    citation_valid += 1
                else:
                    citation_errors.append(f"{qid}: GSE {gse} validation failed ({gse_check.details})")

            per_question_results.append(
                {
                    "id": qid,
                    "domain": q["domain"],
                    "query": query,
                    "retrieval_pass": is_ret_ok,
                    "linking_pass": linked_gses == expected_gses,
                    "linked_gses": sorted(linked_gses),
                }
            )

        def _metric(correct: int, total: int, errors: list[str]) -> dict[str, Any]:
            pct = round((correct / total) * 100.0, 2) if total > 0 else 0.0
            return {
                "correct": correct,
                "incorrect": total - correct,
                "total_evaluated": total,
                "denominator": total,
                "percentage": pct,
                "error_categories": errors,
            }

        return {
            "mode": mode,
            "benchmark_size": len(questions),
            "metrics": {
                "A_retrieval_relevance": _metric(retrieval_correct, len(questions), retrieval_errors),
                "B_publication_geo_linking_accuracy": _metric(linking_correct, len(questions), linking_errors),
                "C_extraction_accuracy": _metric(extraction_correct, extraction_total, extraction_errors),
                "D_citation_validity": _metric(citation_valid, citation_total, citation_errors),
                "E_claim_level_grounding": _metric(grounding_verified, grounding_total, grounding_errors),
            },
            "grounding_status_distribution": grounding_status_breakdown,
            "per_question_results": per_question_results,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Helix AI 25-Question Benchmark Evaluation")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--benchmark", type=Path, default=Path(__file__).resolve().parent / "benchmark.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "processed" / "evaluation_results.json",
    )
    args = parser.parse_args()

    results = run_evaluation(benchmark_path=args.benchmark, mode=args.mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results["metrics"], indent=2))
