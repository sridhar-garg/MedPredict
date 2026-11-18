-- Apply to an existing MedPredict Postgres installation before enabling Google.
BEGIN;
CREATE TABLE IF NOT EXISTS medpredict.google_identities (
 subject TEXT PRIMARY KEY,
 user_id BIGINT NOT NULL UNIQUE REFERENCES medpredict.users(id) ON DELETE CASCADE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE medpredict.google_identities ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON medpredict.google_identities FROM PUBLIC,anon,authenticated;
COMMIT;
