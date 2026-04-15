"""Handler for constellation_finder endpoint."""

import math
from itertools import permutations
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional


def euclidean_dist(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Calculate Euclidean distance between two 3D points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)


class UnionFind:
    """Union-Find data structure with path compression and union by rank."""
    
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n
    
    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x: int, y: int) -> bool:
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True


def cluster_stars(stars: List[dict], max_dist: float) -> List[List[int]]:
    """
    Cluster stars by connectivity using Union-Find.
    
    Args:
        stars: List of star dictionaries with 'name', 'x', 'y', 'z'
        max_dist: Maximum distance threshold for connecting stars
        
    Returns:
        List of clusters, each cluster is a list of star indices
    """
    n = len(stars)
    if n == 0:
        return []
    
    uf = UnionFind(n)
    
    # For each pair of stars, union if within max_dist
    for i in range(n):
        pi = (stars[i]["x"], stars[i]["y"], stars[i]["z"])
        for j in range(i + 1, n):
            pj = (stars[j]["x"], stars[j]["y"], stars[j]["z"])
            dist = euclidean_dist(pi, pj)
            if dist <= max_dist:
                uf.union(i, j)
    
    # Group stars by root
    clusters_map: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        root = uf.find(i)
        clusters_map[root].append(i)
    
    return list(clusters_map.values())


def build_mst(cluster_indices: List[int], stars: List[dict]) -> List[Tuple[int, int, float]]:
    """
    Build Minimum Spanning Tree for a cluster using Kruskal's algorithm.
    
    Args:
        cluster_indices: List of star indices in the cluster
        stars: Full list of star dictionaries
        
    Returns:
        List of MST edges as (idx_in_cluster, idx_in_cluster, distance)
    """
    if len(cluster_indices) < 2:
        return []
    
    # Generate all edges with distances
    edges: List[Tuple[float, int, int]] = []
    cache: Dict[Tuple[int, int], float] = {}
    
    for i in range(len(cluster_indices)):
        for j in range(i + 1, len(cluster_indices)):
            idx_i, idx_j = cluster_indices[i], cluster_indices[j]
            pi = (stars[idx_i]["x"], stars[idx_i]["y"], stars[idx_i]["z"])
            pj = (stars[idx_j]["x"], stars[idx_j]["y"], stars[idx_j]["z"])
            
            key = (min(idx_i, idx_j), max(idx_i, idx_j))
            if key not in cache:
                cache[key] = euclidean_dist(pi, pj)
            
            dist = cache[key]
            edges.append((dist, i, j))
    
    # Sort edges by weight
    edges.sort(key=lambda x: x[0])
    
    # Kruskal's algorithm
    uf = UnionFind(len(cluster_indices))
    mst_edges: List[Tuple[int, int, float]] = []
    
    for dist, i, j in edges:
        if uf.union(i, j):
            mst_edges.append((i, j, dist))
            if len(mst_edges) == len(cluster_indices) - 1:
                break
    
    return mst_edges


def get_edge_signature(mst_edges: List[Tuple[int, int, float]]) -> List[Tuple[int, int, int]]:
    """
    Get edge signature with ranks based on sorted order by length.
    
    Args:
        mst_edges: List of MST edges (u, v, distance)
        
    Returns:
        List of (u, v, rank) tuples
    """
    if not mst_edges:
        return []
    
    # Sort edges by distance and assign ranks
    indexed_edges = sorted(enumerate(mst_edges), key=lambda x: x[1][2])
    
    # Create mapping from original index to rank
    edge_rank = {}
    for rank, (orig_idx, _) in enumerate(indexed_edges):
        edge_rank[orig_idx] = rank
    
    # Return edges with ranks
    result = []
    for i, (u, v, _) in enumerate(mst_edges):
        result.append((u, v, edge_rank[i]))
    
    return result


def check_isomorphism(
    target_edges: List[Tuple[int, int, float]],
    candidate_edges: List[Tuple[int, int, float]],
    target_names: List[str],
    candidate_names: List[str]
) -> Optional[List[str]]:
    """
    Check if candidate MST is isomorphic to target constellation.
    
    Args:
        target_edges: Target constellation edges (from, to, distance)
        candidate_edges: Candidate MST edges (u, v, distance)
        target_names: Names for target vertices [0..n-1]
        candidate_names: Names for candidate vertices
        
    Returns:
        List of matched star names if exactly one isomorphism found, None otherwise
    """
    if len(target_edges) != len(candidate_edges):
        return None
    
    if len(target_edges) == 0:
        return None  # Need at least one edge
    
    # Determine number of vertices
    target_vertices = set()
    for u, v, _ in target_edges:
        target_vertices.add(u)
        target_vertices.add(v)
    n = len(target_vertices)
    
    candidate_vertices = set()
    for u, v, _ in candidate_edges:
        candidate_vertices.add(u)
        candidate_vertices.add(v)
    
    if len(candidate_vertices) != n:
        return None
    
    # Build adjacency info for degree-based pruning
    target_degrees = defaultdict(int)
    for u, v, _ in target_edges:
        target_degrees[u] += 1
        target_degrees[v] += 1
    
    candidate_degrees = defaultdict(int)
    for u, v, _ in candidate_edges:
        candidate_degrees[u] += 1
        candidate_degrees[v] += 1
    
    # Get edge signatures (ranks)
    target_sig = get_edge_signature(target_edges)
    candidate_sig = get_edge_signature(candidate_edges)
    
    # Build target edge map: frozenset{u,v} -> rank
    target_edge_map: Dict[frozenset, int] = {}
    for u, v, rank in target_sig:
        target_edge_map[frozenset([u, v])] = rank
    
    # Build candidate edge map: frozenset{u,v} -> rank
    candidate_edge_map: Dict[frozenset, int] = {}
    for u, v, rank in candidate_sig:
        candidate_edge_map[frozenset([u, v])] = rank
    
    # Find valid permutations with degree preservation
    # Group candidate vertices by degree
    candidate_by_degree: Dict[int, List[int]] = defaultdict(list)
    for v in range(n):
        candidate_by_degree[candidate_degrees[v]].append(v)
    
    target_by_degree: Dict[int, List[int]] = defaultdict(list)
    for v in range(n):
        target_by_degree[target_degrees[v]].append(v)
    
    # Check if degree sequences match
    if sorted(target_degrees.values()) != sorted(candidate_degrees.values()):
        return None
    
    matches_found = []
    
    # Generate permutations with degree-preserving constraint
    def generate_degree_preserving_perms():
        """Generate permutations that preserve vertex degrees."""
        degrees = sorted(target_by_degree.keys())
        
        # For each degree level, we need to map target vertices to candidate vertices
        mappings = []
        for deg in degrees:
            targets = target_by_degree[deg]
            candidates = candidate_by_degree[deg]
            mappings.append((targets, candidates))
        
        # Generate all combinations of permutations for each degree group
        from itertools import product
        
        perms_for_groups = []
        for targets, candidates in mappings:
            # All bijections between targets and candidates of same degree
            perms_for_groups.append(list(permutations(candidates)))
        
        for combo in product(*perms_for_groups):
            # Build full permutation
            perm = [0] * n
            for i, (targets, _) in enumerate(mappings):
                for j, t in enumerate(targets):
                    perm[t] = combo[i][j]
            yield perm
    
    for perm in generate_degree_preserving_perms():
        # Map candidate edges through permutation
        mapped_edges_ok = True
        mapped_edge_ranks = {}
        
        for u, v, rank in candidate_sig:
            pu, pv = perm[u], perm[v]
            edge_key = frozenset([pu, pv])
            
            if edge_key not in target_edge_map:
                mapped_edges_ok = False
                break
            
            if target_edge_map[edge_key] != rank:
                mapped_edges_ok = False
                break
            
            mapped_edge_ranks[edge_key] = rank
        
        if not mapped_edges_ok:
            continue
        
        # Verify all target edges are covered
        if len(mapped_edge_ranks) != len(target_edge_map):
            continue
        
        # Valid isomorphism found
        matched_names = [candidate_names[perm[i]] for i in range(n)]
        matches_found.append(matched_names)
        
        # Early exit if more than one match
        if len(matches_found) > 1:
            return None
    
    if len(matches_found) == 1:
        return matches_found[0]
    
    return None


def process_constellation_finder(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process constellation_finder request.
    
    Args:
        data: The validated input data containing:
            - stars: List of star dicts with name, x, y, z
            - cluster_params: min_size, max_size, max_neighbor_distance
            - target_constellation: edges with from, to, distance
            
    Returns:
        Response dictionary with found field and optionally matched_stars
    """
    stars = data["stars"]
    cluster_params = data["cluster_params"]
    target_constellation = data["target_constellation"]
    
    # Step 1: Cluster stars by connectivity
    clusters = cluster_stars(stars, cluster_params["max_neighbor_distance"])
    
    # Step 2: Filter clusters by size
    min_size = cluster_params["min_size"]
    max_size = cluster_params["max_size"]
    valid_clusters = [c for c in clusters if min_size <= len(c) <= max_size]
    
    # Step 3: Build MST for each valid cluster and compare with target
    target_edges = [(e["from"], e["to"], e["distance"]) for e in target_constellation["edges"]]
    
    # Determine number of vertices in target
    target_vertices = set()
    for e in target_edges:
        target_vertices.add(e[0])
        target_vertices.add(e[1])
    target_n = len(target_vertices)
    
    # Target names are just indices 0..n-1
    target_names = list(range(target_n))
    
    matches = []
    
    for cluster in valid_clusters:
        if len(cluster) != target_n:
            continue
        
        # Build MST for this cluster
        mst = build_mst(cluster, stars)
        
        # Get candidate star names
        candidate_names = [stars[i]["name"] for i in cluster]
        
        # Check isomorphism
        result = check_isomorphism(target_edges, mst, target_names, candidate_names)
        
        if result is not None:
            matches.append(result)
    
    # Step 4: Form response
    if len(matches) == 1:
        return {"found": True, "matched_stars": matches[0]}
    else:
        return {"found": False}
