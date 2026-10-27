// intent: Your task is to implement the Splay operation in a splay tree (a binary search tree) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/splaytree_splay/dafny_spec.dfy (Apache-2.0)
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
method splay(tree: Tree, v: int) returns (res: Tree)
    // tree is Box<Node>, so it cannot be Empty
    requires tree.Node?
    requires is_bst(tree)
    // res is Box<Node>, so it cannot be Empty
    ensures res.Node?
    ensures is_bst(res)
    ensures view(res) == view(tree)
    // Postcondition: If v was in the tree, it is now at the root.
    ensures v in view(tree) ==> res.val == v
    // Postcondition: If v was NOT in the tree, the new root is 
    // the last node accessed (implicitly true if res.Node?, but kept for fidelity)
    ensures v !in view(tree) ==> res.val in view(res)
//== solution
