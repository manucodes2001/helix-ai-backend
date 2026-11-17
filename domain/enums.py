"""Domain enumerations eliminating magic strings across Helix AI."""

from __future__ import annotations

from enum import Enum


class RelationshipStatus(str, Enum):
    VERIFIED = "Verified relationship"
    CANDIDATE = "Candidate relationship"
    UNVERIFIED = "Unverified relationship"
    NONE = "No relationship identified"


class ClaimVerificationStatus(str, Enum):
    VERIFIED = "Verified"
    PARTIALLY_SUPPORTED = "Partially supported"
    UNVERIFIED = "Unverified"
    UNSUPPORTED = "Unsupported"
    SOURCE_UNAVAILABLE = "Source unavailable"


class EntityType(str, Enum):
    PMID = "pmid"
    GSE = "gse"
    CITATION = "citation"
    CLAIM = "claim"


class ExtractionFieldName(str, Enum):
    RESEARCH_OBJECTIVE = "research_objective"
    DISEASE_OR_CONDITION = "disease_or_condition"
    ORGANISM = "organism"
    SAMPLE_INFORMATION = "sample_information"
    EXPERIMENTAL_METHODOLOGY = "experimental_methodology"
    GENES_OR_BIOMARKERS = "genes_or_biomarkers"
    MAIN_FINDINGS = "main_findings"
    BIOLOGICAL_PATHWAYS = "biological_pathways"
    DATASET_ACCESSION_REFERENCES = "dataset_accession_references"
    RESEARCH_LIMITATIONS = "research_limitations"

    @classmethod
    def ordered_names(cls) -> list[str]:
        return [item.value for item in cls]
