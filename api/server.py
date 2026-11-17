"""FastAPI REST bridge connecting the React frontend to the Helix AI research pipeline."""

from __future__ import annotations

import sys
from dataclasses import asdict
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure project root is on sys.path so pipeline imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings  # noqa: E402
from pipeline.orchestrator import create_default_pipeline  # noqa: E402

app = FastAPI(
    title="Helix AI API",
    description="REST bridge for the Helix AI Scientific Research Intelligence Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Singleton pipeline
# ---------------------------------------------------------------------------
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = create_default_pipeline()
    return _pipeline


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class PipelineRunRequest(BaseModel):
    query: str
    max_results: int = Field(default=10, ge=1, le=100)
    link_geo: bool = True
    run_extraction: bool = False
    remote_id_verify: bool = False


class GeoLookupRequest(BaseModel):
    gse_accession: str


# ---------------------------------------------------------------------------
# Router for API endpoints (mounted at both /api and root / for Vercel compatibility)
# ---------------------------------------------------------------------------

router = APIRouter()


@router.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "has_openai_key": settings.has_openai_key,
        "has_ncbi_key": settings.has_ncbi_key,
        "openai_model": settings.OPENAI_MODEL,
        "db_path": str(settings.DB_PATH),
    }


@router.get("/dashboard")
def dashboard():
    p = get_pipeline()
    stats = p.repository.get_dashboard_stats()
    recent = p.repository.get_recent_searches(limit=10)
    return {"stats": stats, "recent_searches": recent}


@router.post("/pipeline/run")
def run_pipeline(req: PipelineRunRequest):
    p = get_pipeline()
    try:
        summary = p.execute_query(
            query=req.query,
            max_results=req.max_results,
            link_geo=req.link_geo,
            run_extraction=req.run_extraction,
            remote_id_verify=req.remote_id_verify,
        )
        return asdict(summary)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/publications")
def list_publications(q: str | None = Query(default=None)):
    p = get_pipeline()
    return p.repository.get_all_publications(query_filter=q)


@router.post("/publications/{pmid}/cross-reference")
def cross_reference_publication(pmid: str):
    p = get_pipeline()
    try:
        rels = p.xref.link_publication(pmid)
        return [r.to_dict() for r in rels]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/publications/{pmid}/extract")
def extract_publication(pmid: str):
    p = get_pipeline()
    try:
        p.extraction.extract_for_publication(pmid)
        verified = p.verification.verify_publication_extractions(pmid)
        return [f.to_dict() for f in verified]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/geo")
def list_geo_studies():
    p = get_pipeline()
    return p.repository.get_all_geo_studies()


@router.post("/geo/lookup")
def geo_lookup(req: GeoLookupRequest):
    p = get_pipeline()
    try:
        study = p.geo.fetch_by_accession(req.gse_accession)
        if study is None:
            raise HTTPException(
                status_code=404,
                detail=f"GEO study {req.gse_accession} not found",
            )
        return study.to_dict()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/relationships")
def list_relationships():
    p = get_pipeline()
    return p.repository.get_relationships()


@router.get("/extractions")
def list_extractions(pmid: str | None = Query(default=None)):
    p = get_pipeline()
    return p.repository.get_extraction_fields(pmid=pmid)


@router.get("/verification/logs")
def verification_logs():
    p = get_pipeline()
    return p.repository.get_verification_logs(limit=200)


EXPORT_DATASETS = {
    "publications": "get_publications_df",
    "geo_studies": "get_geo_studies_df",
    "relationships": "get_relationships_df",
    "extractions": "get_extractions_df",
    "master": "get_master_dataset_df",
    "excluded": "get_excluded_records_df",
}


@router.get("/export/{dataset_key}")
def export_csv(dataset_key: str):
    if dataset_key not in EXPORT_DATASETS:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_key}")
    p = get_pipeline()
    method = getattr(p.export, EXPORT_DATASETS[dataset_key])
    df = method()
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dataset_key}.csv"},
    )


# Mount router at /api (standard) AND root (for Vercel path-stripping compatibility)
app.include_router(router, prefix="/api")
app.include_router(router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Helix AI Scientific Intelligence API",
        "docs": "/docs",
    }


@app.get("/api")
def api_root():
    return {
        "status": "ok",
        "service": "Helix AI Scientific Intelligence API",
        "docs": "/docs",
    }
