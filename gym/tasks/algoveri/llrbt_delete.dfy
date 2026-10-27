// intent: Your task is to implement and verify the deletion algorithm for a Left-Leaning Red-Black Tree (LLRBT) in Dafny , which requires maintaining the invariant that we never delete a node from a "2-node" (a Black node with no Red children) to avoid violating Black Height, necessitating the implementation of helper logic (move_red_left, move_red_right) to "push" Red links down from the root to the target node so that the node to be deleted is Red or part of a 3-node cluster; specifically, you must prove that (1) Functional Correctness: the resulting view() contains all original elements except v, and (2) Invariant Maintenance: the resulting tree satisfies is_llrbt() (maintaining balanced Black Height and color rules), while verifying that helpers preserve Black Height by performing "reverse color flips" and optional rotations.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/llrbt_delete/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Option<T> = Some(value: T) | None

datatype Node = Node(
    val: int,            // u64 -> int
    is_red: bool,
    left: Option<Node>,
    right: Option<Node>
) {
    // Standard Set View
    ghost function view(): set<int>
        decreases this
    {
        var left_set := match this.left { case Some(l) => l.view() case None => {} };
        var right_set := match this.right { case Some(r) => r.view() case None => {} };
        left_set + right_set + {this.val}
    }

    // Standard BST Order
    ghost predicate is_bst()
        decreases this
    {
        (match this.left {
            case Some(l) => (forall x :: x in l.view() ==> x < this.val) && l.is_bst()
            case None => true
        }) && (match this.right {
            case Some(r) => (forall x :: x in r.view() ==> x > this.val) && r.is_bst()
            case None => true
        })
    }

    // --- LLRBT SPECIFICS ---

    // Black Height: Returns -1 if invalid
    ghost function black_height(): int
        decreases this
    {
        var lh := match this.left { case Some(l) => l.black_height() case None => 1 };
        var rh := match this.right { case Some(r) => r.black_height() case None => 1 };
        
        if lh != -1 && rh != -1 && lh == rh then
            if !this.is_red then lh + 1 else lh
        else
            -1
    }

    // Local Red-Black Rules
    ghost predicate satisfies_red_props() 
        decreases this
    {
        var left_ok := match this.left { case Some(l) => l.satisfies_red_props() case None => true };
        var right_ok := match this.right { case Some(r) => r.satisfies_red_props() case None => true };
        
        // Rule: No Right-Leaning Red
        var right_is_black := match this.right { case Some(r) => !r.is_red case None => true };

        // Rule: No Double Red on Left
        var no_double_red := match this.left {
            case Some(l) => if l.is_red then match l.left { case Some(ll) => !ll.is_red case None => true } else true
            case None => true
        };

        left_ok && right_ok && right_is_black && no_double_red
    }

    // Main Invariant
    // Note: This allows the root to be Red or Black, 
    // which enables us to use it in the recursive insert spec.
    ghost predicate is_llrbt() {
        this.is_bst() && 
        this.black_height() != -1 && 
        this.satisfies_red_props()
    }
}

// Helper to handle Option<Node> in specs
ghost predicate is_llrbt_opt(tree: Option<Node>) {
    match tree { case Some(n) => n.is_llrbt() case None => true }
}

ghost function view_opt(tree: Option<Node>): set<int> {
    match tree { case Some(n) => n.view() case None => {} }
}

// Operation: Delete
//== signature
method delete(tree: Option<Node>, v: int) returns (res: Option<Node>)
    requires is_llrbt_opt(tree)
    ensures 
        // Functional Correctness
        view_opt(res) == view_opt(tree) - {v}
    ensures
        // Invariant Maintenance
        is_llrbt_opt(res)
//== solution
