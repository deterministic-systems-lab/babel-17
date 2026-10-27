// intent: Compute b raised to the power e with a loop.
// difficulty: medium
//== preamble
function Pow(b: int, e: nat): int
{
  if e == 0 then 1 else b * Pow(b, e - 1)
}
//== signature
method PowIter(b: int, e: nat) returns (p: int)
  ensures p == Pow(b, e)
//== solution
method PowIter(b: int, e: nat) returns (p: int)
  ensures p == Pow(b, e)
{
  p := 1;
  var k := 0;
  while k < e
    invariant 0 <= k <= e
    invariant p == Pow(b, k)
  {
    p := b * p;
    k := k + 1;
  }
}
