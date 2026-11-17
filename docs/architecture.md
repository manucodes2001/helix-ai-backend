# System Architecture & Data Flow: Helix AI

## 1. End-to-End Pipeline Architecture

```text
User Query (Streamlit UI / CLI)
   │
   ▼
[Facade: HelixResearchPipeline]
   ├──► [Engine 1: PubMedEngine] ──► NCBIService + PubMedXMLParser ──► SQLite: publications
   ├──► [Engine 2: CrossReferenceEngine + GEOEngine] ──► ELink + GEOESummaryParser ──► SQLite: geo_studies, pub_geo_relationships
   ├──► [Engine 3: ExtractionEngine] ──► OpenAIService (10-Field Pydantic Schema) ──► SQLite: extractions, extraction_fields
   └──► [Engine 4: VerificationEngine] ──► IdentifierCheck + ClaimGroundingAnalyzer ──► SQLite: verification_logs
   │
   ▼
[Engine 5: Streamlit Dashboard & ExportService] ──► CSV / JSON Research Datasets (A, B, C, D)
```

## 2. Database Schema (`database/schema.sql`)
- `search_queries`: Query execution history, total PubMed hits, duplicates skipped, and excluded counts.
- `publications` (Dataset A): Deduplicated PubMed records keyed by `pmid`.
- `geo_studies` (Dataset B): Validated GEO Series studies keyed by `gse_accession`.
- `pub_geo_relationships` (Dataset C): Evidence-backed `PMID <-> GSE` links with `relationship_method`, `supporting_evidence`, `verification_status`, `confidence_score`, and `uncertainty_indicator`.
- `extractions` & `extraction_fields` (Dataset D): Raw JSON responses plus field-level provenance (`supporting_passage`, `grounding_score`, `verification_status`).
- `verification_logs` & `excluded_records`: Immutable audit trails for identifier checks, claim grounding audits, and malformed/rejected records.
- `api_cache`: SHA-256 keyed HTTP cache with expiration timestamps.
