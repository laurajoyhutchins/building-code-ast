"""Strict contract and canonicalization for source-local NFPA 13 AST bundles."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
import hashlib
import json
import re
from typing import Any

RAW_BUNDLE_SCHEMA = "nfpa13-ast-bundle/0.1.0"
BUNDLE_SCHEMA = "nfpa13-ast-bundle/0.2.0"
PRODUCER_SCHEMA = "nfpa13-ast-producer/0.1.0"
REVIEW_REGISTRY_SCHEMA = "nfpa13-reviewed-cases/0.1.0"
ARTIFACT_ID = "nfpa:13"

TOP_FIELDS = {
    "schema", "producer", "source", "document_ast", "relations",
    "semantic_annotations", "tables", "source_map", "statistics", "validation",
}
RELATION_FIELDS = {
    "type", "source_locator", "target_locator", "target_artifact_id",
    "target_domain", "resolved", "evidence",
}
SEMANTIC_FIELDS = {
    "type", "source_locator", "method", "parser_revision", "review_status", "evidence",
}
PRODUCER_FIELDS = {
    "schema", "repository", "commit_sha", "engine_path", "engine_sha256",
    "wrapper_path", "wrapper_sha256", "python_version", "pymupdf_version",
    "command_options",
}
TARGET_DOMAINS = {"internal", "external_standard", "unspecified_document"}
REVIEW_STATES = {"unreviewed", "reviewed", "rejected"}
EXTERNAL_STANDARD_RE = re.compile(
    r"\b(?P<issuer>ANSI/UL|ASTM|ASME|AWWA|ANSI|IEEE|ISO|UL)[ \t\n]+"
    r"(?P<identifier>[A-Z]?[0-9]+(?:\.[0-9]+)*(?:[A-Z])?(?:[/:-][A-Z0-9.]+)*)\b",
    re.IGNORECASE,
)
DocumentValidator = Callable[[Mapping[str, Any]], Any]
EngineValidator = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _obj(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _arr(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing, extra = sorted(expected - set(value)), sorted(set(value) - expected)
    if missing:
        raise ValueError(f"{label} is missing required fields: {missing}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {extra}")


def _sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _span(value: Any, label: str, source: str, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    span = _obj(value, label)
    _keys(span, {"start", "end", "text"}, label)
    start, end, text = span["start"], span["end"], span["text"]
    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError(f"{label}.start must be an integer")
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError(f"{label}.end must be an integer")
    if not isinstance(text, str) or not 0 <= start <= end <= len(source):
        raise ValueError(f"{label} is invalid")
    if source[start:end] != text:
        raise ValueError(f"{label} does not round-trip to source_text")


def walk_document_nodes(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield root
    for child in _arr(root.get("children", []), "document node children"):
        yield from walk_document_nodes(_obj(child, "document node"))


def document_node_index(document_ast: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for node in walk_document_nodes(_obj(document_ast.get("root"), "document_ast.root")):
        locator = _str(node.get("locator"), "document node locator")
        if locator in result:
            raise ValueError(f"duplicate document node locator: {locator}")
        result[locator] = node
    return result


def _default_document_validator(document_ast: Mapping[str, Any]) -> Any:
    from .document_io import document_ast_from_dict

    return document_ast_from_dict(document_ast)


def _validate_producer(value: Any) -> Mapping[str, Any]:
    producer = _obj(value, "producer")
    _keys(producer, PRODUCER_FIELDS, "producer")
    if producer["schema"] != PRODUCER_SCHEMA:
        raise ValueError(f"producer.schema must be {PRODUCER_SCHEMA}")
    for field in PRODUCER_FIELDS - {"command_options"}:
        _str(producer[field], f"producer.{field}")
    if not re.fullmatch(r"[0-9a-f]{40}", producer["commit_sha"]):
        raise ValueError("producer.commit_sha must be a full lowercase Git commit SHA")
    for field in ("engine_sha256", "wrapper_sha256"):
        if not _sha256(producer[field]):
            raise ValueError(f"producer.{field} must be a lowercase SHA-256")
    _obj(producer["command_options"], "producer.command_options")
    return producer


def _known_locators(bundle: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], set[str]]:
    document_ast = _obj(bundle["document_ast"], "document_ast")
    nodes = document_node_index(document_ast)
    known = set(nodes)
    for node in nodes.values():
        alias = _obj(node.get("attributes", {}), "node attributes").get("target_locator")
        if isinstance(alias, str) and alias:
            known.add(alias)
    for table in _arr(bundle["tables"], "tables"):
        locator = _obj(table, "table").get("locator")
        if isinstance(locator, str):
            known.add(locator)
    return nodes, known


def validate_nfpa13_bundle_contract(
    value: Mapping[str, Any], *, document_validator: DocumentValidator | None = None
) -> dict[str, Any]:
    bundle = _obj(value, "NFPA 13 bundle")
    _keys(bundle, TOP_FIELDS, "NFPA 13 bundle")
    if bundle["schema"] != BUNDLE_SCHEMA:
        raise ValueError(f"NFPA 13 bundle schema must be {BUNDLE_SCHEMA}")
    producer = _validate_producer(bundle["producer"])
    source_meta = _obj(bundle["source"], "source")
    if source_meta.get("artifact_id") != ARTIFACT_ID:
        raise ValueError(f"source.artifact_id must be {ARTIFACT_ID}")
    if not _sha256(_str(source_meta.get("source_pdf_sha256"), "source.source_pdf_sha256")):
        raise ValueError("source.source_pdf_sha256 must be a lowercase SHA-256")

    document_ast = _obj(bundle["document_ast"], "document_ast")
    (document_validator or _default_document_validator)(document_ast)
    source_text = _str(document_ast.get("source_text"), "document_ast.source_text")
    nodes, known = _known_locators(bundle)

    relations = _arr(bundle["relations"], "relations")
    for index, raw in enumerate(relations):
        label = f"relations[{index}]"
        relation = _obj(raw, label)
        _keys(relation, RELATION_FIELDS, label)
        source_locator = _str(relation["source_locator"], f"{label}.source_locator")
        target_locator = _str(relation["target_locator"], f"{label}.target_locator")
        target_domain = _str(relation["target_domain"], f"{label}.target_domain")
        target_artifact = relation["target_artifact_id"]
        resolved = relation["resolved"]
        if source_locator not in known or not isinstance(resolved, bool):
            raise ValueError(f"{label} has invalid source or resolved state")
        if target_domain not in TARGET_DOMAINS:
            raise ValueError(f"{label}.target_domain is unsupported")
        _span(relation["evidence"], f"{label}.evidence", source_text, allow_none=True)
        if target_domain == "internal":
            if target_artifact != ARTIFACT_ID or not resolved or target_locator not in known:
                raise ValueError(f"{label} has invalid internal target")
        elif target_domain == "external_standard":
            if not isinstance(target_artifact, str) or not target_locator.startswith("external:"):
                raise ValueError(f"{label} external-standard target lacks stable identity")
            if not resolved:
                raise ValueError(f"{label} external-standard target must be resolved")
        else:
            if target_artifact is not None:
                raise ValueError(f"{label} unspecified-document target must not guess an artifact")
            if resolved:
                raise ValueError(f"{label} unspecified-document target cannot be resolved")

    semantics = _arr(bundle["semantic_annotations"], "semantic_annotations")
    for index, raw in enumerate(semantics):
        label = f"semantic_annotations[{index}]"
        annotation = _obj(raw, label)
        _keys(annotation, SEMANTIC_FIELDS, label)
        if annotation["source_locator"] not in known:
            raise ValueError(f"{label}.source_locator does not exist")
        if annotation["method"] != "lexical-deterministic":
            raise ValueError(f"{label}.method must be lexical-deterministic")
        if not _sha256(_str(annotation["parser_revision"], f"{label}.parser_revision")):
            raise ValueError(f"{label}.parser_revision must be a lowercase SHA-256")
        if annotation["review_status"] not in REVIEW_STATES:
            raise ValueError(f"{label}.review_status is unsupported")
        _span(annotation["evidence"], f"{label}.evidence", source_text)

    explicit_annex = {
        locator
        for locator, node in nodes.items()
        if locator.startswith("A.")
        and _obj(node.get("attributes", {}), "node attributes").get("explicit") == "true"
        and _obj(node.get("attributes", {}), "node attributes").get("corresponds_to")
    }
    explains = [item for item in relations if item["type"] == "explains"]
    if {item["source_locator"] for item in explains} != explicit_annex:
        raise ValueError("Annex A explains relationships must match explicit correspondence nodes")
    if len(explains) != len(explicit_annex):
        raise ValueError("Annex A explains relationships must be unique")

    expected = {
        "relations": len(relations),
        "resolved_relations": sum(item["resolved"] for item in relations),
        "semantic_annotations": len(semantics),
        "explicit_annex_a_explains": len(explains),
        "external_standard_relations": sum(
            item["target_domain"] == "external_standard" for item in relations
        ),
        "unspecified_document_relations": sum(
            item["target_domain"] == "unspecified_document" for item in relations
        ),
    }
    statistics = _obj(bundle["statistics"], "statistics")
    for key, derived in expected.items():
        if statistics.get(key) != derived:
            raise ValueError(f"statistics.{key} must equal {derived}")
    if _obj(bundle["validation"], "validation").get("passed") is not True:
        raise ValueError("validation.passed must be true")
    return {
        "passed": True,
        "schema": BUNDLE_SCHEMA,
        "producer_commit": producer["commit_sha"],
        "document_nodes": len(nodes),
        **expected,
    }


def read_nfpa13_bundle(
    value: Mapping[str, Any], *, document_validator: DocumentValidator | None = None
) -> dict[str, Any]:
    clone = deepcopy(dict(value))
    validate_nfpa13_bundle_contract(clone, document_validator=document_validator)
    return clone


def _target_identity(relation: Mapping[str, Any]) -> tuple[str | None, str]:
    target = str(relation.get("target_locator", ""))
    if target.startswith("external:"):
        parts = target.split(":", 2)
        issuer = parts[1].upper() if len(parts) > 1 else "UNKNOWN"
        identifier = parts[2].upper() if len(parts) > 2 else target
        return f"standard:{issuer}:{identifier}", "external_standard"
    if relation.get("resolved"):
        return ARTIFACT_ID, "internal"
    return None, "unspecified_document"


def _external_relations(document_ast: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = str(document_ast["source_text"])
    results: list[dict[str, Any]] = []
    for node in walk_document_nodes(_obj(document_ast["root"], "document_ast.root")):
        if _obj(node.get("attributes", {}), "node attributes").get("owns_source") != "true":
            continue
        span = _obj(node["span"], "node span")
        base, text = int(span["start"]), str(span["text"])
        for match in EXTERNAL_STANDARD_RE.finditer(text):
            issuer = match.group("issuer").upper()
            identifier = " ".join(match.group("identifier").upper().split())
            slug = re.sub(r"[^A-Z0-9.]+", "-", identifier).strip("-").lower()
            results.append(
                {
                    "type": "references_external_standard",
                    "source_locator": str(node["locator"]),
                    "target_locator": f"external:{issuer.lower().replace('/', '-')}:{slug}",
                    "target_artifact_id": f"standard:{issuer}:{identifier}",
                    "target_domain": "external_standard",
                    "resolved": True,
                    "evidence": {
                        "start": base + match.start(),
                        "end": base + match.end(),
                        "text": source[base + match.start() : base + match.end()],
                    },
                }
            )
    return results


def _relation_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    evidence = item.get("evidence")
    start = evidence.get("start") if isinstance(evidence, Mapping) else None
    end = evidence.get("end") if isinstance(evidence, Mapping) else None
    return item.get("source_locator"), item.get("type"), item.get("target_locator"), start, end


def finalize_raw_nfpa13_bundle(
    raw_value: Mapping[str, Any],
    *,
    producer: Mapping[str, Any],
    document_validator: DocumentValidator | None = None,
    engine_validator: EngineValidator | None = None,
) -> dict[str, Any]:
    raw = _obj(raw_value, "raw NFPA 13 bundle")
    _keys(raw, TOP_FIELDS - {"producer"}, "raw NFPA 13 bundle")
    if raw.get("schema") != RAW_BUNDLE_SCHEMA:
        raise ValueError(f"raw NFPA 13 bundle schema must be {RAW_BUNDLE_SCHEMA}")
    _validate_producer(producer)
    bundle = deepcopy(dict(raw))
    document_ast = _obj(bundle["document_ast"], "document_ast")
    (document_validator or _default_document_validator)(document_ast)
    nodes = document_node_index(document_ast)

    relations: list[dict[str, Any]] = []
    for raw_relation in _arr(bundle["relations"], "relations"):
        relation = dict(_obj(raw_relation, "relation"))
        if relation.get("type") == "explains":
            source = nodes.get(str(relation.get("source_locator", "")))
            attributes = _obj(source.get("attributes", {}), "node attributes") if source else {}
            if attributes.get("explicit") != "true":
                continue
        relation["target_artifact_id"], relation["target_domain"] = _target_identity(relation)
        relations.append(relation)
    relations.extend(_external_relations(document_ast))
    relations = list({_relation_key(item): item for item in relations}.values())
    relations.sort(
        key=lambda item: (
            str(item["source_locator"]), str(item["type"]), str(item["target_locator"]),
            -1 if item["evidence"] is None else int(item["evidence"]["start"]),
        )
    )
    bundle["relations"] = relations

    semantics: list[dict[str, Any]] = []
    for raw_annotation in _arr(bundle["semantic_annotations"], "semantic_annotations"):
        annotation = dict(_obj(raw_annotation, "semantic annotation"))
        annotation.pop("confidence", None)
        annotation.update(
            method="lexical-deterministic",
            parser_revision=str(producer["wrapper_sha256"]),
            review_status="unreviewed",
        )
        semantics.append(annotation)
    semantics.sort(
        key=lambda item: (
            str(item["source_locator"]), int(item["evidence"]["start"]), str(item["type"])
        )
    )
    bundle["semantic_annotations"] = semantics
    bundle["schema"] = BUNDLE_SCHEMA
    bundle["producer"] = deepcopy(dict(producer))

    statistics = dict(_obj(bundle["statistics"], "statistics"))
    statistics.update(
        relations=len(relations),
        resolved_relations=sum(item["resolved"] for item in relations),
        semantic_annotations=len(semantics),
        explicit_annex_a_explains=sum(item["type"] == "explains" for item in relations),
        external_standard_relations=sum(
            item["target_domain"] == "external_standard" for item in relations
        ),
        unspecified_document_relations=sum(
            item["target_domain"] == "unspecified_document" for item in relations
        ),
    )
    bundle["statistics"] = statistics
    engine_report = (
        dict(engine_validator(bundle))
        if engine_validator
        else {"passed": bool(_obj(raw["validation"], "raw validation").get("passed"))}
    )
    bundle["validation"] = {
        "passed": bool(engine_report.get("passed")),
        "engine": engine_report,
        "contract": {"passed": True},
    }
    contract_report = validate_nfpa13_bundle_contract(
        bundle, document_validator=document_validator
    )
    bundle["validation"] = {
        "passed": bool(engine_report.get("passed")) and contract_report["passed"],
        "engine": engine_report,
        "contract": contract_report,
    }
    validate_nfpa13_bundle_contract(bundle, document_validator=document_validator)
    return bundle


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_review_registry(value: Mapping[str, Any]) -> dict[str, Any]:
    registry = _obj(value, "review registry")
    _keys(
        registry, {"schema", "source_pdf_sha256", "reviewed_at", "cases"},
        "review registry",
    )
    if registry["schema"] != REVIEW_REGISTRY_SCHEMA:
        raise ValueError(f"review registry schema must be {REVIEW_REGISTRY_SCHEMA}")
    if not _sha256(_str(registry["source_pdf_sha256"], "source_pdf_sha256")):
        raise ValueError("review registry source_pdf_sha256 must be a SHA-256")
    _str(registry["reviewed_at"], "reviewed_at")
    ids: set[str] = set()
    categories: set[str] = set()
    cases = _arr(registry["cases"], "cases")
    for index, raw_case in enumerate(cases):
        case = _obj(raw_case, f"cases[{index}]")
        _keys(case, {"id", "category", "locator", "assertion", "expected", "basis"}, f"cases[{index}]")
        case_id = _str(case["id"], f"cases[{index}].id")
        if case_id in ids:
            raise ValueError(f"duplicate review case id: {case_id}")
        ids.add(case_id)
        categories.add(_str(case["category"], f"cases[{index}].category"))
        for field in ("locator", "assertion", "basis"):
            _str(case[field], f"cases[{index}].{field}")
    required = {
        "normative-structure", "annex-structure", "definition", "table",
        "reference", "external-standard", "artifact-filtering",
    }
    missing = sorted(required - categories)
    if missing:
        raise ValueError(f"review registry lacks required categories: {missing}")
    return {"passed": True, "case_count": len(cases), "categories": sorted(categories)}
