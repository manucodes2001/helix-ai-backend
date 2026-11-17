"""Engine 3: AI-Powered Structured Scientific Information Extraction."""

from __future__ import annotations

import json

from domain.enums import ClaimVerificationStatus, ExtractionFieldName
from domain.exceptions import RecordNotFoundError
from domain.models import ExtractedField, UNAVAILABLE_LABEL
from interfaces.llm_extractor import StructuredExtractorProtocol
from interfaces.repository import ResearchRepositoryProtocol
from utils.logging_config import get_logger
from utils.validators import IdentifierValidator

logger = get_logger("extraction_engine")


class ExtractionEngine:
    """Extracts 10 structured biomedical fields per publication with verbatim source provenance."""

    def __init__(
        self,
        repository: ResearchRepositoryProtocol,
        extractor: StructuredExtractorProtocol,
    ) -> None:
        self.repository = repository
        self.extractor = extractor

    def extract_for_publication(self, pmid: str) -> list[ExtractedField]:
        clean_pmid = IdentifierValidator.validate_pmid(pmid)
        pub = self.repository.get_publication(clean_pmid)
        if pub is None:
            raise RecordNotFoundError(f"Publication PMID {clean_pmid} not found in repository.")

        title = (pub.get("title") or "").strip()
        abstract = (pub.get("abstract") or "").strip()
        field_names = ExtractionFieldName.ordered_names()

        if not abstract:
            fields_payload = [
                ExtractedField(
                    pmid=clean_pmid,
                    field_name=fname,
                    extracted_value=UNAVAILABLE_LABEL,
                    supporting_passage="",
                    extraction_method="source_check_no_abstract",
                    verification_status=ClaimVerificationStatus.SOURCE_UNAVAILABLE,
                    verification_notes="Publication abstract is unavailable in PubMed record.",
                    grounding_score=0.0,
                ).to_dict()
                for fname in field_names
            ]
            self.repository.save_extraction(
                pmid=clean_pmid,
                extraction_model="none_source_unavailable",
                raw_json=json.dumps({"status": "Source unavailable", "pmid": clean_pmid}),
                fields=fields_payload,
            )
            return self._load_fields(clean_pmid)

        extracted_dict = self.extractor.extract_scientific_fields(
            pmid=clean_pmid,
            title=title,
            abstract=abstract,
        )

        model_tag = f"openai:{self.extractor.model}"
        fields_to_store: list[dict] = []

        for fname in field_names:
            item = extracted_dict.get(fname, {})
            value = str(item.get("value", UNAVAILABLE_LABEL)).strip() or UNAVAILABLE_LABEL
            passage = str(item.get("supporting_passage", "")).strip()
            is_available = bool(item.get("is_available", False)) and value != UNAVAILABLE_LABEL

            if not is_available:
                ef = ExtractedField(
                    pmid=clean_pmid,
                    field_name=fname,
                    extracted_value=UNAVAILABLE_LABEL,
                    supporting_passage="",
                    extraction_method=model_tag,
                    verification_status=ClaimVerificationStatus.SOURCE_UNAVAILABLE,
                    verification_notes="Marked unavailable in source text by extraction engine.",
                    grounding_score=0.0,
                )
            else:
                ef = ExtractedField(
                    pmid=clean_pmid,
                    field_name=fname,
                    extracted_value=value,
                    supporting_passage=passage,
                    extraction_method=model_tag,
                    verification_status=ClaimVerificationStatus.UNVERIFIED,
                    verification_notes="Pending verification engine audit.",
                    grounding_score=0.0,
                )
            fields_to_store.append(ef.to_dict())

        self.repository.save_extraction(
            pmid=clean_pmid,
            extraction_model=model_tag,
            raw_json=json.dumps(extracted_dict, indent=2),
            fields=fields_to_store,
        )
        return self._load_fields(clean_pmid)

    def _load_fields(self, pmid: str) -> list[ExtractedField]:
        rows = self.repository.get_extraction_fields(pmid)
        return [
            ExtractedField(
                pmid=str(r["pmid"]),
                field_name=str(r["field_name"]),
                extracted_value=str(r["extracted_value"]),
                supporting_passage=str(r.get("supporting_passage", "")),
                extraction_method=str(r.get("extraction_method", "")),
                verification_status=ClaimVerificationStatus(r["verification_status"]),
                verification_notes=str(r.get("verification_notes", "")),
                grounding_score=float(r.get("grounding_score", 0.0)),
                publication_title=str(r.get("publication_title") or ""),
                journal=str(r.get("journal") or ""),
                publication_year=r.get("publication_year"),
                pubmed_url=str(r.get("pubmed_url") or ""),
            )
            for r in rows
        ]
