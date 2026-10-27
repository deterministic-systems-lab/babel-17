// intent: Compute the greatest common divisor of two natural numbers with a loop.
// difficulty: medium
//== preamble
function Gcd(a: nat, b: nat): nat
  decreases b
{
  if b == 0 then a else Gcd(b, a % b)
}
//== signature
method GcdIter(a: nat, b: nat) returns (g: nat)
  ensures g == Gcd(a, b)
//== solution
method GcdIter(a: nat, b: nat) returns (g: nat)
  ensures g == Gcd(a, b)
{
  var x, y := a, b;
  while y != 0
    invariant Gcd(x, y) == Gcd(a, b)
    decreases y
  {
    x, y := y, x % y;
  }
  g := x;
}
