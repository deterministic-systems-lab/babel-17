// intent: Report whether a sequence is in non-decreasing order.
// difficulty: medium
//== preamble
predicate Sorted(s: seq<int>)
{
  forall i, j :: 0 <= i < j < |s| ==> s[i] <= s[j]
}
//== signature
method IsSorted(a: seq<int>) returns (b: bool)
  ensures b <==> Sorted(a)
//== solution
method IsSorted(a: seq<int>) returns (b: bool)
  ensures b <==> Sorted(a)
{
  if |a| < 2 { return true; }
  var k := 1;
  while k < |a|
    invariant 1 <= k <= |a|
    invariant Sorted(a[..k])
  {
    if a[k - 1] > a[k] { return false; }
    k := k + 1;
  }
  assert a[..k] == a;
  return true;
}
