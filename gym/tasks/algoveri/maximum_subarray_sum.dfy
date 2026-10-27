// intent: Your task is to implement the algorithm for the Maximum Subarray Sum problem (commonly known as Kadane's Algorithm) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/maximum_subarray_sum/dafny_spec.dfy (Apache-2.0)
//== preamble
// Recursive definition of sum for a sequence slice [start, end)
ghost function spec_sum(s: seq<int>, start: int, end: int): int
    requires 0 <= start <= end <= |s|
    decreases end - start
{
    if start >= end then
        0
    else
        s[end - 1] + spec_sum(s, start, end - 1)
}
//== signature
method max_subarray_sum(s: seq<int>) returns (result: int)
    requires |s| > 0
    requires |s| <= 100000
    ensures
        forall i: int, j: int :: 0 <= i <= j <= |s| ==> spec_sum(s, i, j) <= result
    ensures
        exists i: int, j: int :: 0 <= i <= j <= |s| && spec_sum(s, i, j) == result
//== solution
