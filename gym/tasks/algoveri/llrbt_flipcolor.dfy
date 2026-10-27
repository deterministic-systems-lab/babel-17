// intent: Your task is to implement and verify the flip_colors operation for a Left-Leaning Red-Black Tree (LLRBT) in Dafny , which is used to split a "4-node" (a conceptual node with 3 values, represented by a Black parent connected to two Red children) by "pushing" the Red links up the tree (turning the children Black and the parent Red).
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/llrbt_flipcolor/dafny_spec.dfy (Apache-2.0)
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

// Operation: Flip Colors
//== signature
method flip_colors(node: Node) returns (res: Node)
    requires node.left.Some? && node.right.Some?
    // Precondition: Parent color differs from children, children have same color
    // (Standard case: Black Parent, Red Children)
    requires node.is_red != node.left.value.is_red
    requires node.left.value.is_red == node.right.value.is_red
    // Explicitly ensure result children exist so .value access is safe
    ensures res.left.Some? && res.right.Some?
    ensures 
        res.view() == node.view()
    ensures
        res.is_bst() == node.is_bst()
    ensures
        // Preservation of Balance: Swapping colors here preserves Black Height
        res.black_height() == node.black_height()
    ensures
        // Toggles
        res.is_red != node.is_red
    ensures
        res.left.value.is_red != node.left.value.is_red
//== solution
