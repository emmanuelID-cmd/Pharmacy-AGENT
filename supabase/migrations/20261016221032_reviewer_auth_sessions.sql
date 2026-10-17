-- Private reviewer authorization and opaque sessions; no Agent/inventory grants.
CREATE ROLE pharmacy_web_auth_backend NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS CONNECTION LIMIT 8;
ALTER ROLE pharmacy_web_auth_backend SET statement_timeout = '5s';
ALTER ROLE pharmacy_web_auth_backend SET lock_timeout = '1s';
ALTER ROLE pharmacy_web_auth_backend SET idle_in_transaction_session_timeout = '5s';
CREATE SCHEMA pharmacy_web;
REVOKE ALL ON SCHEMA pharmacy_web FROM PUBLIC, anon, authenticated, service_role;
CREATE TABLE pharmacy_web.reviewers (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE pharmacy_web.sessions (
    session_hash text PRIMARY KEY CHECK (session_hash ~ '^[a-f0-9]{64}$'),
    user_id uuid NOT NULL REFERENCES pharmacy_web.reviewers(user_id) ON DELETE CASCADE,
    provider_session_id uuid NOT NULL REFERENCES auth.sessions(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL CHECK (expires_at > created_at AND expires_at <= created_at + interval '1 hour')
);
CREATE INDEX reviewer_session_expiry ON pharmacy_web.sessions(expires_at);
CREATE INDEX reviewer_session_provider ON pharmacy_web.sessions(provider_session_id);
CREATE INDEX reviewer_session_user ON pharmacy_web.sessions(user_id);
ALTER TABLE pharmacy_web.reviewers ENABLE ROW LEVEL SECURITY;
ALTER TABLE pharmacy_web.sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA pharmacy_web FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA pharmacy_web TO pharmacy_web_auth_backend;
GRANT SELECT ON pharmacy_web.reviewers, pharmacy_web.sessions TO pharmacy_web_auth_backend;
GRANT INSERT(session_hash,user_id,provider_session_id,expires_at), DELETE ON pharmacy_web.sessions TO pharmacy_web_auth_backend;
-- No runtime grants or policy changes on managed Auth tables. Foreign keys
-- cascade provider session/user deletion without exposing managed records.
CREATE POLICY reviewer_lookup ON pharmacy_web.reviewers FOR SELECT TO pharmacy_web_auth_backend USING (true);
CREATE POLICY session_lookup ON pharmacy_web.sessions FOR SELECT TO pharmacy_web_auth_backend
    USING (session_hash = current_setting('pharmacy_web.session_hash', true));
CREATE POLICY session_issue ON pharmacy_web.sessions FOR INSERT TO pharmacy_web_auth_backend
    WITH CHECK (session_hash = current_setting('pharmacy_web.session_hash', true)
      AND user_id::text = current_setting('pharmacy_web.user_id', true)
      AND EXISTS (SELECT 1 FROM pharmacy_web.reviewers r WHERE r.user_id=sessions.user_id AND r.enabled));
CREATE POLICY session_revoke ON pharmacy_web.sessions FOR DELETE TO pharmacy_web_auth_backend
    USING (session_hash = current_setting('pharmacy_web.session_hash', true) OR expires_at <= now());
-- Existing approved teammate identities only; account confirmation/passwords remain unchanged.
INSERT INTO pharmacy_web.reviewers(user_id)
SELECT id FROM auth.users WHERE id IN
 ('f7f4e528-78d0-4e9d-ae30-fa1579587d82'::uuid,
  '868efbeb-aed0-472e-8ebf-d2270687c523'::uuid,
  '14973943-cf2d-4632-8e1a-15b414628092'::uuid)
ON CONFLICT (user_id) DO NOTHING;
COMMENT ON SCHEMA pharmacy_web IS 'Private approved reviewer/session service; no tokens, passwords, inventory or Agent access.';
