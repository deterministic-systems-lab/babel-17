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
| `(iset T)`, `(map K V)` | ghost only |
| `(seq T)`, `(multiset T)` | ghost only, now of any well-formed T |

So `(option i64)` is a runtime type and `(option int)` a ghost one. A ghost type in a spec's parameters, results or a runtime binding is `E-GHOST-002`:

<!-- expect: E-GHOST-002 -->
```lisp
(spec f (params (o (option int))) (returns (r i64)) (effects))
```

**A data type must be well-formed** (`E-TYPE-001` otherwise):
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

**In a comparison or join,** the second operand takes the first's type, unless only the first is a literal (D109). So put the value whose type you know first:

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

**`match` in runtime code.** A `match` statement moves its scrutinee when that's a moving variable, and each arm owns the fields it binds. A `match` expression never moves anything, so its scrutinee must have a copied type. A data value can't be borrowed, so a recursive read of a tree consumes it. A function that must keep its tree returns it rebuilt.

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
- **Reading:** a copied part is read freely. A moving part can only be read further, by `len`, `idx`, `get`, `field` or `is`, or viewed in ghost code.
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

- **Updating:** `(set-idx p i e)` and `(push p e)` change a vector inside a place. Their root must be a `let-mut` local, or it's `E-OWN-003`. The root must still be live once the statement's values are evaluated, so `(push (field x kids) x)` is `E-OWN-001`.

**Building moving values** (`E-OWN-006`). A constructor call, `tuple`, `(vec-new)` or `seq-build` of a moving type may only be:
- the whole value of a `let`, `let-mut`, `set`, `return`, `set-idx`, `push` or `replace`;
- a runtime `seq-build`'s body, or a `match` statement's scrutinee;
- an argument of a constructor or `tuple` that is itself one of those.

  It may not be a call's argument: bind it to a variable first (D109). And it may never come out of an `if` or `match` expression.

<!-- expect: E-OWN-006 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(spec f (params (c bool) (t tree)) (returns (r tree)) (effects))
(def f (body (return (if c (leaf) t))))
```

**Other rules:**
- **One argument each:** a moving variable may appear in only one argument of a call, constructor or `tuple`, and in only one of a return's expressions (`E-OWN-005`).
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
- **`(rank e)`:** ghost only, `int`.

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
- **Maps:** `(map-lit (k v)*)`, `(update m k v)`, `(lookup m k)` and `(contains m k)` for a key, and `union`, where the second map's values win.
- **`(lookup m k)`** carries the goal `(contains m k)`, `E-PROOF-BOUNDS`.

<!-- expect: ok -->
```lisp
(ghost-fn g ((s (iset int)) (m (map int bool))) bool
  (body (and (contains (union s (iset-lit 1 2)) 2) (lookup (update m 1 true) 1))))
```

**Quantifier binders** need an exact type (D90): `bool`, `int`, and sequences, sets, tuples and data types built only of exact types. Anything with an `i64`, a vector, a slice, a multiset or a map inside is inexact, and is `E-TYPE-001`. So quantify over `int`, and keep runtime data types out of binders:

<!-- expect: E-TYPE-001 -->
```lisp
(data tree () (leaf) (node (val i64) (left tree) (right tree)))
(ghost-fn g () bool (body (forall ((t tree)) true)))
```

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
  - A tuple or data value holding a sequence is compared by SMT equality. So prove its sequences equal first, with an `assert`, and then the two values are equal:

<!-- expect: ok -->
```lisp
(lemma same (params (s (seq int))) (requires (>= (len s) 1))
  (ensures (== (tuple (concat (take s 1) (drop s 1)) 1) (tuple s 1)))
  (body (assert (== (concat (take s 1) (drop s 1)) s))))
```

**Patterns from the suite's proofs** (`suite/b17-1/accept/`):
- **Long invariants:** write them as ghost-fns, so a loop invariant is one call the verifier unfolds only where needed. `bfs`, `coin_change` and `kruskal` do this.
- **A fact at every index:** prove it with a lemma at one index and a `forall` statement.
- **A recursive def on a tree** needs no loop invariant. Each recursive call's `ensures` describes a subtree, and the def proves its own from them, as `bst_insert` does.

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
