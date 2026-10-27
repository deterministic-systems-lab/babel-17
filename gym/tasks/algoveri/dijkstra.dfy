// intent: Your task is to implement Dijkstra's Algorithm for single-source shortest paths and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/dijkstra/dafny_spec.dfy (Apache-2.0)
//== preamble
// Define Option datatype since it is not built-in
datatype Option<T> = Some(value: T) | None

datatype WeightedGraph = WeightedGraph(
    // Adjacency list: adj[u] contains list of (neighbor, weight)
    // u ranges from 0 to size - 1.
    // Weight is int (was i64 in Verus)
    adj: seq<seq<(int, int)>>
)

// Helper predicates/functions for the Graph datatype
ghost function size(g: WeightedGraph): int {
    |g.adj|
}

ghost function view(g: WeightedGraph): seq<seq<(int, int)>> {
    g.adj
}

ghost predicate well_formed(g: WeightedGraph) {
    // 1. Basic Bounds checks
    (forall u: int, i: int :: 
        0 <= u < |g.adj| && 0 <= i < |g.adj[u]| 
        ==> 
        0 <= g.adj[u][i].0 < |g.adj|)
    &&
    // 2. SIMPLE GRAPH CONSTRAINT: No multigraphs allowed.
    // For any node u, all outgoing edges must have distinct targets.
    // This ensures get_edge_weight is deterministic.
    (forall u: int, i: int, j: int :: 
        0 <= u < |g.adj| 
        && 0 <= i < |g.adj[u]| 
        && 0 <= j < |g.adj[u]| 
        && i != j
        ==> 
        g.adj[u][i].0 != g.adj[u][j].0)
}

// --- Weighted Graph Definitions ---

ghost predicate has_edge(g: seq<seq<(int, int)>>, u: int, v: int, w: int) {
    exists i: int :: 
        0 <= u < |g| 
        && 0 <= i < |g[u]| 
        && g[u][i].0 == v
        && g[u][i].1 == w
}

ghost predicate connected(g: seq<seq<(int, int)>>, u: int, v: int) {
    exists w: int :: has_edge(g, u, v, w)
}

ghost predicate is_path(g: seq<seq<(int, int)>>, p: seq<int>) {
    |p| > 0
    && (forall i: int :: 
          0 <= i < |p| - 1 ==> connected(g, p[i], p[i+1]))
}

// Helper to safely extract weight using the epsilon operator
// Because well_formed enforces unique targets, this is uniquely defined for valid edges.
ghost function get_edge_weight(g: seq<seq<(int, int)>>, u: int, v: int): int {
    if exists w :: has_edge(g, u, v, w) then
        var w :| has_edge(g, u, v, w); w
    else 
        0 
}

ghost function path_weight(g: seq<seq<(int, int)>>, p: seq<int>): int 
    decreases |p|
{
    if |p| < 2 then 
        0
    else 
        // Recursive step: weight of prefix + weight of last edge
        path_weight(g, p[..|p| - 1]) + get_edge_weight(g, p[|p| - 2], p[|p| - 1])
}

ghost predicate is_shortest_dist(g: seq<seq<(int, int)>>, start: int, end: int, d: int) {
    && (exists p: seq<int> {:trigger is_path(g, p)} :: 
            is_path(g, p) 
            && p[0] == start 
            && p[|p| - 1] == end 
            && path_weight(g, p) == d
       )
    && (forall p: seq<int> {:trigger is_path(g, p)} :: 
            is_path(g, p) && p[0] == start && p[|p| - 1] == end 
            ==> path_weight(g, p) >= d
       )
}

ghost predicate weights_non_negative(g: seq<seq<(int, int)>>) {
    forall u: int, v: int, w: int :: 
        has_edge(g, u, v, w) ==> w >= 0
}

// We enforce hard limits:
// 1. Graph size <= 100,000
// 2. Edge weights <= 100,000 (absolute value)
ghost predicate weights_and_size_bounded(g: seq<seq<(int, int)>>) {
    && |g| <= 100_000
    && (forall u: int, v: int, w: int :: 
            has_edge(g, u, v, w) ==> (w >= -100_000 && w <= 100_000))
}

// Dijkstra's Algorithm
//== signature
method dijkstra_shortest_paths(graph: WeightedGraph, start: int) returns (res: seq<Option<int>>)
    requires well_formed(graph)
    requires 0 <= start < size(graph)
    requires weights_non_negative(view(graph))
    requires weights_and_size_bounded(view(graph))
    ensures |res| == size(graph)
    ensures forall v: int :: 0 <= v < size(graph) ==> 
        match res[v] {
            case Some(d) => 
                is_shortest_dist(view(graph), start, v, d)
            case None => 
                forall p: seq<int> {:trigger is_path(view(graph), p)} :: 
                    is_path(view(graph), p) && p[0] == start && p[|p| - 1] == v ==> false
        }
//== solution
