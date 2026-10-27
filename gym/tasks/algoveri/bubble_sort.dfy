// intent: Your task is to implement Bubble Sort and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/bubble_sort/dafny_spec.dfy (Apache-2.0)
//== preamble
ghost predicate is_sorted(s: seq<int>) {
    forall i, j :: 0 <= i < j < |s| ==> s[i] <= s[j]
}

ghost predicate is_valid_index_permutation(p: seq<int>, n: int) {
    && |p| == n
    && (forall i {:trigger p[i]} :: 0 <= i < n ==> 0 <= p[i] < n)
    && (forall i, j {:trigger p[i], p[j]} :: 0 <= i < j < n ==> p[i] != p[j])
}

ghost predicate is_permutation(v1: seq<int>, v2: seq<int>) {
    exists p: seq<int> :: 
        is_valid_index_permutation(p, |v1|) 
        && |v1| == |v2|
        && (forall i {:trigger p[i]} :: 0 <= i < |v1| ==> v2[i] == v1[p[i]])
}
//== signature
method bubble_sort(v: seq<int>) returns (v_new: seq<int>)
    ensures is_sorted(v_new)
    ensures is_permutation(v, v_new)
//== solution
