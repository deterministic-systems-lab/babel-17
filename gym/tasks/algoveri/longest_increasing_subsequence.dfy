// intent: You task is to implement the algorithm for longest increasing subsequence problem and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/longest_increasing_subsequence/dafny_spec.dfy (Apache-2.0)
//== preamble
ghost predicate is_valid_is(s: seq<int>, indices: seq<int>) {
    (forall k: int, m: int :: 
        0 <= k < m < |indices| ==> indices[k] < indices[m])
    && 
    (forall k: int :: 
        0 <= k < |indices| ==> 0 <= indices[k] < |s|)
    && 
    (forall k: int, m: int :: 
        0 <= k < m < |indices| ==> s[indices[k]] < s[indices[m]])
}
//== signature
method longest_increasing_subsequence(s: seq<int>) returns (result: int)
    requires |s| <= 0x7FFFFFFFFFFFFFFF
    ensures result >= 0
    ensures
        forall sub: seq<int> :: is_valid_is(s, sub) && |sub| > 0 ==> |sub| <= result
    ensures
        exists sub: seq<int> :: is_valid_is(s, sub) && |sub| == result
//== solution
