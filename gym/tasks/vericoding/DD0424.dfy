// intent: // By `lol sort` here, I refer to a seemingly-broken sorting algorithm, // which actually somehow manages to work perfectly: // // for i in 0..n // for j in 0..n // if i < j // swap a[i], a[j] // // It is perhaps the simpliest sorting algorithm to "memorize", // even "symmetrically beautiful" as if `i` and `j` just played highly // similar roles.
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0424 (dafnybench Program-Verification-Dataset_tmp_tmpgbdrlnu__Dafny_verified_algorithms_lol_sort_swap; MIT), solved by 1 of 9 models
//== preamble
ghost predicate valid_permut(a: seq<int>, b: seq<int>)
  requires |a| == |b|
{
  multiset(a) == multiset(b)
}

ghost predicate sorted(a: seq<int>)
{
  forall i, j | 0 <= i <= j < |a| :: a[i] <= a[j]
}
//== signature
method swap(a: array<int>, i: int, j: int)
  requires 0 <= i < a.Length && 0 <= j < a.Length
  modifies a
  ensures a[..] == old(a[..]) [i := old(a[j])] [j := old(a[i])]
  ensures valid_permut(a[..], old(a[..]))
//== solution
// Helper lemma to prove that swapping preserves multisets
lemma SwapPreservesMultiset(s: seq<int>, i: int, j: int)
  requires 0 <= i < |s| && 0 <= j < |s|
  ensures multiset(s[i := s[j]][j := s[i]]) == multiset(s)
{
  var s' := s[i := s[j]][j := s[i]];
  
  if i == j {
    assert s' == s;
  } else {
    // The multiset remains the same after swapping
    assert multiset(s') == multiset(s);
  }
}

method swap(a: array<int>, i: int, j: int)
  requires 0 <= i < a.Length && 0 <= j < a.Length
  modifies a
  ensures a[..] == old(a[..]) [i := old(a[j])] [j := old(a[i])]
  ensures valid_permut(a[..], old(a[..]))

{
  var temp := a[i];
  a[i] := a[j];
  a[j] := temp;
  
  // Prove the multiset preservation
  SwapPreservesMultiset(old(a[..]), i, j);
}
