// intent: Count how many times x occurs in a sequence.
// difficulty: easy
//== preamble
ghost function Count(s: seq<int>, x: int): nat
{
  if |s| == 0 then 0 else Count(s[..|s| - 1], x) + (if s[|s| - 1] == x then 1 else 0)
}
//== signature
method CountOf(a: seq<int>, x: int) returns (c: nat)
  ensures c == Count(a, x)
//== solution
method CountOf(a: seq<int>, x: int) returns (c: nat)
  ensures c == Count(a, x)
{
  c := 0;
  var k := 0;
  while k < |a|
    invariant 0 <= k <= |a|
    invariant c == Count(a[..k], x)
  {
    assert a[..k + 1][..k] == a[..k];
    if a[k] == x { c := c + 1; }
    k := k + 1;
  }
  assert a[..|a|] == a;
}
