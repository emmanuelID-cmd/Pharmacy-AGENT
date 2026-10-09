"""Bounded untrusted-data contracts. No parsing into executable instructions."""
from dataclasses import dataclass
from enum import StrEnum
import json
import math
import re


class Source(StrEnum):
    INVENTORY = "inventory"
    FDA = "fda"
    USER_REQUEST = "user_request"


class ContractError(ValueError):
    """Safe static reason only; never includes input or decoder diagnostics."""


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 65536
    max_depth: int = 6
    max_nodes: int = 2048
    max_rows: int = 20
    max_field_text: int = 1000
    max_total_text: int = 4096

    def __post_init__(self):
        ceilings = (65536, 8, 4096, 100, 4096, 8192)
        values = (self.max_bytes, self.max_depth, self.max_nodes, self.max_rows,
                  self.max_field_text, self.max_total_text)
        if any(type(v) is not int or not 1 <= v <= cap for v, cap in zip(values, ceilings)):
            raise ContractError("INVALID_LIMITS")


def opaque_reference(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", value) is not None


def validate_tree(value: object, limits: Limits = Limits()) -> None:
    """Bound traversal before scanning. Reject cycles and non-JSON Python values."""
    nodes = 0
    text_count = 0
    ancestors = set()

    def visit(node, depth):
        nonlocal nodes, text_count
        nodes += 1
        if nodes > limits.max_nodes or depth > limits.max_depth:
            raise ContractError("STRUCTURE_LIMIT")
        if type(node) is str:
            if len(node) > limits.max_field_text:
                raise ContractError("TEXT_LIMIT")
            text_count += len(node)
            if text_count > limits.max_total_text:
                raise ContractError("TEXT_BUDGET")
        elif node is None or type(node) is bool:
            return
        elif type(node) in (int, float):
            if type(node) is int and abs(node) > 10**12:
                raise ContractError("NUMBER_LIMIT")
            if type(node) is float and (not math.isfinite(node) or abs(node) > 10**12):
                raise ContractError("INVALID_NUMBER")
        elif type(node) in (dict, list):
            if id(node) in ancestors:
                raise ContractError("CYCLIC_INPUT")
            if len(node) > limits.max_nodes:
                raise ContractError("STRUCTURE_LIMIT")
            ancestors.add(id(node))
            if type(node) is dict:
                for key, child in node.items():
                    if type(key) is not str or not 1 <= len(key) <= 64:
                        raise ContractError("INVALID_FIELD")
                    visit(child, depth + 1)
            else:
                for child in node:
                    visit(child, depth + 1)
            ancestors.remove(id(node))
        else:
            raise ContractError("UNSUPPORTED_INPUT")

    visit(value, 0)


def strict_json_loads(raw: bytes, limits: Limits = Limits()) -> object:
    if type(raw) is not bytes or not raw or len(raw) > limits.max_bytes:
        raise ContractError("PAYLOAD_LIMIT")

    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ContractError("DUPLICATE_FIELD")
            result[key] = value
        return result

    def reject_constant(_):
        raise ContractError("INVALID_NUMBER")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)
    except ContractError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ContractError("INVALID_JSON") from None
    validate_tree(value, limits)
    return value
