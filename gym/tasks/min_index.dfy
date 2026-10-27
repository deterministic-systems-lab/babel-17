// intent: Return the index of a smallest element of a non-empty sequence.
// difficulty: easy
//== preamble
//== signature
method MinIndex(a: seq<int>) returns (m: int)
  requires |a| > 0
  ensures 0 <= m < |a|
  ensures forall i :: 0 <= i < |a| ==> a[m] <= a[i]
//== solution
method MinIndex(a: seq<int>) returns (m: int)
  requires |a| > 0
  ensures 0 <= m < |a|
  ensures forall i :: 0 <= i < |a| ==> a[m] <= a[i]
{
  m := 0;
  var k := 1;
  while k < |a|
    invariant 1 <= k <= |a|
    invariant 0 <= m < k
    invariant forall i :: 0 <= i < k ==> a[m] <= a[i]
  {
    if a[k] < a[m] { m := k; }
    k := k + 1;
  }
}
