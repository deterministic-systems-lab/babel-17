// intent: Compute the integer square root of a natural number.
// difficulty: medium
//== preamble
//== signature
method Isqrt(n: nat) returns (r: nat)
  ensures r * r <= n < (r + 1) * (r + 1)
//== solution
method Isqrt(n: nat) returns (r: nat)
  ensures r * r <= n < (r + 1) * (r + 1)
{
  r := 0;
  while (r + 1) * (r + 1) <= n
    invariant r * r <= n
    decreases n - r * r
  {
    r := r + 1;
  }
}
