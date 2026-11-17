"""Unit tests for Engine 4 (VerificationEngine)."""

import tempfile
import unittest
from pathlib import Path

from database.repository import SQLiteResearchRepository
from domain.enums import ClaimVerificationStatus
from engines.extraction_engine import ExtractionEngine
from engines.pubmed_engine import PubMedEngine
from engines.verification_engine import VerificationEngine
from tests.conftest import FakeLLMExtractor, FakeNCBIClient


class TestVerificationEngine(unittest.TestCase):
    def test_grounding_audit_flags_unsupported_claims(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteResearchRepository(db_path=Path(tmpdir) / "test.db")
            client = FakeNCBIClient()
            PubMedEngine(repository=repo, client=client).search_and_fetch("glioblastoma", max_results=1)

            ext = ExtractionEngine(repository=repo, extractor=FakeLLMExtractor(inject_hallucination=True))
            ver = VerificationEngine(repository=repo, client=client)

            ext.extract_for_publication("24925914")
            audited = ver.verify_publication_extractions("24925914", remote_pmid_check=True)
            by_field = {r.field_name: r for r in audited}

            self.assertEqual(by_field["disease_or_condition"].verification_status, ClaimVerificationStatus.VERIFIED)
            self.assertEqual(by_field["sample_information"].verification_status, ClaimVerificationStatus.UNSUPPORTED)
            self.assertEqual(by_field["research_limitations"].verification_status, ClaimVerificationStatus.SOURCE_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
