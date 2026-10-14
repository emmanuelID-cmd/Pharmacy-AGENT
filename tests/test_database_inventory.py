import os
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from src.pharmacy_tools.database_inventory import _read, read_store_inventory_database
from src.pharmacy_tools.inventory import InventoryUnavailable
from src.injection_prevention import inspect_payload, Source

STAMP = datetime(2026,10,7,13,tzinfo=timezone.utc)


class Rows:
    def __init__(self, rows): self.rows=rows
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows


class Database:
    def __init__(self, *, count=1, days=14, conflict=False, policies=None):
        self.calls=[]
        first=STAMP-timedelta(seconds=1) if conflict else STAMP
        self.results=iter([[],[],[("snapshot-A",first,STAMP,"SYNTHETIC-v0","SYNTHETIC-v0",True)],
            [(f"item-{n}","42023-240-01","Synthetic tablet","Tablet","tablet",Decimal(80),"UNVERIFIED") for n in range(count)],
            [("item-0",(STAMP.date()-timedelta(days=14-n)),Decimal(10)) for n in range(days)],
            [("item-0",["IDENTITY_UNVERIFIED"])], policies or []])
    def execute(self, sql, params=None):
        self.calls.append((sql,params))
        return Rows(next(self.results))


class DatabaseInventoryTests(unittest.TestCase):
    def test_fixed_reader_returns_contract_without_verifying_facts(self):
        db=Database();result=_read(db,1618)
        self.assertEqual(len(result["items"]),1)
        self.assertEqual(result["items"][0]["usable_quantity"],80)
        self.assertEqual(result["items"][0]["reconciliation_state"],"UNVERIFIED")
        self.assertIn("ITEM_POLICY_MISSING",result["items"][0]["exceptions"])
        self.assertTrue(inspect_payload(result,source=Source.INVENTORY).source_contract_valid)
        self.assertIn("READ ONLY",db.calls[0][0])
        for sql,params in db.calls[2:]:
            self.assertNotIn("1618",sql)
            self.assertEqual(params[0],1618)
    def test_incomplete_usage_is_not_filled_with_zero(self):
        result=_read(Database(days=13),1618)["items"][0]
        self.assertEqual(len(result["daily_usage"]["units"]),13)
        self.assertIn("INCOMPLETE_USAGE",result["exceptions"])
    def test_excess_rows_fail_instead_of_truncating(self):
        with self.assertRaisesRegex(InventoryUnavailable,"SOURCE_ROW_LIMIT"):
            _read(Database(count=151),1618)
    def test_reader_returns_the_full_150_row_limit(self):
        result = _read(Database(count=150),1618)
        self.assertEqual(len(result["items"]),150)
        self.assertEqual(len({row["item_id"] for row in result["items"]}),150)
    def test_snapshot_conflict_fails(self):
        with self.assertRaisesRegex(InventoryUnavailable,"SOURCE_CONFLICT"):
            _read(Database(conflict=True),1618)
    def test_policy_is_returned_as_data_without_approval_claim(self):
        p=[("item-0",Decimal(5),Decimal(2),"test-v1","TEST_APPROVED",STAMP-timedelta(days=1),STAMP+timedelta(days=1))]
        row=_read(Database(policies=p),1618)["items"][0]
        self.assertEqual(row["item_policy"]["critical_days"],2)
        self.assertNotIn("ITEM_POLICY_MISSING",row["exceptions"])
    def test_conflicting_policy_fails(self):
        p=("item-0",Decimal(5),Decimal(2),"test-v1","TEST_APPROVED",STAMP,STAMP+timedelta(days=1))
        with self.assertRaisesRegex(InventoryUnavailable,"SOURCE_POLICY_CONFLICT"):
            _read(Database(policies=[p,p]),1618)
    def test_wrong_store_and_bool_rejected_before_credentials(self):
        for store in [True,"1618",9999]:
            with self.assertRaisesRegex(InventoryUnavailable,"WRONG_STORE"):
                read_store_inventory_database(store)
    def test_missing_configuration_fails_closed(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(InventoryUnavailable,"DATABASE_NOT_CONFIGURED"):
                read_store_inventory_database(1618)
    def test_driver_diagnostics_are_redacted(self):
        def bad(*args,**kwargs): raise RuntimeError("PASSWORD_SHOULD_NOT_ESCAPE")
        with patch.dict(os.environ,{"PHARMACY_DATABASE_URL":"postgresql://test"}),patch.dict("sys.modules",{"psycopg":SimpleNamespace(connect=bad)}):
            with self.assertRaises(InventoryUnavailable) as error: read_store_inventory_database(1618)
        self.assertEqual(str(error.exception),"DATABASE_UNAVAILABLE")


if __name__=="__main__": unittest.main()
