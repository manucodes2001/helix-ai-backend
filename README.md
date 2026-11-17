# Helix AI — Scientific Literature-to-Dataset Intelligence Platform

**Helix AI** is a modular, object-oriented biomedical research intelligence platform that connects peer-reviewed publications from **PubMed** with gene expression datasets from **NCBI GEO**, extracts structured experimental metadata via the **OpenAI API**, and audits every AI-generated claim against its source text with verifiable citations.

## Clean Architecture & Folder Structure

```text
helix-ai/
├── app.py                     # Engine 5: Multi-workspace Streamlit Research Dashboard
├── config/settings.py         # Immutable configuration & .env loader
├── domain/                    # Strongly-typed models, enums, and exception hierarchy
├── interfaces/                # Protocol abstractions (Repository, LiteratureClient, LLMExtractor)
├── database/                  # SQLite schema.sql & ACID SQLiteResearchRepository
├── services/                  # NCBIService (+ XML/JSON parsers), OpenAIService, ExportService
├── engines/                   # PubMedEngine, GEOEngine, CrossReferenceEngine, ExtractionEngine, VerificationEngine
├── pipeline/orchestrator.py   # HelixResearchPipeline facade & dependency injection factory
├── utils/                     # IdentifierValidator, ClaimGroundingAnalyzer, secret-redacting logger
├── scripts/collect_corpus.py  # Reproducible CLI batch data collection script
├── evaluation/                # 25-question benchmark.json, evaluate.py, and report.py
├── tests/                     # Modular unit & end-to-end integration test suite
└── docs/                      # PRD.md, architecture.md, LLD.md, evaluation.md, user_research.md
```

## Quickstart Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add OPENAI_API_KEY and NCBI_EMAIL
```

## Run Tests, Benchmark & Streamlit Dashboard

```bash
# Run unit & integration tests
python3 -m unittest discover -s tests -t . -v

# Run the 25-question benchmark and generate docs/evaluation.md
python3 evaluation/evaluate.py --mode offline
python3 evaluation/report.py

# Launch Streamlit dashboard
streamlit run app.py
```
