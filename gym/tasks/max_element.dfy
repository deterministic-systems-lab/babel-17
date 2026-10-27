// intent: Return the largest element of a non-empty sequence.
// difficulty: easy
//== preamble
//== signature
method Max(a: seq<int>) returns (m: int)
  requires |a| > 0
  ensures forall i :: 0 <= i < |a| ==> a[i] <= m
  ensures m in a
//== solution
method Max(a: seq<int>) returns (m: int)
  requires |a| > 0
  ensures forall i :: 0 <= i < |a| ==> a[i] <= m
  ensures m in a
{
  m := a[0];
  var k := 1;
  while k < |a|
    invariant 1 <= k <= |a|
    invariant forall i :: 0 <= i < k ==> a[i] <= m
    invariant m in a
  {
    if a[k] > m { m := a[k]; }
    k := k + 1;
  }
}
