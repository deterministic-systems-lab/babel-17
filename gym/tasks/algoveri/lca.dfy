// intent: Implement a function lowest_common_ancestor that finds the lowest common ancestor of two nodes in a binary tree.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/lca/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Tree = Nil | Node(val: int, left: Tree, right: Tree)

datatype Option<T> = None | Some(get: T) {
    predicate is_some() { this.Some? }
}

// Standard view as a Set of values
ghost function view(t: Tree): set<int> 
    decreases t
{
    match t {
        case Nil => {}
        case Node(v, l, r) => view(l) + view(r) + {v}
    }
}

ghost function contains(t: Tree, target: int): bool 
    decreases t
{
    match t {
        case Nil => false
        case Node(v, l, r) => v == target || contains(l, target) || contains(r, target)
    }
}

// We need to define what it means for a tree to have distinct values.
ghost predicate tree_distinct(t: Tree)
    decreases t
{
    match t {
        case Nil => true
        case Node(v, l, r) => 
            // 1. Left subtree is distinct
            tree_distinct(l) &&
            // 2. Right subtree is distinct
            tree_distinct(r) &&
            // 3. Current value is NOT in left or right subtrees
            !contains(l, v) &&
            !contains(r, v) &&
            // 4. Left and Right sets are disjoint (no shared values)
            (view(l) * view(r) == {}) // Set intersection is empty
    }
}

// With tree_distinct guaranteed, spec_get_depth is now unambiguous.
ghost function spec_get_depth(t: Tree, target: int): Option<int>
    decreases t
{
    match t {
        case Nil => None
        case Node(v, l, r) =>
            if v == target then
                Some(0)
            else
                var left_d := spec_get_depth(l, target);
                var right_d := spec_get_depth(r, target);
                if left_d.Some? then
                    Some(left_d.get + 1)
                else if right_d.Some? then
                    Some(right_d.get + 1)
                else
                    None
    }
}

ghost function spec_get_subtree(t: Tree, target: int): Tree
    decreases t
{
    match t {
        case Nil => Nil
        case Node(v, l, r) =>
            if v == target then
                t
            else
                var left_sub := spec_get_subtree(l, target);
                var right_sub := spec_get_subtree(r, target);
                if left_sub.Node? then left_sub else right_sub
    }
}

ghost predicate is_common_ancestor(t: Tree, anc_val: int, p: int, q: int) {
    var subtree := spec_get_subtree(t, anc_val);
    match subtree {
        case Node(_, _, _) => contains(subtree, p) && contains(subtree, q)
        case Nil => false
    }
}
//== signature
method lowest_common_ancestor(root: Tree, p: int, q: int) returns (res: Option<int>)
    requires p >= 0 // u64 constraint
    requires q >= 0 // u64 constraint
    requires contains(root, p)
    requires contains(root, q)
    // The tree must contain unique values.
    requires tree_distinct(root)
    ensures res.Some?
    ensures is_common_ancestor(root, res.get, p, q)
    ensures forall x: int :: is_common_ancestor(root, x, p, q) ==> 
        spec_get_depth(root, x).Some? && 
        spec_get_depth(root, res.get).Some? &&
        spec_get_depth(root, x).get <= spec_get_depth(root, res.get).get
//== solution
