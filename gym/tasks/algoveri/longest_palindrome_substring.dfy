// intent: Your task is to implement Manacher's algorithm for the Longest Palindromic Substring and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/longest_palindrome_substring/dafny_spec.dfy (Apache-2.0)
//== preamble
// Definition of a Palindrome:
// A sequence is a palindrome if for every index i, the character at i
// is identical to the character at the symmetric position from the end.
predicate is_palindrome(s: seq<int>) {
    // We trigger on s[i] so the solver knows to use this rule 
    // whenever it sees an access to s at index i.
    forall i :: 0 <= i < |s| ==> s[i] == s[|s| - 1 - i]
}

// Helper to check validity of a subrange within a larger sequence.
predicate is_valid_subrange(s: seq<int>, start: int, len: int) {
    && 0 <= start
    && 0 <= len
    && start + len <= |s|
}

// The main verification target.
// Returns a tuple (start_index, length) representing the longest palindrome.
//== signature
method longest_palindromic_substring(s: seq<int>) returns (res: (int, int))
    requires
        // CONSTRAINT: Hard limit of 1,000,000. 
        // Even with Manacher's expansion (2*N + 1), the required size 
        // is ~2,000,001, which fits easily in u32/usize.
        |s| <= 1000000
    ensures
        // Type Constraint: Results must be non-negative (simulating usize)
        res.0 >= 0 && res.1 >= 0
    ensures
        // 1. The result defines a valid substring of the input.
        is_valid_subrange(s, res.0, res.1)
    ensures
        // 2. The substring found is indeed a palindrome.
        is_palindrome(s[res.0 .. res.0 + res.1])
    ensures
        // 3. Maximality: There exists no other valid palindromic substring 
        // with a length strictly greater than the result found.
        forall i, len :: 
            is_valid_subrange(s, i, len) && is_palindrome(s[i .. i + len])
            ==> len <= res.1
//== solution
