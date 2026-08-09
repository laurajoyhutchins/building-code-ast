"""Deterministic publication-neutral provenance graph primitives.

Inputs are normalized relationships already established by source-family
adapters. This module does not discover references, select definition targets,
apply amendments, or copy protected source expression.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ._provenance_graph_projection import project_nodes, project_relationships
from ._provenance_graph_support import canonical_json, cyclic_components, required_string

PROVENANCE_GRAPH_VERSION = "provenance-graph/0.1.0"


def build_provenance_graph(
    *,
    publication: Mapping[str, object],
    nodes: Iterable[Mapping[str, object]],
    relationships: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Project normalized source-family evidence into one stable graph."""

    if not isinstance(publication, Mapping) or set(publication) != {
        "artifact_id",
        "edition_id",
    }:
        raise ValueError("publication must contain artifact_id and edition_id")
    normalized_publication = {
        "artifact_id": required_string(
            publication["artifact_id"], "publication.artifact_id"
        ),
        "edition_id": required_string(
            publication["edition_id"], "publication.edition_id"
        ),
    }
    projected_nodes = project_nodes(normalized_publication, nodes)
    edges, diagnostics, adjacency = project_relationships(
        normalized_publication,
        projected_nodes,
        relationships,
    )
    cycles = [
        {"state": "cyclic", "node_ids": component}
        for component in cyclic_components(adjacency)
    ]
    diagnostics.extend(
        {"state": "cyclic", "node_ids": item["node_ids"]} for item in cycles
    )
    diagnostics.sort(key=canonical_json)
    return {
        "schema_version": PROVENANCE_GRAPH_VERSION,
        "publication": normalized_publication,
        "nodes": sorted(projected_nodes.values(), key=lambda item: str(item["id"])),
        "edges": sorted(edges, key=lambda item: str(item["id"])),
        "diagnostics": diagnostics,
        "cycles": cycles,
    }


def serialize_provenance_graph(graph: Mapping[str, object]) -> str:
    """Serialize a projected graph to canonical deterministic JSON."""

    return canonical_json(graph)
