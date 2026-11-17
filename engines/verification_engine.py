"""Engine 4: Evidence Validation, Identifier Resolution, and Claim-Level Grounding."""

from __future__ import annotations

from domain.enums import ClaimVerificationStatus, EntityType
from domain.exceptions import RecordNotFoundError
from domain.models import ExtractedField, IdentifierCheckResult, UNAVAILABLE_LABEL
from interfaces.literature_client import LiteratureClientProtocol
from interfaces.repository import ResearchRepositoryProtocol
from services.ncbi_service import GEOESummaryParser
from utils.grounding import ClaimGroundingAnalyzer
from utils.logging_config import get_logger
from utils.validators import IdentifierValidator

logger = get_logger("verification_engine")


class VerificationEngine:
    """Audits PMID validity, GEO accession validity, citation correspondence, and claim grounding."""

    def __init__(
        self,
        repository: ResearchRepositoryProtocol,
        client: LiteratureClientProtocol,
    ) -> None:
        self.repository = repository
        self.client = client

    def verify_pmid(self, pmid: str, remote_check: bool = True) -> IdentifierCheckResult:
        if not IdentifierValidator.is_valid_pmid(pmid):
            res = IdentifierCheckResult(
                identifier=str(pmid),
                exists=False,
                title_matches=False,
                status=ClaimVerificationStatus.UNSUPPORTED,
                details="Invalid PMID format",
            )
            self.repository.log_verification(EntityType.PMID.value, str(pmid), res.status.value, res.details, pmid=str(pmid))
            return res

        clean_pmid = IdentifierValidator.validate_pmid(pmid)
        local_pub = self.repository.get_publication(clean_pmid)

        if not remote_check:
            exists = local_pub is not None
            status = ClaimVerificationStatus.VERIFIED if exists else ClaimVerificationStatus.UNVERIFIED
            details = "Verified against local PubMed repository." if exists else "Not found locally; remote check disabled."
            self.repository.log_verification(EntityType.PMID.value, clean_pmid, status.value, details, pmid=clean_pmid)
            return IdentifierCheckResult(clean_pmid, exists, exists, status, details)

        try:
            summary = self.client.esummary(db="pubmed", ids=[clean_pmid])
            doc = summary.get(clean_pmid)
            if not isinstance(doc, dict) or doc.get("error"):
                res = IdentifierCheckResult(
                    identifier=clean_pmid,
                    exists=False,
                    title_matches=False,
                    status=ClaimVerificationStatus.UNSUPPORTED,
                    details=f"PMID {clean_pmid} does not exist in NCBI PubMed.",
                )
                self.repository.log_verification(EntityType.PMID.value, clean_pmid, res.status.value, res.details, pmid=clean_pmid)
                return res

            remote_title = ClaimGroundingAnalyzer.normalize_text(str(doc.get("title", "")))
            if local_pub:
                local_title = ClaimGroundingAnalyzer.normalize_text(local_pub.get("title", ""))
                title_matches = bool(local_title) and (
                    local_title in remote_title or remote_title in local_title or local_title[:40] == remote_title[:40]
                )
            else:
                title_matches = True

            status = ClaimVerificationStatus.VERIFIED if title_matches else ClaimVerificationStatus.PARTIALLY_SUPPORTED
            details = (
                f"Confirmed PMID {clean_pmid} in PubMed with matching title."
                if title_matches
                else f"PMID {clean_pmid} exists in PubMed, but stored title differs from NCBI record."
            )
            self.repository.log_verification(EntityType.PMID.value, clean_pmid, status.value, details, pmid=clean_pmid)
            return IdentifierCheckResult(clean_pmid, True, title_matches, status, details)
        except Exception as exc:
            details = f"Remote PubMed check unavailable ({exc}); local record {'present' if local_pub else 'absent'}."
            status = ClaimVerificationStatus.UNVERIFIED
            self.repository.log_verification(EntityType.PMID.value, clean_pmid, status.value, details, pmid=clean_pmid)
            return IdentifierCheckResult(clean_pmid, local_pub is not None, False, status, details)

    def verify_gse(self, gse_accession: str, remote_check: bool = True) -> IdentifierCheckResult:
        if not IdentifierValidator.is_valid_gse(gse_accession):
            res = IdentifierCheckResult(
                identifier=str(gse_accession),
                exists=False,
                title_matches=False,
                status=ClaimVerificationStatus.UNSUPPORTED,
                details="Invalid GSE accession format",
            )
            self.repository.log_verification(EntityType.GSE.value, str(gse_accession), res.status.value, res.details)
            return res

        clean_gse = IdentifierValidator.validate_gse(gse_accession)
        local_geo = self.repository.get_geo_study(clean_gse)

        if not remote_check:
            exists = local_geo is not None
            status = ClaimVerificationStatus.VERIFIED if exists else ClaimVerificationStatus.UNVERIFIED
            details = "Verified against local GEO repository." if exists else "Not found locally; remote check disabled."
            self.repository.log_verification(EntityType.GSE.value, clean_gse, status.value, details)
            return IdentifierCheckResult(clean_gse, exists, exists, status, details)

        try:
            search_res = self.client.esearch(db="gds", term=f"{clean_gse}[ACCN] AND gse[ETYP]", retmax=3)
            uids = search_res.get("idlist", [])
            if not uids:
                res = IdentifierCheckResult(
                    identifier=clean_gse,
                    exists=False,
                    title_matches=False,
                    status=ClaimVerificationStatus.UNSUPPORTED,
                    details=f"{clean_gse} does not exist in NCBI GEO.",
                )
                self.repository.log_verification(EntityType.GSE.value, clean_gse, res.status.value, res.details)
                return res

            summary = self.client.esummary(db="gds", ids=uids)
            studies, _ = GEOESummaryParser.parse(summary)
            matched = next((s for s in studies if s["gse_accession"] == clean_gse), None)
            if matched is None:
                res = IdentifierCheckResult(
                    identifier=clean_gse,
                    exists=False,
                    title_matches=False,
                    status=ClaimVerificationStatus.UNSUPPORTED,
                    details=f"GDS UIDs resolved, but {clean_gse} Series record was not confirmed.",
                )
                self.repository.log_verification(EntityType.GSE.value, clean_gse, res.status.value, res.details)
                return res

            if local_geo:
                local_title = ClaimGroundingAnalyzer.normalize_text(local_geo.get("study_title", ""))
                remote_title = ClaimGroundingAnalyzer.normalize_text(matched.get("study_title", ""))
                title_matches = bool(local_title) and (local_title == remote_title or local_title[:40] == remote_title[:40])
            else:
                title_matches = True

            status = ClaimVerificationStatus.VERIFIED if title_matches else ClaimVerificationStatus.PARTIALLY_SUPPORTED
            details = (
                f"Confirmed {clean_gse} in NCBI GEO with matching study title."
                if title_matches
                else f"{clean_gse} exists in GEO, but stored study title differs."
            )
            self.repository.log_verification(EntityType.GSE.value, clean_gse, status.value, details)
            return IdentifierCheckResult(clean_gse, True, title_matches, status, details)
        except Exception as exc:
            details = f"Remote GEO check unavailable ({exc})."
            self.repository.log_verification(EntityType.GSE.value, clean_gse, ClaimVerificationStatus.UNVERIFIED.value, details)
            return IdentifierCheckResult(clean_gse, local_geo is not None, False, ClaimVerificationStatus.UNVERIFIED, details)

    def verify_publication_extractions(
        self,
        pmid: str,
        remote_pmid_check: bool = False,
    ) -> list[ExtractedField]:
        clean_pmid = IdentifierValidator.validate_pmid(pmid)
        pub = self.repository.get_publication(clean_pmid)
        if pub is None:
            raise RecordNotFoundError(f"Publication PMID {clean_pmid} not found in repository.")

        pmid_audit = self.verify_pmid(clean_pmid, remote_check=remote_pmid_check)
        source_text = f"{pub.get('title', '')}. {pub.get('abstract', '')}".strip()
        has_abstract = bool((pub.get("abstract") or "").strip())

        fields = self.repository.get_extraction_fields(clean_pmid)
        for field in fields:
            fname = field["field_name"]
            val = (field.get("extracted_value") or "").strip()
            passage = (field.get("supporting_passage") or "").strip()

            if not has_abstract or not val or val == UNAVAILABLE_LABEL:
                status = ClaimVerificationStatus.SOURCE_UNAVAILABLE
                notes = "Field absent in source abstract or source abstract unavailable."
                score = 0.0
            elif not pmid_audit.exists:
                status = ClaimVerificationStatus.UNVERIFIED
                notes = f"Source PMID {clean_pmid} could not be verified in PubMed."
                score = 0.0
            else:
                metrics = ClaimGroundingAnalyzer.evaluate(
                    claim_value=val,
                    supporting_passage=passage,
                    source_text=source_text,
                )
                passage_sim = metrics.passage_similarity
                token_overlap = metrics.token_overlap
                source_overlap = metrics.source_token_overlap

                if not passage:
                    status = ClaimVerificationStatus.UNSUPPORTED
                    notes = "No supporting passage provided for extracted claim."
                    score = 0.0
                elif metrics.missing_numbers:
                    status = ClaimVerificationStatus.UNSUPPORTED
                    notes = f"Numeric values {metrics.missing_numbers} in extracted claim do not appear in source text."
                    score = round(passage_sim * 0.4, 4)
                elif passage_sim < 0.65:
                    status = ClaimVerificationStatus.UNSUPPORTED
                    notes = f"Quoted supporting passage does not match source abstract (similarity={passage_sim:.2f})."
                    score = round(passage_sim, 4)
                elif (metrics.passage_in_source or passage_sim >= 0.85) and (
                    metrics.claim_in_passage or token_overlap >= 0.65
                ):
                    status = ClaimVerificationStatus.VERIFIED
                    notes = f"Verbatim/near-verbatim passage confirmed (sim={passage_sim:.2f}, token_overlap={token_overlap:.2f})."
                    score = round((passage_sim + max(token_overlap, 1.0 if metrics.claim_in_passage else 0.0)) / 2.0, 4)
                elif passage_sim >= 0.65 and max(token_overlap, source_overlap) >= 0.35:
                    status = ClaimVerificationStatus.PARTIALLY_SUPPORTED
                    notes = f"Passage located in source (sim={passage_sim:.2f}), but claim involves paraphrasing/synthesis (overlap={token_overlap:.2f})."
                    score = round((passage_sim + token_overlap) / 2.0, 4)
                else:
                    status = ClaimVerificationStatus.UNSUPPORTED
                    notes = f"Extracted value is not supported by the cited passage (token_overlap={token_overlap:.2f})."
                    score = round(token_overlap, 4)

            self.repository.update_field_verification(
                pmid=clean_pmid,
                field_name=fname,
                verification_status=status.value,
                verification_notes=notes,
                grounding_score=score,
            )
            self.repository.log_verification(
                entity_type=EntityType.CLAIM.value,
                entity_id=f"{clean_pmid}:{fname}",
                status=status.value,
                details=notes,
                pmid=clean_pmid,
                field_name=fname,
            )

        rows = self.repository.get_extraction_fields(clean_pmid)
        return [
            ExtractedField(
                pmid=str(r["pmid"]),
                field_name=str(r["field_name"]),
                extracted_value=str(r["extracted_value"]),
                supporting_passage=str(r.get("supporting_passage", "")),
                extraction_method=str(r.get("extraction_method", "")),
                verification_status=ClaimVerificationStatus(r["verification_status"]),
                verification_notes=str(r.get("verification_notes", "")),
                grounding_score=float(r.get("grounding_score", 0.0)),
                publication_title=str(r.get("publication_title") or ""),
                journal=str(r.get("journal") or ""),
                publication_year=r.get("publication_year"),
                pubmed_url=str(r.get("pubmed_url") or ""),
            )
            for r in rows
        ]
