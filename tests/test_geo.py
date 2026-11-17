"""Unit tests for Engine 2A (GEOEngine)."""

import tempfile
import unittest
from pathlib import Path

from database.repository import SQLiteResearchRepository
from engines.geo_engine import GEOEngine
from tests.conftest import FakeNCBIClient


class TestGEOEngine(unittest.TestCase):
    def test_fetch_valid_gse_and_log_invalid_gse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteResearchRepository(db_path=Path(tmpdir) / "test.db")
            geo = GEOEngine(repository=repo, client=FakeNCBIClient())

            study = geo.fetch_by_accession("gse57872")
            self.assertIsNotNone(study)
            self.assertEqual(study.gse_accession, "GSE57872")
            self.assertEqual(study.platform, "GPL11154")
            self.assertEqual(study.sample_count, 430)

            bad = geo.fetch_by_accession("NOT_A_GSE")
            self.assertIsNone(bad)
            self.assertEqual(len(repo.get_excluded_records()), 1)


if __name__ == "__main__":
    unittest.main()
