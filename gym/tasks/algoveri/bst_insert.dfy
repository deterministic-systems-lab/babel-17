// intent: Your task is to implement a Binary Search Tree and verify that it correctly implements a mathematical Set in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/bst_insert/dafny_spec.dfy (Apache-2.0)
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
method insert(tree: Tree, v: int) returns (res: Tree)
    requires v >= 0 
    requires is_bst(tree)
    ensures is_bst(res)
    ensures view(res) == view(tree) + {v}
//== solution
