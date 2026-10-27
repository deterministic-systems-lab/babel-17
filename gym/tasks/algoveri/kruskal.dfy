// intent: Your task is to implement Kruskal's Algorithm to find the Minimum Spanning Tree (MST) of a connected, undirected, weighted graph and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/kruskal/dafny_spec.dfy (Apache-2.0)
//== preamble
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
    (forall u: int, i: int, j: int :: 
        0 <= u < |g.adj| 
        && 0 <= i < |g.adj[u]| 
        && 0 <= j < |g.adj[u]| 
        && i != j
        ==> 
        g.adj[u][i].0 != g.adj[u][j].0)
}

// --- MST Graph Theory Definitions ---

type Edge = (int, int, int)

ghost predicate has_edge(g: seq<seq<(int, int)>>, u: int, v: int, w: int) {
    exists i: int :: 
        0 <= u < |g| 
        && 0 <= i < |g[u]| 
        && g[u][i].0 == v 
        && g[u][i].1 == w
}

ghost predicate are_valid_edges(g: seq<seq<(int, int)>>, edges: seq<Edge>) {
    forall k: int :: 0 <= k < |edges| ==> 
        has_edge(g, edges[k].0, edges[k].1, edges[k].2)
}

ghost predicate edge_in_set(edges: seq<Edge>, u: int, v: int) {
    exists e_idx: int :: 
        0 <= e_idx < |edges| 
        && (
            (edges[e_idx].0 == u && edges[e_idx].1 == v) || 
            (edges[e_idx].0 == v && edges[e_idx].1 == u)
        )
}

// Isolate the "path validity" check for edge sets
ghost predicate path_follows_edges(edges: seq<Edge>, p: seq<int>) {
    forall k: int :: 0 <= k < |p| - 1 ==> 
        edge_in_set(edges, p[k], p[k+1])
}

// 3. Spanning
ghost predicate edges_connected(edges: seq<Edge>, u: int, v: int) {
    exists p: seq<int> {:trigger path_follows_edges(edges, p)} :: 
        |p| > 0 && p[0] == u && p[|p| - 1] == v &&
        path_follows_edges(edges, p)
}

ghost predicate is_spanning(g: seq<seq<(int, int)>>, edges: seq<Edge>) {
    forall u: int, v: int :: 
        0 <= u < |g| && 0 <= v < |g| 
        ==> edges_connected(edges, u, v)
}

// Tree
ghost predicate is_spanning_tree(g: seq<seq<(int, int)>>, edges: seq<Edge>) {
    && are_valid_edges(g, edges)
    && is_spanning(g, edges)
    && |edges| == |g| - 1
}

// Total Weight
ghost function total_weight(edges: seq<Edge>): int 
    decreases |edges|
{
    if |edges| == 0 then 0
    else edges[0].2 + total_weight(edges[1..])
}

// Minimum Spanning Tree
ghost predicate is_mst(g: seq<seq<(int, int)>>, edges: seq<Edge>) {
    && is_spanning_tree(g, edges)
    && (forall other: seq<Edge> {:trigger is_spanning_tree(g, other)} :: 
            is_spanning_tree(g, other) ==> total_weight(edges) <= total_weight(other))
}

// --- Connectivity Helpers ---

ghost predicate graph_has_any_edge(g: seq<seq<(int, int)>>, u: int, v: int) {
    exists i: int :: 
        0 <= u < |g| 
        && 0 <= i < |g[u]| 
        && g[u][i].0 == v
}

// Isolate the "path validity" check for the graph
ghost predicate path_follows_graph(g: seq<seq<(int, int)>>, p: seq<int>) {
    forall k: int :: 0 <= k < |p| - 1 ==> 
        graph_has_any_edge(g, p[k], p[k+1])
}

ghost predicate nodes_have_path(g: seq<seq<(int, int)>>, u: int, v: int) {
    exists p: seq<int> {:trigger path_follows_graph(g, p)} :: 
        |p| > 0 && p[0] == u && p[|p| - 1] == v &&
        path_follows_graph(g, p)
}

ghost predicate graph_is_connected(g: seq<seq<(int, int)>>) {
    forall u: int, v: int :: 
        0 <= u < |g| && 0 <= v < |g| 
        ==> nodes_have_path(g, u, v)
}

// Bounds Check
ghost predicate weights_bounded(g: seq<seq<(int, int)>>) {
    |g| <= 100_000 && 
    (forall u: int, v: int, w: int :: 
        has_edge(g, u, v, w)
        ==> (w >= -100_000 && w <= 100_000))
}

// Kruskal's Algorithm
//== signature
method kruskal_mst(graph: WeightedGraph) returns (edges: seq<Edge>)
    requires well_formed(graph)
    requires size(graph) > 0
    requires weights_bounded(view(graph))
    requires graph_is_connected(view(graph))
    ensures is_mst(view(graph), edges)
//== solution
