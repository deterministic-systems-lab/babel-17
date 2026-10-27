// intent: Your task is to implement an algorithm to find the Maximum Bipartite Matching and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/max_matching/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype BipartiteGraph = BipartiteGraph(
    // Number of nodes on the Left (U) and Right (V)
    left_size: int,
    right_size: int,
    
    // Adjacency list: adj[u] contains list of neighbors v in Right set.
    // u ranges from 0 to left_size - 1.
    // v ranges from 0 to right_size - 1.
    adj: seq<seq<int>>
)

// Helper predicates/functions for the Graph datatype
ghost predicate well_formed(g: BipartiteGraph) {
    // Basic non-negative constraints for sizes (implicit in usize, explicit in int)
    g.left_size >= 0 && g.right_size >= 0
    // 1. adj length must match left_size
    && |g.adj| == g.left_size 
    && 
    // 2. All neighbors must be valid indices in Right set
    (forall u: int, i: int :: 
        0 <= u < |g.adj| && 0 <= i < |g.adj[u]| 
        ==> 
        0 <= g.adj[u][i] < g.right_size)
}

// --- MATCHING DEFINITIONS ---

// A matching is a set of edges (u, v) where u in Left, v in Right
type Matching = set<(int, int)>

// 1. Edges must exist in the graph
// Note: We pass the raw adjacency list (seq<seq<int>>) to match the 'view' concept
ghost predicate matching_valid_edges(adj: seq<seq<int>>, m: Matching) {
    forall edge: (int, int) :: edge in m ==> 
        (exists i: int :: 
            0 <= edge.0 < |adj| 
            && 0 <= i < |adj[edge.0]| 
            && adj[edge.0][i] == edge.1)
}

// 2. Disjointness
// Since edges are strictly (Left -> Right), we simply check:
// - No two edges share the same Left node (e1.0 != e2.0)
// - No two edges share the same Right node (e1.1 != e2.1)
ghost predicate is_disjoint(m: Matching) {
    forall e1: (int, int), e2: (int, int) :: 
        e1 in m && e2 in m && e1 != e2 ==>
        (e1.0 != e2.0 && e1.1 != e2.1)
}

ghost predicate is_matching(adj: seq<seq<int>>, m: Matching) {
    matching_valid_edges(adj, m)
    && is_disjoint(m)
}

// 3. Maximality
ghost predicate is_max_matching(adj: seq<seq<int>>, m: Matching) {
    is_matching(adj, m)
    && (forall other: Matching :: 
            is_matching(adj, other) ==> |m| >= |other|)
}

// Bounds Check (Safety)
ghost predicate size_bounded(g: BipartiteGraph) {
    g.left_size <= 1000 && g.right_size <= 1000
}

// PROBLEM: Maximum Bipartite Matching
// Input: A bipartite graph defined by sizes and Left->Right adjacency.
// Output: The size of the maximum matching.
//== signature
method max_bipartite_matching(graph: BipartiteGraph) returns (size: int)
    requires well_formed(graph)
    requires size_bounded(graph)
    ensures size >= 0
    ensures exists m: Matching :: 
            is_max_matching(graph.adj, m) 
            && |m| == size
//== solution
