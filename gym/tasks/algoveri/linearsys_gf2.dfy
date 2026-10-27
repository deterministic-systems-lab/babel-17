// intent: Your task is to implement a linear system solver for the field $GF(2)$ (integers modulo 2) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/linearsys_gf2/dafny_spec.dfy (Apache-2.0)
//== preamble
// 1. Field Arithmetic Helpers (GF(2))
function add_gf2(a: int, b: int): int {
    (a + b) % 2
}

function mul_gf2(a: int, b: int): int {
    (a * b) % 2
}

// 2. Validity Checks
predicate is_binary_vector(v: seq<int>) {
    forall i :: 0 <= i < |v| ==> (v[i] == 0 || v[i] == 1)
}

predicate is_binary_matrix(m: seq<seq<int>>, rows: int, cols: int) {
    |m| == rows &&
    // Added trigger { |m[i]| } implicitly via access or explicit if needed
    (forall i :: 0 <= i < rows ==> |m[i]| == cols) &&
    (forall i, j :: 0 <= i < rows && 0 <= j < cols 
        ==> (m[i][j] == 0 || m[i][j] == 1))
}

// 3. Dot Product Specification (Row * Vector)
// Recursive definition matching the Verus spec
function spec_dot_product_gf2(row: seq<int>, x: seq<int>, k: int): int
    decreases if k < 0 then 0 else k + 1
{
    if k < 0 then
        0
    else
        // Bounds check logic from Verus spec
        if k < |row| && k < |x| then
            add_gf2(
                mul_gf2(row[k], x[k]),
                spec_dot_product_gf2(row, x, k - 1)
            )
        else
            spec_dot_product_gf2(row, x, k - 1)
}

// 4. Matrix-Vector Multiplication Specification
predicate is_solution(a: seq<seq<int>>, b: seq<int>, x: seq<int>) {
    |a| == |b| &&
    |a| > 0 &&
    |x| == |a[0]| &&
    is_binary_vector(x) &&
    (forall i :: 0 <= i < |a| ==> 
        spec_dot_product_gf2(a[i], x, |x| - 1) == b[i])
}

// --- Type Conversion Helpers ---
// Dafny uses 'int' natively, so these are identity functions essentially,
// but kept to match the structure if we were wrapping types.
// Since the input is already seq<seq<int>>, we don't strictly need them
// but we define identity mappings for structural alignment.

function to_int_vec(s: seq<int>): seq<int> {
    s
}

function to_int_mat(s: seq<seq<int>>): seq<seq<int>> {
    s
}

// We use 'Option' pattern via a datatype in Dafny
datatype Option<T> = Some(value: T) | None
//== signature
method solve_linear_system_gf2(matrix: seq<seq<int>>, b: seq<int>) returns (res: Option<seq<int>>)
    requires |matrix| > 0
    requires |matrix[0]| > 0
    requires |matrix| == |b|
    requires |matrix| <= 100
    requires |matrix[0]| <= 100
    requires is_binary_matrix(matrix, |matrix|, |matrix[0]|)
    requires is_binary_vector(b)
    
    ensures match res
        case Some(x) => is_solution(matrix, b, x)
        case None => 
            forall x: seq<int> :: 
                (|x| == |matrix[0]| && is_binary_vector(x)) 
                ==> !is_solution(matrix, b, x)
//== solution
