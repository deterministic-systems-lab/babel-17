// intent: Your task is to implement a Depth First Search (DFS) algorithm to determine reachability in a directed graph and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/dfs/dafny_spec.dfy (Apache-2.0)
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

// --- Graph Theory Definitions ---

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

// 3. Reachability 
ghost predicate reachable(g: Graph, start: int, end: int) {
  exists p: seq<int> {:trigger is_path(g, p)} :: 
    is_path(g, p) 
    && p[0] == start 
    && p[|p| - 1] == end
}

// Depth First Search (Reachability)
//== signature
method dfs_check_reachability(graph: Graph, start: int, target: int) returns (res: bool)
  requires well_formed(graph)
  requires 0 <= start < size(graph)
  requires 0 <= target < size(graph)
  ensures res == reachable(graph, start, target)
//== solution
