// intent: Return the running totals of a sequence, starting from 0.
// difficulty: medium
//== preamble
function Sum(s: seq<int>): int
{
  if |s| == 0 then 0 else Sum(s[..|s| - 1]) + s[|s| - 1]
}
//== signature
method PrefixSums(a: seq<int>) returns (p: seq<int>)
  ensures |p| == |a| + 1
  ensures forall i :: 0 <= i <= |a| ==> p[i] == Sum(a[..i])
//== solution
method PrefixSums(a: seq<int>) returns (p: seq<int>)
  ensures |p| == |a| + 1
  ensures forall i :: 0 <= i <= |a| ==> p[i] == Sum(a[..i])
{
  p := [0];
  var k := 0;
  while k < |a|
    invariant 0 <= k <= |a|
    invariant |p| == k + 1
    invariant forall i :: 0 <= i <= k ==> p[i] == Sum(a[..i])
  {
    assert a[..k + 1][..k] == a[..k];
    p := p + [p[k] + a[k]];
    k := k + 1;
  }
}
