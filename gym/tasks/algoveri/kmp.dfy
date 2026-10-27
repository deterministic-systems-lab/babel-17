// intent: Your task is to implement the Knuth-Morris-Pratt (KMP) algorithm to efficiently find all occurrences of a needle (pattern) within a haystack (text) and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/kmp/dafny_spec.dfy (Apache-2.0)
//== preamble
predicate matches_at(haystack: seq<int>, needle: seq<int>, start_index: int) {
    && 0 <= start_index
    && start_index + |needle| <= |haystack|
    && forall i :: 0 <= i < |needle| ==> 
        haystack[start_index + i] == needle[i]
}
//== signature
method kmp_search(haystack: seq<int>, needle: seq<int>) returns (indices: seq<int>)
    requires |haystack| < 1000000
    requires |needle| < 1000000
    ensures 
        // Type Constraint: Indices must be non-negative (simulating usize)
        forall k :: 0 <= k < |indices| ==> indices[k] >= 0
    ensures
        // Soundness: Every index returned is a valid match
        forall i :: 0 <= i < |indices| ==> 
            matches_at(haystack, needle, indices[i])
    ensures
        // Completeness: Every valid match in the haystack is found
        forall i :: matches_at(haystack, needle, i) ==> 
            exists k :: 0 <= k < |indices| && indices[k] == i
//== solution
