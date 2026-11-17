"""Abstract LLM structured extraction protocol allowing model provider swapping."""

from __future__ import annotations

from typing import Any, Protocol


class StructuredExtractorProtocol(Protocol):
    model: str

    def extract_scientific_fields(self, pmid: str, title: str, abstract: str) -> dict[str, Any]: ...
