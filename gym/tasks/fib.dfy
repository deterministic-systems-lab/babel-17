// intent: Compute the nth Fibonacci number.
// difficulty: medium
//== preamble
ghost function Fib(n: nat): nat
{
  if n < 2 then n else Fib(n - 1) + Fib(n - 2)
}
//== signature
method FibIter(n: nat) returns (f: nat)
  ensures f == Fib(n)
//== solution
method FibIter(n: nat) returns (f: nat)
  ensures f == Fib(n)
{
  if n == 0 { return 0; }
  var prev, cur := 0, 1;
  var k := 1;
  while k < n
    invariant 1 <= k <= n
    invariant prev == Fib(k - 1) && cur == Fib(k)
  {
    prev, cur := cur, prev + cur;
    k := k + 1;
  }
  return cur;
}
