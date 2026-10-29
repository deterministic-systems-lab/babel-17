# Accept/reject suites

B17-0's programs are in `accept/` and `reject/`, and B17-1's in `b17-1/` (below).

WP1a's labelled programs (`docs/b17-0.md` §12). WP3's checker must agree with every tier 0 label, and WP5's verifier with every proof label. WP15's interpreter runs the accept programs, and shows each `E-PROOF-*` program's fault on a concrete input. WP7's differential tests build every program that passes tier 0 as Rust and compare its runs with the interpreter's, and WP6's `explain` serves each reject as the example for its code.

## Layout

- `accept/*.b17`: programs that pass every tier 0 check and discharge every proof goal. These are the 20 seed tasks of `gym/tasks/`, ported to B17-0. `merge_sorted.b17` is the worked example of §1, unchanged; it doubles as the `merge_sorted` seed.
- `reject/<CODE>-<what>.b17`: programs with exactly one error, whose code starts the filename. The code is either a tier 0 code from §9's table or a proof goal family (`E-PROOF-*`). Several files may share a code.

Files use the pretty layout, not canonical bytes (§2). WP2's round-trip tests own canonicalization.

## What "accept" assumes

Accept programs rely only on:
- the core library and encoding facts of §9;
- the goal conventions of §7 and §9: clauses checked in order, goals assumed once generated, and loops forgetting only what their body changes.

They contain no hints that a particular solver or seed needs. If WP5's verifier can't discharge one, that's a finding against the encoding or the core library, not a reason to edit the program. Record it in `ACTIVITY.md`.

## Ported task ranges

Seed tasks over Dafny's unbounded `int` gained ranges under D42 and §10's rule, stated per loop step (D60):

| Task | Added precondition |
|---|---|
| `abs` | `x > i64::MIN`, so `-x` fits |
| `fib` | every `fib (i - 1) + fib i` for `1 <= i < n` fits |
| `power` | every `pow b i * b` for `i < e` fits |
| `sum`, `prefix_sums` | every prefix sum plus the next element fits |
| `isqrt` | none: every `r` with `r * r <= n` already fits |

`gcd`, `count` and the index-returning tasks need none. The Dafny versions in `gym/tasks/` take the same preconditions when the M3 task set is built.

## How labels are checked

The labels were first checked by review: by the author, and by an independent model reading the suite against `docs/b17-0.md`. WP3's checker, `b17c/check.py`, now checks every tier 0 label by execution, and the suite and `docs/b17-0.md` froze at version 1.0 once it agreed with all of them (D44). `E-PROOF-*` labels and the proof goals of accept programs are checked by WP5's goal generator, `b17c/goals.py`, which takes its sorts from WP3's types.

## B17-1's programs

`b17-1/accept/` and `b17-1/reject/` hold B17-1's labelled programs (`docs/b17-1.md` §13), in the same layout and under the same assumptions. B17-1 is a draft, and its suite freezes with it, once WP3's checker agrees with every tier 0 label (D44).

**Accept:** a port of the smallest AlgoVeri task for each feature, from `gym/tasks/algoveri/`.

| Program | Shows | Proof |
|---|---|---|
| `bst_insert` | §1's program: data types, `match`, `rank`, allocation | Verified |
| `bst_search` | A recursive read, which consumes its tree | Verified |
| `discrete_logarithm` | An optional result | Verified |
| `longest_palindrome_substring` | A tuple result | Verified, one goal under 9 of 10 seeds |
| `segmenttree_query` | Ghost maps; `replace` on a node's fields | Verified, with D100's `obtain` naming each witness |
| `trie_insert` | A vector of optional nodes, places, `replace`, a runtime `seq-build` of nodes | Verified, with D99 applying a lemma at every key |
| `lca` | `option` throughout | Verified, with D99 applying three induction lemmas at every value |
| `bfs` | A graph record, nested vectors, a quantifier over paths | Bounds only, not yet proved |
| `kruskal` | Tuples in a vector | Bounds only, not yet proved |
| `coin_change` | A quantifier over sequences | Bounds only, not yet proved |

- **Verified:** WP5 proves every goal under 10 shuffled seeds (D23).
- **Bounds only:** the invariants are meant to cover bounds, overflow and termination. Correctness takes D99's `forall` statement and D100's `obtain`, since these proofs quantify over every path, spanning tree or change, and name witnesses.

D99 and D100 are accepted, and WP5 reads B17-1. A proof that fails is a finding against the program, the encoding or the core library, recorded in `ACTIVITY.md` as for B17-0.

**Findings so far:**
- **Brittle:** one of `longest_palindrome_substring`'s outer-loop invariants proves under only 9 of 10 seeds. Its query uses only B17-0's encoding.
- **Encoding gaps, now closed (D105):**
  - `trie_insert`'s view of its keys, and `insert`'s use of it, needed a set literal of sequences to compare members by their elements.
  - `bfs`'s invariant counting the `-1`s in its `dist` vector needed the multiset of a constant `seq-build`.
- **`bfs` isn't finished, even for bounds:**
  - **Termination:** its measure stays at least 0 only if the count of `-1`s never goes negative. That needs §9's fact that a sequence's multiset counts each of its elements at least once, which the encoding lacks.
  - **Its inner loop** needs an invariant that keeps `dist[u]` fixed.
- **Restated without changing its meaning:** `trie_insert`'s `well_formed` now states a child's length before calling `is_empty` on it. A recursive ghost-fn's own goals can't use its own definition (D61), so `is_empty`'s `requires` couldn't otherwise be shown there.

**How the ports differ from AlgoVeri's Dafny:**
- **Contracts:** kept, AlgoVeri's u64 constraints included, as `requires`. So §1's `insert` takes `(>= x 0)`.
- **Names:** B17-1 reserves `contains`, so `lca`'s `contains` is `holds` and `trie_insert`'s is `has_key`. Constructors are value names, so `bfs`'s `graph` parameter is `g`.
- **Types:** runtime fields and parameters are `i64`, and `seq<int>` parameters are slices. Ghost functions keep `int` and `seq`, and `set<int>` is `(iset int)`. Dafny's `Option` is the core library's `option`, whose field is `value`.
- **Methods inside a datatype** are top-level ghost-fns (§11).
- **Ranges (D42, §10's rule):** `discrete_logarithm` requires `g * (p - 1)` to fit, so every step's `g * cur` does. The others need none, since their own preconditions bound every value.
- **Implementations:** the simplest that meet the spec. `longest_palindrome_substring` checks every substring, since the spec asks for no particular algorithm. `kruskal` relabels components instead of keeping a union-find forest, and `bfs` uses a vector as its queue.

**Reject:** 48 programs, each with exactly one error named by its code. They cover every case §13 lists, and each new rule of §2–§9: 43 with a tier 0 code and 5 with a proof family.

**How the labels are checked:**
- **By review first,** as B17-0's were. Codex reviewed every label against both spec documents, and found no wrong label.
- **Tier 0 labels by execution:** WP3's checker, `b17c/check.py`, now checks them with `--subset 1`, and agrees with all 58.
- **Proof labels:** WP5's verifier, `b17c/verify.py --subset 1`, checks them. Each of the 5 fails exactly its labelled goal.
- **Rust:** WP7's differential tests build each B17-1 program that passes tier 0 as a Rust crate, with `--subset 1`, and compare its runs with the interpreter's (D111). They cover the accept programs on the interpreter's inputs, and the two proof rejects whose defs reach `err BOUNDS` and `err FIELD`.
- **Runs:** WP15's interpreter runs every accept program on inputs its `requires` allows, with `--subset 1`. It shows the fault of the three proof rejects that have a def or ghost-fn on a concrete input. The other two are lemmas, whose bodies never run (D57), so only WP5 can show theirs.
