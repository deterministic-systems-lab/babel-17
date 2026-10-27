// intent: Your task is to implement the Coin Change algorithm (finding minimum number of coins) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/coin_change/dafny_spec.dfy (Apache-2.0)
//== preamble
// Calculates total monetary value: sum(counts[i] * coins[i])
ghost function total_amount(counts: seq<int>, coins: seq<int>): int
    requires |counts| == |coins|
    decreases |counts|
{
    if |counts| == 0 then
        0
    else
        (counts[0] * coins[0]) + 
        total_amount(counts[1..], coins[1..])
}

// Calculates total number of coins used: sum(counts[i])
ghost function total_coins(counts: seq<int>): int
    decreases |counts|
{
    if |counts| == 0 then
        0
    else
        counts[0] + total_coins(counts[1..])
}

// Definition of a valid change strategy:
// 1. One count per coin type
// 2. All counts non-negative
// 3. Total value equals target amount
ghost predicate is_valid_change(counts: seq<int>, coins: seq<int>, amount: int) {
    |counts| == |coins| &&
    (forall i: int :: 0 <= i < |counts| ==> counts[i] >= 0) &&
    total_amount(counts, coins) == amount
}

// Returns -1 if impossible, otherwise the minimum number of coins.
//== signature
method coin_change(coins: seq<int>, amount: int) returns (min_coins: int)
    requires |coins| > 0
    requires |coins| <= 100
    requires amount <= 10000
    // Coins must be positive
    requires forall i: int :: 0 <= i < |coins| ==> coins[i] > 0
    requires forall i: int :: 0 <= i < |coins| ==> coins[i] <= 10000
    ensures
        // Case 1: Solution exists
        min_coins != -1 ==> (
            // Existence
            (exists counts: seq<int> :: is_valid_change(counts, coins, amount) && total_coins(counts) == min_coins)
            &&
            // Lower Bound (Optimality)
            (forall counts: seq<int> :: is_valid_change(counts, coins, amount) ==> total_coins(counts) >= min_coins)
        )
    ensures
        // Case 2: Impossible
        min_coins == -1 ==> (
            forall counts: seq<int> :: is_valid_change(counts, coins, amount) ==> false
        )
//== solution
