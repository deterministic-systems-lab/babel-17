// intent: Your task is to specify the K-th Smallest Element algorithm acting on a vector of integers and verify its correctness properties in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/k_smallest/dafny_spec.dfy (Apache-2.0)
//== preamble
ghost predicate is_sorted(s: seq<int>) {
    forall i, j {:trigger s[i], s[j]} :: 0 <= i < j < |s| ==> s[i] <= s[j]
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

// Mathematical definition: "val" is the k-th smallest element of "s" if
// the sorted version of "s" has "val" at index "k".
ghost predicate is_kth_smallest(s: seq<int>, k: int, val: int) {
    exists sorted_s: seq<int> {:trigger is_sorted(sorted_s)} ::
        is_permutation(s, sorted_s)
        && is_sorted(sorted_s)
        && 0 <= k < |s|
        && sorted_s[k] == val
}
//== signature
method quick_select(v: seq<int>, k: int) returns (v_new: seq<int>, res: int)
    requires 0 <= k < |v|
    ensures 
        // 1. Data Integrity: The array remains a valid permutation of the input
        is_permutation(v, v_new)
    ensures 
        // 2. Correctness: The return value is truly the k-th smallest element
        is_kth_smallest(v, k, res)
//== solution
