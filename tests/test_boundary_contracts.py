import unittest
from src.injection_prevention.boundary_contracts import ContractError, Limits, strict_json_loads, validate_tree


class BoundaryContractTests(unittest.TestCase):
    def test_valid_nested_data_and_utf8(self):
        value = {"items": [{"product_label": "Médication A", "quantity": 0}]}
        validate_tree(value)
        self.assertEqual(strict_json_loads('{"label":"Médication A"}'.encode()), {"label": "Médication A"})

    def test_parser_rejects_duplicates_nonfinite_and_bad_encoding(self):
        for value in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'not-json'):
            with self.subTest(value=value), self.assertRaises(ContractError):
                strict_json_loads(value)

    def test_bounded_depth_size_and_text(self):
        for value in (b'x'*65537, b'['*1000+b'0'+b']'*1000):
            with self.assertRaises(ContractError):
                strict_json_loads(value)
        with self.assertRaises(ContractError):
            validate_tree({"label": "A"*1001})
        with self.assertRaises(ContractError):
            validate_tree(["A"*1000]*5)
        with self.assertRaises(ContractError):
            validate_tree([0]*2049)

    def test_nonjson_cycle_numeric_and_invalid_policy_fail_closed(self):
        cycle=[]
        cycle.append(cycle)
        for value in (cycle, {"x": b'image'}, {"x": float('nan')}, {"x": 10**13}, {1: "A"}):
            with self.assertRaises(ContractError):
                validate_tree(value)
        for value in (True, 0, 65537):
            with self.assertRaises(ContractError):
                Limits(max_bytes=value)
