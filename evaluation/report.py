"""Generate a formatted Markdown evaluation report from actual benchmark metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def render_evaluation_markdown(results: dict[str, Any]) -> str:
    metrics = results["metrics"]
    dist = results.get("grounding_status_distribution", {})

    lines = [
        "# Helix AI — Benchmark Evaluation Report",
        "",
        f"- **Evaluation Mode:** `{results['mode']}`",
        f"- **Benchmark Corpus Size:** `{results['benchmark_size']}` manually reviewed biomedical research questions",
        "- **Methodology:** All 25 benchmark questions are strictly separated from the 5 development queries. Each of the five quality dimensions is measured and reported independently without combining scores into an artificial aggregate.",
        "",
        "## Independent Evaluation Results",
        "",
        "| Dimension | Correct | Incorrect | Denominator | Score (%) |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]

    labels = {
        "A_retrieval_relevance": "A. Retrieval Relevance",
        "B_publication_geo_linking_accuracy": "B. Publication–GEO Linking Accuracy",
        "C_extraction_accuracy": "C. Extraction Accuracy",
        "D_citation_validity": "D. Citation Validity (PMID & GSE)",
        "E_claim_level_grounding": "E. Claim-Level Grounding",
    }

    for key, label in labels.items():
        m = metrics[key]
        lines.append(
            f"| {label} | {m['correct']} | {m['incorrect']} | {m['denominator']} | **{m['percentage']:.2f}%** |"
        )

    lines.extend(
        [
            "",
            "## Claim-Level Grounding Status Breakdown",
            "",
            "| Verification Status | Field Count |",
            "| :--- | :---: |",
        ]
    )
    for status_name, cnt in sorted(dist.items()):
        lines.append(f"| {status_name} | {cnt} |")

    lines.extend(["", "## Observed Error Categories & Diagnostic Findings", ""])
    for key, label in labels.items():
        errs = metrics[key]["error_categories"]
        lines.append(f"### {label}")
        if not errs:
            lines.append("- No errors observed in this dimension.")
        else:
            for e in errs:
                lines.append(f"- `{e}`")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    res_path = base / "data" / "processed" / "evaluation_results.json"
    out_md = base / "docs" / "evaluation.md"
    data = json.loads(res_path.read_text(encoding="utf-8"))
    out_md.write_text(render_evaluation_markdown(data), encoding="utf-8")
    print(f"Wrote evaluation report to {out_md}")
