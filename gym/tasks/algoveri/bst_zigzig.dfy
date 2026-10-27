// intent: Your task is to implement the Zig-Zig operation (Double Right Rotation) in a binary search tree and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/bst_zigzig/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Tree = Empty | Node(val: int, left: Tree, right: Tree)

function view(tree: Tree): set<int>
    decreases tree
{
    match tree
    case Empty => {}
    case Node(val, left, right) => view(left) + view(right) + {val}
}

predicate is_bst(tree: Tree)
    decreases tree
{
    match tree
    case Empty => true
    case Node(val, left, right) =>
        (forall x :: x in view(left) ==> x < val) &&
        is_bst(left) &&
        (forall x :: x in view(right) ==> x > val) &&
        is_bst(right)
}
//== signature
method zig_zig(g: Tree) returns (res: Tree)
    // g corresponds to Box<Node>, so it is non-Empty
    requires g.Node?
    // g.left.is_some()
    requires g.left.Node?
    // g.left.get_Some_0().left.is_some()
    requires g.left.left.Node?
    requires is_bst(g)
    ensures is_bst(res)
    ensures view(res) == view(g)
    // X (grandchild) is now root
    ensures res.val == g.left.left.val
//== solution
