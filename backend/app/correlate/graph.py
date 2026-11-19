"""Evidence graph (§3.7): nodes are findings (plus evidence and the platform profile), edges are rules."""
from __future__ import annotations

import networkx as nx

from .rules import Edge, F, describe

VIEW_W, VIEW_H = 420, 230
COLUMNS = {"video": (70, 0), "audio": (70, 1), "cross-modal": (190, None), "image": (300, 0), "text": (300, 1), "profile": (392, None)}
ABBR = {"video": "VID", "audio": "AUD", "cross-modal": "XM", "image": "IMG", "text": "TXT", "profile": "WA", "evidence": "EV"}


def build(findings: list[F], edges: list[Edge], ev_kinds: dict[str, str]) -> nx.DiGraph:
    g = nx.DiGraph()
    by_id = {f.finding_id: f for f in findings}
    for e in edges:
        for node in (e.source, e.target):
            if node in g:
                continue
            if node in by_id:
                g.add_node(node, modality=by_id[node].modality, label=node, kind="finding")
            elif node == "PRF":
                g.add_node(node, modality="profile", label="platform", kind="profile")
            else:
                g.add_node(node, modality=ev_kinds.get(node, "evidence"), label=f"{node} {ev_kinds.get(node, '')}".strip(), kind="evidence")
        g.add_edge(e.source, e.target, rule_id=e.rule_id, relation=e.relation, weak=e.weak)
    return g


def layout(g: nx.DiGraph) -> dict[str, tuple[int, int]]:
    """Deterministic column layout in the UI's 420×230 view box, grouped by modality."""
    groups: dict[tuple[int, int | None], list[str]] = {}
    for n, d in sorted(g.nodes(data=True)):
        x, half = COLUMNS.get(d["modality"], (190, None))
        groups.setdefault((x, half), []).append(n)
    pos = {}
    for (x, half), nodes in groups.items():
        top, bottom = (25, VIEW_H - 45) if half is None else ((25, VIEW_H / 2 - 20) if half == 0 else (VIEW_H / 2 + 10, VIEW_H - 45))
        for i, n in enumerate(nodes):
            y = (top + bottom) / 2 if len(nodes) == 1 else top + (bottom - top) * i / (len(nodes) - 1)
            pos[n] = (int(x), int(round(y + 20)))
    return pos


def export(findings: list[F], edges: list[Edge], ev_kinds: dict[str, str]) -> dict:
    g = build(findings, edges, ev_kinds)
    pos = layout(g)
    nodes = [{"id": n, "abbr": ABBR.get(d["modality"], "EV"), "label": d["label"], "kind": d["kind"],
              "modality": d["modality"], "x": pos[n][0], "y": pos[n][1]} for n, d in sorted(g.nodes(data=True))]
    rules: dict[str, dict] = {}
    for e in edges:
        r = rules.setdefault(e.rule_id + ("w" if e.weak else ""), describe(e) | {"edges": []})
        r["edges"].append([e.source, e.target])
        if e.note not in r["links"]:
            r["links"] += f"; {e.note}"
    return {"nodes": nodes, "edges": [{"from": e.source, "to": e.target, "rule": e.rule_id, "relation": e.relation,
                                       "weak": e.weak} for e in edges],
            "rules": sorted(rules.values(), key=lambda r: r["id"])}
