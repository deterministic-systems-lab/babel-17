// intent: Your task is to implement an algorithm to check if a graph is Bipartite (2-colorable) and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/bipartite_check/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Option<T> = Some(value: T) | None

datatype Graph = Graph(adj: seq<seq<int>>)

// Helper predicates/functions for the Graph datatype
ghost predicate well_formed(g: Graph) {
  forall u: int, i: int :: 
    0 <= u < |g.adj| && 0 <= i < |g.adj[u]| 
    ==> 
    0 <= g.adj[u][i] < |g.adj|
}

ghost function size(g: Graph): int {
  |g.adj|
}

// --- Basic Graph Definitions ---

ghost predicate has_edge(g: Graph, u: int, v: int) {
  exists i: int :: 
    0 <= u < |g.adj| 
    && 0 <= i < |g.adj[u]| 
    && g.adj[u][i] == v
}

// Bipartite (2-Coloring) Definitions
// A coloring is valid if no two connected nodes share the same color.
// We represent colors as booleans (false=ColorA, true=ColorB).
ghost predicate is_valid_coloring(g: Graph, colors: seq<bool>) {
  && |colors| == size(g)
  && (forall u: int, v: int :: 
        has_edge(g, u, v) 
        ==> 
        // In Dafny, we must ensure indices are within bounds for valid access
        0 <= u < |colors| && 0 <= v < |colors| && colors[u] != colors[v])
}

// Helper to state that a graph IS bipartite (exists some valid coloring)
ghost predicate is_bipartite(g: Graph) {
  exists colors: seq<bool> :: is_valid_coloring(g, colors)
}

// Bipartite Check (2-Coloring)
// Functional Correctness:
// - If Bipartite: Returns Some(colors).
// - If Not: Returns None.
//== signature
method check_bipartite(graph: Graph) returns (res: Option<seq<bool>>)
  requires well_formed(graph)
  ensures match res {
    case Some(colors) => is_valid_coloring(graph, colors)
    case None => !is_bipartite(graph)
  }
//== solution
