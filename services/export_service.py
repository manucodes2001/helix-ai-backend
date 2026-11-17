"""CSV and JSON dataset export utilities for Helix AI."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config.settings import Settings, get_settings
from database.repository import SQLiteResearchRepository
from interfaces.repository import ResearchRepositoryProtocol


class ExportService:
    """Exports Datasets A, B, C, D1, D2, and Excluded Records Audit logs to CSV/JSON."""

    def __init__(
        self,
        repository: ResearchRepositoryProtocol | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or SQLiteResearchRepository(db_path=self.settings.DB_PATH)

    def get_publications_df(self) -> pd.DataFrame:
        rows = self.repository.get_all_publications()
        columns = [
            "pmid", "title", "authors", "journal", "publication_year",
            "abstract", "doi", "pubmed_url", "source_query",
        ]
        return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)

    def get_geo_studies_df(self) -> pd.DataFrame:
        rows = self.repository.get_all_geo_studies()
        columns = [
            "gse_accession", "study_title", "organism", "platform",
            "sample_count", "study_summary", "associated_pmids", "geo_url",
        ]
        return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)

    def get_relationships_df(self) -> pd.DataFrame:
        rows = self.repository.get_relationships()
        columns = [
            "pmid", "publication_title", "gse_accession", "study_title",
            "relationship_method", "supporting_evidence", "verification_status",
            "confidence_score", "uncertainty_indicator",
        ]
        return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)

    def get_extractions_df(self) -> pd.DataFrame:
        rows = self.repository.get_extraction_fields()
        columns = [
            "pmid", "publication_title", "field_name", "extracted_value",
            "supporting_passage", "extraction_method", "verification_status",
            "grounding_score", "verification_notes",
        ]
        return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)

    def get_master_dataset_df(self) -> pd.DataFrame:
        rows = self.repository.get_master_research_dataset()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def get_excluded_records_df(self) -> pd.DataFrame:
        rows = self.repository.get_excluded_records()
        columns = ["id", "record_type", "raw_identifier", "exclusion_reason", "source_context", "recorded_at"]
        return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)

    @staticmethod
    def to_csv_bytes(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")

    def export_all_to_directory(self, output_dir: Path | None = None) -> dict[str, Path]:
        target = output_dir or self.settings.PROCESSED_DATA_DIR
        target.mkdir(parents=True, exist_ok=True)

        exports = {
            "publications_csv": (target / "dataset_a_publications.csv", self.get_publications_df()),
            "geo_studies_csv": (target / "dataset_b_geo_studies.csv", self.get_geo_studies_df()),
            "relationships_csv": (target / "dataset_c_pub_geo_relationships.csv", self.get_relationships_df()),
            "extractions_csv": (target / "dataset_d_extracted_provenance.csv", self.get_extractions_df()),
            "master_csv": (target / "dataset_d_master_research.csv", self.get_master_dataset_df()),
            "excluded_csv": (target / "excluded_records_audit.csv", self.get_excluded_records_df()),
        }

        written: dict[str, Path] = {}
        for key, (path, df) in exports.items():
            df.to_csv(path, index=False)
            written[key] = path

        master_json_path = target / "dataset_d_master_research.json"
        master_json_path.write_text(
            json.dumps(self.repository.get_master_research_dataset(), indent=2),
            encoding="utf-8",
        )
        written["master_json"] = master_json_path
        return written
