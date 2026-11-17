"""Unit tests for Engine 3 (ExtractionEngine)."""

import tempfile
import unittest
from pathlib import Path

from database.repository import SQLiteResearchRepository
from domain.enums import ClaimVerificationStatus, ExtractionFieldName
from domain.models import UNAVAILABLE_LABEL
from engines.extraction_engine import ExtractionEngine
from engines.pubmed_engine import PubMedEngine
from tests.conftest import FakeLLMExtractor, FakeNCBIClient


class TestExtractionEngine(unittest.TestCase):
    def test_structured_extraction_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteResearchRepository(db_path=Path(tmpdir) / "test.db")
            client = FakeNCBIClient()
            PubMedEngine(repository=repo, client=client).search_and_fetch("glioblastoma", max_results=1)

            ext = ExtractionEngine(repository=repo, extractor=FakeLLMExtractor(inject_hallucination=False))
            fields = ext.extract_for_publication("24925914")
            self.assertEqual(len(fields), len(ExtractionFieldName.ordered_names()))

            by_name = {f.field_name: f for f in fields}
            self.assertEqual(by_name["disease_or_condition"].extracted_value, "Primary glioblastoma")
            self.assertIn("GSE57872", by_name["disease_or_condition"].supporting_passage)
            self.assertEqual(by_name["research_limitations"].extracted_value, UNAVAILABLE_LABEL)
            self.assertEqual(by_name["research_limitations"].verification_status, ClaimVerificationStatus.SOURCE_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
