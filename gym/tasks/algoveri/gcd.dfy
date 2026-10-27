// intent: Your task is to implement the Euclidean Algorithm to compute the Greatest Common Divisor (GCD) of two integers and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/gcd/dafny_spec.dfy (Apache-2.0)
//== preamble
// Mathematical definition of divisibility:
// d divides n if there exists some integer k such that d * k = n.
ghost predicate divides(d: nat, n: nat)
{
  exists k: nat :: d * k == n
}

// Predicate defining the properties of the Greatest Common Divisor (g):
// 1. g must be a common divisor of a and b.
// 2. g must be greater than or equal to any other common divisor d.
ghost predicate is_gcd(g: nat, a: nat, b: nat)
{
  divides(g, a) &&
  divides(g, b) &&
  (forall d: nat :: divides(d, a) && divides(d, b) ==> d <= g)
}

// The declarative specification for GCD.
ghost function spec_gcd(a: nat, b: nat): nat
{
  if a == 0 && b == 0 then
    0
  else
    // Dafny requires proof that such a g exists for the Hilbert epsilon operator (:|)
    // We guard it to satisfy the verifier without proving the number theory lemma here.
    if exists g: nat :: is_gcd(g, a, b) then
      var g: nat :| is_gcd(g, a, b); g
    else
      1 // Unreachable mathematically
}
//== signature
method compute_gcd(a: int, b: int) returns (res: int)
  // Simulate u64: inputs are non-negative
  requires a >= 0 && b >= 0
  ensures res == spec_gcd(a, b)
  // Result is unsigned
  ensures res >= 0
//== solution
