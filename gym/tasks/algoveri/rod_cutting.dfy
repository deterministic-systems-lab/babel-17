// intent: Your task is to implement the Rod Cutting algorithm (a classic Dynamic Programming problem from CLRS) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/rod_cutting/dafny_spec.dfy (Apache-2.0)
//== preamble
// Calculates the total length of the pieces
function sum_lengths(cuts: seq<int>): int
    decreases |cuts|
{
    if |cuts| == 0 then
        0
    else
        cuts[0] + sum_lengths(cuts[1..])
}

// Helper: Safe price lookup that returns 0 for out-of-bounds
function get_price(prices: seq<int>, idx: int): int {
    if 0 <= idx < |prices| then
        prices[idx]
    else
        0
}

// Calculates revenue recursively.
function calculate_revenue(cuts: seq<int>, prices: seq<int>): int
    decreases |cuts|
{
    if |cuts| == 0 then
        0
    else
        // Revenue is price of first piece + revenue of remaining pieces
        get_price(prices, cuts[0] - 1) + 
        calculate_revenue(cuts[1..], prices)
}

// Definition of a valid strategy: positive cuts, valid prices, sums to n
predicate is_valid_strategy(cuts: seq<int>, n: int, prices: seq<int>) {
    (forall i: int :: 0 <= i < |cuts| ==> cuts[i] > 0) &&
    (forall i: int :: 0 <= i < |cuts| ==> cuts[i] - 1 < |prices|) &&
    sum_lengths(cuts) == n
}
//== signature
method rod_cutting(n: int, prices: seq<int>) returns (result: int)
    requires |prices| >= n
    requires n <= 1000
    // Constraints matching Verus u64/usize unsigned and explicit bounds
    requires forall i: int :: 0 <= i < |prices| ==> 0 <= prices[i] <= 10000
    ensures result >= 0
    // 1. Upper Bound
    ensures forall cuts: seq<int> :: (is_valid_strategy(cuts, n, prices) 
            ==> calculate_revenue(cuts, prices) <= result)
    // 2. Existence
    ensures exists cuts: seq<int> :: (is_valid_strategy(cuts, n, prices) 
            && calculate_revenue(cuts, prices) == result)
//== solution
