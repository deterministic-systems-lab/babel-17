// intent: Your task is to implement a solver for the Discrete Logarithm Problem and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/discrete_logarithm/dafny_spec.dfy (Apache-2.0)
//== preamble
// Recursive definition of Modular Exponentiation: (b^e) % m
ghost function spec_pow_mod(b: int, e: int, m: int): int
  decreases e
  requires m > 1
{
  if e <= 0 then
    1
  else
    (b * spec_pow_mod(b, e - 1, m)) % m
}

// The predicate that defines a valid Discrete Logarithm x
ghost predicate is_discrete_log(g: int, h: int, p: int, x: int)
  requires p > 1
{
  spec_pow_mod(g, x, p) == h % p
}

// Dafny uses a datatype for Option
datatype Option<T> = Some(value: T) | None
//== signature
method discrete_log_naive(g: int, h: int, p: int) returns (res: Option<int>)
  // Simulate u64: inputs are non-negative
  requires g >= 0 && h >= 0 && p >= 0
  requires p > 1
  
  ensures match res
    case Some(x) => 
      // 1. It is a valid solution
      is_discrete_log(g, h, p, x) &&
      // 2. It is within bounds
      0 <= x < p &&
      // 3. It is the *smallest* solution
      (forall k :: 0 <= k < x ==> !is_discrete_log(g, h, p, k))
    case None =>
      // We assert that NO solution exists in the range [0, p)
      forall k :: 0 <= k < p ==> !is_discrete_log(g, h, p, k)
//== solution
