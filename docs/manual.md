# B17-0: the agent reference manual (WP8)

This manual is for the model writing B17-0. It gives every rule you need, every error code you can meet, and a minimal example of each. Every example states its outcome, and `b17c/test_manual.py` checks each one: in CI its tier 0 outcome, and wherever Z3 is installed its proof outcome too. So the examples can't drift from the language. The prose is checked by review.

The full semantics is `docs/b17-0.md`. Its sections are cited as `b17-0.md` §2, and this manual's own as §2 below. When the two disagree, `b17-0.md` wins, and the disagreement is a bug in this manual.

**How a task reaches you** (`b17-0.md` §10). You get a module header, frozen `ghost-fn`s and one frozen `spec`. You return a `def` for that spec. You may add `lemma`s, `ghost-fn`s, and `spec`-and-`def` pairs for helpers. You never edit the task's spec.

**How to use the toolchain** (§13 below). `b17c/agent.py check FILE` gives every error as JSON. For a failed proof it gives the goal, the items it depends on, and often a counterexample, with whether the interpreter reproduces it.

## 1. A module

<!-- expect: ok -->
```lisp
(module abs
  (header
    (purpose "Return the absolute value of an integer.")
    (invariants "The result is non-negative and equals x or its negation.")
    (failures "None. x = i64::MIN is excluded because its negation does not fit."))
  (spec abs
    (params (x i64))
    (returns (y i64))
    (requires (> x -9223372036854775808))
    (ensures (>= y 0) (or (== y x) (== y (neg x))))
    (effects))
  (def abs
    (body
      (if (< x 0) (return (neg x)) (return x)))))
```

- **The header** comes first: `purpose`, `invariants` and `failures`, each a string.
- **Items** follow in any order: `spec`, `def`, `ghost-fn` and `lemma`. A `def` implements the `spec` of the same name and never repeats its contracts (D39).
- **The spec's clauses** are `params`, `returns`, then `requires` and `ensures` if present, and always `effects`. Leave out an empty `requires` or `ensures` rather than writing `(requires)` (D54).
- **Clause order is fixed** (`b17-0.md` §2). A `ghost-fn` is `(ghost-fn NAME (param*) TYPE (requires e)* (decreases e)? (body e))`. A `lemma` is `(lemma NAME (params ...) (requires e*)? (ensures e*)? (decreases e)? (body stmt*))`. A `def` is `(def NAME (decreases e)? (body stmt*))`.
- **Effects** appear at most once each, in the order `alloc`, `panic`, `io`.
- **Layout** is free, but only whitespace may differ from the canonical form (`b17-0.md` §2):
  - whitespace is space, tab, line feed or carriage return, and list elements need at least one between them;
  - there are no comments;
  - integers have no `+`, no leading zeros and no `-0`, and `(neg 5)` is written `-5`;
  - strings escape only `\"` and `\\`, and hold no control characters;
  - lists nest at most 128 deep.
- **Items may refer to one another in any order.**

The examples below show only items. Each sits in a module with a header, like the one above.

## 2. Names

- **Shape:** a name matches `[a-z][a-z0-9_]*`.
- **Reserved:** every word of the grammar is reserved, such as `block`, `len` and `vec`, and using one as a name doesn't parse. The core library's names (§12 below) are reserved too, but declaring one is `E-TYPE-002`.
- **No shadowing** (D41): parameter and local names are unique within an item, even across separate blocks, and none may reuse an item's name.
- **Results** are unique among the spec's parameters and results (D66). They're in scope only in `ensures`, so a `def` may give a local its result's name.
- **Binders** of `forall`, `exists` and `fn` may not reuse any name in scope where they appear. Separate binders may share a name.
- **Scope** (D66): a local is visible from its declaration to the end of its `block`, loop body or `if` branch. A branch is one statement, so a `let` that forms a whole branch is visible nowhere after it.

<!-- expect: E-PARSE-001 -->
```lisp
(spec block (params) (returns) (effects))
```

<!-- expect: E-TYPE-002 -->
```lisp
(spec f (params (x i64)) (returns (r i64)) (effects))
(def f (body (let x i64 1) (return x)))
```

`x` is already a parameter. Name the local something else.

## 3. Types

| Type | Where | Values |
|---|---|---|
| `bool` | everywhere | `true`, `false` |
| `i64` | everywhere | integers in [-2^63, 2^63) |
| `int` | ghost code only | all integers |
| `(vec T)` | everywhere, owned | sequences of `bool` or `i64` |
| `(ref (slice T))` | a spec's parameters only | a borrowed vector, read-only |
| `(seq T)`, `(multiset T)` | ghost code only | sequences and multisets of `bool`, `i64` or `int` |

- **Collections don't nest** in B17-0, and there are no tuples, data types, strings or floats (`b17-0.md` §11).
- **Runtime code has no conversions** (D34): `i64` never mixes with `bool`.
- **In ghost code,** `i64` is a subtype of `int`, a vector or slice is viewed as a `seq`, and `(seq T)` and `(multiset T)` are subtypes of `(seq U)` and `(multiset U)` when T is of U (D107).
  - **So they compare:** `(multiset a)`, for a vector `a` of `i64`, compares with the multiset of a `(seq int)`, such as a core ghost-fn's result.
  - **Nothing narrows:** a `(seq int)` is never a `(seq i64)`. So state your own ghost-fns' and lemmas' collections over `int`, where every `i64` collection fits.
- **Element types** are only `bool`, `i64` and, in ghost code, `int`. Anything else, such as `(seq (seq int))`, is `E-TYPE-001` (D68).
- **A literal** is an `i64` in runtime code, and an `int` in ghost code unless its destination is an `i64` (D70).

<!-- expect: E-TYPE-001 -->
```lisp
(spec f (params (x i64)) (returns (r i64)) (effects))
(def f (body (return (+ x true))))
```

<!-- expect: E-GHOST-002 -->
```lisp
(spec f (params (x i64)) (returns (r i64)) (effects))
(def f (body (let n int 0) (return x)))
```

`int` is a ghost type, so a runtime local can't have it. Use `i64`, or `ghost-let` for a ghost local.

## 4. Specs, defs and calls

A spec may return several results. A caller binds them all with `(let ((x T) ...) (call f e*))`, or `let-mut` for mutable locals, one name per result (D43, D74). A callee with no results is called with a bare `(call f e*)`. Arguments are evaluated left to right, and an owned vector argument must be a live variable, which moves (D73).

<!-- expect: ok -->
```lisp
(spec divmod
  (params (a i64) (b i64))
  (returns (q i64) (r i64))
  (requires (>= a 0) (> b 0))
  (ensures (== a (+ (* q b) r)) (and (<= 0 r) (< r b)))
  (effects))
(def divmod (body (return (/ a b) (% a b))))
(spec half (params (a i64)) (returns (h i64)) (requires (>= a 0)) (ensures (<= h a)) (effects))
(def half (body (let ((q i64) (r i64)) (call divmod a 2)) (return q)))
```

- **Calls are modular:** the caller proves the callee's `requires` and assumes its `ensures`. It never sees the callee's body.
- **Clauses are checked in order:** each `requires`, `ensures` or loop invariant may assume the ones before it, so a later clause may index with a value an earlier one bounds.
- **`/` and `%` truncate toward zero,** as Rust's do (D37).
- **A call is a statement,** never an expression. A ghost-fn call, written `(NAME e*)`, is an expression in ghost code only.

<!-- expect: E-TYPE-002 -->
```lisp
(def orphan (body (return)))
```

Every `def` implements a spec of the same name (D39).

<!-- expect: E-TYPE-001 -->
```lisp
(spec one (params) (returns (r i64)) (ensures (== r 1)) (effects))
(def one (body (return 1)))
(spec caller (params) (returns) (effects))
(def caller (body (call one) (return)))
```

`(call one)` as a statement drops `one`'s result. Bind it with `(let ((x i64)) (call one))` (D74).

## 5. Expressions

- **Arithmetic:** `+`, `-`, `*`, `/`, `%` and `neg`.
  - In runtime code, `+`, `-`, `*` and `neg` carry an `OVERFLOW` goal that the result fits in `i64`.
  - `/` and `%` carry a `DIV` goal: a non-zero divisor and, in runtime code, not `-2^63` by `-1`, which Rust rejects even for `%`.
  - In ghost code, arithmetic is on `int`, and only `/` and `%` have a goal.
- **Comparison:** `<`, `<=`, `>` and `>=` take integers. `==` and `!=` take `bool` or integers, and collections in ghost code only (`E-GHOST-002` in runtime code, D71).
- **Logic:** `and`, `or` and `=>` are binary, so `(and a (and b c))`, and they short-circuit. `not` takes one operand.
- **`(if c a b)`** is an expression. In runtime code it can't produce a vector (`E-OWN-006`).
- **Sequences:** `(len s)` and `(idx s i)` work everywhere, and `len` is an `i64` in runtime code and an `int` in ghost code. `seq-lit`, `take`, `drop`, `concat`, `last`, `contains`, `multiset`, `msum` and `occurrences` are ghost-only. `idx`, `take`, `drop` and `last` carry `BOUNDS` goals.
- **Building:** `(seq-build n (fn (i) e))` has n elements, with `0 <= i < n` assumed inside e (D38), and a `BOUNDS` goal that n isn't negative. In runtime code it's a vector with effect `alloc`, and in ghost code a `seq`.

<!-- expect: ok -->
```lisp
(spec reverse
  (params (a (ref (slice i64))))
  (returns (r (vec i64)))
  (ensures (== (len r) (len a))
           (forall ((i int)) (=> (and (<= 0 i) (< i (len a))) (== (idx r i) (idx a (- (- (len a) 1) i))))))
  (effects alloc))
(def reverse (body (return (seq-build (len a) (fn (i) (idx a (- (- (len a) 1) i)))))))
```

## 6. Statements

| Statement | Does |
|---|---|
| `(let x T e)`, `(let-mut x T e)` | Declares a local, mutable with `let-mut` |
| `(set x e)` | Assigns a `let-mut` runtime local |
| `(set-idx v i e)`, `(push v e)` | Changes a `let-mut` vector in place, with a `BOUNDS` goal for `set-idx`; `push` has effect `alloc` |
| `(if c s1 s2)`, `(block s*)` | Branch and sequence; `(block)` does nothing |
| `(while c (invariant e)* (decreases d) s*)` | A loop: invariants, then its measure, then its body |
| `(call f e*)`, `(let ((x T) ...) (call f e*))` | Calls a def or lemma, binding one name per result; bare when it has none |
| `(return e*)` | Ends the def with one expression per result |
| `(panic "text")`, `(print e)` | Effects `panic` and `io`; `print` takes an `i64` |
| `(assert e)`, `(ghost-let x T e)`, `(ghost-let-mut x T e)`, `(ghost-set x e)` | Ghost statements, erased before the program runs |

- **Mutation** (D75): `set`, `set-idx` and `push` change `let-mut` runtime locals, and `ghost-set` changes `ghost-let-mut` locals. Changing a parameter or an immutable local is `E-OWN-003`, and changing a binding of the other kind is `E-GHOST-001`.
- **Loops:** every loop needs a `decreases`, an integer that is at least 0 whenever the condition holds and drops across each pass that continues normally. A pass that returns or panics needn't decrease it.

<!-- expect: ok -->
```lisp
(spec ones
  (params (n i64))
  (returns (v (vec i64)))
  (requires (and (>= n 0) (<= n 1000)))
  (ensures (== (len v) n))
  (effects alloc))
(def ones
  (body
    (let-mut v (vec i64) (vec-new))
    (let-mut i i64 0)
    (while (< i n)
      (invariant (and (<= 0 i) (<= i n)))
      (invariant (== (len v) i))
      (decreases (- n i))
      (push v 1)
      (set i (+ i 1)))
    (return v)))
```

<!-- expect: ok -->
```lisp
(spec shout (params (x i64)) (returns) (effects panic io))
(def shout (body (if (< x 0) (panic "negative") (block)) (print x) (return)))
```

## 7. Ghost code

Ghost code exists only for proofs and is erased before the program runs. It covers contracts, invariants, measures, `assert`, ghost locals, and the bodies of ghost-fns and lemmas. In it, arithmetic is on `int` and can't overflow, and quantifiers and sequence operations are allowed.

- **A ghost-fn** is a pure function that specs use. Callers see its body. A recursive one needs a `decreases`.
- **A lemma** states a fact and proves it. Its body holds only `assert`, ghost locals, lemma calls, `if`, `block`, `while` over ghost locals and `(return)`. Its `ensures` must hold at every `(return)` and at the end of the body, and an empty body proves only what its `requires` imply. A `return` with values in a lemma is `E-GHOST-003`.
- **Ghost-fn calls** carry a `PRE` goal for the ghost-fn's `requires`, and each ghost-fn's body is proved well-defined under its own `requires`.
- **`forall` and `exists`** bind `int` or `bool`, never `i64` (D68).

<!-- expect: ok -->
```lisp
(ghost-fn double ((x int)) int (body (* 2 x)))
(spec twice (params (x i64)) (returns (r i64)) (requires (in_i64 (double x))) (ensures (== r (double x))) (effects))
(def twice (body (return (+ x x))))
(lemma chain (params (a int) (b int) (c int)) (requires (<= a b) (<= b c)) (ensures (<= a c))
  (body (call law_le_trans a b c)))
```

<!-- expect: E-GHOST-001 -->
```lisp
(spec f (params (x i64)) (returns (r i64)) (effects))
(def f (body (ghost-let g i64 x) (return g)))
```

A ghost local never flows into a runtime value.

<!-- expect: E-GHOST-002 -->
```lisp
(ghost-fn double ((x int)) int (body (* 2 x)))
(spec f (params (x i64)) (returns (r i64)) (effects))
(def f (body (return (double x))))
```

Runtime code can't call a ghost-fn. Compute the value in runtime code, and use the ghost-fn in the spec.

<!-- expect: E-GHOST-003 -->
```lisp
(spec tick (params) (returns) (effects))
(def tick (body (return)))
(lemma l (params) (body (call tick)))
```

A lemma is ghost code, so it can't call a def.

## 8. Ownership

Vectors are owned and move. Slices are borrows that never outlive the call they're passed to. There are no lifetimes (`b17-0.md` §5, D36).

1. **Copying and moving.** `bool`, `i64` and slices are copied. Vectors move when used whole: as a `let` initializer, the right side of `set`, an owned argument or in `return`. `len`, `idx`, `borrow` and ghost code read a vector without moving it.
2. **Use after move** is `E-OWN-001`, until `set` gives the variable a new value. Ghost code may read any binding, moved or not, and a moved parameter still denotes its entry value.
3. **Slices** come only from `(borrow v)` as a def-call argument for a slice parameter, or from a slice parameter passed straight through. Anywhere else a slice is `E-OWN-002`, and no local, result or ghost-fn may have a slice type.
4. **Mutation** needs a `let-mut` local (`E-OWN-003`). To change an owned vector parameter, move it into one first.
5. **Branches and loops.** After an `if`, a vector moved on either branch that continues is moved. A branch that returns or panics doesn't count. A loop body's normal exit leaves every outer vector as it found it, live or moved (`E-OWN-004`).
6. **A vector appears in at most one argument** of a call, or one expression of a return, however it's used (`E-OWN-005`). Bind `(len v)` to a local first. Several uses inside one argument count once, and lemma calls are exempt (D72).
7. **Only variables, `(vec-new)`, `seq-build` and call results** are vector expressions in runtime code. An `if` can't produce one (`E-OWN-006`).

An in-place algorithm takes its vector by value and returns it:

<!-- expect: ok -->
```lisp
(spec zero_first
  (params (a (vec i64)))
  (returns (r (vec i64)))
  (requires (> (len a) 0))
  (ensures (== (len r) (len a)) (== (idx r 0) 0))
  (effects))
(def zero_first (body (let-mut b (vec i64) a) (set-idx b 0 0) (return b)))
```

<!-- expect: E-OWN-001 -->
```lisp
(spec f (params (v (vec i64))) (returns (n i64)) (effects))
(def f (body (let w (vec i64) v) (return (len v))))
```

<!-- expect: E-OWN-002 -->
```lisp
(spec f (params (v (vec i64))) (returns (n i64)) (effects))
(def f (body (let s (ref (slice i64)) (borrow v)) (return 0)))
```

<!-- expect: E-OWN-003 -->
```lisp
(spec f (params (x i64)) (returns (r i64)) (effects))
(def f (body (set x 1) (return x)))
```

<!-- expect: E-OWN-004 -->
```lisp
(spec f (params (v (vec i64)) (n i64)) (returns (r i64)) (effects))
(def f
  (body
    (let-mut i i64 0)
    (while (< i n)
      (invariant (<= i n))
      (decreases (- n i))
      (let w (vec i64) v)
      (set i (+ i 1)))
    (return i)))
```

<!-- expect: E-OWN-005 -->
```lisp
(spec total (params (a (ref (slice i64))) (b (ref (slice i64)))) (returns (n i64)) (effects))
(def total (body (return 0)))
(spec twice (params (v (vec i64))) (returns (n i64)) (effects))
(def twice (body (let ((n i64)) (call total (borrow v) (borrow v))) (return n)))
```

<!-- expect: E-OWN-006 -->
```lisp
(spec f (params (v (vec i64)) (c bool)) (returns (r (vec i64))) (effects))
(def f (body (let w (vec i64) (if c v (vec-new))) (return w)))
```

Use an `if` statement with a `return` or a `set` in each branch instead.

## 9. Effects

A spec's `effects` lists what its def may do, in the order `alloc`, `panic`, `io`. `push` and a runtime `seq-build` have `alloc`, `panic` has `panic`, `print` has `io`, `vec-new` has none, and a call has its callee's effects. A statement's effects include everything inside it. An empty `(effects)` promises none of them (`b17-0.md` §6).

`ensures` constrain only normal returns. Leaving out `panic` rules out `(panic ...)`. The runtime errors the proof goals rule out, and allocation failure, which aborts, are outside the effects.

<!-- expect: E-EFF-001 -->
```lisp
(spec f (params) (returns (v (vec i64))) (effects))
(def f (body (let-mut v (vec i64) (vec-new)) (push v 1) (return v)))
```

## 10. Returns and recursion

- **Every path** through a def ends in `return` or `panic` (`E-RET-001`). A loop may always end, so code after a loop needs its own `return`. Statements after a `return` are still checked for names and types (D77).
- **Recursion** needs a `decreases` on the item (`E-TERM-001`). At each recursive call, the verifier proves `0 <= callee measure < caller measure` under the callee's `requires` (a `TERM` goal). Mutual recursion isn't allowed (`E-TERM-002`).

<!-- expect: ok -->
```lisp
(ghost-fn fib ((n int)) int (requires (>= n 0)) (decreases n)
  (body (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2))))))
```

<!-- expect: E-RET-001 -->
```lisp
(spec f (params (c bool)) (returns (r i64)) (effects))
(def f (body (if c (return 1) (block))))
```

<!-- expect: E-TERM-001 -->
```lisp
(ghost-fn loop ((n int)) int (body (loop n)))
```

<!-- expect: E-TERM-002 -->
```lisp
(ghost-fn even ((n int)) bool (requires (>= n 0)) (decreases n) (body (if (== n 0) true (odd (- n 1)))))
(ghost-fn odd ((n int)) bool (requires (>= n 0)) (decreases n) (body (if (== n 0) false (even (- n 1)))))
```

## 11. Proof goals

Once a module passes tier 0, the verifier sends one goal per obligation to Z3 (`b17-0.md` §9). Each one below fails, and the text after it says how to fix it. Every goal is assumed once it's generated, so one wrong step reports only that step.

<!-- expect: E-PROOF-BOUNDS -->
```lisp
(spec first (params (a (ref (slice i64)))) (returns (x i64)) (effects))
(def first (body (return (idx a 0))))
```

An index must be in range. Add `(requires (> (len a) 0))`. `BOUNDS` also covers `set-idx`, `take`, `drop`, `last`, and a negative `seq-build` length.

<!-- expect: E-PROOF-OVERFLOW -->
```lisp
(spec succ (params (x i64)) (returns (y i64)) (ensures (== y (+ x 1))) (effects))
(def succ (body (return (+ x 1))))
```

Runtime arithmetic must fit in `i64`. Add `(requires (< x 9223372036854775807))`.

<!-- expect: E-PROOF-DIV -->
```lisp
(spec quot (params (x i64) (y i64)) (returns (q i64)) (requires (!= y 0)) (effects))
(def quot (body (return (/ x y))))
```

A divisor must be non-zero, and `-2^63 / -1` overflows. Also require `(not (and (== x -9223372036854775808) (== y -1)))`.

<!-- expect: E-PROOF-PRE -->
```lisp
(spec pos (params (x i64)) (returns (r i64)) (requires (> x 0)) (ensures (== r x)) (effects))
(def pos (body (return x)))
(spec caller (params (y i64)) (returns (r i64)) (effects))
(def caller (body (let ((r i64)) (call pos y)) (return r)))
```

A call must establish its callee's `requires`, for a def, a lemma or a ghost-fn alike. Require it of `caller` too, or check `y` first.

<!-- expect: E-PROOF-INV-ENTRY -->
```lisp
(spec f (params (n i64)) (returns (r i64)) (requires (>= n 0)) (effects))
(def f
  (body
    (let-mut i i64 0)
    (while (< i n) (invariant (>= i 1)) (decreases (- n i)) (set i (+ i 1)))
    (return i)))
```

An invariant must hold before the first pass. Here `i` starts at 0.

<!-- expect: E-PROOF-INV-KEEP -->
```lisp
(spec f (params (n i64)) (returns (r i64)) (requires (>= n 0)) (effects))
(def f
  (body
    (let-mut i i64 0)
    (while (< i n) (invariant (and (<= 0 i) (<= i n))) (invariant (== i 0)) (decreases (- n i)) (set i (+ i 1)))
    (return i)))
```

Every pass must keep each invariant. `(== i 0)` breaks after one pass. Remove it: the first invariant already holds on every pass.

<!-- expect: E-PROOF-TERM -->
```lisp
(spec f (params (n i64)) (returns (r i64)) (requires (and (>= n 0) (< n 100))) (effects))
(def f
  (body
    (let-mut i i64 0)
    (while (< i n) (invariant (and (<= 0 i) (<= i n))) (decreases (+ n i)) (set i (+ i 1)))
    (return i)))
```

The measure must drop on every pass. `(+ n i)` grows. Use `(- n i)`. `TERM` also covers a measure going negative while the condition holds, and a recursive call that doesn't descend.

<!-- expect: E-PROOF-POST -->
```lisp
(spec f (params (x i64)) (returns (y i64)) (requires (< x 100)) (ensures (> y x)) (effects))
(def f (body (return x)))
```

Every `return` must establish the `ensures`, and so must the end of a lemma's body.

<!-- expect: E-PROOF-ASSERT -->
```lisp
(spec f (params (x i64)) (returns) (effects))
(def f (body (assert (> x 0)) (return)))
```

An `assert` must follow from what's known at that point.

**Stating ranges** (`b17-0.md` §10, D60). A computation whose values must fit in `i64` should require it in the terms each step uses, so every overflow goal has its fact at hand. `sum` requires each partial sum plus its next element to fit:

<!-- expect: ok -->
```lisp
(ghost-fn sum_of ((s (seq int))) int (decreases (len s))
  (body (if (== (len s) 0) 0 (+ (sum_of (take s (- (len s) 1))) (last s)))))
(spec sum
  (params (a (ref (slice i64))))
  (returns (s i64))
  (requires (forall ((i int)) (=> (and (<= 0 i) (< i (len a))) (in_i64 (+ (sum_of (take a i)) (idx a i))))))
  (ensures (== s (sum_of a)))
  (effects))
(def sum
  (body
    (let-mut s i64 0)
    (let-mut i i64 0)
    (while (< i (len a))
      (invariant (and (<= 0 i) (<= i (len a))))
      (invariant (== s (sum_of (take a i))))
      (decreases (- (len a) i))
      (set s (+ s (idx a i)))
      (set i (+ i 1)))
    (return s)))
```

## 12. The core library

`b17c/core.b17` is in scope in every module, and its names are reserved (D51). These are all its items, one per line, with each law's empty `(body)` left out:

<!-- core items -->
```lisp
(ghost-fn sorted ((s (seq int))) bool (body (forall ((i int) (j int)) (=> (and (and (<= 0 i) (< i j)) (< j (len s))) (<= (idx s i) (idx s j))))))
(ghost-fn in_i64 ((x int)) bool (body (and (<= -9223372036854775808 x) (< x 9223372036854775808))))
(ghost-fn seq_update ((s (seq int)) (i int) (e int)) (seq int) (requires (and (<= 0 i) (< i (len s)))) (body (concat (take s i) (concat (seq-lit e) (drop s (+ i 1))))))
(lemma law_i64_range (params (x i64)) (ensures (in_i64 x)))
(lemma law_vec_len_range (params (v (vec i64))) (ensures (< (len v) 9223372036854775808)))
(lemma law_len_nonneg (params (s (seq int))) (ensures (>= (len s) 0)))
(lemma law_len_unit (params (x int)) (ensures (== (len (seq-lit x)) 1)))
(lemma law_len_concat (params (s (seq int)) (t (seq int))) (ensures (== (len (concat s t)) (+ (len s) (len t)))))
(lemma law_len_take (params (s (seq int)) (k int)) (requires (and (<= 0 k) (<= k (len s)))) (ensures (== (len (take s k)) k)))
(lemma law_len_drop (params (s (seq int)) (k int)) (requires (and (<= 0 k) (<= k (len s)))) (ensures (== (len (drop s k)) (- (len s) k))))
(lemma law_idx_concat (params (s (seq int)) (t (seq int)) (i int)) (requires (and (<= 0 i) (< i (+ (len s) (len t))))) (ensures (== (idx (concat s t) i) (if (< i (len s)) (idx s i) (idx t (- i (len s)))))))
(lemma law_idx_take (params (s (seq int)) (k int) (i int)) (requires (and (and (<= 0 i) (< i k)) (<= k (len s)))) (ensures (== (idx (take s k) i) (idx s i))))
(lemma law_idx_drop (params (s (seq int)) (k int) (i int)) (requires (and (and (<= 0 k) (<= k (len s))) (and (<= 0 i) (< i (- (len s) k))))) (ensures (== (idx (drop s k) i) (idx s (+ i k)))))
(lemma law_last (params (s (seq int))) (requires (> (len s) 0)) (ensures (== (last s) (idx s (- (len s) 1)))))
(lemma law_take_all (params (s (seq int))) (ensures (== (take s (len s)) s)))
(lemma law_take_none (params (s (seq int))) (ensures (== (take s 0) (seq-lit))))
(lemma law_take_take (params (s (seq int)) (k int) (j int)) (requires (and (and (<= 0 j) (<= j k)) (<= k (len s)))) (ensures (== (take (take s k) j) (take s j))))
(lemma law_take_step (params (s (seq int)) (i int)) (requires (and (<= 0 i) (< i (len s)))) (ensures (== (take s (+ i 1)) (concat (take s i) (seq-lit (idx s i))))))
(lemma law_seq_ext (params (s (seq int)) (t (seq int))) (requires (and (== (len s) (len t)) (forall ((i int)) (=> (and (<= 0 i) (< i (len s))) (== (idx s i) (idx t i)))))) (ensures (== s t)))
(lemma law_contains (params (s (seq int)) (x int)) (ensures (== (contains s x) (exists ((i int)) (and (and (<= 0 i) (< i (len s))) (== (idx s i) x))))))
(lemma law_contains_concat (params (s (seq int)) (t (seq int)) (x int)) (ensures (== (contains (concat s t) x) (or (contains s x) (contains t x)))))
(lemma law_contains_unit (params (y int) (x int)) (ensures (== (contains (seq-lit y) x) (== x y))))
(lemma law_contains_none (params (s (seq int)) (x int)) (ensures (not (contains (take s 0) x))))
(lemma law_occurrences_concat (params (s (seq int)) (t (seq int)) (x int)) (ensures (== (occurrences (concat s t) x) (+ (occurrences s x) (occurrences t x)))))
(lemma law_occurrences_unit (params (y int) (x int)) (ensures (== (occurrences (seq-lit y) x) (if (== x y) 1 0))))
(lemma law_occurrences_none (params (s (seq int)) (x int)) (ensures (== (occurrences (take s 0) x) 0)))
(lemma law_multiset_occurrences (params (s (seq int)) (t (seq int)) (x int)) (requires (== (multiset s) (multiset t))) (ensures (== (occurrences s x) (occurrences t x))))
(lemma law_multiset_concat (params (s (seq int)) (t (seq int))) (ensures (== (multiset (concat s t)) (msum (multiset s) (multiset t)))))
(lemma law_update_len (params (s (seq int)) (i int) (e int)) (requires (and (<= 0 i) (< i (len s)))) (ensures (== (len (seq_update s i e)) (len s))))
(lemma law_update_at (params (s (seq int)) (i int) (e int)) (requires (and (<= 0 i) (< i (len s)))) (ensures (== (idx (seq_update s i e) i) e)))
(lemma law_update_other (params (s (seq int)) (i int) (e int) (k int)) (requires (and (and (<= 0 i) (< i (len s))) (and (and (<= 0 k) (< k (len s))) (!= k i)))) (ensures (== (idx (seq_update s i e) k) (idx s k))))
(lemma law_le_refl (params (a int)) (ensures (<= a a)))
(lemma law_le_trans (params (a int) (b int) (c int)) (requires (and (<= a b) (<= b c))) (ensures (<= a c)))
(lemma law_le_antisym (params (a int) (b int)) (requires (and (<= a b) (<= b a))) (ensures (== a b)))
(lemma law_le_total (params (a int) (b int)) (ensures (or (<= a b) (<= b a))))
(lemma law_lt_succ (params (a int) (b int)) (requires (< a b)) (ensures (<= (+ a 1) b)))
```

- **The ghost-fns:** `sorted`, `in_i64` for stating ranges, and `seq_update`, which is s with element i replaced by e. Callers see their bodies.
- **The laws** are lemmas you call. The verifier already knows them, since each is one of `b17-0.md` §9's background facts or the laws of integer order, or follows directly from them and `seq_update`'s body. So you call a law only to point a proof at a particular instance. They're stated over `int`, and every `i64` collection fits (§3 below).
- **Three more facts** are known with no law to call (`b17-0.md` §9):
  - after `(set-idx v i e)`, v has the same length, `(idx v i)` is e, every other element is unchanged, and `(multiset v)` loses one count of the old `(idx v i)` and gains one of e;
  - after `(push v e)`, v is `(concat v (seq-lit e))`;
  - two multisets are equal when every count is.

So a swap keeps a vector's multiset with no lemma, and a sort's invariant `(== (multiset v) (multiset a))` holds across each swap with no help:

<!-- expect: ok -->
```lisp
(spec swap
  (params (a (vec i64)) (i i64) (j i64))
  (returns (r (vec i64)))
  (requires (and (and (<= 0 i) (< i (len a))) (and (<= 0 j) (< j (len a)))))
  (ensures (== (multiset r) (multiset a)))
  (effects))
(def swap
  (body
    (let-mut v (vec i64) a)
    (let t i64 (idx v i))
    (set-idx v i (idx v j))
    (set-idx v j t)
    (return v)))
```

## 13. The toolchain

The tools read B17-1 by default, so B17-0 takes `--subset 0`. `agent.py` reads only B17-0.

```sh
uv run --no-project b17c/check.py --subset 0 FILE      # tier 0: FILE:LINE:COL: CODE: message
uv run --no-project b17c/verify.py --subset 0 FILE     # every goal, under the canonical seed and 10 shuffled ones
uv run --no-project b17c/agent.py check FILE           # every error as JSON (interface 3); exit 1 if any
uv run --no-project b17c/agent.py explain CODE         # a code's rule, with a labelled example
uv run --no-project b17c/agent.py obligations FILE NAME     # every goal of an item, with its verdict
uv run --no-project b17c/agent.py impact FILE CHANGED       # which goals a changed spec breaks
uv run --no-project b17c/agent.py search FILE QUERY         # specs that guarantee QUERY's spec
uv run --no-project b17c/agent.py simulate FILE NAME ARG... # a checked run
uv run --no-project b17c/interp.py --subset 0 --check FILE NAME ARG...  # a run, contracts checked with --check
uv run --no-project b17c/rust.py --subset 0 --run FILE NAME ARG...      # the same run, as emitted Rust
```

`agent.py`'s queries that solve take `--seeds N` and `--cache DIR`. Tier 0 errors come first: while any remain, no proof goals are generated.

**A diagnostic** (D93) holds `code`, `severity`, `node` and `message`. A failed proof adds:
- `goal`, written over your names;
- `context`: the items you need, as `kind name`;
- `dependents`: how many later goals of the same item assume this one. Fix the ones with the most dependents first;
- `budget_used`, and `repairs`, which is empty for now;
- often a `counterexample` for every parameter, with `reproduced`: `true` when a checked run on it fails too, `false` when it doesn't, and `null` when no run is possible.

A reproduced counterexample is a real failing input. One that isn't may be spurious, since it's found against fewer axioms than the verdict. Trust the verdict, read the goal, and treat that model only as a hint.

## 14. Codes

| Code | Section | Meaning |
|---|---|---|
| `E-PARSE-001` | 2 | Not a term of the grammar, or a reserved word as a name |
| `E-TYPE-001` | 3, 4 | A type mismatch, or a name of the wrong kind |
| `E-TYPE-002` | 2, 4 | An undefined or reused name, a def with no spec, or a duplicate spec |
| `E-GHOST-001` | 7 | A ghost binding in runtime code |
| `E-GHOST-002` | 3, 7 | A ghost type, ghost-only operation or ghost-fn call in runtime code |
| `E-GHOST-003` | 7 | A runtime statement in ghost code |
| `E-OWN-001` to `E-OWN-006` | 8 | The ownership rules |
| `E-EFF-001` | 9 | A def's effects exceed its spec's |
| `E-RET-001` | 10 | A path that doesn't end in `return` or `panic` |
| `E-TERM-001` | 10 | Recursion without `decreases` |
| `E-TERM-002` | 10 | Mutual recursion |
| `E-PROOF-*` | 11 | A proof goal that isn't discharged: `BOUNDS`, `OVERFLOW`, `DIV`, `PRE`, `INV-ENTRY`, `INV-KEEP`, `TERM`, `POST`, `ASSERT` |

Some triggers the table doesn't name:
- **`E-TYPE-001`** also covers a name of the wrong kind, such as an item used as a value, and a malformed type (D67, D68).
- **`E-TYPE-002`** also covers two specs identical up to names (D45).
- **`E-GHOST-001`** also covers a ghost local changed with `set`, or a runtime one with `ghost-set` (D75).
- **`E-GHOST-002`** also covers `==` on collections in runtime code (D71).
- **`E-GHOST-003`** also covers a `return` with values in a lemma.
- **One error, one diagnostic** (D78): an expression that fails a check doesn't cascade, and a moved vector is reported at its first use only.
