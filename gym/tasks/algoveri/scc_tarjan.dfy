// intent: our task is to implement Tarjan's Algorithm to find the Strongly Connected Components (SCCs) of a directed graph and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/scc_tarjan/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Graph = Graph(adj: seq<seq<int>>)

// Helper predicates/functions for the Graph datatype
ghost function size(g: Graph): int {
    |g.adj|
}

ghost function view(g: Graph): seq<seq<int>> {
    g.adj
}

ghost predicate well_formed(g: Graph) {
    forall u: int, i: int :: 
        0 <= u < |g.adj| && 0 <= i < |g.adj[u]| 
        ==> 
        0 <= g.adj[u][i] < |g.adj|
}

// --- GRAPH PATH DEFINITIONS ---

ghost predicate has_edge(g: seq<seq<int>>, u: int, v: int) {
    exists i: int :: 
        0 <= u < |g| && 0 <= i < |g[u]| 
        && g[u][i] == v
}

ghost predicate path_valid(g: seq<seq<int>>, p: seq<int>) {
    forall k: int :: 0 <= k < |p| - 1 ==>
        has_edge(g, p[k], p[k+1])
}

ghost predicate has_path(g: seq<seq<int>>, u: int, v: int) {
    exists p: seq<int> {:trigger path_valid(g, p)} :: 
        |p| > 0 && p[0] == u && p[|p| - 1] == v 
        && path_valid(g, p)
}

// --- SCC DEFINITIONS ---

ghost predicate seq_contains(s: seq<int>, v: int) {
    exists i: int :: 0 <= i < |s| && s[i] == v
}

// 1. Internal Strong Connectivity
ghost predicate is_strongly_connected(g: seq<seq<int>>, comp: seq<int>) {
    && |comp| > 0
    && (forall i: int :: 0 <= i < |comp| ==> 0 <= comp[i] < |g|)
    && (forall u: int, v: int :: 
            seq_contains(comp, u) && seq_contains(comp, v) ==> 
            (has_path(g, u, v) && has_path(g, v, u))
       )
}

// 2. Partition Property
ghost predicate is_covered(sccs: seq<seq<int>>, u: int) {
    exists i: int :: 0 <= i < |sccs| && seq_contains(sccs[i], u)
}

ghost predicate are_disjoint(sccs: seq<seq<int>>) {
    forall i: int, j: int, u: int :: 
        0 <= i < |sccs| && 0 <= j < |sccs| && i != j ==>
        !(seq_contains(sccs[i], u) && seq_contains(sccs[j], u))
}

ghost predicate is_partition(g: seq<seq<int>>, sccs: seq<seq<int>>) {
    && are_disjoint(sccs)
    && (forall u: int :: 0 <= u < |g| ==> is_covered(sccs, u))
}

// 3. Maximality (Condensation DAG Property)

// NEW HELPER: Is there a path from ANY node in component i to ANY node in component j?
// FIXED: Added requires clause to prevent index out of range
ghost predicate scc_has_path(g: seq<seq<int>>, sccs: seq<seq<int>>, i: int, j: int) 
    requires 0 <= i < |sccs|
    requires 0 <= j < |sccs|
{
    exists u: int, v: int :: 
        seq_contains(sccs[i], u) 
        && seq_contains(sccs[j], v) 
        && has_path(g, u, v)
}

ghost predicate is_maximal_scc_structure(g: seq<seq<int>>, sccs: seq<seq<int>>) {
    forall i: int, j: int :: 
        0 <= i < |sccs| && 0 <= j < |sccs| && i != j ==>
        // If there is a path from SCC i to SCC j, there must NOT be a path back
        (scc_has_path(g, sccs, i, j) ==> !scc_has_path(g, sccs, j, i))
}

ghost predicate is_valid_scc_result(g: seq<seq<int>>, sccs: seq<seq<int>>) {
    && is_partition(g, sccs)
    && (forall i: int :: 0 <= i < |sccs| ==> is_strongly_connected(g, sccs[i]))
    && is_maximal_scc_structure(g, sccs)
}

// Bounds Check
ghost predicate size_bounded(g: seq<seq<int>>) {
    |g| <= 1000
}

// PROBLEM: Tarjan's SCC Algorithm
//== signature
method find_sccs(graph: Graph) returns (sccs: seq<seq<int>>)
    requires well_formed(graph)
    requires size_bounded(view(graph))
    ensures is_valid_scc_result(view(graph), sccs)
//== solution
