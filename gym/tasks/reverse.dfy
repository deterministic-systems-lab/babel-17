// intent: Return a sequence with the elements of the input in reverse order.
// difficulty: easy
//== preamble
//== signature
method Reverse(a: seq<int>) returns (r: seq<int>)
  ensures |r| == |a|
  ensures forall i :: 0 <= i < |a| ==> r[i] == a[|a| - 1 - i]
//== solution
method Reverse(a: seq<int>) returns (r: seq<int>)
  ensures |r| == |a|
  ensures forall i :: 0 <= i < |a| ==> r[i] == a[|a| - 1 - i]
{
  r := [];
  var k := 0;
  while k < |a|
    invariant 0 <= k <= |a|
    invariant |r| == k
    invariant forall i :: 0 <= i < k ==> r[i] == a[|a| - 1 - i]
  {
    r := r + [a[|a| - 1 - k]];
    k := k + 1;
  }
}
