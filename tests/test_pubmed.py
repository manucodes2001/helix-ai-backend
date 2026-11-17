"""Unit tests for Engine 1 (PubMedEngine)."""

import tempfile
import unittest
from pathlib import Path

from database.repository import SQLiteResearchRepository
from engines.pubmed_engine import PubMedEngine
from tests.conftest import FakeNCBIClient


class TestPubMedEngine(unittest.TestCase):
    def test_search_fetch_and_deduplication(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteResearchRepository(db_path=Path(tmpdir) / "test.db")
            engine = PubMedEngine(repository=repo, client=FakeNCBIClient())

            b1 = engine.search_and_fetch("glioblastoma single-cell RNA-seq", max_results=5)
            self.assertEqual(b1.newly_inserted, 1)
            self.assertEqual(b1.duplicates_skipped, 0)
            self.assertEqual(b1.publications[0].pmid, "24925914")
            self.assertEqual(b1.publications[0].doi, "10.1126/science.1254257")

            b2 = engine.search_and_fetch("glioblastoma single-cell RNA-seq", max_results=5)
            self.assertEqual(b2.newly_inserted, 0)
            self.assertEqual(b2.duplicates_skipped, 1)

    def test_empty_query_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteResearchRepository(db_path=Path(tmpdir) / "test.db")
            engine = PubMedEngine(repository=repo, client=FakeNCBIClient())
            with self.assertRaises(ValueError):
                engine.search_and_fetch("   ")


if __name__ == "__main__":
    unittest.main()
