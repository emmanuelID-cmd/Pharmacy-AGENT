"""Print the reviewed public catalog and synthetic fixture as additive seed SQL."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/catalog/fda_ndc_150.json"
FIXTURE = ROOT / "data/synthetic/store_1618_inventory_150.json"


def quoted(text):
    return "'" + text.replace("'", "''") + "'"


def main():
    catalog_raw = CATALOG.read_text(encoding="utf-8").strip()
    fixture_raw = FIXTURE.read_text(encoding="utf-8").strip()
    catalog = json.loads(catalog_raw)
    fixture = json.loads(fixture_raw)
    ndcs = [row["package_ndc"] for row in catalog["packages"]]
    assert len(ndcs) == len(set(ndcs)) == len(fixture["items"]) == 150
    assert ndcs == [row["package_ndc"] for row in fixture["items"]]
    digest = hashlib.sha256(fixture_raw.encode("utf-8")).hexdigest()
    print("-- Additive public catalog and explicitly synthetic 150-row local snapshot.")
    print("-- FDA NDC directory listing is not evidence of FDA approval or clearance.")
    print("create temp table catalog_seed_source(payload jsonb) on commit preserve rows;")
    print(f"insert into catalog_seed_source values({quoted(catalog_raw)}::jsonb);")
    print("""insert into pharmacy.catalog_products
 (product_ndc,generic_name,brand_name,dosage_form,product_type,fda_source_url,fda_dataset_updated,fda_retrieved_at)
 select distinct on (p->>'product_ndc') p->>'product_ndc',p->>'generic_name',
 p->>'brand_name',p->>'dosage_form',p->>'product_type',c.payload->>'source_url',
 (c.payload->>'dataset_updated')::date,(c.payload->>'retrieved_at')::timestamptz
 from catalog_seed_source c cross join lateral jsonb_array_elements(c.payload->'packages') p
 order by p->>'product_ndc',p->>'package_ndc' on conflict do nothing;""")
    print("""insert into pharmacy.catalog_packages
 (package_ndc,product_ndc,package_description,marketing_start_date,rxnorm_mapping_state,atc_class_state)
 select p->>'package_ndc',p->>'product_ndc',p->>'package_description',
 p->>'marketing_start_date',p->>'rxnorm_mapping_state',p->>'atc_class_state'
 from catalog_seed_source c cross join lateral jsonb_array_elements(c.payload->'packages') p
 on conflict do nothing;""")
    print("""insert into pharmacy.catalog_rxnorm_mappings(package_ndc,rxcui,source_url)
 select p->>'package_ndc',r.value,'https://rxnav.nlm.nih.gov/REST/rxcui.json'
 from catalog_seed_source c cross join lateral jsonb_array_elements(c.payload->'packages') p
 cross join lateral jsonb_array_elements_text(p->'rxnorm_rxcuis') r(value)
 on conflict do nothing;""")
    print("""insert into pharmacy.catalog_atc_classes(package_ndc,rxcui,class_id,class_name,source_url)
 select p->>'package_ndc',p->'rxnorm_rxcuis'->>0,k->>'class_id',k->>'class_name',
 'https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json'
 from catalog_seed_source c cross join lateral jsonb_array_elements(c.payload->'packages') p
 cross join lateral jsonb_array_elements(p->'atc_classes') k
 where p->>'rxnorm_mapping_state'='SINGLE' on conflict do nothing;""")
    print("drop table catalog_seed_source;")
    print("create temp table catalog_stock_source(payload jsonb) on commit preserve rows;")
    print(f"insert into catalog_stock_source values({quoted(fixture_raw)}::jsonb);")
    print(f"""insert into pharmacy.synthetic_imports(import_id,store_id,source_sha256,synthetic,payload)
 values('catalog-fixture-2026-10-07',1618,'{digest}',true,
 (select payload from catalog_stock_source)) on conflict do nothing;""")
    print(f"""do $$ begin if not exists(select 1 from pharmacy.synthetic_imports
 where import_id='catalog-fixture-2026-10-07' and source_sha256='{digest}')
 then raise exception 'CATALOG_FIXTURE_IMPORT_CONFLICT'; end if; end $$;""")
    print("""insert into pharmacy.medication_items
 (store_id,item_id,package_ndc,product_label,dosage_form,dispensing_unit,catalog_package_ndc)
 select 1618,i->>'item_id',i->>'package_ndc',i->>'product_label',
 i->>'dosage_form',i->>'dispensing_unit',i->>'package_ndc'
 from catalog_stock_source s cross join lateral jsonb_array_elements(s.payload->'items') i
 on conflict do nothing;""")
    print("""insert into pharmacy.inventory_snapshots
 (store_id,item_id,snapshot_reference,import_id,as_of,synthetic,source_policy_version,
 usable_quantity,dispensing_unit,reconciliation_state)
 select 1618,i->>'item_id',s.payload->>'snapshot_reference','catalog-fixture-2026-10-07',
 (s.payload->>'snapshot_timestamp')::timestamptz,true,s.payload->>'policy_version',
 (i->>'usable_quantity')::numeric,i->>'dispensing_unit','UNVERIFIED'
 from catalog_stock_source s cross join lateral jsonb_array_elements(s.payload->'items') i
 on conflict do nothing;""")
    print("""insert into pharmacy.daily_usage
 (store_id,item_id,usage_date,units,dispensing_unit,completeness,import_id)
 select 1618,i->>'item_id',(i->'daily_usage'->>'window_end')::date-(14-u.n::integer),
 u.val::text::numeric,i->>'dispensing_unit','SOURCE_REPORTED','catalog-fixture-2026-10-07'
 from catalog_stock_source s cross join lateral jsonb_array_elements(s.payload->'items') i
 cross join lateral jsonb_array_elements(i->'daily_usage'->'units') with ordinality u(val,n)
 where jsonb_array_length(i->'daily_usage'->'units')=14 on conflict do nothing;""")
    print("""insert into pharmacy.inventory_exceptions
 (exception_id,store_id,item_id,import_id,reason_codes)
 select 'catalog:'||(i->>'item_id'),1618,i->>'item_id','catalog-fixture-2026-10-07',
 array['ITEM_POLICY_MISSING','IDENTITY_UNVERIFIED']::text[]
 from catalog_stock_source s cross join lateral jsonb_array_elements(s.payload->'items') i
 on conflict do nothing;""")
    print("drop table catalog_stock_source;")


if __name__ == "__main__":
    main()
