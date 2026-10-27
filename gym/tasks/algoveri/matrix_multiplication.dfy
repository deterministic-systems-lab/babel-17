// intent: Your task is to implement Matrix Multiplication and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/matrix_multiplication/dafny_spec.dfy (Apache-2.0)
//== preamble
// Calculate dot product of row A[r] and col B[c]
function dot_product(row_vals: seq<int>, B_vals: seq<seq<int>>, c: int, k: int): int
    // k must be within bounds of the row vector we are iterating
    requires 0 <= k <= |row_vals|
    // k must be within bounds of the matrix B (number of rows)
    requires 0 <= k <= |B_vals|
    // The column index c must be valid for every row in B we access
    requires forall i :: 0 <= i < k ==> 0 <= c < |B_vals[i]|
    decreases k
{
    if k <= 0 then 0
    else row_vals[k-1] * B_vals[k-1][c] + dot_product(row_vals, B_vals, c, k-1)
}

// Helper to check if a matrix is valid (all rows have same length 'cols')
predicate is_valid_matrix(m: seq<seq<int>>, rows: int, cols: int)
{
    |m| == rows &&
    (forall i :: 0 <= i < rows ==> |m[i]| == cols)
}
//== signature
method matrix_multiply(A: seq<seq<int>>, B: seq<seq<int>>) returns (C: seq<seq<int>>)
    requires |A| > 0 && |B| > 0
    requires |A[0]| == |B| // cols A == rows B
    requires |A| <= 10 
    requires |B| <= 10
    requires |B[0]| <= 10
    // A is a valid n x m matrix
    requires forall i :: 0 <= i < |A| ==> |A[i]| == |B|
    // B is a valid m x k matrix
    requires forall i :: 0 <= i < |B| ==> |B[i]| == |B[0]|
    // Value bounds
    requires forall i, j :: 0 <= i < |A| && 0 <= j < |A[i]| ==> 0 <= A[i][j] <= 100
    requires forall i, j :: 0 <= i < |B| && 0 <= j < |B[i]| ==> 0 <= B[i][j] <= 100

    ensures |C| == |A|
    ensures |C| > 0 ==> |C[0]| == |B[0]|
    // Result C is valid Size(A) x Size(B[0])
    ensures is_valid_matrix(C, |A|, |B[0]|)
    // Each element is the dot product
    ensures forall i, j :: 
        (0 <= i < |C| && 0 <= j < |C[0]| ==> C[i][j] == dot_product(A[i], B, j, |B|))
//== solution
