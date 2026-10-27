// intent: Your task is to implement the update (modify) operation for a Range Maximum Segment Tree using a functional (immutable) approach and verify its correctness in Dafny , where the operation updates the value at a specific index $idx$ to $v$ by creating a new version of the tree (path copying) via recursion—returning a new leaf for the base case and a new internal node with updated max value for the recursive step—while formally proving (1) Functional Correctness: in the returned tree, the value at $idx$ is exactly $v$, (2) Frame Preservation: for all other indices $k \neq idx$, the value is identical to the old tree, and (3) Invariant Preservation: the new tree maintains the is_segment_tree invariant, ensuring structural integrity and the Max property remain valid.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/segmenttree_modify/dafny_spec.dfy (Apache-2.0)
//== preamble
datatype Option<T> = Some(value: T) | None

datatype Node = Node(
    val: int,            // Stores the Max value for the current range (u64)
    low: int,            // Range lower bound (inclusive)
    high: int,           // Range upper bound (exclusive)
    left: Option<Node>,
    right: Option<Node>
) {
    // The view returns a Map from index -> value
    ghost function view(): map<int, int>
        decreases this
    {
        var left_view := match this.left {
            case Some(l) => l.view()
            case None => map[]
        };
        var right_view := match this.right {
            case Some(r) => r.view()
            case None => map[]
        };
        
        // Leaf logic: if no children, we represent the point 'low'.
        if left.None? && right.None? then
            map[low := val]
        else
            // Union of disjoint domains
            left_view + right_view
    }

    // Checks structural integrity and the Max property
    ghost predicate is_segment_tree()
        decreases this
    {
        // 1. Basic Range Validity (and u64 constraints)
        && 0 <= this.low < this.high
        && 0 <= this.val
        
        // 2. Structural Recursion
        && (match (this.left, this.right) {
            case (Some(l), Some(r)) => 
                // Internal Node
                var mid := (this.low + this.high) / 2;
                
                // Child ranges must line up exactly
                && l.low == this.low && l.high == mid
                && r.low == mid && r.high == this.high
                
                // Recursive validity
                && l.is_segment_tree()
                && r.is_segment_tree()
                
                // The Max Property: Node val must be max of children
                && this.val == (if l.val > r.val then l.val else r.val)

            case (None, None) => 
                // Leaf Node
                // Must represent a single point
                && this.high == this.low + 1
                // Implicitly, val is the value of this leaf
                && true

            case _ => false // Segment trees are full binary trees (0 or 2 children)
        })
        
        // 3. View Consistency (The view domain matches the range)
        && (forall k :: k in this.view() <==> this.low <= k < this.high)
        // 4. Value Consistency (The stored val is >= all items in view)
        && (forall k :: k in this.view() ==> this.view()[k] <= this.val)
    }
}

// Renamed 'modify' to 'update' to avoid keyword collision in Dafny
//== signature
method update(node: Node, idx: int, v: int) returns (res: Node)
    // Constraint: unsigned integers
    requires v >= 0
    requires node.is_segment_tree()
    requires node.low <= idx < node.high
    ensures 
        && res.is_segment_tree()
        && res.low == node.low
        && res.high == node.high
        // Functional Correctness & Frame Preservation:
        // The view matches the old view, but with the specific key updated
        && res.view() == node.view()[idx := v]
//== solution
