"""Private helpers for the publication-neutral provenance graph."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json

FORBIDDEN_EVIDENCE_KEYS = {
    "text",
    "source_text",
    "raw_text",
    "expression",
    "source_expression",
    "prose",
}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_id(prefix: str, value: Mapping[str, object]) -> str:
    digest = sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def source_safe_evidence(value: object, label: str) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise ValueError(f"{label} must use non-empty string keys")
            lowered = key.lower()
            if lowered in FORBIDDEN_EVIDENCE_KEYS or (
                lowered.endswith("_text") and not lowered.endswith("_text_sha256")
            ):
                raise ValueError(
                    f"{label} must remain source-safe and omit source expression"
                )
            result[key] = source_safe_evidence(value[key], f"{label}.{key}")
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [source_safe_evidence(item, f"{label}[]") for item in value]
    raise ValueError(f"{label} contains an unsupported value")


def cyclic_components(adjacency: Mapping[str, set[str]]) -> list[list[str]]:
    nodes = set(adjacency)
    reverse: dict[str, set[str]] = {}
    for source, targets in adjacency.items():
        for target in targets:
            nodes.add(target)
            reverse.setdefault(target, set()).add(source)

    seen: set[str] = set()
    order: list[str] = []
    for start in sorted(nodes):
        if start in seen:
            continue
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                order.append(node)
                continue
            if node in seen:
                continue
            seen.add(node)
            stack.append((node, True))
            for target in reversed(sorted(adjacency.get(node, set()))):
                if target not in seen:
                    stack.append((target, False))

    assigned: set[str] = set()
    result: list[list[str]] = []
    for start in reversed(order):
        if start in assigned:
            continue
        component: list[str] = []
        stack = [start]
        assigned.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for source in reversed(sorted(reverse.get(node, set()))):
                if source not in assigned:
                    assigned.add(source)
                    stack.append(source)
        component.sort()
        if len(component) > 1 or (
            component and component[0] in adjacency.get(component[0], set())
        ):
            result.append(component)
    return sorted(result)
