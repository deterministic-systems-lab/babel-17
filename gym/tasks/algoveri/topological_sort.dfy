// intent: Your task is to implement a Topological Sort algorithm and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/topological_sort/dafny_spec.dfy (Apache-2.0)
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

// Topological Sort Definitions
// A sequence is a valid topological sort if:
// a. It is a permutation of all nodes in the graph.
// b. For every edge u -> v, u appears BEFORE v in the sequence.
ghost predicate is_topological_ordering(g: Graph, order: seq<int>) {
  // Must contain all nodes exactly once (permutation of 0..N-1)
  && |order| == size(g)
  && (forall n: int :: 0 <= n < size(g) ==> n in order)
  && (forall i: int, j: int :: 0 <= i < j < |order| ==> order[i] != order[j])
  
  // The core topological property: No edge goes "backwards"
  // If u appears at index i, and v appears at index j, and i > j, then NO edge u -> v.
  && (forall i: int, j: int :: 
        0 <= j < i < |order| 
        ==> 
        !has_edge(g, order[i], order[j]))
}

// Topological Sort
// Functional Correctness:
// - If DAG: Returns Some(order) where order satisfies topo constraints.
// - If Cycle: Returns None.
//== signature
method topological_sort(graph: Graph) returns (res: Option<seq<int>>)
  requires well_formed(graph)
  ensures match res {
    case Some(order) => 
      // 1. The graph must be acyclic
      !graph_has_cycle(graph) 
      // 2. The returned vector is a valid ordering
      && is_topological_ordering(graph, order)
    case None => 
      // Must contain a cycle if sort is impossible
      graph_has_cycle(graph)
  }
//== solution
