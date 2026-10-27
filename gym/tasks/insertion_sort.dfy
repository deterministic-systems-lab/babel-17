// intent: Sort an array in place, keeping exactly the same elements.
// difficulty: hard
//== preamble
ghost predicate Sorted(s: seq<int>)
{
  forall i, j :: 0 <= i < j < |s| ==> s[i] <= s[j]
}
//== signature
method InsertionSort(a: array<int>)
  modifies a
  ensures Sorted(a[..])
  ensures multiset(a[..]) == multiset(old(a[..]))
//== solution
method InsertionSort(a: array<int>)
  modifies a
  ensures Sorted(a[..])
  ensures multiset(a[..]) == multiset(old(a[..]))
{
  var i := 0;
  while i < a.Length
    invariant 0 <= i <= a.Length
    invariant forall p, q :: 0 <= p < q < i ==> a[p] <= a[q]
    invariant multiset(a[..]) == multiset(old(a[..]))
  {
    var j := i;
    while j > 0 && a[j - 1] > a[j]
      invariant 0 <= j <= i
      invariant forall p, q :: 0 <= p < q <= i && p != j && q != j ==> a[p] <= a[q]
      invariant forall q :: j < q <= i ==> a[j] < a[q]
      invariant multiset(a[..]) == multiset(old(a[..]))
    {
      a[j - 1], a[j] := a[j], a[j - 1];
      j := j - 1;
    }
    i := i + 1;
  }
}
