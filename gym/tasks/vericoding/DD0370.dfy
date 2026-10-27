// intent: (no description in the source)
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0370 (dafnybench Program-Verification-Dataset_tmp_tmpgbdrlnu__Dafny_algorithms_and_leetcode_ProgramProofs_ch15_QuickSort; MIT), solved by 1 of 9 models
//== preamble
method Partition(a: array<int>, lo: int, hi: int) returns (p: int)
    requires 0 <= lo < hi <= a.Length
    modifies a
    ensures lo <= p < hi
{
  assume{:axiom} false;
}

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

method QuickSortAux(a: array<int>, lo: int, hi: int)
    requires 0 <= lo <= hi <= a.Length
    requires SplitPoint(a, lo) && SplitPoint(a, hi)
    modifies a
    ensures forall i,j :: lo <= i < j < hi ==> a[i] <= a[j]
    ensures SwapFrame(a, lo, hi)
    ensures SplitPoint(a, lo) && SplitPoint(a, hi)
    decreases hi - lo
{
  assume{:axiom} false;
}
//== signature
method QuickSort(a: array<int>)
    modifies a
    ensures forall i,j :: 0 <= i < j < a.Length ==> a[i] <= a[j]
    ensures multiset(a[..]) == old(multiset(a[..]))
//== solution
lemma SplitPointEmpty(a: array<int>)
    ensures SplitPoint(a, 0)
    ensures SplitPoint(a, a.Length)
{
    // SplitPoint(a, 0) holds vacuously since there are no i < 0
    // SplitPoint(a, a.Length) holds vacuously since there are no j >= a.Length
}

method QuickSort(a: array<int>)
    modifies a
    ensures forall i,j :: 0 <= i < j < a.Length ==> a[i] <= a[j]
    ensures multiset(a[..]) == old(multiset(a[..]))

{
    if a.Length > 0 {
        SplitPointEmpty(a);
        QuickSortAux(a, 0, a.Length);
    }
}
