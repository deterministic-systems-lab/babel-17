// intent: Add up the elements of a sequence.
// difficulty: easy
//== preamble
ghost function Sum(s: seq<int>): int
{
  if |s| == 0 then 0 else Sum(s[..|s| - 1]) + s[|s| - 1]
}
//== signature
method SumOf(a: seq<int>) returns (s: int)
  ensures s == Sum(a)
//== solution
method SumOf(a: seq<int>) returns (s: int)
  ensures s == Sum(a)
{
  s := 0;
  var k := 0;
  while k < |a|
    invariant 0 <= k <= |a|
    invariant s == Sum(a[..k])
  {
    assert a[..k + 1][..k] == a[..k];
    s := s + a[k];
    k := k + 1;
  }
  assert a[..|a|] == a;
}
