-- Private synthetic demo state. No inventory grants, public API or Agent tool.
CREATE ROLE pharmacy_demo_backend LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS CONNECTION LIMIT 8;
ALTER ROLE pharmacy_demo_backend SET statement_timeout = '5s';
ALTER ROLE pharmacy_demo_backend SET lock_timeout = '1s';
ALTER ROLE pharmacy_demo_backend SET idle_in_transaction_session_timeout = '5s';
CREATE SCHEMA pharmacy_demo AUTHORIZATION postgres;
REVOKE ALL ON SCHEMA pharmacy_demo FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA pharmacy_demo TO pharmacy_demo_backend;
CREATE TABLE pharmacy_demo.rooms (
    room_id uuid PRIMARY KEY,
    owner_hash text NOT NULL CHECK (owner_hash ~ '^[a-f0-9]{64}$'),
    manufacturer_hash text CHECK (manufacturer_hash ~ '^[a-f0-9]{64}$' AND manufacturer_hash <> owner_hash),
    invite_hash text UNIQUE CHECK (invite_hash ~ '^[a-f0-9]{64}$'),
    invite_expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '24 hours',
    state jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(state) = 'object' AND octet_length(state::text) <= 2097152),
    CHECK ((invite_hash IS NULL) = (invite_expires_at IS NULL)),
    CHECK (expires_at > created_at AND expires_at <= created_at + interval '24 hours'),
    CHECK (invite_expires_at IS NULL OR invite_expires_at <= expires_at)
);
CREATE INDEX demo_rooms_expiry ON pharmacy_demo.rooms (expires_at);
ALTER TABLE pharmacy_demo.rooms ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON pharmacy_demo.rooms FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON pharmacy_demo.rooms TO pharmacy_demo_backend;
-- Context is supplied only by the authenticated server, never by model/tool SQL.
-- The backend may inspect expired rows only for cleanup; API lookups always require a live room.
CREATE POLICY demo_room_read ON pharmacy_demo.rooms FOR SELECT TO pharmacy_demo_backend USING (
    expires_at <= now() OR (expires_at > now() AND (
      owner_hash = current_setting('pharmacy_demo.device_hash', true)
      OR manufacturer_hash = current_setting('pharmacy_demo.device_hash', true)
      OR (manufacturer_hash IS NULL AND invite_hash = current_setting('pharmacy_demo.invite_hash', true) AND invite_expires_at > now())
    ))
);
CREATE POLICY demo_room_create ON pharmacy_demo.rooms FOR INSERT TO pharmacy_demo_backend WITH CHECK (
    owner_hash = current_setting('pharmacy_demo.device_hash', true) AND manufacturer_hash IS NULL
);
CREATE POLICY demo_room_update ON pharmacy_demo.rooms FOR UPDATE TO pharmacy_demo_backend USING (
    expires_at > now() AND (
      owner_hash = current_setting('pharmacy_demo.device_hash', true)
      OR manufacturer_hash = current_setting('pharmacy_demo.device_hash', true)
      OR (manufacturer_hash IS NULL AND invite_hash = current_setting('pharmacy_demo.invite_hash', true) AND invite_expires_at > now())
    )
) WITH CHECK (
    expires_at > now() AND (owner_hash = current_setting('pharmacy_demo.device_hash', true)
      OR manufacturer_hash = current_setting('pharmacy_demo.device_hash', true))
);
CREATE POLICY demo_room_expiry_cleanup ON pharmacy_demo.rooms FOR DELETE TO pharmacy_demo_backend USING (expires_at <= now());
COMMENT ON SCHEMA pharmacy_demo IS 'Private human-operated synthetic two-phone demo; never Agent or inventory writes.';
