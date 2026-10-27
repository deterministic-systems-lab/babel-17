// intent: // By `lol sort` here, I refer to a seemingly-broken sorting algorithm, // which actually somehow manages to work perfectly: // // for i in 0..n // for j in 0..n // if i < j // swap a[i], a[j] // // It is perhaps the simpliest sorting algorithm to "memorize", // even "symmetrically beautiful" as if `i` and `j` just played highly // similar roles.
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0423 (dafnybench Program-Verification-Dataset_tmp_tmpgbdrlnu__Dafny_verified_algorithms_lol_sort_lol_sort; MIT), solved by 1 of 9 models
//== preamble
ghost predicate valid_permut(a: seq<int>, b: seq<int>)
  requires |a| == |b|
{
  multiset(a) == multiset(b)
}

method swap(a: array<int>, i: int, j: int)
  requires 0 <= i < a.Length && 0 <= j < a.Length
  modifies a
  ensures a[..] == old(a[..]) [i := old(a[j])] [j := old(a[i])]
  ensures valid_permut(a[..], old(a[..]))
{
  assume{:axiom} false;
}

ghost predicate sorted(a: seq<int>)
{
  forall i, j | 0 <= i <= j < |a| :: a[i] <= a[j]
}
//== signature
method lol_sort(a: array<int>)
  modifies a
  ensures valid_permut(a[..], old(a[..]))
  ensures sorted(a[..])
//== solution
// Helper lemma to show that swapping preserves sortedness in the prefix
lemma SwapPreservesSortedPrefix(a: seq<int>, i: int, j: int, k: int)
  requires 0 <= i < |a| && 0 <= j < |a|
  requires 0 <= k <= i
  requires forall p, q | 0 <= p <= q < k :: a[p] <= a[q]
  requires forall p, q | 0 <= p < k <= q < |a| :: a[p] <= a[q]
  requires i < j && a[i] > a[j]
  ensures var a' := a[i := a[j]][j := a[i]];
          forall p, q | 0 <= p <= q < k :: a'[p] <= a'[q]
{
  var a' := a[i := a[j]][j := a[i]];
  forall p, q | 0 <= p <= q < k
    ensures a'[p] <= a'[q]
  {
    if p < k && q < k {
      assert a'[p] == a[p] && a'[q] == a[q];
    }
  }
}

// Helper lemma for the partition property after swap
lemma SwapPreservesPartition(a: seq<int>, i: int, j: int, k: int)
  requires 0 <= i < |a| && 0 <= j < |a|
  requires 0 <= k <= i
  requires forall p, q | 0 <= p < k <= q < |a| :: a[p] <= a[q]
  requires i < j && a[i] > a[j]
  ensures var a' := a[i := a[j]][j := a[i]];
          forall p, q | 0 <= p < k <= q < |a| :: a'[p] <= a'[q]
{
  var a' := a[i := a[j]][j := a[i]];
  forall p, q | 0 <= p < k <= q < |a|
    ensures a'[p] <= a'[q]
  {
    if p < k {
      if q == i {
        assert a'[p] == a[p] && a'[i] == a[j];
        assert a[p] <= a[j];
      } else if q == j {
        assert a'[p] == a[p] && a'[j] == a[i];
        assert a[p] <= a[i];
      } else {
        assert a'[p] == a[p] && a'[q] == a[q];
        assert a[p] <= a[q];
      }
    }
  }
}

method lol_sort(a: array<int>)
  modifies a
  ensures valid_permut(a[..], old(a[..]))
  ensures sorted(a[..])

{
  var n := a.Length;
  
  for i := 0 to n
    invariant valid_permut(a[..], old(a[..]))
    invariant forall p, q | 0 <= p <= q < i :: a[p] <= a[q]
    invariant forall p, q | 0 <= p < i <= q < n :: a[p] <= a[q]
  {
    for j := 0 to n
      invariant valid_permut(a[..], old(a[..]))
      invariant forall p, q | 0 <= p <= q < i :: a[p] <= a[q]
      invariant forall p, q | 0 <= p < i <= q < n :: a[p] <= a[q]
      invariant forall k | 0 <= k < j :: if k < i then a[k] <= a[i] else a[i] <= a[k]
    {
      if i < j && a[i] > a[j] {
        SwapPreservesSortedPrefix(a[..], i, j, i);
        SwapPreservesPartition(a[..], i, j, i);
        swap(a, i, j);
      }
    }
  }
}
