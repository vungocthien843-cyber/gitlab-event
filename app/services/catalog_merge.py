"""
catalog_merge.py — gộp nhiều ParsedFile (mỗi file 1 lần parse_single) thành
một graph document duy nhất, scope.kind = "merged".

Luật merge, đúng những gì đã thống nhất khi review từng file riêng:
  - Node: dedupe theo id. Chỉ file tự khai báo mới được ghi `spec`.
          Hai file cùng nhận là chủ một node -> lỗi (không âm thầm ghi đè).
  - Edge: gộp thẳng, dedupe theo id (đọc trùng 1 file 2 lần thì không nhân đôi).
  - Diagnostics: cộng dồn theo file, cộng thêm 3 loại phát hiện chỉ có được
    khi nhìn toàn cục: cạnh mồ côi (provider/publisher vắng mặt) và chu trình
    phụ thuộc xuyên nhiều file.

Không phụ thuộc thứ tự đọc file — xem tests ở cuối file.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from app.services.catalog_to_graph import (
    OWNED_VIA_RELATION,
    SCHEMA_VERSION,
    SPEC_VERSION,
    Diagnostics,
    ParsedFile,
    _edge_sort_key,
    build_nx_graph,
)


def _merge_node(existing: dict[str, Any] | None, incoming: dict[str, Any],
               d: Diagnostics) -> dict[str, Any]:
    """Hợp nhất 2 bản khai của cùng 1 node id. Không bao giờ ghi đè âm thầm:
    nếu cả hai đều tự nhận là chủ (declared_by khác nhau, cả hai non-null),
    giữ bản đến trước và bắn lỗi — không đoán ai đúng."""
    if existing is None:
        return dict(incoming)

    if existing["declared_by"] is None:
        return dict(incoming) if incoming["declared_by"] else existing
    if incoming["declared_by"] is None:
        return existing
    if existing["declared_by"] == incoming["declared_by"]:
        return existing  # cùng 1 file, không phải xung đột thật

    code = "DUPLICATE_DECLARATION" if existing["kind"] == "component" else "AMBIGUOUS_OWNER"
    d.err(code,
          f"{existing['id']} được khai là chủ bởi cả "
          f"'{existing['declared_by']}' và '{incoming['declared_by']}'",
          subject=existing["id"], source=incoming["declared_by"])
    return existing


def _check_orphan_edges(nodes: dict[str, Any], edges: list[dict[str, Any]],
                        d: Diagnostics) -> None:
    """Sau khi gộp toàn cục: node nào bị subscribe/consume nhưng không ai
    provides/publishes vào nó — chỉ phát hiện được khi nhìn nhiều file cùng lúc."""
    provided_targets = {e["target"] for e in edges if e["relation"] in OWNED_VIA_RELATION.values()}
    for node_id, node in nodes.items():
        if node["kind"] not in ("api", "topic") or node["declared_by"] is not None:
            continue
        if node_id in provided_targets:
            continue
        consumers = [e["declared_by"] for e in edges
                    if e["target"] == node_id and e["relation"] in ("consumes", "subscribes")]
        if not consumers:
            continue
        code = "API_NO_PROVIDER" if node["kind"] == "api" else "TOPIC_NO_PUBLISHER"
        verb = "gọi" if node["kind"] == "api" else "subscribe"
        d.warn(code,
               f"{node_id} được {len(consumers)} component {verb} tới nhưng "
               "chưa có ai provides/publishes",
               subject=node_id)


def merge_documents(parsed: list[ParsedFile]) -> dict[str, Any]:
    d = Diagnostics()
    nodes: dict[str, Any] = {}
    edges: list[dict[str, Any]] = []
    seen_edge_ids: set[str] = set()
    sources: list[dict[str, Any]] = []

    for p in parsed:
        sources.append({"file": p.filename, "root": p.root_id})

        for e in p.diagnostics.errors:
            e.source = e.source or p.filename
            d.errors.append(e)
        for w in p.diagnostics.warnings:
            w.source = w.source or p.filename
            d.warnings.append(w)

        for node_id, node in p.nodes.items():
            nodes[node_id] = _merge_node(nodes.get(node_id), node, d)

        for e in p.edges:
            if e["id"] in seen_edge_ids:
                continue
            seen_edge_ids.add(e["id"])
            edges.append(e)

    if nodes:
        g = build_nx_graph(nodes, edges)
        for cycle in nx.simple_cycles(g):
            if len(cycle) > 1:
                d.warn("DEPENDENCY_CYCLE",
                       "Chu trình phụ thuộc xuyên file: " + " -> ".join(cycle + [cycle[0]]),
                       subject=cycle[0])
        _check_orphan_edges(nodes, edges, d)

    ordered_nodes = {k: nodes[k] for k in sorted(nodes)}
    ordered_edges = sorted(edges, key=_edge_sort_key)

    def _diag_key(i):
        return (i.source or "", i.code, i.subject or "", i.message)

    d.errors.sort(key=_diag_key)
    d.warnings.sort(key=_diag_key)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "specVersion": SPEC_VERSION,
        "scope": {
            "kind": "merged",
            "root": None,
            "sources": sorted(sources, key=lambda s: s["file"]),
        },
        "nodes": ordered_nodes,
        "edges": ordered_edges,
        "diagnostics": d.as_dict(),
    }
