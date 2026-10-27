// intent: Your task is to implement the Unbounded Knapsack algorithm (also known as the Complete Knapsack problem) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/knapsack_unbounded/dafny_spec.dfy (Apache-2.0)
//== preamble
// Calculates the total weight of the selected items: sum(count[i] * weight[i])
ghost function total_weight(counts: seq<int>, weights: seq<int>): int
    requires |counts| <= |weights|
    decreases |counts|
{
    if |counts| == 0 then
        0
    else
        (counts[0] * weights[0]) + 
        total_weight(counts[1..], weights[1..])
}

// Calculates the total value of the selected items: sum(count[i] * value[i])
ghost function total_value(counts: seq<int>, values: seq<int>): int
    requires |counts| <= |values|
    decreases |counts|
{
    if |counts| == 0 then
        0
    else
        (counts[0] * values[0]) + 
        total_value(counts[1..], values[1..])
}

// Definition of a valid strategy: 
// 1. Counts length matches items length
// 2. All counts are non-negative
// 3. Total weight does not exceed capacity
ghost predicate is_valid_strategy(counts: seq<int>, weights: seq<int>, capacity: int)
{
    |counts| == |weights| &&
    (forall i :: 0 <= i < |counts| ==> counts[i] >= 0) &&
    total_weight(counts, weights) <= capacity
}
//== signature
method solve_knapsack_unbounded(weights: seq<int>, values: seq<int>, capacity: int) returns (max_val: int)
    requires |weights| == |values|
    requires |weights| > 0
    requires 0 <= capacity <= 1000 // Explicitly constrain non-negative capacity
    requires forall i :: 0 <= i < |weights| ==> weights[i] > 0 // Weights must be positive (> 0) to avoid infinite loops
    requires forall i :: 0 <= i < |weights| ==> weights[i] <= 1000
    requires forall i :: 0 <= i < |values| ==> 0 <= values[i] <= 1000 // Explicitly constrain non-negative values
    ensures max_val >= 0
    ensures
        // 1. Upper Bound
        forall counts: seq<int> :: 
            is_valid_strategy(counts, weights, capacity)
            ==> total_value(counts, values) <= max_val
    ensures
        // 2. Existence
        exists counts: seq<int> :: 
            is_valid_strategy(counts, weights, capacity)
            && total_value(counts, values) == max_val
//== solution
