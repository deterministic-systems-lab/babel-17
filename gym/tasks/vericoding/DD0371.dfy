// intent: (no description in the source)
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0371 (dafnybench Program-Verification-Dataset_tmp_tmpgbdrlnu__Dafny_algorithms_and_leetcode_ProgramProofs_ch15_QuickSortAux; MIT), solved by 1 of 9 models
//== preamble
ghost predicate SplitPoint(a: array<int>, n: int)
    reads a
    requires 0 <= n <= n

{
    forall i,j :: 0 <= i < n <= j < a.Length ==> a[i] <= a[j]
}

twostate predicate SwapFrame(a: array<int>, lo: int, hi: int)
    requires 0 <= lo <= hi <= a.Length
    reads a
{
    (forall i :: 0 <= i < lo || hi <= i < a.Length ==> a[i] == old(a[i])) && multiset(a[..]) == old(multiset(a[..]))
}

method Partition(a: array<int>, lo: int, hi: int) returns (p: int)
    requires 0 <= lo < hi <= a.Length
    requires SplitPoint(a, lo) && SplitPoint(a, hi)
    modifies a
    ensures lo <= p < hi
    ensures forall i :: lo <= i < p ==> a[i] < a[p]
    ensures forall i :: p <= i < hi ==> a[p] <= a[i]
    ensures SplitPoint(a, lo) && SplitPoint(a, hi)
    ensures SwapFrame(a, lo, hi)
{
  assume{:axiom} false;
}
//== signature
method QuickSortAux(a: array<int>, lo: int, hi: int)
    requires 0 <= lo <= hi <= a.Length
    requires SplitPoint(a, lo) && SplitPoint(a, hi)
    modifies a
    ensures forall i,j :: lo <= i < j < hi ==> a[i] <= a[j]
    ensures SwapFrame(a, lo, hi)
    ensures SplitPoint(a, lo) && SplitPoint(a, hi)
    decreases hi - lo
//== solution
method QuickSortAux(a: array<int>, lo: int, hi: int)
    requires 0 <= lo <= hi <= a.Length
    requires SplitPoint(a, lo) && SplitPoint(a, hi)
    modifies a
    ensures forall i,j :: lo <= i < j < hi ==> a[i] <= a[j]
    ensures SwapFrame(a, lo, hi)
    ensures SplitPoint(a, lo) && SplitPoint(a, hi)
    decreases hi - lo

{
    if lo + 1 >= hi {
        // Base case: 0 or 1 element, already sorted
    } else {
        var p := Partition(a, lo, hi);
        
        // After partition:
        // - a[lo..p) < a[p]
        // - a[p..hi) >= a[p]
        // - SplitPoint(a, lo) and SplitPoint(a, hi) are preserved
        
        QuickSortAux(a, lo, p);
        // Now a[lo..p) is sorted
        
        QuickSortAux(a, p + 1, hi);
        // Now a[p+1..hi) is sorted
        
        // Since a[lo..p) are all < a[p] and a[p+1..hi) are all >= a[p],
        // and both subarrays are sorted, the entire array a[lo..hi) is sorted
    }
}
