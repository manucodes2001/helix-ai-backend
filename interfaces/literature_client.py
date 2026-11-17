"""Abstract literature & dataset API protocol for NCBI E-utilities or offline doubles."""

from __future__ import annotations

from typing import Any, Protocol


class LiteratureClientProtocol(Protocol):
    def esearch(
        self,
        db: str,
        term: str,
        retstart: int = 0,
        retmax: int = 10,
        sort: str = "relevance",
        use_cache: bool = True,
    ) -> dict[str, Any]: ...

    def efetch_pubmed_xml(self, pmids: list[str], use_cache: bool = True) -> str: ...
    def esummary(self, db: str, ids: list[str], use_cache: bool = True) -> dict[str, Any]: ...

    def elink(
        self,
        dbfrom: str,
        db: str,
        ids: list[str],
        linkname: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]: ...
