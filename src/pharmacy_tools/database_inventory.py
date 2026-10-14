"""Fixed read-only PostgreSQL inventory adapter. Returned evidence remains untrusted."""
import json
import os
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from .inventory import CONFIGURED_STORE_ID, InventoryUnavailable
try:
    from ..injection_prevention import ContractError, strict_json_loads
    from ..injection_prevention.boundary_contracts import InventoryLimits
except ImportError:
    from injection_prevention import ContractError, strict_json_loads
    from injection_prevention.boundary_contracts import InventoryLimits

MAX_ITEMS = 150


def _number(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _read(connection, store_id):
    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    connection.execute("SET LOCAL statement_timeout = '5s'")
    header = connection.execute("""
        SELECT snapshot_reference, min(as_of), max(as_of),
               min(source_policy_version), max(source_policy_version), bool_and(synthetic)
        FROM pharmacy.inventory_snapshots WHERE store_id = %s
        GROUP BY snapshot_reference ORDER BY max(as_of) DESC, snapshot_reference DESC LIMIT 1
    """, (store_id,)).fetchone()
    if header is None:
        raise InventoryUnavailable("EMPTY_SOURCE")
    reference, oldest, as_of, policy, last_policy, synthetic = header
    if oldest != as_of or policy != last_policy or synthetic is not True:
        raise InventoryUnavailable("SOURCE_CONFLICT")
    rows = connection.execute("""
        SELECT i.item_id, i.package_ndc, i.product_label, i.dosage_form, i.dispensing_unit,
               s.usable_quantity, s.reconciliation_state
        FROM pharmacy.medication_items i JOIN pharmacy.inventory_snapshots s
          ON s.store_id=i.store_id AND s.item_id=i.item_id
        WHERE i.store_id=%s AND s.snapshot_reference=%s AND i.active
        ORDER BY i.item_id LIMIT 151
    """, (store_id, reference)).fetchall()
    if not rows:
        raise InventoryUnavailable("EMPTY_SOURCE")
    if len(rows) > MAX_ITEMS:
        raise InventoryUnavailable("SOURCE_ROW_LIMIT")
    ids = [row[0] for row in rows]
    end = as_of.astimezone(ZoneInfo("America/New_York")).date() - timedelta(days=1)
    start = end - timedelta(days=13)
    usage = connection.execute("""
        SELECT item_id, usage_date, units FROM pharmacy.daily_usage
        WHERE store_id=%s AND item_id=ANY(%s) AND usage_date BETWEEN %s AND %s
        ORDER BY item_id,usage_date LIMIT 2101
    """, (store_id, ids, start, end)).fetchall()
    exceptions = connection.execute("""
        SELECT item_id,reason_codes FROM pharmacy.inventory_exceptions
        WHERE store_id=%s AND item_id=ANY(%s) AND resolution_state='OPEN'
        AND import_id IN (SELECT import_id FROM pharmacy.inventory_snapshots
                          WHERE store_id=%s AND snapshot_reference=%s)
        ORDER BY item_id,exception_id LIMIT 751
    """, (store_id, ids, store_id, reference)).fetchall()
    if len(exceptions) > 750:
        raise InventoryUnavailable("SOURCE_EXCEPTION_LIMIT")
    by_id = {item: [] for item in ids}
    reasons = {item: set() for item in ids}
    for item, date, units in usage:
        by_id[item].append((date, _number(units)))
    for item, codes in exceptions:
        reasons[item].update(codes)
    # Policy contents are not inferred from the legacy snapshot policy version.
    policies = connection.execute("""
        SELECT item_id,low_days,critical_days,version,approval,effective_at,expires_at
        FROM pharmacy.item_policies WHERE store_id=%s AND item_id=ANY(%s)
        AND approval IN ('TEST_APPROVED','OPERATION_APPROVED')
        AND effective_at<=%s AND expires_at>%s ORDER BY item_id,policy_id LIMIT 151
    """, (store_id, ids, as_of, as_of)).fetchall()
    policy_by_id = {}
    for item, low, critical, version, approval, effective, expires in policies:
        if item in policy_by_id:
            raise InventoryUnavailable("SOURCE_POLICY_CONFLICT")
        policy_by_id[item] = dict(low_days=_number(low),critical_days=_number(critical),
                                 version=version,approval=approval,
                                 effective_at=effective.isoformat(),expires_at=expires.isoformat())
    expected = [start + timedelta(days=n) for n in range(14)]
    items = []
    for item, ndc, label, form, unit, stock, state in rows:
        daily = by_id[item]
        if [date for date, value in daily] != expected:
            reasons[item].add("INCOMPLETE_USAGE")
        if item not in policy_by_id:
            reasons[item].add("ITEM_POLICY_MISSING")
        else:
            reasons[item].discard("ITEM_POLICY_MISSING")
        result = dict(item_id=item,package_ndc=ndc,product_label=label,dosage_form=form,
                      dispensing_unit=unit,usable_quantity=_number(stock),reconciliation_state=state,
                      daily_usage=dict(window_end=end.isoformat(),units=[value for date,value in daily]),
                      exceptions=sorted(reasons[item]))
        if item in policy_by_id:
            result["item_policy"] = policy_by_id[item]
        items.append(result)
    payload = dict(store_id=store_id,synthetic=True,snapshot_reference=reference,
                   snapshot_timestamp=as_of.isoformat(),policy_version=policy,items=items)
    return strict_json_loads(json.dumps(payload,allow_nan=False).encode("utf-8"), InventoryLimits())


def read_store_inventory_database(store_id):
    """Uses PHARMACY_DATABASE_URL from trusted backend environment; no credential tool argument."""
    if type(store_id) is not int or store_id != CONFIGURED_STORE_ID:
        raise InventoryUnavailable("WRONG_STORE")
    url = os.environ.get("PHARMACY_DATABASE_URL")
    if not url:
        raise InventoryUnavailable("DATABASE_NOT_CONFIGURED")
    try:
        import psycopg
        with psycopg.connect(url,connect_timeout=5,sslmode="require",prepare_threshold=None) as connection:
            return _read(connection,store_id)
    except InventoryUnavailable:
        raise
    except Exception:
        # Driver errors may contain credentials/host details. Never expose them.
        raise InventoryUnavailable("DATABASE_UNAVAILABLE") from None
