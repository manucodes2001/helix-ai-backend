"""Unit tests for Engine 2B (CrossReferenceEngine)."""

import tempfile
import unittest
from pathlib import Path

from database.repository import SQLiteResearchRepository
from domain.enums import RelationshipStatus
from engines.cross_reference_engine import CrossReferenceEngine
from engines.pubmed_engine import PubMedEngine
from tests.conftest import FakeNCBIClient


class TestCrossReferenceEngine(unittest.TestCase):
    def test_verified_relationship_and_heuristic_rejection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteResearchRepository(db_path=Path(tmpdir) / "test.db")
            client = FakeNCBIClient()
            PubMedEngine(repository=repo, client=client).search_and_fetch("glioblastoma", max_results=1)
            xref = CrossReferenceEngine(repository=repo, client=client)

            rels = xref.link_publication("24925914")
            self.assertEqual(len(rels), 1)
            self.assertEqual(rels[0].gse_accession, "GSE57872")
            self.assertEqual(rels[0].verification_status, RelationshipStatus.VERIFIED)
            self.assertGreaterEqual(rels[0].confidence_score, 0.95)

            rejected = xref.evaluate_heuristic_cooccurrence("24925914", "GSE99999", ["glioblastoma", "EGFR"])
            self.assertEqual(rejected.verification_status, RelationshipStatus.NONE)
            self.assertEqual(rejected.confidence_score, 0.0)


if __name__ == "__main__":
    unittest.main()
