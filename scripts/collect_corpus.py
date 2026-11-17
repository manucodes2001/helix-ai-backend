"""Reproducible CLI pipeline script for collecting PubMed + GEO records and exporting datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import get_settings
from pipeline.orchestrator import create_default_pipeline
from utils.logging_config import get_logger, setup_logging

DEFAULT_QUERIES = [
    "Gene expression in breast cancer",
    "Alzheimer's disease biomarkers",
    "Inflammatory pathways in rheumatoid arthritis",
    "Oxidative stress in liver disease",
    "Gene expression in Type 2 diabetes",
]


def run_corpus_collection(
    queries: list[str],
    max_results_per_query: int = 5,
    run_extraction: bool = False,
) -> dict[str, int]:
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL, log_file=settings.DATA_DIR / "helix_ai.log")
    logger = get_logger("collect_corpus")

    pipeline = create_default_pipeline(settings=settings)
    totals = {"queries": len(queries), "publications": 0, "geo_links": 0, "verified_links": 0, "extracted": 0}

    for q in queries:
        logger.info("Processing query: %s", q)
        res = pipeline.execute_query(
            query=q,
            max_results=max_results_per_query,
            link_geo=True,
            run_extraction=run_extraction,
            remote_id_verify=True,
        )
        totals["publications"] += res.retrieved_publications
        totals["geo_links"] += res.geo_links_discovered
        totals["verified_links"] += res.verified_geo_links
        totals["extracted"] += res.extracted_publications
        for err in res.errors:
            logger.warning(err)

    written = pipeline.export.export_all_to_directory()
    logger.info("Exported datasets: %s", {k: str(v) for k, v in written.items()})
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Helix AI Reproducible Data Collection Pipeline")
    parser.add_argument("--max-results", type=int, default=5, help="Max PubMed records per query")
    parser.add_argument("--extract", action="store_true", help="Run OpenAI extraction & verification")
    parser.add_argument("--query", action="append", help="Custom query (can be specified multiple times)")
    args = parser.parse_args()

    target_queries = args.query if args.query else DEFAULT_QUERIES
    stats = run_corpus_collection(
        queries=target_queries,
        max_results_per_query=args.max_results,
        run_extraction=args.extract,
    )
    print("Collection summary:", stats)
