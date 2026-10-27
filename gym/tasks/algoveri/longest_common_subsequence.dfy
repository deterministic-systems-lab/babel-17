// intent: Your task is to implement the Longest Common Subsequence (LCS) algorithm and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/longest_common_subsequence/dafny_spec.dfy (Apache-2.0)
//== preamble
// Helper for max
function max(a: int, b: int): int {
    if a > b then a else b
}

// LCS recursive specification
function lcs_spec(s1: seq<char>, s2: seq<char>): int
    decreases |s1|, |s2|
{
    if |s1| == 0 || |s2| == 0 then
        0
    else
        // Use s1[..|s1|-1] to get subrange excluding last element
        // Dafny syntax for slice is s[low..high]
        if s1[|s1|-1] == s2[|s2|-1] then
            1 + lcs_spec(s1[..|s1|-1], s2[..|s2|-1])
        else
            max(
                lcs_spec(s1[..|s1|-1], s2),
                lcs_spec(s1, s2[..|s2|-1])
            )
}
//== signature
method solve_longest_common_subsequence(s: seq<char>, t: seq<char>) returns (len: int)
    requires |s| <= 3000
    requires |t| <= 3000
    ensures len == lcs_spec(s, t)
    // Implicit constraint from usize in Verus
    ensures len >= 0
//== solution
