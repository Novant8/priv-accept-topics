CREATE TABLE IF NOT EXISTS cache (
    domain TEXT PRIMARY KEY,
    attested BOOLEAN NOT NULL,
    attestation_result TEXT
)