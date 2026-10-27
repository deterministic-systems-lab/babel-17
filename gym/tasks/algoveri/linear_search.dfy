// intent: Your task is to implement the Linear Search algorithm (specifically the lower_bound variant) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/linear_search/dafny_spec.dfy (Apache-2.0)
//== preamble
predicate is_sorted(s: seq<int>) {
    forall i, j {:trigger s[i], s[j]} :: 
        0 <= i <= j < |s| ==> s[i] <= s[j]
}
//== signature
method linear_search_lower_bound(s: seq<int>, target: int) returns (result: int)
    requires |s| <= 0x7FFFFFFF
    requires is_sorted(s)
    ensures result >= 0
    ensures result <= |s|
    ensures forall i {:trigger s[i]} :: 0 <= i < result ==> s[i] < target
    ensures forall i {:trigger s[i]} :: result <= i < |s| ==> s[i] >= target
//== solution
