// intent: Report whether every element of a sequence is positive.
// difficulty: easy
//== preamble
//== signature
method AllPositive(a: seq<int>) returns (b: bool)
  ensures b <==> forall i :: 0 <= i < |a| ==> a[i] > 0
//== solution
method AllPositive(a: seq<int>) returns (b: bool)
  ensures b <==> forall i :: 0 <= i < |a| ==> a[i] > 0
{
  b := true;
  var k := 0;
  while k < |a|
    invariant 0 <= k <= |a|
    invariant b <==> forall i :: 0 <= i < k ==> a[i] > 0
  {
    if a[k] <= 0 { b := false; }
    k := k + 1;
  }
}
