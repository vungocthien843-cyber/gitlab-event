"""
catalog_to_graph.py — catalog-info.yaml  ->  {stem}.graph.json

Pipeline:
    YAML (pyyaml, strict loader)
      -> validate          (schema + format rules, gom hết lỗi)
      -> canonicalize      (ref -> node id + relation)
      -> graph             (networkX DiGraph, chiều = chiều phụ thuộc)
      -> document          (nodes dict + edges list + diagnostics)
      -> JSON file

Usage:
    python catalog_to_graph.py catalog.yaml
    python catalog_to_graph.py catalog.yaml -o build/graph.json
    python catalog_to_graph.py catalog.yaml --no-timestamp --quiet
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

SCHEMA_VERSION = "1.1"
SPEC_VERSION = "vsf-idp.io/v2"

# ─────────────────────────────────────────────────────────────────────────────
# Rules
# ─────────────────────────────────────────────────────────────────────────────

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")          # system, namespace, spec.id
REF_NAME_RE = re.compile(r"^[a-z][a-z0-9._-]*$")     # name-part: topic có dấu '.'
REF_RE = re.compile(r"^(?P<kind>[A-Za-z]+):(?P<namespace>[^/]+)/(?P<name>.+)$")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")

DOMAIN_MAX_LEN = 128

API_TYPES = {"service", "gateway"}
CATALOG_ONLY_TYPES = {
    "worker", "batch", "job", "library", "website", "mobile-app",
    "data-pipeline", "function", "plugin", "tool", "documentation", "other",
}
ALL_TYPES = API_TYPES | CATALOG_ONLY_TYPES

MEMBER_ROLES = {"techlead", "maintainer", "member"}

# ref kind -> (node kind, relation).  Đây là bảng ngữ nghĩa trung tâm:
# kind trong yaml vừa quyết định loại node, vừa quyết định tên cạnh.
REF_KIND_MAP: dict[str, tuple[str, str]] = {
    "system":       ("system",    "partOf"),
    "component":    ("component", "dependsOn"),
    "resource":     ("resource",  "dependsOn"),
    "providesApis": ("api",       "provides"),
    "consumesApis": ("api",       "consumes"),
    "publishesTo":  ("topic",     "publishes"),
    "consumesFrom": ("topic",     "subscribes"),
}

NODE_KINDS = {"system", "component", "resource", "api", "topic"}

# Trong JSON, source LUÔN là component khai báo (đọc xuôi: "X provides Y").
# Nhưng chiều PHỤ THUỘC thì ngược lại ở 2 quan hệ: api tồn tại nhờ component,
# consumer của topic phụ thuộc vào publisher. Bảng này chỉ dùng khi dựng
# networkX graph để nx.ancestors() trả đúng "ai chết theo nếu X chết".
RELATION_REVERSED = {"provides", "publishes"}

# Quyền sở hữu node — quyết định trường declared_by:
#   component → file tự khai báo chính nó (metadata + spec.id)
#   api       → component nào 'provides' nó. Hai component cùng provides = lỗi.
#   topic     → KHÔNG ai sở hữu: nhiều producer cùng publish vào một topic là hợp lệ.
#   resource  → KHÔNG ai sở hữu: hạ tầng cần catalog riêng, ngoài phạm vi file này.
#   system    → KHÔNG ai sở hữu: cần file khai báo cấp system.
# 3 kind cuối có declared_by = null vĩnh viễn, không bao giờ cảnh báo về chuyện đó.
OWNED_VIA_RELATION = {"api": "provides"}
UNOWNABLE_KINDS = {"system", "resource", "topic"}
SPEC_BEARING_KINDS = {"component"}

KNOWN_PROTOCOLS = {
    "rest": "REST", "grpc": "gRPC", "kafka": "Kafka",
    "websocket": "WebSocket", "graphql": "GraphQL", "soap": "SOAP",
}


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Issue:
    code: str
    message: str
    yaml_path: str | None = None
    subject: str | None = None
    source: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d = {"code": self.code, "message": self.message}
        for k in ("subject", "yaml_path", "source"):
            if getattr(self, k) is not None:
                d[k] = getattr(self, k)
        return d


@dataclass
class Diagnostics:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def err(self, code: str, message: str, **kw: Any) -> None:
        self.errors.append(Issue(code, message, **kw))

    def warn(self, code: str, message: str, **kw: Any) -> None:
        self.warnings.append(Issue(code, message, **kw))

    def as_dict(self) -> dict[str, Any]:
        return {
            "errors": [i.as_dict() for i in self.errors],
            "warnings": [i.as_dict() for i in self.warnings],
        }


class FatalError(Exception):
    """Lỗi khiến không parse tiếp được (YAML hỏng, root sai kiểu)."""

    def __init__(self, issue: Issue) -> None:
        self.issue = issue
        super().__init__(issue.message)


# ─────────────────────────────────────────────────────────────────────────────
# Strict YAML loader — pyyaml mặc định nuốt duplicate key, ở đây thì reject
# ─────────────────────────────────────────────────────────────────────────────

class StrictLoader(yaml.SafeLoader):
    pass


def _no_duplicate_keys(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False):
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def load_yaml(text: str) -> dict[str, Any]:
    try:
        doc = yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        raise FatalError(Issue("YAML_SYNTAX", str(exc), yaml_path="$")) from exc
    if not isinstance(doc, dict):
        raise FatalError(Issue("TYPE_MISMATCH", "Root của file phải là mapping",
                               yaml_path="$"))
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# Field-level validators
# ─────────────────────────────────────────────────────────────────────────────

def _require_str(value: Any, path: str, d: Diagnostics) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        d.err("REQUIRED", "Field bắt buộc, không được rỗng", yaml_path=path)
        return None
    if not isinstance(value, str):
        d.err("TYPE_MISMATCH", f"Phải là string, nhận {type(value).__name__}",
              yaml_path=path)
        return None
    return value.strip()


def _check_slug(value: str, path: str, d: Diagnostics) -> None:
    if not SLUG_RE.match(value):
        d.err("INVALID_FORMAT",
              f"'{value}' không khớp ^[a-z][a-z0-9-]*$ "
              "(chữ thường, không space, không chữ hoa)", yaml_path=path)


def _check_freetext(value: str, path: str, d: Diagnostics,
                    max_len: int | None = None) -> None:
    if CONTROL_CHARS_RE.search(value):
        d.err("CONTROL_CHARS", "Không được chứa control characters (U+0000–001F, DEL)",
              yaml_path=path)
    if max_len and len(value) > max_len:
        d.err("TOO_LONG", f"Tối đa {max_len} ký tự, hiện tại {len(value)}",
              yaml_path=path)


# ─────────────────────────────────────────────────────────────────────────────
# Canonicalize: ref string -> node id + relation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParsedRef:
    node_id: str
    node_kind: str
    namespace: str
    name: str
    relation: str


def parse_ref(raw: str, path: str, d: Diagnostics) -> ParsedRef | None:
    m = REF_RE.match(raw)
    if not m:
        d.err("INVALID_REF", f"'{raw}' phải có dạng '{{kind}}:{{namespace}}/{{name}}'",
              yaml_path=path)
        return None

    kind, ns, name = m.group("kind"), m.group("namespace"), m.group("name")

    if kind not in REF_KIND_MAP:
        d.err("UNKNOWN_KIND",
              f"kind '{kind}' không hợp lệ. Cho phép: {', '.join(sorted(REF_KIND_MAP))}",
              yaml_path=path)
        return None
    if not SLUG_RE.match(ns):
        d.err("INVALID_FORMAT", f"namespace '{ns}' trong ref không khớp ^[a-z][a-z0-9-]*$",
              yaml_path=path)
        return None
    if not REF_NAME_RE.match(name):
        d.err("INVALID_FORMAT", f"name '{name}' trong ref không hợp lệ", yaml_path=path)
        return None

    node_kind, relation = REF_KIND_MAP[kind]
    return ParsedRef(f"{node_kind}:{ns}/{name}", node_kind, ns, name, relation)


# ─────────────────────────────────────────────────────────────────────────────
# Parse 1 file -> nodes / edges
# ─────────────────────────────────────────────────────────────────────────────

def parse_document(doc: dict[str, Any], filename: str,
                   d: Diagnostics) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    """Trả về (nodes, edges, root_id). Node self luôn đứng đầu nodes."""

    if doc.get("specVersion") != SPEC_VERSION:
        d.err("UNSUPPORTED_VERSION",
              f"Chỉ hỗ trợ specVersion '{SPEC_VERSION}', nhận '{doc.get('specVersion')}'",
              yaml_path="specVersion", source=filename)

    meta = doc.get("metadata")
    if not isinstance(meta, dict):
        raise FatalError(Issue("TYPE_MISMATCH", "metadata phải là mapping",
                               yaml_path="metadata", source=filename))
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise FatalError(Issue("TYPE_MISMATCH", "spec phải là mapping",
                               yaml_path="spec", source=filename))

    # ── metadata ─────────────────────────────────────────────────────────────
    domain = _require_str(meta.get("domain"), "metadata.domain", d)
    if domain:
        _check_freetext(domain, "metadata.domain", d, DOMAIN_MAX_LEN)

    system = _require_str(meta.get("system"), "metadata.system", d)
    if system:
        _check_slug(system, "metadata.system", d)

    namespace = _require_str(meta.get("namespace"), "metadata.namespace", d)
    if namespace:
        _check_slug(namespace, "metadata.namespace", d)

    # ── spec ─────────────────────────────────────────────────────────────────
    stype = _require_str(spec.get("type"), "spec.type", d)
    if stype and stype not in ALL_TYPES:
        d.err("INVALID_ENUM",
              f"type '{stype}' không hợp lệ. Cho phép: {', '.join(sorted(ALL_TYPES))}",
              yaml_path="spec.type")
        stype = None
    if stype == "job":
        d.warn("TYPE_ALIAS", "'job' là alias của 'batch' (Backstage compat)",
               yaml_path="spec.type")

    sid = _require_str(spec.get("id"), "spec.id", d)
    if sid:
        _check_slug(sid, "spec.id", d)

    display_name = _require_str(spec.get("name"), "spec.name", d)
    if display_name:
        _check_freetext(display_name, "spec.name", d)

    description = spec.get("description")
    if description is not None:
        description = _require_str(description, "spec.description", d)
        if description:
            _check_freetext(description, "spec.description", d)

    # ── owners.members ───────────────────────────────────────────────────────
    owners = spec.get("owners") or {}
    members_raw = owners.get("members") if isinstance(owners, dict) else None
    members: list[dict[str, str]] = []

    if not isinstance(members_raw, list) or not members_raw:
        d.err("REQUIRED", "Cần ít nhất 1 member với role techlead",
              yaml_path="spec.owners.members")
    else:
        seen_users: set[str] = set()
        for i, m in enumerate(members_raw):
            p = f"spec.owners.members[{i}]"
            if not isinstance(m, dict):
                d.err("TYPE_MISMATCH", "Member phải là mapping {user, role}", yaml_path=p)
                continue
            user = _require_str(m.get("user"), f"{p}.user", d)
            role = _require_str(m.get("role"), f"{p}.role", d)
            if role and role not in MEMBER_ROLES:
                d.err("INVALID_ENUM",
                      f"role '{role}' không hợp lệ. Cho phép: {', '.join(sorted(MEMBER_ROLES))}",
                      yaml_path=f"{p}.role")
                role = None
            if user and user.lower() in seen_users:
                d.err("DUPLICATE", f"User '{user}' bị khai báo trùng", yaml_path=f"{p}.user")
                continue
            if user:
                seen_users.add(user.lower())
            if user and role:
                members.append({"user_email": user, "role": role})

        if members and not any(m["role"] == "techlead" for m in members):
            d.err("MISSING_TECHLEAD", "Phải có ít nhất 1 member với role 'techlead'",
                  yaml_path="spec.owners.members")

    # ── review ───────────────────────────────────────────────────────────────
    review = spec.get("review") or {}
    branch = None
    if not isinstance(review, dict):
        d.err("TYPE_MISMATCH", "review phải là mapping", yaml_path="spec.review")
    else:
        branch = _require_str(review.get("branch"), "spec.review.branch", d)

    # ── node self ────────────────────────────────────────────────────────────
    root_id = f"component:{namespace}/{sid}" if namespace and sid else None
    nodes: dict[str, Any] = {}

    if root_id:
        nodes[root_id] = {
            "id": root_id,
            "kind": "component",
            "namespace": namespace,
            "name": sid,
            "declared_by": filename,
            "spec": {
                "service_key": f"{system}.{sid}" if system else None,
                "display_name": display_name,
                "description": description,
                "system": system,
                "domain": domain,
                "type": stype,
                "has_api_surface": stype in API_TYPES,
                "review": {"branch": branch},
                "members": members,
            },
        }

    # ── topology -> edges + stub nodes ───────────────────────────────────────
    topology = spec.get("topology") or []
    edges: list[dict[str, Any]] = []

    if not isinstance(topology, list):
        d.err("TYPE_MISMATCH", "topology phải là list", yaml_path="spec.topology")
        topology = []

    seen_edge_ids: set[str] = set()

    for i, entry in enumerate(topology):
        p = f"spec.topology[{i}]"
        if not isinstance(entry, dict):
            d.err("TYPE_MISMATCH", "Entry phải là mapping {ref, protocol?, reason?}",
                  yaml_path=p)
            continue

        raw_ref = _require_str(entry.get("ref"), f"{p}.ref", d)
        if not raw_ref:
            continue
        ref = parse_ref(raw_ref, f"{p}.ref", d)
        if not ref or not root_id:
            continue

        if ref.node_id == root_id:
            d.err("SELF_REFERENCE", f"'{raw_ref}' trỏ về chính component này",
                  yaml_path=f"{p}.ref")
            continue

        edge_id = f"{root_id}|{ref.relation}|{ref.node_id}"
        if edge_id in seen_edge_ids:
            d.err("DUPLICATE_EDGE", f"Cạnh '{ref.relation}' tới '{ref.node_id}' bị khai báo trùng",
                  yaml_path=f"{p}.ref")
            continue
        seen_edge_ids.add(edge_id)

        protocol = entry.get("protocol")
        if protocol is not None:
            protocol = str(protocol).strip()
            protocol = KNOWN_PROTOCOLS.get(protocol.lower(), protocol)

        reason = entry.get("reason")
        reason = str(reason).strip() if reason is not None else None

        # Node đích — chỉ tạo nếu chưa tồn tại, không bao giờ ghi đè.
        # Quyền sở hữu gán ở pass riêng phía dưới.
        if ref.node_id not in nodes:
            nodes[ref.node_id] = {
                "id": ref.node_id,
                "kind": ref.node_kind,
                "namespace": ref.namespace,
                "name": ref.name,
                "declared_by": None,
                "spec": None,
            }

        edges.append({
            "id": edge_id,
            "source": root_id,
            "target": ref.node_id,
            "relation": ref.relation,
            "protocol": protocol,
            "reason": reason,
            "declared_by": root_id,
            "yaml_path": p,
        })

    # ── Gán quyền sở hữu ─────────────────────────────────────────────────────
    _assign_ownership(nodes, edges, filename, d)

    # ── cross-field consistency ──────────────────────────────────────────────
    _check_consistency(nodes, edges, system, sid, stype, root_id, namespace, d)

    return nodes, edges, root_id


def _assign_ownership(nodes: dict[str, Any], edges: list[dict[str, Any]],
                      filename: str, d: Diagnostics) -> None:
    """Component đã tự sở hữu lúc tạo. Ở đây gán chủ cho api qua cạnh 'provides'.
    topic / resource / system cố tình để trống — xem OWNED_VIA_RELATION."""
    for e in edges:
        target = nodes[e["target"]]
        if OWNED_VIA_RELATION.get(target["kind"]) != e["relation"]:
            continue

        if target["declared_by"] is None:
            target["declared_by"] = filename
            d.warn("AWAITING_SPEC_INGEST",
                   f"{target['id']} đã có chủ nhưng chưa có spec — "
                   "chờ ingest registry.yaml + openapi.yaml",
                   subject=target["id"], yaml_path=e["yaml_path"], source=filename)
        elif target["declared_by"] != filename:
            d.err("AMBIGUOUS_OWNER",
                  f"{target['id']} được provides bởi cả "
                  f"'{target['declared_by']}' và '{filename}'",
                  subject=target["id"], yaml_path=e["yaml_path"], source=filename)


def _check_consistency(nodes: dict[str, Any], edges: list[dict[str, Any]],
                       system: str | None, sid: str | None, stype: str | None,
                       root_id: str | None, namespace: str | None,
                       d: Diagnostics) -> None:
    system_edges = [e for e in edges if e["relation"] == "partOf"]
    if not system_edges:
        d.warn("MISSING_SYSTEM_REF",
               f"Chưa khai báo 'system:{namespace}/{system}' (quan hệ partOf)",
               yaml_path="spec.topology")
    for e in system_edges:
        if system and nodes[e["target"]]["name"] != system:
            d.err("SYSTEM_MISMATCH",
                  f"'{e['target']}' không khớp metadata.system = '{system}'",
                  yaml_path=e["yaml_path"], subject=e["target"])

    provides = [e for e in edges if e["relation"] == "provides"]
    if stype in API_TYPES and not provides:
        d.warn("MISSING_PROVIDES_API",
               f"type '{stype}' có API surface nhưng chưa khai báo providesApis",
               yaml_path="spec.topology")
    if stype in CATALOG_ONLY_TYPES and provides:
        d.err("UNEXPECTED_PROVIDES_API",
              f"type '{stype}' không có API surface nhưng khai báo providesApis",
              yaml_path=provides[0]["yaml_path"])
    for e in provides:
        if sid and nodes[e["target"]]["name"] != sid:
            d.warn("PROVIDES_API_MISMATCH",
                   f"API '{nodes[e['target']]['name']}' khác spec.id '{sid}'",
                   yaml_path=e["yaml_path"], subject=e["target"])


# ─────────────────────────────────────────────────────────────────────────────
# networkX — chiều cạnh = chiều phụ thuộc (source phụ thuộc target)
# ─────────────────────────────────────────────────────────────────────────────

def build_nx_graph(nodes: dict[str, Any], edges: list[dict[str, Any]]) -> nx.DiGraph:
    g = nx.DiGraph()
    for node_id, node in nodes.items():
        g.add_node(node_id, **{k: v for k, v in node.items() if k != "id"})
    for e in edges:
        src, tgt = e["source"], e["target"]
        if e["relation"] in RELATION_REVERSED:
            src, tgt = tgt, src
        g.add_edge(src, tgt, relation=e["relation"], protocol=e["protocol"],
                   declared_by=e["declared_by"])
    return g


def check_cycles(g: nx.DiGraph, d: Diagnostics) -> None:
    for cycle in nx.simple_cycles(g):
        if len(cycle) > 1:
            d.warn("DEPENDENCY_CYCLE",
                   "Chu trình phụ thuộc: " + " -> ".join(cycle + [cycle[0]]),
                   subject=cycle[0])


# ─────────────────────────────────────────────────────────────────────────────
# Document assembly
# ─────────────────────────────────────────────────────────────────────────────

def assert_invariants(nodes: dict[str, Any], edges: list[dict[str, Any]]) -> None:
    """4 bất biến của schema — sai một cái là bug ở phía sinh, không phải input."""
    for key, node in nodes.items():
        assert key == node["id"], f"key '{key}' != node.id '{node['id']}'"
        assert node["kind"] in NODE_KINDS, f"node kind lạ: {node['kind']}"
        if node["spec"] is not None:
            assert node["kind"] in SPEC_BEARING_KINDS, \
                f"'{key}': kind '{node['kind']}' không được mang spec"
            assert node["declared_by"] is not None, \
                f"'{key}': có spec nhưng không có declared_by"
        if node["kind"] in UNOWNABLE_KINDS:
            assert node["declared_by"] is None, \
                f"'{key}': kind '{node['kind']}' không được có chủ sở hữu"
    for e in edges:
        assert e["source"] in nodes, f"edge source '{e['source']}' không có trong nodes"
        assert e["target"] in nodes, f"edge target '{e['target']}' không có trong nodes"


TOPOLOGY_INDEX_RE = re.compile(r"\[(\d+)\]")


def _edge_sort_key(edge: dict[str, Any]) -> tuple[str, int, str]:
    """Sắp theo (component khai báo, thứ tự dòng trong topology).
    Tất định như sắp theo id, nhưng đối chiếu với YAML lúc review MR thì dò được
    bằng mắt. Phần tử thứ 3 chỉ để phá hoà khi yaml_path thiếu chỉ số."""
    m = TOPOLOGY_INDEX_RE.search(edge.get("yaml_path") or "")
    return (edge["declared_by"] or "", int(m.group(1)) if m else 0, edge["id"])


@dataclass
class ParsedFile:
    """Kết quả parse 1 file, trước khi đóng gói scope — dùng lại được cho
    CLI (1 file), cho merge nhiều file, và cho API."""
    filename: str
    nodes: dict[str, Any]
    edges: list[dict[str, Any]]
    root_id: str | None
    diagnostics: Diagnostics


def parse_single(yaml_text: str, filename: str) -> ParsedFile:
    d = Diagnostics()
    try:
        doc = load_yaml(yaml_text)
        nodes, edges, root_id = parse_document(doc, filename, d)
    except FatalError as exc:
        d.errors.append(exc.issue)
        nodes, edges, root_id = {}, [], None

    if nodes and not d.errors:
        check_cycles(build_nx_graph(nodes, edges), d)
        assert_invariants(nodes, edges)

    return ParsedFile(filename, nodes, edges, root_id, d)


def build_document(yaml_text: str, filename: str,
                   timestamp: bool = True) -> dict[str, Any]:
    p = parse_single(yaml_text, filename)

    # Thứ tự tất định: node theo id, edge theo (file khai báo, thứ tự trong topology)
    ordered_nodes = {k: p.nodes[k] for k in sorted(p.nodes)}
    ordered_edges = sorted(p.edges, key=_edge_sort_key)

    out: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "specVersion": SPEC_VERSION,
    }
    if timestamp:
        out["generatedAt"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    out["scope"] = {
        "kind": "single",
        "root": p.root_id,
        "sources": [{"file": filename, "root": p.root_id}],
    }
    out["nodes"] = ordered_nodes
    out["edges"] = ordered_edges
    out["diagnostics"] = p.diagnostics.as_dict()
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Console summary
# ─────────────────────────────────────────────────────────────────────────────

def render_summary(out: dict[str, Any], out_path: Path) -> str:
    diag = out["diagnostics"]
    nodes, edges = out["nodes"], out["edges"]
    lines: list[str] = []

    if diag["errors"]:
        lines.append(f"FAILED — {len(diag['errors'])} lỗi")
        pad = max(len(e.get("yaml_path") or "-") for e in diag["errors"])
        for i, e in enumerate(diag["errors"], 1):
            lines.append(f"  {i:>2}. {(e.get('yaml_path') or '-').ljust(pad)}  "
                         f"{e['code']}: {e['message']}")
        return "\n".join(lines)

    by_kind: dict[str, int] = {}
    for n in nodes.values():
        by_kind[n["kind"]] = by_kind.get(n["kind"], 0) + 1
    by_rel: dict[str, int] = {}
    for e in edges:
        by_rel[e["relation"]] = by_rel.get(e["relation"], 0) + 1
    owned = sum(1 for n in nodes.values() if n["declared_by"])
    full = sum(1 for n in nodes.values() if n["spec"])

    lines.append(f"OK  {out['scope']['root']}")
    lines.append(f"    nodes  {len(nodes):>3}  ("
                 + ", ".join(f"{k} {v}" for k, v in sorted(by_kind.items()))
                 + f") — {full} đủ spec, {owned - full} chờ ingest, "
                 + f"{len(nodes) - owned} chưa có chủ")
    lines.append(f"    edges  {len(edges):>3}  ("
                 + ", ".join(f"{k} {v}" for k, v in sorted(by_rel.items())) + ")")
    if diag["warnings"]:
        lines.append(f"    warn   {len(diag['warnings']):>3}")
        for w in diag["warnings"]:
            lines.append(f"           {w['code']}: {w['message']}")
    lines.append(f"    -> {out_path}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="catalog-info.yaml -> graph JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ví dụ:\n"
               "  python catalog_to_graph.py catalog.yaml\n"
               "  python catalog_to_graph.py catalog.yaml -o build/graph.json\n"
               "  python catalog_to_graph.py catalog.yaml --no-timestamp\n")
    ap.add_argument("input", type=Path, help="file catalog-info.yaml")
    ap.add_argument("-o", "--output", type=Path,
                    help="file JSON đích (mặc định: {stem}.graph.json cạnh input)")
    ap.add_argument("--no-timestamp", action="store_true",
                    help="bỏ generatedAt để output tất định theo byte")
    ap.add_argument("--quiet", action="store_true", help="không in tóm tắt")
    args = ap.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    try:
        yaml_text = args.input.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Không tìm thấy file: {args.input}", file=sys.stderr)
        return 2

    out_path = args.output or args.input.with_suffix("").with_suffix(".graph.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out = build_document(yaml_text, args.input.name, timestamp=not args.no_timestamp)

    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if not args.quiet:
        print(render_summary(out, out_path))

    return 1 if out["diagnostics"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
