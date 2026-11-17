"""OpenAI Structured Extraction adapter implementing StructuredExtractorProtocol."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from config.settings import Settings, get_settings
from domain.enums import ExtractionFieldName
from domain.exceptions import ConfigurationError, OpenAIExtractionError
from domain.models import UNAVAILABLE_LABEL
from utils.grounding import safe_json_loads
from utils.logging_config import get_logger

logger = get_logger("openai_service")


class ExtractedFieldItem(BaseModel):
    value: str = Field(description="Extracted scientific fact, or 'Unavailable in source text' if absent.")
    supporting_passage: str = Field(
        description="Exact verbatim sentence or phrase from the title/abstract supporting the value, or '' if unavailable."
    )
    is_available: bool = Field(description="True only if explicitly stated in the provided text.")


class ScientificExtractionSchema(BaseModel):
    research_objective: ExtractedFieldItem
    disease_or_condition: ExtractedFieldItem
    organism: ExtractedFieldItem
    sample_information: ExtractedFieldItem
    experimental_methodology: ExtractedFieldItem
    genes_or_biomarkers: ExtractedFieldItem
    main_findings: ExtractedFieldItem
    biological_pathways: ExtractedFieldItem
    dataset_accession_references: ExtractedFieldItem
    research_limitations: ExtractedFieldItem


class OpenAIService:
    """OpenAI Chat Completions adapter producing Pydantic-validated 10-field extraction payloads."""

    SYSTEM_PROMPT = """You are Helix AI, a strict biomedical scientific information extraction engine.
Your task is to extract structured scientific facts from a PubMed publication's title and abstract.

CRITICAL RULES:
1. Extract ONLY facts explicitly stated in the provided Title and Abstract.
2. NEVER guess, extrapolate, or invent experimental findings, sample sizes, genes, pathways, or GEO accessions.
3. If a field is not explicitly mentioned in the provided text, set:
   - value: "Unavailable in source text"
   - supporting_passage: ""
   - is_available: false
4. For every available field, copy the exact verbatim supporting sentence or phrase from the Title or Abstract into supporting_passage.
5. Output valid JSON matching the required 10-field schema."""

    def __init__(
        self,
        client: Any | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.api_key = (api_key if api_key is not None else self.settings.OPENAI_API_KEY).strip()
        self.base_url = (base_url if base_url is not None else self.settings.OPENAI_BASE_URL).strip()
        self.model = (model or self.settings.OPENAI_MODEL).strip()
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if OpenAI is None:
            raise ConfigurationError("The 'openai' Python package is not installed. Run: pip install openai")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Set OPENAI_API_KEY in your .env file before running AI extraction."
            )
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url or None,
        )
        return self._client

    def extract_scientific_fields(self, pmid: str, title: str, abstract: str) -> dict[str, Any]:
        client = self._get_client()
        field_names = ExtractionFieldName.ordered_names()
        user_prompt = (
            f"PMID: {pmid}\n"
            f"Title: {title}\n"
            f"Abstract: {abstract}\n\n"
            "Extract the 10 scientific fields as JSON with keys: "
            + ", ".join(field_names)
            + ". Each key must map to an object with keys: value (string), supporting_passage (string), is_available (boolean)."
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.settings.OPENAI_TEMPERATURE,
                max_tokens=self.settings.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            raise OpenAIExtractionError(f"OpenAI API call failed for PMID {pmid}: {exc}") from exc

        raw_content = response.choices[0].message.content or "{}"
        parsed = safe_json_loads(raw_content, default={})
        if not isinstance(parsed, dict):
            raise OpenAIExtractionError(f"OpenAI returned non-dict JSON payload for PMID {pmid}")

        normalized_payload: dict[str, dict[str, Any]] = {}
        for field_name in field_names:
            raw_item = parsed.get(field_name)
            if isinstance(raw_item, dict):
                val = str(raw_item.get("value", "")).strip() or UNAVAILABLE_LABEL
                passage = str(raw_item.get("supporting_passage", "")).strip()
                avail = bool(raw_item.get("is_available", val != UNAVAILABLE_LABEL))
                if val == UNAVAILABLE_LABEL:
                    avail = False
                    passage = ""
                item = ExtractedFieldItem(value=val, supporting_passage=passage, is_available=avail)
            else:
                item = ExtractedFieldItem(value=UNAVAILABLE_LABEL, supporting_passage="", is_available=False)
            normalized_payload[field_name] = item.model_dump()

        return ScientificExtractionSchema(**normalized_payload).model_dump()
