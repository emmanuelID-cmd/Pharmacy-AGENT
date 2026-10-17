-- Synthetic fixtures and temporary role membership: run only inside BEGIN/ROLLBACK.
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM auth.users WHERE id IN ('00000000-0000-4000-8000-000000000101','00000000-0000-4000-8000-000000000102')) THEN RAISE EXCEPTION 'fixture identity occupied'; END IF;
END $$;
INSERT INTO auth.users(id,email,email_confirmed_at) VALUES
 ('00000000-0000-4000-8000-000000000101','auth-one@example.invalid',now()),
 ('00000000-0000-4000-8000-000000000102','auth-two@example.invalid',now());
INSERT INTO auth.sessions(id,user_id,not_after) VALUES
 ('00000000-0000-4000-8000-000000000201','00000000-0000-4000-8000-000000000101',now()+interval '1 hour'),
 ('00000000-0000-4000-8000-000000000202','00000000-0000-4000-8000-000000000102',now()+interval '1 hour');
INSERT INTO pharmacy_web.reviewers(user_id) VALUES
 ('00000000-0000-4000-8000-000000000101'),('00000000-0000-4000-8000-000000000102');
GRANT pharmacy_web_auth_backend TO postgres WITH SET TRUE;
SET LOCAL ROLE pharmacy_web_auth_backend;
SELECT set_config('pharmacy_web.session_hash',repeat('a',64),true),set_config('pharmacy_web.user_id','00000000-0000-4000-8000-000000000101',true);
INSERT INTO pharmacy_web.sessions(session_hash,user_id,provider_session_id,expires_at)
VALUES(repeat('a',64),'00000000-0000-4000-8000-000000000101','00000000-0000-4000-8000-000000000201',now()+interval '10 minutes');
DO $$ BEGIN
 IF (SELECT count(*) FROM pharmacy_web.sessions)<>1 THEN RAISE EXCEPTION 'own session missing'; END IF;
 BEGIN EXECUTE 'select encrypted_password from auth.users'; RAISE EXCEPTION 'password hash access granted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN EXECUTE 'select * from auth.sessions'; RAISE EXCEPTION 'provider secret columns accessible'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN EXECUTE 'select * from pharmacy.inventory_snapshots'; RAISE EXCEPTION 'auth role read inventory'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN EXECUTE 'select * from pharmacy_demo.rooms'; RAISE EXCEPTION 'auth role read paired data'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN UPDATE pharmacy_web.reviewers SET enabled=true; RAISE EXCEPTION 'auth role can grant reviewer access'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
SELECT set_config('pharmacy_web.session_hash',repeat('b',64),true);
DO $$ BEGIN
 IF (SELECT count(*) FROM pharmacy_web.sessions)<>0 THEN RAISE EXCEPTION 'other cookie read session'; END IF;
 BEGIN
  INSERT INTO pharmacy_web.sessions(session_hash,user_id,provider_session_id,expires_at)
  VALUES(repeat('b',64),'00000000-0000-4000-8000-000000000102','00000000-0000-4000-8000-000000000202',now()+interval '10 minutes');
  RAISE EXCEPTION 'unverified user context accepted';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
SELECT set_config('pharmacy_web.user_id','00000000-0000-4000-8000-000000000102',true);
INSERT INTO pharmacy_web.sessions(session_hash,user_id,provider_session_id,expires_at)
VALUES(repeat('b',64),'00000000-0000-4000-8000-000000000102','00000000-0000-4000-8000-000000000202',now()+interval '10 minutes');
SELECT set_config('pharmacy_web.session_hash',repeat('c',64),true);
DO $$ BEGIN
 BEGIN
  INSERT INTO pharmacy_web.sessions(session_hash,user_id,provider_session_id,expires_at)
  VALUES(repeat('c',64),'00000000-0000-4000-8000-000000000102','00000000-0000-4000-8000-000000000202',now()+interval '2 hours');
  RAISE EXCEPTION 'overlong session accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
RESET ROLE;
UPDATE pharmacy_web.reviewers SET enabled=false WHERE user_id='00000000-0000-4000-8000-000000000101';
SET LOCAL ROLE pharmacy_web_auth_backend;
SELECT set_config('pharmacy_web.session_hash',repeat('a',64),true);
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM pharmacy_web.sessions s JOIN pharmacy_web.reviewers r ON r.user_id=s.user_id AND r.enabled) THEN RAISE EXCEPTION 'disabled reviewer still resolves'; END IF;
END $$;
RESET ROLE;
DELETE FROM auth.sessions WHERE id='00000000-0000-4000-8000-000000000201';
SET LOCAL ROLE pharmacy_web_auth_backend;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pharmacy_web.sessions) THEN RAISE EXCEPTION 'provider session deletion did not cascade'; END IF; END $$;
SELECT set_config('pharmacy_web.session_hash',repeat('b',64),true);
DELETE FROM pharmacy_web.sessions WHERE session_hash=repeat('b',64);
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pharmacy_web.sessions) THEN RAISE EXCEPTION 'logout did not revoke'; END IF; END $$;
RESET ROLE;
DO $$ BEGIN
 IF has_schema_privilege('anon','pharmacy_web','USAGE') OR has_schema_privilege('authenticated','pharmacy_web','USAGE') OR has_schema_privilege('service_role','pharmacy_web','USAGE') THEN RAISE EXCEPTION 'public auth schema exposed'; END IF;
 IF (SELECT rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb FROM pg_roles WHERE rolname='pharmacy_web_auth_backend') THEN RAISE EXCEPTION 'auth role excessive privileges'; END IF;
 IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid='pharmacy_web.sessions'::regclass) OR NOT (SELECT relrowsecurity FROM pg_class WHERE oid='pharmacy_web.reviewers'::regclass) THEN RAISE EXCEPTION 'auth RLS missing'; END IF;
 IF has_schema_privilege('pharmacy_agent_backend','pharmacy_web','USAGE') THEN RAISE EXCEPTION 'Agent reader has auth access'; END IF;
END $$;
