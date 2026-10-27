// intent: /* This task requires writing a Dafny method that determines whether a natural number is a power of four.
// difficulty: vericoding
// source: vericoding 387cd6999679 DV0013 (verina verina_advanced_14_task; MIT), solved by 1 of 8 models
//== preamble
ghost function Power(base: int, exp: nat): int
{
  if exp == 0 then 1
  else base * Power(base, exp - 1)
}
//== signature
method IfPowerOfFour(n: nat) returns (result: bool)
    ensures result <==> (exists m: nat :: n == Power(4, m))
//== solution
/* helper modified by LLM (iteration 5): Simplified helpers with direct equivalence proof */
function IsPowerOfFourComputable(n: nat): bool
{
  if n == 0 then false
  else if n == 1 then true
  else if n % 4 != 0 then false
  else IsPowerOfFourComputable(n / 4)
}

lemma PowerPositive(m: nat)
  ensures Power(4, m) >= 1
{
  if m == 0 {
    assert Power(4, 0) == 1;
  } else {
    PowerPositive(m - 1);
    assert Power(4, m) == 4 * Power(4, m - 1);
    assert Power(4, m - 1) >= 1;
    assert Power(4, m) >= 4;
  }
}

lemma IsPowerOfFourCorrect(n: nat)
  ensures IsPowerOfFourComputable(n) <==> (exists m: nat :: n == Power(4, m))
{
  if n == 0 {
    if exists m: nat :: n == Power(4, m) {
      var m: nat :| n == Power(4, m);
      PowerPositive(m);
      assert Power(4, m) >= 1;
      assert false;
    }
  } else if n == 1 {
    assert n == Power(4, 0);
    assert exists m: nat :: n == Power(4, m);
  } else if n % 4 != 0 {
    if exists m: nat :: n == Power(4, m) {
      var m: nat :| n == Power(4, m);
      if m == 0 {
        assert n == 1;
        assert false;
      } else {
        assert n == 4 * Power(4, m - 1);
        assert n % 4 == 0;
        assert false;
      }
    }
  } else {
    IsPowerOfFourCorrect(n / 4);
    if exists m: nat :: n == Power(4, m) {
      var m: nat :| n == Power(4, m);
      assert m > 0;
      assert n / 4 == Power(4, m - 1);
      assert exists k: nat :: n / 4 == Power(4, k);
    }
    if exists m: nat :: n / 4 == Power(4, m) {
      var m: nat :| n / 4 == Power(4, m);
      assert n == Power(4, m + 1);
      assert exists k: nat :: n == Power(4, k);
    }
  }
}

method IfPowerOfFour(n: nat) returns (result: bool)
    ensures result <==> (exists m: nat :: n == Power(4, m))

/* code modified by LLM (iteration 5): Direct call to lemma that establishes postcondition */
{
  result := IsPowerOfFourComputable(n);
  IsPowerOfFourCorrect(n);
}
