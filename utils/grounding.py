"""Claim-level text normalization and passage grounding analyzer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


@dataclass(frozen=True, slots=True)
class GroundingMetrics:
    """Quantitative evidence alignment scores between an extracted claim and source text."""

    passage_in_source: bool
    passage_similarity: float
    claim_in_passage: bool
    token_overlap: float
    source_token_overlap: float
    missing_numbers: list[str]


class ClaimGroundingAnalyzer:
    """Evaluates whether an extracted claim is faithfully backed by a verbatim passage in source text."""

    STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
        "at", "by", "for", "with", "about", "against", "between", "into",
        "through", "during", "before", "after", "above", "below", "to", "from",
        "up", "down", "in", "out", "on", "off", "over", "under", "again",
        "further", "once", "here", "there", "where", "why", "how", "all", "any",
        "both", "each", "few", "more", "most", "other", "some", "such", "no",
        "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s",
        "t", "can", "will", "just", "don", "should", "now", "of", "was", "were",
        "is", "are", "been", "being", "have", "has", "had", "having", "do", "does",
        "did", "doing", "this", "that", "these", "those", "it", "its", "as", "we",
        "our", "their", "they", "which", "who", "whom", "using", "used", "study",
        "results", "showed", "found", "demonstrated", "observed", "significantly",
    }

    NUMBER_REGEX = re.compile(r"\b\d+(?:\.\d+)?\b")

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s.-]", " ", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def tokenize_content_words(cls, text: str) -> set[str]:
        norm = cls.normalize_text(text)
        tokens = re.findall(r"[a-z0-9][a-z0-9._-]*", norm)
        return {tok for tok in tokens if len(tok) > 1 and tok not in cls.STOPWORDS}

    @classmethod
    def extract_numbers(cls, text: str) -> set[str]:
        if not text:
            return set()
        return set(cls.NUMBER_REGEX.findall(text))

    @classmethod
    def evaluate(
        cls,
        claim_value: str,
        supporting_passage: str,
        source_text: str,
    ) -> GroundingMetrics:
        norm_source = cls.normalize_text(source_text)
        norm_passage = cls.normalize_text(supporting_passage)
        norm_claim = cls.normalize_text(claim_value)

        if not norm_source or not norm_passage:
            return GroundingMetrics(
                passage_in_source=False,
                passage_similarity=0.0,
                claim_in_passage=False,
                token_overlap=0.0,
                source_token_overlap=0.0,
                missing_numbers=sorted(cls.extract_numbers(claim_value) - cls.extract_numbers(source_text)),
            )

        passage_in_source = norm_passage in norm_source

        if passage_in_source:
            passage_similarity = 1.0
        else:
            p_len = len(norm_passage)
            s_len = len(norm_source)
            if s_len <= p_len:
                passage_similarity = SequenceMatcher(None, norm_passage, norm_source).ratio()
            else:
                best_ratio = 0.0
                step = max(1, p_len // 4)
                for idx in range(0, s_len - p_len + step, step):
                    window = norm_source[idx : idx + p_len + 20]
                    ratio = SequenceMatcher(None, norm_passage, window).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                    if best_ratio >= 0.92:
                        break
                passage_similarity = round(best_ratio, 4)

        claim_in_passage = bool(norm_claim) and (norm_claim in norm_passage)

        claim_tokens = cls.tokenize_content_words(claim_value)
        passage_tokens = cls.tokenize_content_words(supporting_passage)
        source_tokens = cls.tokenize_content_words(source_text)

        if claim_tokens:
            token_overlap = round(len(claim_tokens & passage_tokens) / len(claim_tokens), 4)
            source_token_overlap = round(len(claim_tokens & source_tokens) / len(claim_tokens), 4)
        else:
            token_overlap = 1.0 if claim_in_passage else 0.0
            source_token_overlap = 1.0 if (norm_claim and norm_claim in norm_source) else 0.0

        missing_numbers = sorted(cls.extract_numbers(claim_value) - cls.extract_numbers(source_text))

        return GroundingMetrics(
            passage_in_source=passage_in_source,
            passage_similarity=round(float(passage_similarity), 4),
            claim_in_passage=claim_in_passage,
            token_overlap=token_overlap,
            source_token_overlap=source_token_overlap,
            missing_numbers=missing_numbers,
        )


def safe_json_loads(raw: str, default: Any = None) -> Any:
    if not raw:
        return default
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return default
