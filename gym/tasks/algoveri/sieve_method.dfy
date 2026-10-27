// intent: Your task is to implement the classic Sieve of Eratosthenes algorithm to find all prime numbers up to a limit $N$ and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/sieve_method/dafny_spec.dfy (Apache-2.0)
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
method sieve_of_eratosthenes(n: int) returns (primes: seq<bool>)
  // Simulate usize (non-negative) and bound constraint
  requires 0 <= n <= 100_000
  
  ensures |primes| == n
  // Functional Correctness: 
  // Dafny automatically triggers on primes[i] here because it appears in the body.
  ensures forall i :: 0 <= i < n ==> primes[i] == is_prime(i)
//== solution
