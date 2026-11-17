"""Unit tests for IdentifierValidator and ClaimGroundingAnalyzer."""

import unittest

from domain.exceptions import IdentifierValidationError
from utils.grounding import ClaimGroundingAnalyzer
from utils.validators import IdentifierValidator


class TestValidatorsAndGrounding(unittest.TestCase):
    def test_identifier_validators(self):
        self.assertEqual(IdentifierValidator.validate_pmid("PMID: 24925914"), "24925914")
        self.assertEqual(IdentifierValidator.validate_gse("gse57872"), "GSE57872")
        self.assertEqual(IdentifierValidator.validate_doi("https://doi.org/10.1126/science.1254257"), "10.1126/science.1254257")
        with self.assertRaises(IdentifierValidationError):
            IdentifierValidator.validate_pmid("ABC123")
        with self.assertRaises(IdentifierValidationError):
            IdentifierValidator.validate_gse("GPL570")

    def test_grounding_analyzer_detects_numeric_hallucination(self):
        src = "We profiled 430 cells from five primary glioblastomas."
        ok = ClaimGroundingAnalyzer.evaluate("430 cells", src, src)
        self.assertTrue(ok.passage_in_source)
        self.assertEqual(ok.missing_numbers, [])

        bad = ClaimGroundingAnalyzer.evaluate("999 cells", src, src)
        self.assertEqual(bad.missing_numbers, ["999"])


if __name__ == "__main__":
    unittest.main()
