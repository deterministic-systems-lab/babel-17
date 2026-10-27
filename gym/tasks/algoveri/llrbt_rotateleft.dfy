// intent: Your task is to implement and verify a left rotation (fixup_rotate_left) that enforces the "Left-Leaning" invariant for a Left-Leaning Red-Black Tree (LLRBT) in Dafny , ensuring that if a Red link appears on the right (Black Parent $\to$ Red Right Child), the edge is rotated to make it a Left Red link; specifically, you must prove (1) Structure: the original right child becomes the new root and the original parent becomes the new left child, (2) Set Preservation: the abstract view() remains identical, (3) Color Logic: the new root retains the old root's color (preserving external black height) while the new left child (old root) becomes Red, and (4) Balance Preservation: res.black_height() == node.black_height().
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/llrbt_rotateleft/dafny_spec.dfy (Apache-2.0)
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
    ghost predicate is_llrbt() {
        this.is_bst() && 
        this.black_height() != -1 && 
        this.satisfies_red_props()
    }
}

// Operation: Rotate Left (Fixup)
// Distinct from BST rotate because it MUST prove black_height is preserved.
//== signature
method fixup_rotate_left(node: Node) returns (res: Node)
    requires node.is_bst()
    requires node.right.Some? && node.right.value.is_red
    // Explicitly ensure the result structure allows property access
    ensures res.left.Some?
    ensures 
        // Structural
        res.is_bst()
    ensures
        res.view() == node.view()
    ensures
        // Colors & Balance
        res.black_height() == node.black_height() // The Critical Proof
    ensures
        res.is_red == node.is_red
    ensures
        res.left.value.is_red
//== solution
