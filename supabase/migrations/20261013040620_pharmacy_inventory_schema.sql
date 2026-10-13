-- Private synthetic storage. No patient records or operational write interface.
create schema pharmacy;
revoke all on schema pharmacy from public,anon,authenticated;
create table pharmacy.stores(store_id integer primary key check(store_id=1618),timezone text not null check(timezone='America/New_York'));
create table pharmacy.synthetic_imports(import_id text primary key,store_id integer not null references pharmacy.stores,source_sha256 text not null check(source_sha256 ~ '^[0-9a-f]{64}$'),synthetic boolean not null check(synthetic),payload jsonb not null check(jsonb_typeof(payload)='object'),imported_at timestamptz not null default now());
create table pharmacy.medication_items(
 store_id integer not null references pharmacy.stores,item_id text not null,package_ndc text not null,
 product_label text not null,dosage_form text not null,dispensing_unit text not null check(dispensing_unit in ('tablet','capsule','mL','unit')),
 strength text,package_quantity numeric(18,6) check(package_quantity>0 and package_quantity not in ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)),package_unit text,
 identity_verified boolean not null default false,active boolean not null default true,
 primary key(store_id,item_id),unique(store_id,package_ndc),unique(store_id,item_id,dispensing_unit),
 check(package_ndc ~ '^([0-9]{4}-[0-9]{4}-[0-9]{2}|[0-9]{5}-[0-9]{3}-[0-9]{2}|[0-9]{5}-[0-9]{4}-[0-9])$'),
 check(not identity_verified or (strength is not null and package_quantity is not null and package_unit is not null))
);
create table pharmacy.item_policies(
 policy_id text primary key,store_id integer not null,item_id text not null,version text not null,
 approval text not null check(approval in ('DRAFT','TEST_APPROVED','OPERATION_APPROVED','RETIRED')),
 critical_days numeric(12,6) not null,low_days numeric(12,6) not null,effective_at timestamptz not null,expires_at timestamptz not null,
 foreign key(store_id,item_id) references pharmacy.medication_items,
 check(critical_days>0 and low_days>critical_days and low_days not in ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)),check(expires_at>effective_at)
);
create function pharmacy.check_policy_interval() returns trigger language plpgsql set search_path=pg_catalog,pharmacy as $$
begin
 perform 1 from pharmacy.medication_items where store_id=new.store_id and item_id=new.item_id for update;
 if new.approval in ('TEST_APPROVED','OPERATION_APPROVED') and exists(select 1 from pharmacy.item_policies p where p.store_id=new.store_id and p.item_id=new.item_id and p.policy_id<>new.policy_id and p.approval in ('TEST_APPROVED','OPERATION_APPROVED') and tstzrange(p.effective_at,p.expires_at,'[)') && tstzrange(new.effective_at,new.expires_at,'[)')) then raise exception 'OVERLAPPING_ITEM_POLICY' using errcode='23514'; end if;
 return new;
end $$;
create trigger validate_policy_interval before insert or update on pharmacy.item_policies for each row execute function pharmacy.check_policy_interval();
create table pharmacy.inventory_events(event_id text primary key,store_id integer not null,item_id text not null,source_event_key text not null,source_version integer not null check(source_version>=0),event_type text not null,source_status text not null,quantity numeric(18,6) not null check(quantity>=0 and quantity not in ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)),dispensing_unit text not null check(dispensing_unit in ('tablet','capsule','mL','unit')),occurred_at timestamptz not null,foreign key(store_id,item_id,dispensing_unit) references pharmacy.medication_items(store_id,item_id,dispensing_unit),unique(store_id,source_event_key,source_version));
create table pharmacy.inventory_snapshots(store_id integer not null,item_id text not null,snapshot_reference text not null,import_id text not null references pharmacy.synthetic_imports,as_of timestamptz not null,synthetic boolean not null check(synthetic),source_policy_version text not null,usable_quantity numeric(18,6) check(usable_quantity>=0 and usable_quantity not in ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)),dispensing_unit text not null check(dispensing_unit in ('tablet','capsule','mL','unit')),reconciliation_state text not null check(reconciliation_state in ('UNVERIFIED','VERIFIED','NEEDS_REVIEW')),primary key(store_id,item_id,snapshot_reference),foreign key(store_id,item_id,dispensing_unit) references pharmacy.medication_items(store_id,item_id,dispensing_unit));
create table pharmacy.daily_usage(store_id integer not null,item_id text not null,usage_date date not null,units numeric(18,6) not null check(units>=0 and units not in ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)),dispensing_unit text not null check(dispensing_unit in ('tablet','capsule','mL','unit')),completeness text not null check(completeness in ('SOURCE_REPORTED','VERIFIED')),import_id text not null references pharmacy.synthetic_imports,primary key(store_id,item_id,usage_date),foreign key(store_id,item_id,dispensing_unit) references pharmacy.medication_items(store_id,item_id,dispensing_unit));
create table pharmacy.inventory_exceptions(exception_id text primary key,store_id integer not null,item_id text not null,import_id text not null references pharmacy.synthetic_imports,reason_codes text[] not null check(cardinality(reason_codes)>0),resolution_state text not null default 'OPEN' check(resolution_state in ('OPEN','RESOLVED')),foreign key(store_id,item_id) references pharmacy.medication_items);
create table pharmacy.audit_events(audit_id bigint generated always as identity primary key,store_id integer not null references pharmacy.stores,actor_reference text not null,action text not null,object_reference text not null,occurred_at timestamptz not null default now(),safe_evidence jsonb not null default '{}'::jsonb);
create index item_policy_lookup on pharmacy.item_policies(store_id,item_id,effective_at);
create index event_item_time on pharmacy.inventory_events(store_id,item_id,occurred_at);
create index snapshot_import on pharmacy.inventory_snapshots(import_id);
create index usage_import on pharmacy.daily_usage(import_id);
create index exception_item on pharmacy.inventory_exceptions(store_id,item_id);
create index exception_import on pharmacy.inventory_exceptions(import_id);
create index audit_store_time on pharmacy.audit_events(store_id,occurred_at);
