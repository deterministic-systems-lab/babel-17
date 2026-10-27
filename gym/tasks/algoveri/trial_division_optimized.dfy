// intent: Your task is to implement an efficient Primality Test using trial division up to the square root and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/trial_division_optimized/dafny_spec.dfy (Apache-2.0)
//== preamble
predicate divides(d: int, n: int)
  requires d != 0
{
  n % d == 0
}

predicate is_prime(n: int)
{
  n > 1 &&
  forall d :: 1 < d < n ==> !divides(d, n)
}
//== signature
method check_prime(n: int) returns (res: bool)
  // Simulate u64: input is non-negative
  requires n >= 0
  ensures res == is_prime(n)
//== solution
