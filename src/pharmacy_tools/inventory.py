"""read_store_inventory: read-only reader for the store's synthetic inventory snapshot.

The tool only reads and shape-checks the source. It does not calculate days of
supply, classify stock or decide what is trusted: that is the harness's job, and
everything returned here stays untrusted data for injection_prevention.inspect_payload.
"""
from pathlib import Path

try:  # imported as src.pharmacy_tools (tests run from the repo root)
    from ..injection_prevention import ContractError, strict_json_loads
except ImportError:  # imported as pharmacy_tools with src on PYTHONPATH
    from injection_prevention import ContractError, strict_json_loads

CONFIGURED_STORE_ID = 1618
FIXTURE_PATH = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "store_1618_inventory.json"


class InventoryUnavailable(Exception):
    """Static, safe reason code only; never raw file content or stack traces."""

    def __init__(self, reason_code):
        super().__init__(reason_code)
        self.reason_code = reason_code


def read_store_inventory(store_id, *, path=FIXTURE_PATH):
    """Return the synthetic inventory payload for the configured store.

    Raises InventoryUnavailable with a static reason code when the source is
    missing, unreadable, malformed, for another store, not labeled synthetic or
    empty. An empty or unreadable source never means healthy stock.
    """
    if type(store_id) is not int or store_id != CONFIGURED_STORE_ID:
        raise InventoryUnavailable("WRONG_STORE")
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise InventoryUnavailable("SOURCE_UNREADABLE") from None
    try:
        payload = strict_json_loads(raw)  # size cap, no duplicate keys, no NaN/Infinity
    except (ContractError, ValueError, UnicodeDecodeError):
        raise InventoryUnavailable("SOURCE_MALFORMED") from None

    if type(payload) is not dict:
        raise InventoryUnavailable("SOURCE_MALFORMED")
    if payload.get("store_id") != CONFIGURED_STORE_ID:
        raise InventoryUnavailable("WRONG_STORE")
    if payload.get("synthetic") is not True:
        raise InventoryUnavailable("NOT_LABELED_SYNTHETIC")
    if type(payload.get("items")) is not list or not payload["items"]:
        raise InventoryUnavailable("EMPTY_SOURCE")
    return payload
