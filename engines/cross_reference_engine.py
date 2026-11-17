"""Engine 2B: Evidence-Graded PubMed-GEO Cross-Referencing Engine."""

from __future__ import annotations

from typing import Any

from domain.enums import RelationshipStatus
from domain.exceptions import RecordNotFoundError
from domain.models import GEOStudy, PubGeoRelationship
from engines.geo_engine import GEOEngine
from interfaces.literature_client import LiteratureClientProtocol
from interfaces.repository import ResearchRepositoryProtocol
from utils.logging_config import get_logger
from utils.validators import IdentifierValidator

logger = get_logger("cross_reference_engine")


class CrossReferenceEngine:
    """Links PubMed publications to GEO datasets using strictly verifiable evidence signals."""

    def __init__(
        self,
        repository: ResearchRepositoryProtocol,
        client: LiteratureClientProtocol,
        geo_engine: GEOEngine | None = None,
    ) -> None:
        self.repository = repository
        self.client = client
        self.geo_engine = geo_engine or GEOEngine(repository=repository, client=client)

    def link_publication(self, pmid: str, use_cache: bool = True) -> list[PubGeoRelationship]:
        clean_pmid = IdentifierValidator.validate_pmid(pmid)
        pub = self.repository.get_publication(clean_pmid)
        if pub is None:
            raise RecordNotFoundError(f"Publication PMID {clean_pmid} not found in repository.")

        combined_text = f"{pub.get('title', '')}. {pub.get('abstract', '')}"
        text_mentions = IdentifierValidator.extract_gse_mentions(combined_text)
        mention_map: dict[str, str] = {m["gse_accession"]: m["context_snippet"] for m in text_mentions}

        elink_gse_map: dict[str, str] = {}
        try:
            linksets = self.client.elink(
                dbfrom="pubmed",
                db="gds",
                ids=[clean_pmid],
                linkname="pubmed_gds",
                use_cache=use_cache,
            )
            gds_uids: list[str] = []
            for ls in linksets:
                if ls["source_id"] == clean_pmid:
                    gds_uids.extend(ls["target_ids"])
            if gds_uids:
                resolved_studies = self.geo_engine.fetch_by_gds_uids(list(dict.fromkeys(gds_uids)), use_cache=use_cache)
                for study in resolved_studies:
                    elink_gse_map[study.gse_accession] = f"Entrez ELink pubmed_gds (GDS UID: {study.gds_uid or 'N/A'})"
        except Exception as exc:
            logger.warning("ELink lookup failed for PMID %s: %s", clean_pmid, exc)

        all_candidate_gses = list(dict.fromkeys([*mention_map.keys(), *elink_gse_map.keys()]))

        if not all_candidate_gses:
            no_rel = PubGeoRelationship(
                pmid=clean_pmid,
                gse_accession="NONE",
                relationship_method="automated_text_and_elink_scan",
                supporting_evidence="No GSE accession mentioned in abstract/title and no Entrez pubmed_gds ELink found.",
                verification_status=RelationshipStatus.NONE,
                confidence_score=0.0,
                uncertainty_indicator="None",
            )
            self.repository.upsert_relationship(no_rel.to_dict())
            return self._load_relationships(clean_pmid)

        for gse in all_candidate_gses:
            if not IdentifierValidator.is_valid_gse(gse):
                continue

            study_row = self.repository.get_geo_study(gse)
            study: GEOStudy | None = GEOStudy.from_dict(study_row) if study_row else None
            if study is None:
                study = self.geo_engine.fetch_by_accession(gse, use_cache=use_cache)

            in_text = gse in mention_map
            in_elink = gse in elink_gse_map
            in_geo_metadata = clean_pmid in (study.pmid_list if study else [])

            if study is not None and (
                (in_elink and in_geo_metadata)
                or (in_text and in_geo_metadata)
                or (in_text and in_elink)
            ):
                methods: list[str] = []
                evidence_parts: list[str] = []
                if in_text:
                    methods.append("abstract_explicit_accession")
                    evidence_parts.append(f"Text mention: '{mention_map[gse]}'")
                if in_elink:
                    methods.append("ncbi_elink_pubmed_gds")
                    evidence_parts.append(elink_gse_map[gse])
                if in_geo_metadata:
                    methods.append("geo_record_pmid_backref")
                    evidence_parts.append(f"GEO {gse} lists PMID {clean_pmid} in associated_pmids")

                rel = PubGeoRelationship(
                    pmid=clean_pmid,
                    gse_accession=gse,
                    relationship_method="+".join(methods),
                    supporting_evidence=" | ".join(evidence_parts),
                    verification_status=RelationshipStatus.VERIFIED,
                    confidence_score=0.98,
                    uncertainty_indicator="Low",
                )
            elif study is not None and (in_elink or in_geo_metadata or in_text):
                if in_elink:
                    method = "ncbi_elink_pubmed_gds_only"
                    evidence = f"{elink_gse_map[gse]} (awaiting bidirectional PMID confirmation in GEO summary)"
                elif in_geo_metadata:
                    method = "geo_record_pmid_backref_only"
                    evidence = f"GEO {gse} lists PMID {clean_pmid} in associated_pmids"
                else:
                    method = "abstract_explicit_accession_only"
                    evidence = f"Text mention: '{mention_map[gse]}' (GEO record resolved, but GEO metadata does not back-reference PMID {clean_pmid})"

                rel = PubGeoRelationship(
                    pmid=clean_pmid,
                    gse_accession=gse,
                    relationship_method=method,
                    supporting_evidence=evidence,
                    verification_status=RelationshipStatus.CANDIDATE,
                    confidence_score=0.75,
                    uncertainty_indicator="Medium",
                )
            else:
                rel = PubGeoRelationship(
                    pmid=clean_pmid,
                    gse_accession=gse,
                    relationship_method="unconfirmed_text_accession_mention",
                    supporting_evidence=f"Text mention: '{mention_map.get(gse, '')}' — GEO record {gse} could not be confirmed in NCBI GEO.",
                    verification_status=RelationshipStatus.UNVERIFIED,
                    confidence_score=0.30,
                    uncertainty_indicator="High",
                )

            self.repository.upsert_relationship(rel.to_dict())

        return self._load_relationships(clean_pmid)

    def evaluate_heuristic_cooccurrence(
        self,
        pmid: str,
        gse_accession: str,
        shared_terms: list[str],
    ) -> PubGeoRelationship:
        """Reject heuristic keyword/disease overlap lacking accession or ELink proof."""
        clean_pmid = IdentifierValidator.validate_pmid(pmid)
        clean_gse = gse_accession.strip().upper()
        terms_str = ", ".join(shared_terms) if shared_terms else "shared biological keywords"
        rel = PubGeoRelationship(
            pmid=clean_pmid,
            gse_accession=clean_gse,
            relationship_method="heuristic_keyword_cooccurrence_rejected",
            supporting_evidence=f"Rejected heuristic overlap ({terms_str}): no ELink or explicit GSE accession evidence.",
            verification_status=RelationshipStatus.NONE,
            confidence_score=0.0,
            uncertainty_indicator="Rejected - Heuristic Only",
        )
        if self.repository.publication_exists(clean_pmid):
            self.repository.upsert_relationship(rel.to_dict())
        return rel

    def _load_relationships(self, pmid: str) -> list[PubGeoRelationship]:
        rows = self.repository.get_relationships(pmid)
        return [
            PubGeoRelationship(
                pmid=str(r["pmid"]),
                gse_accession=str(r["gse_accession"]),
                relationship_method=str(r["relationship_method"]),
                supporting_evidence=str(r.get("supporting_evidence", "")),
                verification_status=RelationshipStatus(r["verification_status"]),
                confidence_score=float(r.get("confidence_score", 0.0)),
                uncertainty_indicator=str(r.get("uncertainty_indicator", "High")),
                publication_title=str(r.get("publication_title") or ""),
                study_title=str(r.get("study_title") or ""),
                organism=str(r.get("organism") or ""),
                platform=str(r.get("platform") or ""),
                sample_count=r.get("sample_count"),
                geo_url=str(r.get("geo_url") or ""),
            )
            for r in rows
        ]
