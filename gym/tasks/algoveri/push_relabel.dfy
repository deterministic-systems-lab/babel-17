// intent: Your task is to implement the Push-Relabel Algorithm to find the maximum flow in a directed graph and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/push_relabel/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype CapacityGraph = CapacityGraph(
    // Adjacency list: adj[u] contains list of (neighbor, capacity)
    // u ranges from 0 to size - 1.
    // Capacity is int (was i64 in Verus)
    adj: seq<seq<(int, int)>>
)

// Helper predicates/functions for the Graph datatype
ghost function size(g: CapacityGraph): int {
    |g.adj|
}

ghost function view(g: CapacityGraph): seq<seq<(int, int)>> {
    g.adj
}

ghost predicate well_formed(g: CapacityGraph) {
    // 1. Basic Bounds checks
    (forall u: int, i: int :: 
        0 <= u < |g.adj| && 0 <= i < |g.adj[u]| 
        ==> 
        0 <= g.adj[u][i].0 < |g.adj|)
    &&
    // 2. SIMPLE GRAPH CONSTRAINT: No multigraphs allowed.
    // For any node u, all outgoing edges must have distinct targets.
    // This is critical because FlowMap uses (u, v) as a key, which cannot distinguish parallel edges.
    (forall u: int, i: int, j: int :: 
        0 <= u < |g.adj| 
        && 0 <= i < |g.adj[u]| 
        && 0 <= j < |g.adj[u]| 
        && i != j
        ==> 
        g.adj[u][i].0 != g.adj[u][j].0)
}

// --- MAX FLOW THEORY ---

// 1. Basic Definitions
ghost predicate has_capacity(g: seq<seq<(int, int)>>, u: int, v: int, c: int) {
    exists i: int :: 
        0 <= u < |g| && 0 <= i < |g[u]| 
        && g[u][i].0 == v 
        && g[u][i].1 == c
}

type FlowMap = map<(int, int), int>

ghost function get_flow(f: FlowMap, u: int, v: int): int {
    if (u, v) in f then f[(u, v)] else 0
}

// 2. Capacity Constraint
ghost predicate respects_capacity(g: seq<seq<(int, int)>>, f: FlowMap) {
    forall u: int, v: int :: 
        (u, v) in f ==> (
            f[(u, v)] > 0 ==> (
                exists c: int :: has_capacity(g, u, v, c) && f[(u, v)] <= c
            )
        )
}

// 3. Flow Summation Helpers
ghost function sum_flow_out_recursive(g: seq<seq<(int, int)>>, f: FlowMap, u: int, idx: int): int
    decreases idx
{
    if idx <= 0 || u < 0 || u >= |g| then 
        0 
    else
        // Inlined 'neighbor' to fix syntax error
        if idx - 1 < |g[u]| then
            sum_flow_out_recursive(g, f, u, idx - 1) + get_flow(f, u, g[u][idx - 1].0)
        else 
            sum_flow_out_recursive(g, f, u, idx - 1)
}

ghost function sum_flow_in_recursive(g: seq<seq<(int, int)>>, f: FlowMap, u: int, v_idx: int): int
    decreases v_idx
{
    if v_idx <= 0 then
        0
    else
        sum_flow_in_recursive(g, f, u, v_idx - 1) + get_flow(f, v_idx - 1, u)
}

ghost function total_flow_out(g: seq<seq<(int, int)>>, f: FlowMap, u: int): int {
    if 0 <= u < |g| then 
        sum_flow_out_recursive(g, f, u, |g[u]|)
    else 0
}

ghost function total_flow_in(g: seq<seq<(int, int)>>, f: FlowMap, u: int): int {
    sum_flow_in_recursive(g, f, u, |g|)
}

// 4. Flow Conservation
ghost predicate is_conserved(g: seq<seq<(int, int)>>, f: FlowMap, s: int, t: int) {
    forall u: int :: 
        0 <= u < |g| && u != s && u != t 
        ==> total_flow_in(g, f, u) == total_flow_out(g, f, u)
}

// 5. Validity
ghost predicate is_valid_flow(g: seq<seq<(int, int)>>, f: FlowMap, s: int, t: int) {
    && respects_capacity(g, f)
    && is_conserved(g, f, s, t)
    // Non-negative flow constraint
    && (forall u: int, v: int :: (u, v) in f ==> f[(u, v)] >= 0)
}

// 6. Value of the Flow
ghost function flow_val(g: seq<seq<(int, int)>>, f: FlowMap, s: int): int {
    total_flow_out(g, f, s) - total_flow_in(g, f, s)
}

// 7. Global Optimality
ghost predicate is_max_flow(g: seq<seq<(int, int)>>, f: FlowMap, s: int, t: int) {
    && is_valid_flow(g, f, s, t)
    && (forall other: FlowMap {:trigger is_valid_flow(g, other, s, t)} :: 
            is_valid_flow(g, other, s, t) ==> flow_val(g, f, s) >= flow_val(g, other, s))
}

// 8. Bounds Check
ghost predicate capacities_bounded(g: seq<seq<(int, int)>>) {
    |g| <= 1000 &&
    (forall u: int, v: int, c: int :: 
         has_capacity(g, u, v, c) ==> (c >= 0 && c <= 100_000))
}

// PROBLEM: Max Flow
//== signature
method max_flow_value(graph: CapacityGraph, s: int, t: int) returns (max_val: int)
    requires well_formed(graph)
    requires capacities_bounded(view(graph))
    requires 0 <= s < size(graph)
    requires 0 <= t < size(graph)
    requires s != t
    ensures exists f: FlowMap :: 
            is_max_flow(view(graph), f, s, t) 
            && flow_val(view(graph), f, s) == max_val
//== solution
