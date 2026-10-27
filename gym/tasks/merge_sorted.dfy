// intent: Merge two sorted sequences into one sorted sequence holding every element of both, duplicates kept.
// difficulty: hard
//== preamble
ghost predicate Sorted(s: seq<int>)
{
  forall i, j :: 0 <= i < j < |s| ==> s[i] <= s[j]
}
//== signature
method MergeSorted(a: seq<int>, b: seq<int>) returns (out: seq<int>)
  requires Sorted(a) && Sorted(b)
  ensures Sorted(out)
  ensures multiset(out) == multiset(a) + multiset(b)
//== solution
method MergeSorted(a: seq<int>, b: seq<int>) returns (out: seq<int>)
  requires Sorted(a) && Sorted(b)
  ensures Sorted(out)
  ensures multiset(out) == multiset(a) + multiset(b)
{
  out := [];
  var i, j := 0, 0;
  while i < |a| || j < |b|
    invariant 0 <= i <= |a| && 0 <= j <= |b|
    invariant Sorted(out)
    invariant multiset(out) == multiset(a[..i]) + multiset(b[..j])
    invariant |out| > 0 && i < |a| ==> out[|out| - 1] <= a[i]
    invariant |out| > 0 && j < |b| ==> out[|out| - 1] <= b[j]
    decreases |a| - i + |b| - j
  {
    if j == |b| || (i < |a| && a[i] <= b[j]) {
      assert a[..i + 1] == a[..i] + [a[i]];
      out := out + [a[i]];
      i := i + 1;
    } else {
      assert b[..j + 1] == b[..j] + [b[j]];
      out := out + [b[j]];
      j := j + 1;
    }
  }
  assert a[..i] == a && b[..j] == b;
}
