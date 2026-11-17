# Low-Level Design (LLD) & Class Architecture: Helix AI

## 1. Architectural Principles & Design Patterns
Helix AI follows **Clean Architecture** and **SOLID** object-oriented design so each layer can be understood, tested, and extended independently:

1. **Dependency Inversion (`interfaces/`):**
   - `ResearchRepositoryProtocol` (`interfaces/repository.py`)
   - `LiteratureClientProtocol` (`interfaces/literature_client.py`)
   - `StructuredExtractorProtocol` (`interfaces/llm_extractor.py`)
   - All five engines (`engines/*.py`) depend strictly on these `Protocol` contracts rather than concrete SQLite, `requests`, or OpenAI SDK classes.
2. **Domain Model & Enum Layer (`domain/`):**
   - `domain/enums.py`: `RelationshipStatus`, `ClaimVerificationStatus`, `EntityType`, `ExtractionFieldName`.
   - `domain/models.py`: Strongly typed `@dataclass(slots=True)` entities (`Publication`, `GEOStudy`, `PubGeoRelationship`, `ExtractedField`, `IdentifierCheckResult`, `SearchBatchResult`, `PipelineRunSummary`).
   - `domain/exceptions.py`: Typed exception hierarchy (`HelixAIError`, `ConfigurationError`, `IdentifierValidationError`, `RecordNotFoundError`, `NCBIAPIError`, `OpenAIExtractionError`).
3. **Repository & Unit-of-Work Pattern (`database/repository.py`):**
   - `SQLiteResearchRepository` encapsulates all SQLite persistence behind an ACID `transaction()` context manager with foreign keys enabled.
4. **Adapter & Stateless Parser Pattern (`services/`):**
   - `NCBIService` implements `LiteratureClientProtocol` with rate-limiting, retries, and SHA-256 caching, delegating XML/JSON parsing to `PubMedXMLParser`, `GEOESummaryParser`, and `EntrezELinkParser`.
   - `OpenAIService` implements `StructuredExtractorProtocol` with Pydantic schema validation (`ScientificExtractionSchema`).
5. **Facade & Composition Root (`pipeline/orchestrator.py`):**
   - `HelixResearchPipeline` exposes a single high-level `execute_query()` workflow consumed by both `app.py` (Streamlit UI) and `scripts/collect_corpus.py` (CLI).
   - `create_default_pipeline()` wires concrete dependencies cleanly in one place.

## 2. How to Extend Helix AI
- **Add a new literature/dataset source (e.g., Europe PMC or ArrayExpress):** Implement `LiteratureClientProtocol` and pass it into `create_default_pipeline(ncbi_client=...)`.
- **Swap LLM providers (e.g., Anthropic Claude or local vLLM):** Implement `StructuredExtractorProtocol` (`extract_scientific_fields`) and pass it into `create_default_pipeline(llm_extractor=...)`.
- **Migrate storage from SQLite to PostgreSQL:** Implement `ResearchRepositoryProtocol` and pass it into `create_default_pipeline(repository=...)`.
