// intent: Your task is to implement the standard $O(N^2)$ algorithm for multiplying two polynomials and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/polymul_naive/dafny_spec.dfy (Apache-2.0)
//== preamble
// Helper to convert inputs. In Dafny, we use int directly, so this is identity.
ghost function to_int(s: seq<int>): seq<int> {
    s
}

// Helper: Enforce bounds on coefficients to prevent overflow.
ghost predicate coeffs_bounded(s: seq<int>) {
    forall i :: 0 <= i < |s| ==> -1_000_000 <= s[i] <= 1_000_000
}

// Recursive definition of the convolution sum
ghost function spec_convolution_sum(a: seq<int>, b: seq<int>, k: int, current_i: int): int
    decreases if current_i < 0 then 0 else current_i + 1
{
    if current_i < 0 then
        0
    else
        // Calculate the term for the current index i
        var term := if current_i < |a| && (k - current_i) < |b| && (k - current_i) >= 0 then
            a[current_i] * b[k - current_i]
        else
            0;
        // Recursive step
        term + spec_convolution_sum(a, b, k, current_i - 1)
}

// Wrapper for the full convolution coefficient at index k
ghost function spec_poly_mul_coeff(a: seq<int>, b: seq<int>, k: int): int {
    spec_convolution_sum(a, b, k, k)
}
//== signature
method poly_multiply(a: seq<int>, b: seq<int>) returns (res: seq<int>)
    requires |a| > 0
    requires |b| > 0
    requires |a| + |b| <= 1000
    // Safety Precondition: Coefficients are bounded
    requires coeffs_bounded(a)
    requires coeffs_bounded(b)
    
    ensures |res| == |a| + |b| - 1
    // Functional Correctness
    ensures forall k :: 0 <= k < |res| ==> res[k] == spec_poly_mul_coeff(a, b, k)
//== solution
