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


def get_edge_signature(mst_edges: List[Tuple[int, int, float]]) -> Dict[Tuple[int, int], int]:
    """
    Get edge signature with ranks based on sorted order by length.
    
    Args:
        mst_edges: List of MST edges (u, v, distance)
        
    Returns:
        Dict mapping normalized edge key (min_u_v, max_u_v) to rank
    """
    if not mst_edges:
        return {}
    
    # Sort edges by distance and assign ranks
    sorted_edges = sorted(mst_edges, key=lambda e: e[2])
    
    # Create mapping from normalized edge key to rank
    signature = {}
    for rank, (u, v, _) in enumerate(sorted_edges):
        key = (min(u, v), max(u, v))
        signature[key] = rank
    
    return signature


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
    
    # Special case: single edge - any bijection works
    if len(target_edges) == 1 and len(candidate_edges) == 1:
        # For n=2, just return the candidate names in order
        # Any permutation is valid since there's only one edge
        return candidate_names[:len(target_names)]
    
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
    
    # Generate all permutations for small n, or degree-preserving for larger
    def generate_perms():
        """Generate all permutations or degree-preserving permutations."""
        if n <= 2:
            # For n=2, generate all permutations explicitly
            for perm in permutations(range(n)):
                yield list(perm)
        else:
            # For n >= 3, use degree-preserving optimization
            degrees = sorted(target_by_degree.keys())
            
            mappings = []
            for deg in degrees:
                targets = target_by_degree[deg]
                candidates = candidate_by_degree[deg]
                mappings.append((targets, candidates))
            
            from itertools import product
            
            perms_for_groups = []
            for targets, candidates in mappings:
                perms_for_groups.append(list(permutations(candidates)))
            
            for combo in product(*perms_for_groups):
                perm = [0] * n
                for i, (targets, _) in enumerate(mappings):
                    for j, t in enumerate(targets):
                        perm[t] = combo[i][j]
                yield perm
    
    for perm in generate_perms():
        # Check structural match and rank match
        struct_match = True
        rank_match = True
        
        for tu, tv, _ in target_edges:
            # Map target vertices through permutation
            cu, cv = perm[tu], perm[tv]
            key_target = (min(tu, tv), max(tu, tv))
            key_candidate = (min(cu, cv), max(cu, cv))
            
            # Structure: edge must exist in candidate
            if key_candidate not in candidate_sig:
                struct_match = False
                break
            
            # Order: ranks must match
            if target_sig[key_target] != candidate_sig[key_candidate]:
                rank_match = False
                break
        
        if struct_match and rank_match:
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
    # Use from_ (Python attribute name) instead of "from" (JSON key)
    target_edges = [(e["from_"], e["to"], e["distance"]) for e in target_constellation["edges"]]
    
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
