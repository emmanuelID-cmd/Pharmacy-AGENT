# Synthetic inventory fixture: store 1618

SYNTHETIC INVENTORY TEST data. Not CVS inventory; quantities and usage are invented.
Only `42023-240-01` and `0009-0280-02` are real package NDCs (FDA shortage records verified 2026-10-12);
`99901-*` NDCs are placeholders expected to return NO_MATCH.

`daily_usage.units` holds 14 daily totals in date order, ending on `window_end`
(the last completed local day before `snapshot_timestamp`).

`dispensing_unit` uses only the units `TrustedFact` accepts: `tablet`, `capsule`, `mL`, `unit`
(vials, inhalers and tubes are counted as `unit`).

| Item | Purpose |
|---|---|
| item-001 | Eval Case 1: 6.22 days ABOVE_THRESHOLD |
| item-002 | Eval Case 2: zero usage -> UNKNOWN |
| item-003 | exactly 2.00 days CRITICAL |
| item-004 | exactly 5.00 days LOW |
| item-005 | 3.75 days LOW |
| item-006 | zero stock with usage CRITICAL |
| item-007 | 25.00 days ABOVE_THRESHOLD |
| item-008 | 13 usage days -> MANUAL_REVIEW |
| item-009 | 5.10 days ABOVE_THRESHOLD |
| item-010 | 2.10 days LOW |
| item-011 | 10.00 days ABOVE_THRESHOLD |
| item-012 | negative stock -> MANUAL_REVIEW |
| item-013 | missing usable stock -> MANUAL_REVIEW |
| item-014 | 3.00 days LOW |
| item-015 | 1.00 day CRITICAL |
| item-016 | 8.00 days ABOVE_THRESHOLD |
| item-017 | 6.43 days ABOVE_THRESHOLD |
| item-018 | 1.33 days CRITICAL |
| item-019 | 4.00 days LOW |
| item-020 | 30.00 days ABOVE_THRESHOLD |
