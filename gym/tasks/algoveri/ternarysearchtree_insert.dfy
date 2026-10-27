// intent: Your task is to implement the Insert operation for a Ternary Search Tree (TST) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/ternarysearchtree_insert/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Option<T> = Some(value: T) | None

datatype Node = Node(
    val: int,            // The character at this node (u8)
    is_end: bool,        // Does a key end here?
    left: Option<Node>,  // Char < val
    mid: Option<Node>,   // Char == val (next char)
    right: Option<Node>  // Char > val
) {
    // A node is "empty" if it marks no key and has no children.
    // Used for pruning (cleanup).
    ghost predicate is_empty() {
        && !this.is_end
        && this.left.None?
        && this.mid.None?
        && this.right.None?
    }

    // Structural Integrity + BST Invariants + Pruning
    // This is the core correctness predicate.
    ghost predicate well_formed() 
        decreases this
    {
        // 0. Type constraint for u8
        && 0 <= this.val < 256
        
        // 1. Recursive structural validity
        // 2. Pruning: No child should be "empty"
        // 3. BST Property: 
        //    - All keys in 'left' must start with char < this.val
        //    - All keys in 'right' must start with char > this.val
        
        // Check Left Child
        && (match this.left {
            case Some(l) => 
                && l.well_formed()
                && !l.is_empty()
                // The BST Invariant for Left:
                && (forall s | s in l.view() :: |s| > 0 && s[0] < this.val)
            case None => true
        })
        // Check Right Child
        && (match this.right {
            case Some(r) => 
                && r.well_formed()
                && !r.is_empty()
                // The BST Invariant for Right:
                && (forall s | s in r.view() :: |s| > 0 && s[0] > this.val)
            case None => true
        })
        // Check Middle Child (Trie Property)
        && (match this.mid {
            case Some(m) => 
                && m.well_formed()
                && !m.is_empty()
                // No character constraints on mid relative to this.val, 
                // because mid represents the *next* character.
            case None => true
        })
    }

    // Recursive definition of containment.
    // Note: TST nodes typically store non-empty paths relative to the parent's branching.
    ghost function contains(key: seq<int>): bool
        decreases this
    {
        if |key| == 0 then
            // A node always implies a character; empty string cannot reside "in" a node in this encoding
            false 
        else
            var c := key[0];
            if c < this.val then
                // Delegate to left, key remains same
                match this.left {
                    case Some(l) => l.contains(key)
                    case None => false
                }
            else if c > this.val then
                // Delegate to right, key remains same
                match this.right {
                    case Some(r) => r.contains(key)
                    case None => false
                }
            else
                // c == this.val. Match found.
                if |key| == 1 then
                    this.is_end
                else
                    // Continue to mid with the rest of the key
                    match this.mid {
                        case Some(m) => m.contains(key[1..])
                        case None => false
                    }
    }

    // View as a Set of byte sequences
    // Using iset (infinite set) for abstraction, though the actual set is finite.
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

ghost predicate opt_well_formed(node: Option<Node>) {
    match node {
        case Some(n) => n.well_formed() && !n.is_empty()
        case None => true
    }
}
//== signature
method insert(tree: Option<Node>, key: seq<int>) returns (res: Node)
    requires opt_well_formed(tree)
    // Constraint: Input key elements must represent bytes (u8)
    requires forall k :: k in key ==> 0 <= k < 256
    requires |key| > 0
    ensures 
        // Invariant Preservation
        && res.well_formed()
        && !res.is_empty()
        // Set Update
        && res.view() == opt_view(tree) + iset{key}
//== solution
