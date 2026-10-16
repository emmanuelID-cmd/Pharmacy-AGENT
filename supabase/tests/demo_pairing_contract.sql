-- Execute inside BEGIN/ROLLBACK; fixtures and temporary membership never persist.
GRANT pharmacy_demo_backend TO postgres WITH SET TRUE;
GRANT pharmacy_agent_backend TO postgres WITH SET TRUE;
SET LOCAL ROLE pharmacy_demo_backend;
SELECT set_config('pharmacy_demo.device_hash', repeat('a',64), true), set_config('pharmacy_demo.invite_hash','',true);
INSERT INTO pharmacy_demo.rooms (room_id,owner_hash,invite_hash,invite_expires_at)
VALUES ('00000000-0000-4000-8000-000000000001',repeat('a',64),repeat('b',64),now()+interval '10 minutes');
DO $$ BEGIN
 IF (SELECT count(*) FROM pharmacy_demo.rooms) <> 1 THEN RAISE EXCEPTION 'owner cannot read own room'; END IF;
END $$;
SELECT set_config('pharmacy_demo.device_hash',repeat('c',64),true);
DO $$ BEGIN
 IF (SELECT count(*) FROM pharmacy_demo.rooms) <> 0 THEN RAISE EXCEPTION 'unpaired device read room'; END IF;
 BEGIN
  INSERT INTO pharmacy_demo.rooms (room_id,owner_hash) VALUES ('00000000-0000-4000-8000-000000000002',repeat('d',64));
  RAISE EXCEPTION 'spoofed owner accepted';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
  EXECUTE 'select * from pharmacy.inventory_snapshots limit 1';
  RAISE EXCEPTION 'demo role read inventory';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
SELECT set_config('pharmacy_demo.invite_hash',repeat('b',64),true);
UPDATE pharmacy_demo.rooms SET manufacturer_hash=repeat('c',64),invite_hash=NULL,invite_expires_at=NULL
WHERE room_id='00000000-0000-4000-8000-000000000001';
SELECT set_config('pharmacy_demo.invite_hash','',true);
DO $$ BEGIN
 IF (SELECT count(*) FROM pharmacy_demo.rooms) <> 1 THEN RAISE EXCEPTION 'manufacturer binding failed'; END IF;
END $$;
SELECT set_config('pharmacy_demo.device_hash',repeat('d',64),true),set_config('pharmacy_demo.invite_hash',repeat('b',64),true);
DO $$ BEGIN
 IF (SELECT count(*) FROM pharmacy_demo.rooms) <> 0 THEN RAISE EXCEPTION 'consumed code replay accepted'; END IF;
END $$;
RESET ROLE;
SET LOCAL ROLE pharmacy_agent_backend;
DO $$ BEGIN
 BEGIN
  EXECUTE 'select * from pharmacy_demo.rooms';
  RAISE EXCEPTION 'inventory reader read private demo';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
  EXECUTE 'insert into pharmacy_demo.rooms (room_id,owner_hash) values (gen_random_uuid(),repeat(''a'',64))';
  RAISE EXCEPTION 'inventory reader wrote demo';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE;
DO $$ BEGIN
 IF has_schema_privilege('anon','pharmacy_demo','USAGE') OR has_schema_privilege('authenticated','pharmacy_demo','USAGE')
    OR has_schema_privilege('service_role','pharmacy_demo','USAGE') THEN RAISE EXCEPTION 'public API role has demo schema access'; END IF;
 IF (SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname='pharmacy_demo_backend') THEN RAISE EXCEPTION 'demo role bypasses RLS'; END IF;
 IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid='pharmacy_demo.rooms'::regclass) THEN RAISE EXCEPTION 'RLS missing'; END IF;
END $$;

SET LOCAL ROLE pharmacy_demo_backend;
SELECT set_config('pharmacy_demo.device_hash',repeat('e',64),true), set_config('pharmacy_demo.invite_hash','',true);
INSERT INTO pharmacy_demo.rooms (room_id,owner_hash,created_at,expires_at)
VALUES ('00000000-0000-4000-8000-000000000003',repeat('e',64),now()-interval '25 hours',now()-interval '1 hour');
DO $$ DECLARE affected integer; BEGIN
 DELETE FROM pharmacy_demo.rooms WHERE room_id='00000000-0000-4000-8000-000000000003' AND expires_at <= now();
 GET DIAGNOSTICS affected=ROW_COUNT;
 IF affected<>1 THEN RAISE EXCEPTION 'expired cleanup did not remove exactly the expired row'; END IF;
 BEGIN
  INSERT INTO pharmacy_demo.rooms (room_id,owner_hash,state)
  VALUES ('00000000-0000-4000-8000-000000000004',repeat('e',64),'[]'::jsonb);
  RAISE EXCEPTION 'non-object state accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  EXECUTE 'delete from pharmacy.inventory_snapshots where false';
  RAISE EXCEPTION 'demo role has inventory write grant';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE;
