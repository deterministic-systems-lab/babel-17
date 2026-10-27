// intent: Your task is to implement the Zig-Zag operation (Left-Right Rotation) in a binary search tree and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/bst_zigzag/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Tree = Empty | Node(val: int, left: Tree, right: Tree)

ghost function view(tree: Tree): set<int>
    decreases tree
{
    match tree
    case Empty => {}
    case Node(val, left, right) => view(left) + view(right) + {val}
}

ghost predicate is_bst(tree: Tree)
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
method zig_zag(g: Tree) returns (res: Tree)
    // g corresponds to Box<Node>, so it is non-Empty
    requires g.Node?
    // g.left is Some (P exists)
    requires g.left.Node?
    // g.left.right is Some (X exists - the 'Zig-Zag' shape)
    requires g.left.right.Node?
    requires is_bst(g)
    ensures is_bst(res)
    ensures view(res) == view(g)
    // X (the original grandchild) is now the root
    ensures res.val == g.left.right.val
//== solution
