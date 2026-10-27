// intent: Your task is to implement an algorithm to detect if a directed graph (unweighted) contains a cycle and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/cycle_detection/dafny_spec.dfy (Apache-2.0)
//== preamble
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

ghost predicate is_path(g: Graph, p: seq<int>) {
  |p| > 0 &&
  (forall i: int :: 0 <= i < |p| - 1 
      ==> has_edge(g, p[i], p[i+1]))
}

// A cycle is a path that starts and ends at the same node.
ghost predicate is_cycle(g: Graph, p: seq<int>) {
  is_path(g, p)
  && |p| > 1
  && p[0] == p[|p| - 1]
}

ghost predicate graph_has_cycle(g: Graph) {
  exists p: seq<int> :: is_cycle(g, p)
}

// Cycle Detection (Whole Graph)
// Functional Correctness:
// - true  <==> The graph contains at least one cycle.
// - false <==> The graph is a DAG (Directed Acyclic Graph).
//== signature
method has_cycle(graph: Graph) returns (res: bool)
  requires well_formed(graph)
  ensures res == graph_has_cycle(graph)
//== solution
