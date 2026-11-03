# B17-1: the agent reference manual's supplement (WP8)

This supplement is for the model writing B17-1. Read `docs/manual.md` first: everything there holds in B17-1 unless a section here changes it. This adds data types, tuples, `match`, ghost sets and maps, places, and two proof statements. Every example states its outcome, and `b17c/test_manual.py` checks each one at subset 1, as it checks the manual's.

The full semantics is `docs/b17-1.md`, written as changes to `docs/b17-0.md`. Its sections are cited as `b17-1.md` §2, and this supplement's own as §2 below. When they disagree, `b17-1.md` wins.

**How a task reaches you** (D112). You get a module header, the frozen `data` items and `ghost-fn`s the task's spec refers to, and one frozen `spec`. You return a `def` for that spec. You may add `lemma`s, `ghost-fn`s, `data` items, and `spec`-and-`def` pairs for helpers, but never edit the task's items.

**The toolchain** reads B17-1 by default: `b17c/agent.py check FILE`. A failed proof's counterexample shows a tuple or data value as a term, such as `(node 2 (leaf) (leaf))`. Sets, maps and multisets get no counterexample yet.

## 1. A module

<!-- expect: ok -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(ghost-fn size ((t tree)) int (decreases (rank t))
  (body (match t (case (leaf) 0) (case (node v l r) (+ 1 (+ (size l) (size r)))))))
(spec root_or (params (t tree) (d i64)) (returns (r i64))
  (ensures (=> (is leaf t) (== r d)))
  (effects))
(def root_or
  (body (match t
    (case (leaf) (return d))
    (case (node v l r) (return v)))))
```

- **`data`** declares a type and its constructors: `(data NAME (PARAMS) (CTOR (FIELD TYPE)...)...)`. With no parameters, write `()`.
- **`match`** takes a value apart, with one `case` per constructor, in declaration order. Each pattern binds the fields. There are no wildcards and no nested patterns.
- **`rank`** is a data value's height, so `(decreases (rank t))` proves a recursion on t's parts terminates.

## 2. Names and syntax

**Reserved words**, besides B17-0's: `data`, `case`, `match`, `is`, `field`, `tuple`, `get`, `replace`, `rank`, `iset`, `iset-lit`, `iset-of`, `map`, `map-lit`, `union`, `diff`, `inter`, `update`, `lookup`, `obtain`. Using one as a name is `E-PARSE-001`.

**Two namespaces** (D82). Types, meaning data types and type parameters, are one namespace, and values another. So a parameter `tree` of type `tree` is fine, and a type may share its name with its one constructor. The constructor is then a value name, so a parameter must be named apart from it:

<!-- expect: ok -->
```lisp
(data graph () (graph (adj (vec (vec i64)))))
(ghost-fn order ((g graph)) int (body (len (field g adj))))
```

- **Constructors are value names:** they can't share a name with an item, another constructor, or the core library's `none` and `some` (`E-TYPE-002`).
- **Fields** are unique within a data type, across all its constructors, and may repeat in other types.
- **Type parameters** may not repeat within their item, or be named `option`.

<!-- expect: E-TYPE-002 -->
```lisp
(data cell () (empty) (some (v i64)))
```

**Case binders** are locals of their arm. An item's locals never share a name, even in different arms (D41). A case binder also may not reuse a name in scope, including an enclosing quantifier's or `seq-build`'s binder, or a result inside `ensures` (D109):

<!-- expect: E-TYPE-002 -->
```lisp
(ghost-fn g ((o (option bool))) bool
  (body (forall ((x bool)) (match o (case (none) x) (case (some x) x)))))
```

**Two data types identical up to names** are `E-TYPE-002`, as two such specs are. That includes one identical to the core library's `option`.

## 3. Types

| Type | Runtime? |
|---|---|
| `(tuple T1 ... Tn)`, n ≥ 2 | when every Ti is |
| `D` or `(D T1 ... Tn)`, a data type | when every field type is, after substitution |
| `(vec T)` | for any runtime T, vectors of tuples and data included |
| `(ref (slice T))` | a spec's parameter only, for any runtime T |
| `(iset T)`, `(map K V)` | ghost only |
| `(seq T)`, `(multiset T)` | ghost only, now of any well-formed T |

So `(option i64)` is a runtime type and `(option int)` a ghost one. A ghost type in a spec's parameters, results or a runtime binding is `E-GHOST-002`:

<!-- expect: E-GHOST-002 -->
```lisp
(spec f (params (o (option int))) (returns (r i64)) (effects))
```

**A data type must be well-formed** (`E-TYPE-001` otherwise):
- it's applied to exactly as many types as it has parameters, so `(option i64 bool)` is wrong;
- it has a finite value, so some constructor's fields all have one;
- it never contains itself inside an `iset`, `map` or `multiset`;
- a vector field holds a runtime type;
- it uses itself only applied to its own parameters, in order.

<!-- expect: E-TYPE-001 -->
```lisp
(data loop () (more (next loop)))
```

Two data types that contain each other are `E-TERM-002`, as mutually recursive functions are:

<!-- expect: E-TERM-002 -->
```lisp
(data a () (ca (x b)))
(data b () (cb) (cb2 (y a)))
```

**Subtyping, in ghost code:** tuples, data types, sets, maps and multisets are covariant, so a `(tuple i64 bool)` is a `(tuple int bool)`. Nothing narrows, and vectors aren't covariant.

<!-- expect: ok -->
```lisp
(ghost-fn widen ((p (tuple i64 bool)) (o (option i64))) (tuple (tuple int bool) (option int)) (body (tuple p o)))
```

## 4. Runtime code, ghost code and literals

**Both contexts:** constructor calls, `match`, `is`, `field`, `tuple` and `get`.

**Ghost code only:** `rank`, sets, maps and their operations, and `==` on anything but `bool` and `i64`. In runtime code each is `E-GHOST-002`:

<!-- expect: E-GHOST-002 -->
```lisp
(spec f (params (p (tuple i64 i64))) (returns (r bool)) (effects))
(def f (body (return (== p p))))
```

Runtime code also can't build a value of a ghost data type (`E-GHOST-002`).

**Literals take their types from their destination** (D70):
- `(none)`, `(iset-lit)` and `(map-lit)` take their open types from where they go;
- with no destination, an open type is `int` in ghost code and `i64` in runtime code;
- an empty literal inside another value, as in `(some (seq-lit))`, takes its type where that value is used.

**In a comparison or join,** the second operand takes the first's type when that isn't `bool`, `i64` or `int`, unless only the first is a literal (D109). So put the value whose type you know first. A sequence literal takes its element type only from a `seq`, never from a vector or slice, so compared with a `(vec i64)` its integers are `int`s (D113):

<!-- expect: E-TYPE-001 -->
```lisp
(ghost-fn g () bool (body (== (none) (some true))))
```

<!-- expect: ok -->
```lisp
(ghost-fn g () bool (body (!= (some true) (none))))
```

## 5. Ownership

The manual's rules hold, with "vector" read as "moving value".

**Copying and moving.**
- **Copied:** `bool`, `i64`, and a tuple or data value whose types inside are all copied, unless its type is recursive. So `(option i64)` and `(tuple i64 bool)` are copied.
- **Moving:** vectors, recursive data types such as `tree`, and anything holding them. A moving value moves when it's used whole in an owned position, as a vector does.

<!-- expect: E-OWN-001 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(spec f (params (t tree)) (returns (r tree)) (effects))
(def f (body (let u tree t) (return t)))
```

**`match` in runtime code.**
- **A `match` statement** moves its scrutinee when that's a moving variable, and each arm owns the fields it binds. A moving scrutinee must be a variable, so bind a built value first.
- **A `match` expression** never moves anything, so its scrutinee must have a copied type.
- **Arms join moves** as an `if`'s branches do: a variable moved in an arm that continues past the `match` is moved afterwards. An arm that returns or panics doesn't count.

A data value can't be borrowed, so a recursive read of a tree consumes it. A function that must keep its tree returns it rebuilt.

<!-- expect: ok -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(spec has (params (t tree) (x i64)) (returns (r bool)) (effects))
(def has (decreases (rank t))
  (body (match t
    (case (leaf) (return false))
    (case (node v l r)
      (if (== v x) (return true)
        (if (< x v) (block (let ((bl bool)) (call has l x)) (return bl))
          (block (let ((br bool)) (call has r x)) (return br))))))))
```

**Places** name a part of a value: a variable, `(idx p i)`, `(get p K)` or `(field p F)`.
- **Reading:** a copied part is read freely. A moving part can only be read further, by `len`, `idx`, `get`, `field` or `is`, or viewed in ghost code. That holds for a slice's moving elements too: `(len (idx rows 0))` is fine, but a slice is read-only, so nothing in it moves or changes.
- **Moving out:** using a moving part whole moves it out of its place, which is `E-OWN-007`. That includes making it a `match` statement's scrutinee:

<!-- expect: E-OWN-007 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(data pair () (pair (fst tree) (snd tree)))
(spec f (params (p pair)) (returns (r tree)) (effects))
(def f (body (return (field p fst))))
```

- **Taking out:** `(let x T (replace p e))` moves p's value into x and leaves e in its place. p's root must be a `let-mut` local. It's the only way to move a value out of a place:

<!-- expect: ok -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(data pair () (pair (fst tree) (snd tree)))
(spec f (params (p pair)) (returns (r tree)) (effects))
(def f (body (let-mut q pair p) (let a tree (replace (field q fst) (leaf))) (return a)))
```

- **Updating:** `(set-idx p i e)` and `(push p e)` change a vector inside a place. Their root must be a `let-mut` local, or it's `E-OWN-003`.
- **Goals:** a `set-idx`, `push` or `replace` through a place carries a `BOUNDS` goal for each `idx` the place passes through, and a `FIELD` goal for each `field`. A `push` also has B17-0's `OVERFLOW` goal on the vector's length (D114). The root must still be live once the statement's values are evaluated, so `(push (field x kids) x)` is `E-OWN-001`.

**Building moving values** (`E-OWN-006`). A constructor call, `tuple`, `(vec-new)` or `seq-build` of a moving type may only be:
- the whole value of a `let`, `let-mut`, `set`, `return`, `set-idx`, `push` or `replace`;
- a runtime `seq-build`'s body;
- an argument of a constructor or `tuple` that is itself one of those.

  It may not be a call's argument or a `match` scrutinee: bind it to a variable first (D109). It may never come out of an `if` or `match` expression, or be read as a temporary, as in `(len (vec-new))`.

<!-- expect: E-OWN-006 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(spec f (params (c bool) (t tree)) (returns (r tree)) (effects))
(def f (body (return (if c (leaf) t))))
```

**Other rules:**
- **One argument each:** a moving variable may appear in only one argument of a def call, constructor or `tuple`, and in only one of a return's expressions (`E-OWN-005`). A lemma call is ghost, so it's exempt.
- **`seq-build` bodies:** a runtime `seq-build`'s body runs once per element, so it can't move a variable declared outside it (`E-OWN-004`).
- **Slices:** no type may contain one (`E-OWN-002`).

<!-- expect: E-OWN-005 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(spec f (params (t tree)) (returns (r (tuple tree tree))) (effects))
(def f (body (return (tuple t t))))
```

## 6. Effects

A constructor with a boxed field has effect `alloc`: a field whose type mentions its own data type other than inside a vector. `node` has two, so building one needs `alloc` (`E-EFF-001`). A trie's `(vec (option trie))` field isn't boxed.

<!-- expect: E-EFF-001 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(spec f (params (x i64)) (returns (r tree)) (effects))
(def f (body (let t tree (node x (leaf) (leaf))) (return t)))
```

## 7. Expressions and statements

**Data values and tuples:**
- **`(C e1 ... en)`:** a value of C's data type. Its type parameters come from the destination first, then the arguments.
- **`(is C e)`:** `bool`, for C a constructor of e's type.
- **`(field e F)`:** F's value. It carries a `FIELD` goal unless every constructor has F, so read fields inside the right `match` arm, or after `is`.
- **`(tuple e1 ... en)`:** a tuple of n ≥ 2 components, and `(get e K)` its K-th, for a literal K counting from 0.
- **`(rank e)`:** ghost only, `int`, for e a data value. Anything else, a tuple included, is `E-TYPE-001`.

**`match`.** It takes one arm per constructor, in the type's declaration order. A tuple's single arm is `(case (tuple a b) ...)`. A missing, repeated or misplaced arm is `E-TYPE-001`.
- **As an expression,** every arm has the match's type.
- **As a statement,** the arms are statements.
- **Inside each arm,** the verifier knows which constructor built the scrutinee.

<!-- expect: E-TYPE-001 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(ghost-fn g ((t tree)) int (body (match t (case (node v l r) v) (case (leaf) 0))))
```

**Sets and maps,** ghost only:
- **Sets:** `(iset-lit e*)`, `(iset-of ((x T)) e)` for every x where e holds, `union`, `diff`, `inter`, and `(contains s x)`.
- **Maps:** `(map-lit (k v)*)`, where a later entry with the same key wins, `(update m k v)`, `(lookup m k)` and `(contains m k)` for a key, and `union`, where the second map's values win.
- **`(lookup m k)`** carries the goal `(contains m k)`, `E-PROOF-BOUNDS`.

<!-- expect: ok -->
```lisp
(ghost-fn g ((s (iset int)) (m (map int bool))) bool
  (body (and (contains (union s (iset-lit 1 2)) 2) (lookup (update m 1 true) 1))))
```

**Quantifier binders** need an exact type (D90): `bool`, `int`, and sequences, sets, tuples and data types built only of exact types. Anything with an `i64`, a vector, a slice, a multiset or a map inside is inexact, and is `E-TYPE-001`. So is a data type that contains itself through a `seq`, such as `(data rose () (bud) (rose (kids (seq rose))))`. So quantify over `int`, and keep runtime data types out of binders:

<!-- expect: E-TYPE-001 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(ghost-fn g () bool (body (forall ((t tree)) true)))
```

**Lemma bodies** may also use `match`, `forall` statements and `obtain`.

**`forall` statements** (D99) apply a lemma at every value of their binders. They are allowed wherever a lemma call is.
- **The form:** `(forall ((x T) ...) (call L e*))`.
- **What follows:** from there on, for every x, L's `requires` implies its `ensures`.
- **Its `requires`** is no goal, so pass the binders and let it guard them.

<!-- expect: ok -->
```lisp
(lemma sq (params (k int)) (requires (> k 0)) (ensures (> (* k k) 0)) (body))
(lemma all (params) (ensures (forall ((k int)) (=> (> k 0) (> (* k k) 0))))
  (body (forall ((k int)) (call sq k))))
```

**`obtain`** (D100) proves an ∃ and names its witness. It's an immutable ghost local, visible to the end of its block. Its goal is the ∃, an `E-PROOF-ASSERT` when it fails.

<!-- expect: ok -->
```lisp
(lemma big (params (n int)) (ensures (exists ((m int)) (> m n)))
  (body (obtain ((m int)) (> m n)) (assert (> m n))))
```

## 8. Proof goals and proving

**New goals:**
- **`E-PROOF-FIELD`:** a field read's value was built by a constructor that has the field.
- **`E-PROOF-BOUNDS`:** it also covers a map lookup's key, and each `idx` a place passes through.

<!-- expect: E-PROOF-FIELD -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(spec root (params (t tree)) (returns (r i64)) (effects))
(def root (body (return (field t val))))
```

**What the verifier knows:**
- **`match` and `is`:** in each arm, the scrutinee equals its constructor applied to the binders.
- **`rank`:** it's at least 0, and a value's parts have smaller ranks. So `(decreases (rank t))` proves recursion on t's fields, in defs, lemmas and ghost-fns.
- **Ghost-fns** unfold only where a proof applies them (D106). To use a definition, mention the ghost-fn at the arguments you need, as an `assert` does.
- **Recursive ghost-fns:** their equations hold only for arguments of their parameter types that satisfy their `requires`.
- **Equality:** values compare field by field, and sets and maps by members.
  - Sequences compare by length and elements, and equal ones are the same sequence (D108).
  - A tuple or data value holding a sequence is compared by SMT equality, and so is a sequence used as a set's member, a map's key, a multiset's element or another sequence's element. So prove the sequences equal first, with an `assert`, and then the values that hold them are equal too:

<!-- expect: ok -->
```lisp
(lemma same (params (s (seq int))) (requires (>= (len s) 1))
  (ensures (== (tuple (concat (take s 1) (drop s 1)) 1) (tuple s 1)))
  (body (assert (== (concat (take s 1) (drop s 1)) s))))
```

<!-- expect: ok -->
```lisp
(lemma member (params (s (seq int)) (m (iset (seq int))))
  (requires (>= (len s) 1) (contains m s))
  (ensures (contains m (concat (take s 1) (drop s 1))))
  (body (assert (== (concat (take s 1) (drop s 1)) s))))
```

**Patterns from the suite's proofs** (`suite/b17-1/accept/`):
- **Long invariants:** write them as ghost-fns, so a loop invariant is one call the verifier unfolds only where needed. `bfs`, `coin_change` and `kruskal` do this.
- **A fact at every index:** prove it with a lemma at one index and a `forall` statement.
- **A recursive def on a tree** needs no loop invariant. Each recursive call's `ensures` describes a subtree, and the def proves its own from them, as `bst_insert` does.
- **Before changing a moving value,** keep a ghost snapshot of it, `(ghost-let before node n)`, and relate the new value to the old one with lemmas, as `trie_insert` does.
- **To match a moving field,** take it out with `replace` first, as `segmenttree_query` does.
- **To use an ∃** from a `requires` or a lemma, name its witness with `obtain`, then state what follows for it.

## 9. The core library's `option`

`(data option (t) (none) (some (value t)))` is in every B17-1 module. `option` is reserved as a type name, and `none` and `some` as value names. Read the value with `(field o value)` after `(is some o)`, or in a `match` arm. `(option i64)` is copied, and `(option tree)` moves.

<!-- expect: ok -->
```lisp
(spec get_or (params (o (option i64)) (d i64)) (returns (r i64))
  (ensures (=> (is none o) (== r d)))
  (effects))
(def get_or (body (match o (case (none) (return d)) (case (some v) (return v)))))
```

## 10. Codes

B17-1 adds one tier 0 code and one proof family. Its other new rules reuse B17-0's codes.

| Code | Section | Meaning |
|---|---|---|
| `E-OWN-007` | 5 | A moving value moved out of a place: whole in an owned position, or as a runtime `match` statement's scrutinee |
| `E-PROOF-FIELD` | 8 | A field read's value wasn't proved built by a constructor that has the field |

Where B17-1's rules reuse codes:
- **`E-PARSE-001`:** a reserved word as a name, and `replace` outside a `let` or `let-mut` initializer.
- **`E-TYPE-001`:** a malformed data type, a misplaced `match` arm, a field or constructor of the wrong type, `get` out of range, and an inexact binder.
- **`E-TYPE-002`:** a reused type, constructor, field or case-binder name, and two data types identical up to names.
- **`E-GHOST-002`:** a ghost type or value, `rank`, a set or map, or `==` on a compound value, in runtime code.
- **`E-OWN-001` to `E-OWN-006`:** §5's rules for moving values.
- **`E-EFF-001`:** a boxed constructor without `alloc`.
- **`E-TERM-002`:** two data types that contain each other.

## 11. A worked long proof

This is a complete module for another task, which verifies with no errors, as a worked example of a long proof:

<!-- expect: ok -->
```lisp
(module bfs
  (header
    (purpose "Find the length of a shortest path between two vertices of a directed graph, or report that none exists.")
    (invariants "A distance is the length of a shortest path; none means the target is unreachable.")
    (failures "Allocation failure aborts."))
  (data graph () (graph (adj (vec (vec i64)))))
  (ghost-fn well_formed ((g graph)) bool
    (body (forall ((u int) (i int))
      (=> (and (and (<= 0 u) (< u (len (field g adj)))) (and (<= 0 i) (< i (len (idx (field g adj) u)))))
          (and (<= 0 (idx (idx (field g adj) u) i)) (< (idx (idx (field g adj) u) i) (len (field g adj))))))))
  (ghost-fn size ((g graph)) int
    (body (len (field g adj))))
  (ghost-fn has_edge ((g graph) (u int) (v int)) bool
    (body (exists ((i int))
      (and (and (and (<= 0 u) (< u (len (field g adj)))) (and (<= 0 i) (< i (len (idx (field g adj) u)))))
           (== (idx (idx (field g adj) u) i) v)))))
  (ghost-fn is_path ((g graph) (p (seq int))) bool
    (body (and (> (len p) 0)
               (forall ((i int)) (=> (and (<= 0 i) (< i (- (len p) 1))) (has_edge g (idx p i) (idx p (+ i 1))))))))
  (ghost-fn reachable ((g graph) (start int) (end int)) bool
    (body (exists ((p (seq int)))
      (and (and (is_path g p) (== (idx p 0) start)) (== (idx p (- (len p) 1)) end)))))
  (ghost-fn is_shortest_distance ((g graph) (start int) (end int) (d int)) bool
    (body (and
      (exists ((p (seq int)))
        (and (and (and (is_path g p) (== (idx p 0) start)) (== (idx p (- (len p) 1)) end)) (== (len p) (+ d 1))))
      (forall ((p (seq int)))
        (=> (and (and (is_path g p) (== (idx p 0) start)) (== (idx p (- (len p) 1)) end)) (>= (len p) (+ d 1)))))))

  (ghost-fn ge_m1 ((dist (seq int))) bool
    (body (forall ((w int)) (=> (and (<= 0 w) (< w (len dist))) (>= (idx dist w) -1)))))
  (ghost-fn in_range ((queue (seq int)) (n int)) bool
    (body (forall ((k int)) (=> (and (<= 0 k) (< k (len queue))) (and (<= 0 (idx queue k)) (< (idx queue k) n))))))
  (ghost-fn queue_dist ((dist (seq int)) (queue (seq int))) bool
    (body (forall ((k int)) (=> (and (and (<= 0 k) (< k (len queue))) (and (<= 0 (idx queue k)) (< (idx queue k) (len dist))))
      (and (<= 0 (idx dist (idx queue k))) (<= (idx dist (idx queue k)) k))))))
  (ghost-fn positions ((dist (seq int)) (queue (seq int)) (pos (seq int))) bool
    (body (forall ((w int)) (=> (and (and (and (<= 0 w) (< w (len dist))) (< w (len pos))) (>= (idx dist w) 0))
      (and (and (<= 0 (idx pos w)) (< (idx pos w) (len queue))) (== (idx queue (idx pos w)) w))))))
  (ghost-fn sorted_q ((dist (seq int)) (queue (seq int))) bool
    (body (forall ((a int) (b int)) (=> (and (and (and (<= 0 a) (<= a b)) (< b (len queue))) (and (and (<= 0 (idx queue a)) (< (idx queue a) (len dist))) (and (<= 0 (idx queue b)) (< (idx queue b) (len dist)))))
      (<= (idx dist (idx queue a)) (idx dist (idx queue b)))))))
  (ghost-fn spread ((dist (seq int)) (queue (seq int)) (top int)) bool
    (body (forall ((b int)) (=> (and (and (<= 0 b) (< b (len queue))) (and (<= 0 (idx queue b)) (< (idx queue b) (len dist)))) (<= (idx dist (idx queue b)) top)))))
  (ghost-fn closed ((g graph) (dist (seq int)) (queue (seq int)) (head int)) bool
    (body (forall ((k int) (e int))
      (=> (and (and (and (<= 0 k) (< k head)) (< k (len queue)))
               (and (and (<= 0 (idx queue k)) (< (idx queue k) (len (field g adj))))
                    (and (and (<= 0 e) (< e (len (idx (field g adj) (idx queue k)))))
                         (and (and (<= 0 (idx (idx (field g adj) (idx queue k)) e)) (< (idx (idx (field g adj) (idx queue k)) e) (len dist)))
                              (< (idx queue k) (len dist))))))
          (and (>= (idx dist (idx (idx (field g adj) (idx queue k)) e)) 0)
               (<= (idx dist (idx (idx (field g adj) (idx queue k)) e)) (+ (idx dist (idx queue k)) 1)))))))
  (ghost-fn partial ((g graph) (dist (seq int)) (u int) (i int) (du int)) bool
    (body (forall ((e int))
      (=> (and (and (and (<= 0 e) (< e i)) (and (<= 0 u) (< u (len (field g adj)))))
               (and (< e (len (idx (field g adj) u)))
                    (and (<= 0 (idx (idx (field g adj) u) e)) (< (idx (idx (field g adj) u) e) (len dist)))))
          (and (>= (idx dist (idx (idx (field g adj) u) e)) 0) (<= (idx dist (idx (idx (field g adj) u) e)) (+ du 1)))))))
  (ghost-fn witnesses ((g graph) (start int) (dist (seq int)) (wit (seq (seq int)))) bool
    (body (forall ((w int)) (=> (and (and (and (<= 0 w) (< w (len dist))) (< w (len wit))) (>= (idx dist w) 0))
      (and (is_path g (idx wit w))
           (and (and (== (idx (idx wit w) 0) start) (== (len (idx wit w)) (+ (idx dist w) 1)))
                (== (idx (idx wit w) (- (len (idx wit w)) 1)) w)))))))
  (ghost-fn far ((g graph) (start int) (w int) (bound int)) bool
    (body (forall ((p (seq int))) (=> (and (and (is_path g p) (== (idx p 0) start)) (== (idx p (- (len p) 1)) w))
      (>= (len p) bound)))))
  (ghost-fn minimal ((g graph) (start int) (dist (seq int))) bool
    (body (forall ((w int)) (=> (and (and (<= 0 w) (< w (len dist))) (>= (idx dist w) 0)) (far g start w (+ (idx dist w) 1))))))
  (ghost-fn below ((dist (seq int)) (pos (seq int)) (head int) (lim int)) bool
    (body (forall ((w int)) (=> (and (and (and (<= 0 w) (< w (len dist))) (< w (len pos))) (and (>= (idx dist w) 0) (< (idx dist w) lim)))
      (< (idx pos w) head)))))
  (ghost-fn notin ((queue (seq int)) (v int)) bool
    (body (forall ((k int)) (=> (and (<= 0 k) (< k (len queue))) (!= (idx queue k) v)))))
  (ghost-fn upd ((s0 (seq int)) (s1 (seq int)) (v int) (x int)) bool
    (body (and (and (== (len s1) (len s0)) (and (<= 0 v) (< v (len s0))))
               (and (== (idx s1 v) x) (forall ((w int)) (=> (and (and (<= 0 w) (< w (len s0))) (!= w v)) (== (idx s1 w) (idx s0 w))))))))
  (ghost-fn updw ((s0 (seq (seq int))) (s1 (seq (seq int))) (v int) (x (seq int))) bool
    (body (and (and (== (len s1) (len s0)) (and (<= 0 v) (< v (len s0))))
               (and (== (idx s1 v) x) (forall ((w int)) (=> (and (and (<= 0 w) (< w (len s0))) (!= w v)) (== (idx s1 w) (idx s0 w))))))))
  (ghost-fn appended ((q0 (seq int)) (q1 (seq int)) (v int)) bool
    (body (and (and (== (len q1) (+ (len q0) 1)) (== (idx q1 (len q0)) v))
               (forall ((k int)) (=> (and (<= 0 k) (< k (len q0))) (== (idx q1 k) (idx q0 k)))))))

  (lemma count_nonneg (params (s (seq int)) (x int) (k int))
    (requires (and (<= 0 k) (<= k (len s))))
    (ensures (>= (occurrences (take s k) x) 0))
    (decreases k)
    (body (if (> k 0) (call count_nonneg s x (- k 1)) (block))))
  (lemma count_member (params (s (seq int)) (j int) (k int))
    (requires (and (and (<= 0 j) (< j k)) (<= k (len s))))
    (ensures (>= (occurrences (take s k) (idx s j)) 1))
    (decreases k)
    (body (if (> k (+ j 1)) (call count_member s j (- k 1)) (call count_nonneg s (idx s j) j))))
  (lemma reach (params (g graph) (start int) (dist (seq int)) (queue (seq int)) (pos (seq int)) (head int) (lim int)
                       (p (seq int)) (m int))
    (requires
      (well_formed g) (== (len dist) (len (field g adj))) (and (<= 0 start) (< start (len dist))) (== (idx dist start) 0)
      (and (<= 0 head) (<= head (len queue))) (in_range queue (len dist)) (== (len pos) (len dist))
      (positions dist queue pos) (below dist pos head lim) (closed g dist queue head)
      (is_path g p) (== (idx p 0) start) (and (and (<= 0 m) (< m (len p))) (<= m lim)))
    (ensures
      (and (<= 0 (idx p m)) (< (idx p m) (len dist)))
      (and (>= (idx dist (idx p m)) 0) (<= (idx dist (idx p m)) m)))
    (decreases m)
    (body
      (if (> m 0)
        (block
          (call reach g start dist queue pos head lim p (- m 1))
          (assert (has_edge g (idx p (- m 1)) (idx p m)))
          (obtain ((e int)) (and (and (<= 0 e) (< e (len (idx (field g adj) (idx p (- m 1))))))
                                 (== (idx (idx (field g adj) (idx p (- m 1))) e) (idx p m))))
          (assert (== (idx queue (idx pos (idx p (- m 1)))) (idx p (- m 1)))))
        (block))))
  (lemma no_shorter (params (g graph) (start int) (dist (seq int)) (queue (seq int)) (pos (seq int)) (head int) (lim int) (v int))
    (requires
      (well_formed g) (== (len dist) (len (field g adj))) (and (<= 0 start) (< start (len dist))) (== (idx dist start) 0)
      (and (<= 0 head) (<= head (len queue))) (in_range queue (len dist)) (== (len pos) (len dist))
      (positions dist queue pos) (below dist pos head lim) (closed g dist queue head)
      (and (<= 0 v) (< v (len dist))) (== (idx dist v) -1))
    (ensures (far g start v (+ lim 2)))
    (body (forall ((p (seq int))) (call reach g start dist queue pos head lim p (- (len p) 1)))))
  (lemma below_from_sorted (params (dist (seq int)) (queue (seq int)) (pos (seq int)) (head int) (du int))
    (requires (sorted_q dist queue) (positions dist queue pos) (in_range queue (len dist)) (== (len pos) (len dist))
              (and (<= 0 head) (< head (len queue))) (== (idx dist (idx queue head)) du))
    (ensures (below dist pos head du))
    (body))
  (lemma below_all (params (dist (seq int)) (queue (seq int)) (pos (seq int)) (head int) (lim int))
    (requires (positions dist queue pos) (== (len pos) (len dist)) (== head (len queue)))
    (ensures (below dist pos head lim))
    (body))
  (lemma step_ge (params (dist0 (seq int)) (dist (seq int)) (v int) (x int))
    (requires (ge_m1 dist0) (upd dist0 dist v x) (>= x 0))
    (ensures (ge_m1 dist))
    (body))
  (lemma step_range (params (queue0 (seq int)) (queue (seq int)) (v int) (n int))
    (requires (in_range queue0 n) (appended queue0 queue v) (and (<= 0 v) (< v n)))
    (ensures (in_range queue n))
    (body))
  (lemma step_qdist (params (dist0 (seq int)) (queue0 (seq int)) (dist (seq int)) (queue (seq int)) (v int) (x int))
    (requires (queue_dist dist0 queue0) (in_range queue0 (len dist0)) (notin queue0 v) (upd dist0 dist v x)
              (appended queue0 queue v) (and (<= 0 x) (<= x (len queue0))))
    (ensures (queue_dist dist queue))
    (body))
  (lemma step_pos (params (dist0 (seq int)) (queue0 (seq int)) (pos0 (seq int)) (dist (seq int)) (queue (seq int))
                          (pos (seq int)) (v int) (x int))
    (requires (positions dist0 queue0 pos0) (== (len pos0) (len dist0)) (upd dist0 dist v x) (== (idx dist0 v) -1)
              (appended queue0 queue v) (upd pos0 pos v (len queue0)))
    (ensures (positions dist queue pos))
    (body))
  (lemma step_sorted (params (dist0 (seq int)) (queue0 (seq int)) (dist (seq int)) (queue (seq int)) (v int) (x int))
    (requires (sorted_q dist0 queue0) (spread dist0 queue0 x) (in_range queue0 (len dist0)) (notin queue0 v)
              (upd dist0 dist v x) (appended queue0 queue v))
    (ensures (sorted_q dist queue))
    (body))
  (lemma step_spread (params (dist0 (seq int)) (queue0 (seq int)) (dist (seq int)) (queue (seq int)) (v int) (x int))
    (requires (spread dist0 queue0 x) (in_range queue0 (len dist0)) (notin queue0 v) (upd dist0 dist v x) (appended queue0 queue v))
    (ensures (spread dist queue x))
    (body))
  (lemma step_closed (params (g graph) (dist0 (seq int)) (queue0 (seq int)) (dist (seq int)) (queue (seq int)) (head int)
                             (v int) (x int))
    (requires (closed g dist0 queue0 head) (<= head (len queue0)) (in_range queue0 (len dist0)) (notin queue0 v)
              (upd dist0 dist v x) (== (idx dist0 v) -1) (appended queue0 queue v))
    (ensures (closed g dist queue head))
    (body))
  (lemma step_partial (params (g graph) (dist0 (seq int)) (dist (seq int)) (u int) (i int) (du int) (v int))
    (requires (partial g dist0 u i du) (upd dist0 dist v (+ du 1)) (== (idx dist0 v) -1) (>= du 0)
              (and (<= 0 u) (< u (len (field g adj)))) (and (<= 0 i) (< i (len (idx (field g adj) u))))
              (== (idx (idx (field g adj) u) i) v))
    (ensures (partial g dist u (+ i 1) du))
    (body))
  (lemma step_partial_seen (params (g graph) (dist (seq int)) (u int) (i int) (du int))
    (requires (partial g dist u i du) (and (<= 0 u) (< u (len (field g adj)))) (and (<= 0 i) (< i (len (idx (field g adj) u))))
              (and (<= 0 (idx (idx (field g adj) u) i)) (< (idx (idx (field g adj) u) i) (len dist)))
              (and (>= (idx dist (idx (idx (field g adj) u) i)) 0) (<= (idx dist (idx (idx (field g adj) u) i)) (+ du 1))))
    (ensures (partial g dist u (+ i 1) du))
    (body))
  (lemma step_wit (params (g graph) (start int) (dist0 (seq int)) (wit0 (seq (seq int))) (dist (seq int)) (wit (seq (seq int)))
                          (u int) (v int) (x int))
    (requires (witnesses g start dist0 wit0) (== (len wit0) (len dist0)) (and (<= 0 u) (< u (len dist0))) (!= u v)
              (>= (idx dist0 u) 0) (== x (+ (idx dist0 u) 1)) (has_edge g u v)
              (upd dist0 dist v x) (updw wit0 wit v (concat (idx wit0 u) (seq-lit v))))
    (ensures (witnesses g start dist wit))
    (body))
  (lemma step_min (params (g graph) (start int) (dist0 (seq int)) (dist (seq int)) (v int) (x int))
    (requires (minimal g start dist0) (upd dist0 dist v x) (far g start v (+ x 1)))
    (ensures (minimal g start dist))
    (body))
  (lemma step_head (params (g graph) (dist (seq int)) (queue (seq int)) (head int) (u int) (du int))
    (requires (and (<= 0 u) (< u (len (field g adj)))) (== (len dist) (len (field g adj)))
              (closed g dist queue head) (partial g dist u (len (idx (field g adj) u)) du)
              (and (<= 0 head) (< head (len queue))) (== (idx queue head) u) (== (idx dist u) du))
    (ensures (closed g dist queue (+ head 1)))
    (body))
  (lemma spread_up (params (dist (seq int)) (queue (seq int)) (head int) (du int))
    (requires (spread dist queue (+ du 1)) (sorted_q dist queue) (in_range queue (len dist))
              (and (<= 0 head) (< head (len queue))) (== (idx dist (idx queue head)) du))
    (ensures (=> (< (+ head 1) (len queue)) (spread dist queue (+ (idx dist (idx queue (+ head 1))) 1))))
    (body))
  (spec bfs_shortest_path
    (params (g graph) (start i64) (target i64))
    (returns (res (option i64)))
    (requires
      (well_formed g)
      (<= (size g) 10000)
      (and (<= 0 start) (< start (size g)))
      (and (<= 0 target) (< target (size g))))
    (ensures
      (match res
        (case (none) (not (reachable g start target)))
        (case (some d) (is_shortest_distance g start target d))))
    (effects alloc))
  (def bfs_shortest_path
    (body
      (let n i64 (len (field g adj)))
      (let-mut dist (vec i64) (seq-build n (fn (j) -1)))
      (set-idx dist start 0)
      (let-mut queue (vec i64) (vec-new))
      (push queue start)
      (ghost-let-mut pos (seq int) (seq-build n (fn (j2) 0)))
      (ghost-let-mut wit (seq (seq int)) (seq-build n (fn (j3) (seq-lit start))))
      (let-mut head i64 0)
      (while (< head (len queue))
        (invariant (and (<= 0 head) (<= head (len queue))))
        (invariant (== (len dist) n))
        (invariant (== (+ (len queue) (occurrences dist -1)) n))
        (invariant (>= (occurrences dist -1) 0))
        (invariant (ge_m1 dist))
        (invariant (in_range queue n))
        (invariant (queue_dist dist queue))
        (invariant (== (idx dist start) 0))
        (invariant (and (== (len pos) n) (== (len wit) n)))
        (invariant (positions dist queue pos))
        (invariant (sorted_q dist queue))
        (invariant (witnesses g start dist wit))
        (invariant (minimal g start dist))
        (invariant (=> (< head (len queue)) (spread dist queue (+ (idx dist (idx queue head)) 1))))
        (invariant (closed g dist queue head))
        (decreases (+ (* 2 (occurrences dist -1)) (- (len queue) head)))
        (let u i64 (idx queue head))
        (assert (and (<= 0 u) (< u n)))
        (let du i64 (idx dist u))
        (let q0 i64 (len queue))
        (let deg i64 (len (idx (field g adj) u)))
        (let-mut i i64 0)
        (while (< i deg)
          (invariant (and (<= 0 i) (<= i deg)))
          (invariant (< head (len queue)))
          (invariant (>= (len queue) q0))
          (invariant (== (idx queue head) u))
          (invariant (== (len dist) n))
        (invariant (== (+ (len queue) (occurrences dist -1)) n))
        (invariant (>= (occurrences dist -1) 0))
        (invariant (ge_m1 dist))
        (invariant (in_range queue n))
        (invariant (queue_dist dist queue))
        (invariant (== (idx dist start) 0))
        (invariant (and (== (len pos) n) (== (len wit) n)))
        (invariant (positions dist queue pos))
        (invariant (sorted_q dist queue))
        (invariant (witnesses g start dist wit))
        (invariant (minimal g start dist))
          (invariant (== (idx dist u) du))
          (invariant (spread dist queue (+ du 1)))
          (invariant (closed g dist queue head))
          (invariant (partial g dist u i du))
          (decreases (- deg i))
          (let v i64 (idx (idx (field g adj) u) i))
          (if (== (idx dist v) -1)
            (block
              (call count_member dist v (len dist))
              (call below_from_sorted dist queue pos head du)
              (call no_shorter g start dist queue pos head du v)
              (assert (notin queue v))
              (assert (has_edge g u v))
              (ghost-let dist0 (seq int) dist)
              (ghost-let queue0 (seq int) queue)
              (ghost-let pos0 (seq int) pos)
              (ghost-let wit0 (seq (seq int)) wit)
              (ghost-set pos (seq-build n (fn (j4) (if (== j4 v) (len queue) (idx pos j4)))))
              (ghost-set wit (seq-build n (fn (j5) (if (== j5 v) (concat (idx wit u) (seq-lit v)) (idx wit j5)))))
              (set-idx dist v (+ du 1))
              (push queue v)
              (assert (upd dist0 dist v (+ du 1)))
              (assert (appended queue0 queue v))
              (assert (upd pos0 pos v (len queue0)))
              (assert (updw wit0 wit v (concat (idx wit0 u) (seq-lit v))))
              (call step_ge dist0 dist v (+ du 1))
              (call step_range queue0 queue v n)
              (call step_qdist dist0 queue0 dist queue v (+ du 1))
              (call step_pos dist0 queue0 pos0 dist queue pos v (+ du 1))
              (call step_sorted dist0 queue0 dist queue v (+ du 1))
              (call step_spread dist0 queue0 dist queue v (+ du 1))
              (call step_closed g dist0 queue0 dist queue head v (+ du 1))
              (call step_partial g dist0 dist u i du v)
              (call step_wit g start dist0 wit0 dist wit u v (+ du 1))
              (call step_min g start dist0 dist v (+ du 1)))
            (call step_partial_seen g dist u i du))
          (set i (+ i 1)))
        (call step_head g dist queue head u du)
        (call spread_up dist queue head du)
        (set head (+ head 1)))
      (forall ((l int)) (call below_all dist queue pos head l))
      (forall ((p (seq int))) (call reach g start dist queue pos head (len p) p (- (len p) 1)))
      (if (== (idx dist target) -1)
        (return (none))
        (return (some (idx dist target)))))))
```
