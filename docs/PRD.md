# Product Requirements Document (PRD): Helix AI

## 1. Problem Statement
Biomedical and bioinformatics researchers spend significant manual effort navigating fragmented databases (PubMed for literature, NCBI GEO for gene expression datasets, spreadsheets for data extraction) to assemble evidence-backed literature syntheses. General-purpose LLM chatbots frequently fabricate citations, invent GEO accessions, or extrapolate findings unsupported by source abstracts.

## 2. Target Users & Personas
- **Wet-Lab Biomedical Researcher:** Needs rapid identification of public gene expression cohorts linked to disease mechanisms without writing custom API scripts.
- **Bioinformatics / Computational Biology Researcher:** Needs verified `PMID <-> GSE` mappings, platform (`GPL`) metadata, and sample counts (`GSM`) for meta-analyses.
- **Graduate Student / Research Assistant:** Needs structured extraction tables with verbatim provenance and audit trails for systematic reviews.

## 3. Core Functional Requirements
1. **Engine 1 — PubMed Literature Retrieval (`engines/pubmed_engine.py`):** Query NCBI E-utilities (`esearch`, `efetch`), parse XML metadata (`PMID`, `Title`, `Authors`, `Journal`, `Year`, `Abstract`, `DOI`, `URL`), deduplicate on `PMID`, paginate results, and cache responses.
2. **Engine 2 — PubMed–GEO Cross-Referencing (`engines/geo_engine.py`, `engines/cross_reference_engine.py`):** Discover `GSE` accessions via NCBI Entrez `ELink` (`pubmed_gds`), GEO `esummary` PMID back-references, and explicit abstract accession parsing (`GSE\d+`). Enforce strict relationship statuses (`Verified relationship`, `Candidate relationship`, `Unverified relationship`, `No relationship identified`). Never link records solely on shared disease/gene keywords.
3. **Engine 3 — AI-Powered Scientific Information Extraction (`engines/extraction_engine.py`):** Extract 10 structured biomedical fields via OpenAI JSON mode with verbatim `supporting_passage` provenance and explicit `Unavailable in source text` handling.
4. **Engine 4 — Evidence Validation & Citation Verification (`engines/verification_engine.py`):** Independently validate `PMID` and `GSE` existence/title correspondence and audit claim-level grounding (`Verified`, `Partially supported`, `Unverified`, `Unsupported`, `Source unavailable`).
5. **Engine 5 — Streamlit Research Dashboard (`app.py`):** Seven-workspace interactive UI with CSV export center (`services/export_service.py`).
