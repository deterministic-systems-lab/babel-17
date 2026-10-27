// intent: Your task is to implement the "Exponentiation by Squaring" Algorithm and verify its functional correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/fast_exponential/dafny_spec.dfy (Apache-2.0)
//== preamble
// Pure mathematical definition of power
function spec_pow(b: nat, e: nat): nat
  decreases e
{
  if e == 0 then
    1
  else
    b * spec_pow(b, e - 1)
}
//== signature
method exponentiation(b: int, e: int) returns (res: int)
  // Simulate u64 types (non-negative)
  requires b >= 0 
  requires e >= 0
  // Precondition: Result fits in u64 (0xffff_ffff_ffff_ffff)
  requires spec_pow(b, e) <= 0xffff_ffff_ffff_ffff
  
  ensures res == spec_pow(b, e)
  // Ensure return value preserves non-negativity
  ensures res >= 0
//== solution
