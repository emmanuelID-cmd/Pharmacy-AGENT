-- Public medication identities only. Listing does not establish FDA approval.
-- No stock, usage, patient, prescription, or operational policy is imported here.
create table pharmacy.catalog_products(
 product_ndc text primary key,
 generic_name text not null,
 brand_name text not null,
 dosage_form text not null,
 product_type text not null check(product_type='HUMAN PRESCRIPTION DRUG'),
 fda_source_url text not null check(fda_source_url='https://api.fda.gov/drug/ndc.json?limit=500'),
 fda_dataset_updated date not null,
 fda_retrieved_at timestamptz not null,
 check(length(generic_name) between 1 and 120),
 check(length(brand_name)<=120),
 check(length(dosage_form)<=80)
);
create table pharmacy.catalog_packages(
 package_ndc text primary key,
 product_ndc text not null references pharmacy.catalog_products(product_ndc),
 package_description text not null,
 marketing_start_date text not null,
 rxnorm_mapping_state text not null check(rxnorm_mapping_state in ('SINGLE','MULTIPLE','MISSING','UNAVAILABLE')),
 atc_class_state text not null check(atc_class_state in ('MAPPED','MISSING','NOT_MAPPED','UNAVAILABLE')),
 check(package_ndc ~ '^([0-9]{4}-[0-9]{4}-[0-9]{2}|[0-9]{5}-[0-9]{3}-[0-9]{2}|[0-9]{5}-[0-9]{4}-[0-9])$'),
 check(length(package_description)<=300),
 check(marketing_start_date='' or marketing_start_date ~ '^[0-9]{8}$'),
 check((rxnorm_mapping_state='SINGLE' and atc_class_state in ('MAPPED','MISSING','UNAVAILABLE'))
    or (rxnorm_mapping_state<>'SINGLE' and atc_class_state='NOT_MAPPED'))
);
create table pharmacy.catalog_rxnorm_mappings(
 package_ndc text not null references pharmacy.catalog_packages(package_ndc),
 rxcui text not null check(rxcui ~ '^[0-9]{1,12}$'),
 source_url text not null check(source_url='https://rxnav.nlm.nih.gov/REST/rxcui.json'),
 primary key(package_ndc,rxcui)
);
create table pharmacy.catalog_atc_classes(
 package_ndc text not null,
 rxcui text not null,
 class_id text not null,
 class_name text not null,
 source_url text not null check(source_url='https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json'),
 primary key(package_ndc,rxcui,class_id),
 foreign key(package_ndc,rxcui) references pharmacy.catalog_rxnorm_mappings(package_ndc,rxcui),
 check(length(class_id) between 1 and 30),
 check(length(class_name) between 1 and 160)
);
alter table pharmacy.medication_items
 add column catalog_package_ndc text references pharmacy.catalog_packages(package_ndc),
 add constraint catalog_ndc_matches_stock_ndc
 check(catalog_package_ndc is null or catalog_package_ndc=package_ndc);
create index catalog_package_product on pharmacy.catalog_packages(product_ndc);
alter table pharmacy.catalog_products enable row level security;
alter table pharmacy.catalog_packages enable row level security;
alter table pharmacy.catalog_rxnorm_mappings enable row level security;
alter table pharmacy.catalog_atc_classes enable row level security;
revoke all on pharmacy.catalog_products,pharmacy.catalog_packages,
 pharmacy.catalog_rxnorm_mappings,pharmacy.catalog_atc_classes from public,anon,authenticated;
grant select on pharmacy.catalog_products,pharmacy.catalog_packages,
 pharmacy.catalog_rxnorm_mappings,pharmacy.catalog_atc_classes to pharmacy_inventory_reader;
create policy reader_catalog on pharmacy.catalog_products for select to pharmacy_inventory_reader using(true);
create policy reader_catalog on pharmacy.catalog_packages for select to pharmacy_inventory_reader using(true);
create policy reader_catalog on pharmacy.catalog_rxnorm_mappings for select to pharmacy_inventory_reader using(true);
create policy reader_catalog on pharmacy.catalog_atc_classes for select to pharmacy_inventory_reader using(true);
