-- Helix AI Relational Schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    db_source TEXT NOT NULL DEFAULT 'pubmed',
    retmax INTEGER NOT NULL DEFAULT 10,
    total_found INTEGER NOT NULL DEFAULT 0,
    retrieved_count INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    excluded_count INTEGER NOT NULL DEFAULT 0,
    executed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS publications (
    pmid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    journal TEXT NOT NULL DEFAULT '',
    publication_year INTEGER,
    abstract TEXT NOT NULL DEFAULT '',
    doi TEXT,
    pubmed_url TEXT NOT NULL,
    source_query TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS geo_studies (
    gse_accession TEXT PRIMARY KEY,
    gds_uid TEXT,
    study_title TEXT NOT NULL,
    organism TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '',
    sample_count INTEGER,
    study_summary TEXT NOT NULL DEFAULT '',
    associated_pmids TEXT NOT NULL DEFAULT '',
    geo_url TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pub_geo_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pmid TEXT NOT NULL,
    gse_accession TEXT NOT NULL,
    relationship_method TEXT NOT NULL,
    supporting_evidence TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL CHECK (
        verification_status IN (
            'Verified relationship',
            'Candidate relationship',
            'Unverified relationship',
            'No relationship identified'
        )
    ),
    confidence_score REAL NOT NULL DEFAULT 0.0,
    uncertainty_indicator TEXT NOT NULL DEFAULT 'High',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pmid, gse_accession, relationship_method),
    FOREIGN KEY (pmid) REFERENCES publications(pmid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pmid TEXT NOT NULL UNIQUE,
    extraction_model TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    extracted_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pmid) REFERENCES publications(pmid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS extraction_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pmid TEXT NOT NULL,
    field_name TEXT NOT NULL,
    extracted_value TEXT NOT NULL,
    supporting_passage TEXT NOT NULL DEFAULT '',
    extraction_method TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'Unverified' CHECK (
        verification_status IN (
            'Verified',
            'Partially supported',
            'Unverified',
            'Unsupported',
            'Source unavailable'
        )
    ),
    verification_notes TEXT NOT NULL DEFAULT '',
    grounding_score REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pmid, field_name),
    FOREIGN KEY (pmid) REFERENCES publications(pmid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS verification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('pmid', 'gse', 'citation', 'claim')),
    entity_id TEXT NOT NULL,
    pmid TEXT,
    field_name TEXT,
    status TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS excluded_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL,
    raw_identifier TEXT NOT NULL,
    exclusion_reason TEXT NOT NULL,
    source_context TEXT NOT NULL DEFAULT '',
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS api_cache (
    cache_key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    response_payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_publications_year ON publications(publication_year);
CREATE INDEX IF NOT EXISTS idx_pub_geo_pmid ON pub_geo_relationships(pmid);
CREATE INDEX IF NOT EXISTS idx_pub_geo_gse ON pub_geo_relationships(gse_accession);
CREATE INDEX IF NOT EXISTS idx_extraction_fields_pmid ON extraction_fields(pmid);
CREATE INDEX IF NOT EXISTS idx_extraction_fields_status ON extraction_fields(verification_status);
CREATE INDEX IF NOT EXISTS idx_verification_logs_entity ON verification_logs(entity_type, entity_id);
