"""Union-find (disjoint-set) with path compression.

Inlined from `minhash-dedup-practice/src/dedup_pipeline.py` so SomaliWeb v1's
pipeline is self-contained — no sibling-repo dependency.

Used by Phase 4 to cluster pairs of documents whose verified Jaccard exceeds
τ = 0.80. Each connected component becomes one near-duplicate cluster, after
which the keep-rule (default: ``longest``) picks a single survivor per cluster.

Why union-find rather than pairwise decisions
---------------------------------------------
Suppose A↔B (J = 0.85), B↔C (J = 0.85), A↔C (J = 0.78 < τ). Pairwise logic
keeps A and C as separate documents and only removes B. Union-find treats the
component {A, B, C} as one cluster, applying the keep-rule consistently.
Triangles (and bigger components) need graph-level logic.
"""

from __future__ import annotations

from collections import defaultdict


class UnionFind:
    """Nearly-linear union-find with path compression. Auto-adds nodes on find."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path compression
            x = self.parent[x]
        return x

    def union(self, x: str, y: str) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry

    def components(self) -> list[set[str]]:
        groups: dict[str, set[str]] = defaultdict(set)
        for x in list(self.parent):
            groups[self.find(x)].add(x)
        return list(groups.values())
