// intent: Your task is to implement the Search operation for a Byte-based Trie data structure (Prefix Tree) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/trie_search/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Option<T> = Some(value: T) | None

datatype Node = Node(
    is_end: bool,
    // A sequence of children, representing bytes 0..255
    children: seq<Option<Node>>
) {
    // A node is "empty" (useless) if it marks no key and leads to no keys.
    // Added requirement that children sequence must be size 256 for this check to be valid.
    predicate is_empty() 
        requires |this.children| == 256
    {
        !this.is_end && (forall i: int {:trigger this.children[i]} :: 0 <= i < 256 ==> this.children[i].None?)
    }

    // Standard structural integrity + The Pruning Invariant
    predicate well_formed() 
        decreases this
    {
        // 1. Must have exactly 256 slots (for u8)
        && |this.children| == 256
        // 2. Recursive check for all children
        && (forall i: int {:trigger this.children[i]} :: 0 <= i < 256 ==> 
            match this.children[i] {
                case Some(child) => 
                    // The child must be structurally valid
                    && child.well_formed()
                    // CRITICAL: The child must not be useless.
                    // Note: child.well_formed() guarantees |child.children| == 256, satisfying is_empty's precondition
                    && !child.is_empty()
                case None => true
            }
        )
    }

    // Recursive definition of containment
    function contains(key: seq<int>): bool
        decreases |key|
    {
        if |key| == 0 then
            this.is_end
        else
            var char_idx := key[0];
            if 0 <= char_idx < |this.children| then
                match this.children[char_idx] {
                    case Some(child) => child.contains(key[1..])
                    case None => false
                }
            else
                false
    }

    // View as a Set of byte sequences
    // Note: Using iset (infinite set) because Dafny 'set' is finite
    ghost function view(): iset<seq<int>> {
        iset key: seq<int> | this.contains(key)
    }
}

ghost function opt_view(node: Option<Node>): iset<seq<int>> {
    match node {
        case Some(n) => n.view()
        case None => iset{}
    }
}

predicate opt_well_formed(node: Option<Node>) {
    match node {
        case Some(n) => 
            // The node structure is valid
            && n.well_formed() 
            // The root itself must not be useless (if it is, the tree should be None)
            && !n.is_empty()
        case None => true
    }
}
//== signature
method search(tree: Option<Node>, key: seq<int>) returns (res: bool)
    requires opt_well_formed(tree)
    // Constraint: Input key elements must represent bytes (u8)
    requires forall k :: k in key ==> 0 <= k < 256 
    ensures res == (key in opt_view(tree))
//== solution
