// intent: Your task is to implement the build operation for a Range Maximum Segment Tree and verify its correctness in Dafny .
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/segmenttree_build/dafny_spec.dfy (Apache-2.0)
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
        
        // We construct the union. Since domains are disjoint in a valid segment tree,
        // map union (+) is sufficient.
        // For a leaf (left=None, right=None), we implicitly represent the point 'low'.
        // However, the recursive logic below relies on 'is_segment_tree' to enforce leaf structure.
        // A strictly structural view definition:
        if left.None? && right.None? then
            map[low := val] // Leaf logic implicit in Verus spec via "leaf -> true" and view consistency check
        else
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
                // Implicitly, val is the value of this leaf, which is consistent
                && true

            case _ => false // Segment trees are full binary trees (0 or 2 children)
        })
        
        // 3. View Consistency (The view domain matches the range)
        && (forall k :: k in this.view() <==> this.low <= k < this.high)
        // 4. Value Consistency (The stored val is >= all items in view)
        && (forall k :: k in this.view() ==> this.view()[k] <= this.val)
    }
}
//== signature
method build(l: int, r: int) returns (res: Node)
    // Constraint: unsigned integers
    requires 0 <= l < r
    ensures 
        && res.is_segment_tree()
        && res.low == l
        && res.high == r
        // All values in the map are initialized to 0
        && (forall k :: l <= k < r ==> k in res.view() && res.view()[k] == 0)
//== solution
