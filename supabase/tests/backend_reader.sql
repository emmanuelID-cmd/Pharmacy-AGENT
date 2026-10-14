-- Exercise inside a transaction with temporary postgres SET-role membership.

grant pharmacy_agent_backend to postgres with set true;
set local role pharmacy_agent_backend;
do $$ begin
 if (select count(*) from pharmacy.catalog_packages)<>150 then raise exception 'LOGIN_READ_FAILED'; end if;
 begin update pharmacy.inventory_snapshots set usable_quantity=1; raise exception 'LOGIN_WRITE_ALLOWED'; exception when insufficient_privilege then null; end;
 begin delete from pharmacy.medication_items; raise exception 'LOGIN_DELETE_ALLOWED'; exception when insufficient_privilege then null; end;
 begin perform payload from pharmacy.synthetic_imports; raise exception 'LOGIN_RAW_READ_ALLOWED'; exception when insufficient_privilege then null; end;
end $$;
reset role;
select 'PASS: dedicated login inherits scoped read grants, write/raw access denied' as verification;
