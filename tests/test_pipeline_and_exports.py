"""End-to-end integration tests for HelixResearchPipeline, ExportService, and Streamlit UI syntax."""

import ast
import tempfile
import unittest
from pathlib import Path

from database.repository import SQLiteResearchRepository
from pipeline.orchestrator import create_default_pipeline
from tests.conftest import FakeLLMExtractor, FakeNCBIClient


class TestPipelineAndExports(unittest.TestCase):
    def test_end_to_end_pipeline_execution_and_csv_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            repo = SQLiteResearchRepository(db_path=tmp_path / "integration.db")
            pipeline = create_default_pipeline(
                repository=repo,
                ncbi_client=FakeNCBIClient(),
                llm_extractor=FakeLLMExtractor(inject_hallucination=False),
            )

            summary = pipeline.execute_query(
                query="Single-cell RNA-seq in glioblastoma",
                max_results=5,
                link_geo=True,
                run_extraction=True,
                remote_id_verify=True,
            )

            self.assertEqual(summary.retrieved_publications, 1)
            self.assertEqual(summary.verified_geo_links, 1)
            self.assertEqual(summary.extracted_publications, 1)
            self.assertEqual(summary.errors, [])

            written = pipeline.export.export_all_to_directory(tmp_path / "exports")
            self.assertTrue(written["publications_csv"].exists())
            self.assertTrue(written["geo_studies_csv"].exists())
            self.assertTrue(written["relationships_csv"].exists())
            self.assertTrue(written["extractions_csv"].exists())
            self.assertTrue(written["master_csv"].exists())
            self.assertTrue(written["master_json"].exists())

    def test_streamlit_app_parses_cleanly(self):
        app_path = Path(__file__).resolve().parent.parent / "app.py"
        if app_path.exists():
            ast.parse(app_path.read_text(encoding="utf-8"))
        else:
            server_path = Path(__file__).resolve().parent.parent / "api" / "server.py"
            ast.parse(server_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
