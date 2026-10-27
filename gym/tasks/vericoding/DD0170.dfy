// intent: (no description in the source)
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0170 (dafnybench Dafny_Learning_Experience_tmp_tmpuxvcet_u_week1_7_A2_Q1_trimmed_copy_-_副本_ComputeCount; MIT), solved by 1 of 9 models
//== preamble
ghost function Count(hi: nat, s:seq<int>): int
    requires 0 <= hi <= |s|
    decreases hi
{
    if hi == 0 then 0
    else if s[hi-1]%2 == 0 then 1 + Count(hi-1, s) else Count(hi-1, s)
}
//== signature
method ComputeCount(CountIndex:nat, a:seq<int>,b:array<int>) returns (p:nat)
    requires  CountIndex == 0 || (|a| == b.Length && 1 <= CountIndex <= |a|)
    decreases CountIndex
    modifies b
    ensures p == Count(CountIndex,a)
//== solution
method ComputeCount(CountIndex:nat, a:seq<int>,b:array<int>) returns (p:nat)
    requires  CountIndex == 0 || (|a| == b.Length && 1 <= CountIndex <= |a|)
    decreases CountIndex
    modifies b
    ensures p == Count(CountIndex,a)

{
    if CountIndex == 0 {
        p := 0;
    } else {
        var subCount := ComputeCount(CountIndex - 1, a, b);
        if a[CountIndex - 1] % 2 == 0 {
            p := 1 + subCount;
        } else {
            p := subCount;
        }
    }
}
