# B17-0: the agent reference manual (WP8)

This manual is for the model writing B17-0. It gives every rule you need, every error code you can meet, and a minimal example of each. Every example states its outcome, and `b17c/test_manual.py` checks each one: in CI its tier 0 outcome, and wherever Z3 is installed its proof outcome too. So the manual can't drift from the language.

The full semantics is `docs/b17-0.md`, cited here as §2 to §12. When the two disagree, `b17-0.md` wins, and the disagreement is a bug in this manual.

**How a task reaches you** (§10). You get a module header, frozen `ghost-fn`s and one frozen `spec`. You return a `def` for that spec. You may add `lemma`s, `ghost-fn`s, and `spec`-and-`def` pairs for helpers. You never edit the task's spec.

**How to use the toolchain** (§13 below). `b17c/agent.py check FILE` gives every error as JSON. For a failed proof it gives the goal, a counterexample the interpreter replays, and what it depends on.

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
- **Layout** is free, but only whitespace may differ from the canonical form. There are no comments (§2).

The examples below show only items. Each sits in a module with a header, like the one above.

## 2. Names

- **Shape:** a name matches `[a-z][a-z0-9_]*`.
- **Reserved:** every word of the grammar is reserved, such as `block`, `len` and `vec`, and using one as a name doesn't parse. The core library's names (§12 below) are reserved too, but declaring one is `E-TYPE-002`.
- **No shadowing** (D41): parameter, result and local names are unique within an item, even across blocks, and none may reuse an item's name.
- **Scope** (D66): a local is visible from its declaration to the end of its `block`, loop body or `if` branch. Results are visible only in `ensures`, so a `def` may name a local after its result.

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

- **Collections don't nest** in B17-0, and there are no tuples, data types, strings or floats (§11).
- **Runtime code has no conversions** (D34): `i64` never mixes with `bool`.
- **In ghost code,** `i64` is a subtype of `int`, and a vector or slice is viewed as a `seq`.
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

A spec may return several results. A caller binds them with `let`, one name per result, and must bind them all (D43, D74).

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

- **Arithmetic:** `+`, `-`, `*`, `/`, `%` and `neg`. In runtime code each carries a goal that its result fits in `i64` (§11 below).
- **Comparison and logic:** `<`, `<=`, `>`, `>=`, `==`, `!=`, `and`, `or`, `=>` and `not`. Operators are binary, so `(and a (and b c))`. `and`, `or` and `=>` short-circuit.
- **`(if c a b)`** is an expression. In runtime code it can't produce a vector (`E-OWN-006`).
- **Sequences:** `(len s)` and `(idx s i)` work everywhere. `seq-lit`, `take`, `drop`, `concat`, `last`, `contains`, `multiset`, `msum` and `occurrences` are ghost-only.
- **Building a vector:** `(seq-build n (fn (i) e))` makes a vector of n elements, with `0 <= i < n` assumed inside e (D38). In runtime code it has effect `alloc`.

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
| `(set x e)` | Assigns a `let-mut` local |
| `(set-idx v i e)`, `(push v e)` | Changes a `let-mut` vector in place; `push` has effect `alloc` |
| `(if c s1 s2)`, `(block s*)` | Branch and sequence; `(block)` does nothing |
| `(while c (invariant e)* (decreases d) s*)` | A loop: invariants, then its measure, then its body |
| `(call f e*)`, `(let ((x T)*) (call f e*))` | Calls a def or lemma, binding its results |
| `(return e*)` | Ends the def with one expression per result |
| `(panic "text")`, `(print e)` | Effects `panic` and `io` |
| `(assert e)`, `(ghost-let x T e)`, `(ghost-let-mut x T e)`, `(ghost-set x e)` | Ghost statements, erased before the program runs |

Every loop needs a `decreases`: an integer that stays at least 0 and drops on every pass.

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
- **A lemma** states a fact and proves it. Its body holds only ghost statements and lemma calls, and an empty body proves what its `requires` imply.
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

Vectors are owned and move. Slices are borrows that never outlive the call they're passed to. There are no lifetimes (§5, D36).

1. **Copying and moving.** `bool`, `i64` and slices are copied. Vectors move when used whole: as a `let` initializer, the right side of `set`, an owned argument or in `return`. `len`, `idx`, `borrow` and ghost code read a vector without moving it.
2. **Use after move** is `E-OWN-001`, until `set` gives the variable a new value. Ghost code still sees a moved parameter's entry value.
3. **Slices** come only from `(borrow v)`, as a def-call argument for a slice parameter. Anywhere else a slice is `E-OWN-002`.
4. **Mutation** needs a `let-mut` local (`E-OWN-003`). To change an owned vector parameter, move it into one first.
5. **A loop body** leaves every outer vector as it found it (`E-OWN-004`).
6. **A vector appears in at most one argument** of a call, or one expression of a return (`E-OWN-005`). Bind `(len v)` to a local first.
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

A spec's `effects` lists what its def may do, in the order `alloc`, `panic`, `io`. `push` and a runtime `seq-build` have `alloc`, `panic` has `panic`, `print` has `io`, and a call has its callee's effects. An empty `(effects)` promises none of them (§6).

<!-- expect: E-EFF-001 -->
```lisp
(spec f (params) (returns (v (vec i64))) (effects))
(def f (body (let-mut v (vec i64) (vec-new)) (push v 1) (return v)))
```

## 10. Returns and recursion

- **Every path** through a def ends in `return` or `panic` (`E-RET-001`). A loop may always end, so code after a loop needs its own `return`.
- **Recursion** needs a `decreases` on the item (`E-TERM-001`). Mutual recursion isn't allowed (`E-TERM-002`).

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

Once a module passes tier 0, the verifier sends one goal per obligation to Z3 (§9). Each one below fails, and the text after it says how to fix it. Every goal is assumed once it's generated, so one wrong step reports only that step.

<!-- expect: E-PROOF-BOUNDS -->
```lisp
(spec first (params (a (ref (slice i64)))) (returns (x i64)) (effects))
(def first (body (return (idx a 0))))
```

An index must be in range. Add `(requires (> (len a) 0))`.

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

A call must establish its callee's `requires`. Require it of `caller` too, or check `y` first.

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

Every pass must keep each invariant. `(== i 0)` breaks after one pass. State what stays true, such as `(<= i n)`.

<!-- expect: E-PROOF-TERM -->
```lisp
(spec f (params (n i64)) (returns (r i64)) (requires (and (>= n 0) (< n 100))) (effects))
(def f
  (body
    (let-mut i i64 0)
    (while (< i n) (invariant (and (<= 0 i) (<= i n))) (decreases (+ n i)) (set i (+ i 1)))
    (return i)))
```

The measure must drop on every pass. `(+ n i)` grows. Use `(- n i)`.

<!-- expect: E-PROOF-POST -->
```lisp
(spec f (params (x i64)) (returns (y i64)) (requires (< x 100)) (ensures (> y x)) (effects))
(def f (body (return x)))
```

Every `return` must establish the `ensures`.

<!-- expect: E-PROOF-ASSERT -->
```lisp
(spec f (params (x i64)) (returns) (effects))
(def f (body (assert (> x 0)) (return)))
```

An `assert` must follow from what's known at that point.

**Stating ranges** (§10, D60). A computation whose values must fit in `i64` should require it in the terms each step uses, so every overflow goal has its fact at hand. `sum` requires each partial sum plus its next element to fit:

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

In scope in every module, with names reserved (§9, D51):
- **`(sorted s)`:** every element at most each later one.
- **`(in_i64 x)`:** x lies in [-2^63, 2^63).
- **`(seq_update s i e)`:** s with element i replaced by e.
- **Laws, as lemmas you call:** the sequence facts §9 lists, such as `law_take_step` and `law_idx_concat`, and the laws of integer order, such as `law_le_trans`. The verifier already states every §9 fact, so you call a law only to point a proof at it.

## 13. The toolchain

```sh
uv run --no-project b17c/check.py FILE                 # tier 0: FILE:LINE:COL: CODE: message
uv run --no-project b17c/verify.py FILE                # every goal, under 10 shuffled seeds
uv run --no-project b17c/agent.py check FILE           # every error as JSON (interface 3)
uv run --no-project b17c/agent.py explain CODE         # a code's rule, with a labelled example
uv run --no-project b17c/agent.py obligations FILE NAME
uv run --no-project b17c/agent.py simulate FILE NAME ARG...   # a checked run
uv run --no-project b17c/interp.py FILE NAME ARG...    # a plain run
```

**A diagnostic** (D93) holds:
- `code` and `node`;
- for a failed proof, the `goal` written over your names;
- a `counterexample`, with `reproduced` saying whether a checked run on it fails too;
- `context`: the items you need;
- `dependents`: how many later goals assume this one. Fix the ones with the most dependents first.

A counterexample that isn't reproduced usually means the proof needs a stronger invariant, not a code change.

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
