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
| `bst_insert` | §1's program: data types, `match`, `rank`, allocation | Written |
| `bst_search` | A recursive read, which consumes its tree | Written |
| `discrete_logarithm` | An optional result | Written |
| `longest_palindrome_substring` | A tuple result | Written |
| `segmenttree_query` | Ghost maps; `replace` on a node's fields | Needs D100 for the witness step |
| `trie_insert` | A vector of optional nodes, places, `replace`, a runtime `seq-build` of nodes | Needs D99 for the view step |
| `lca` | `option` throughout | Needs D99 for `find`'s postcondition |
| `bfs` | A graph record, nested vectors, a quantifier over paths | Bounds only |
| `kruskal` | Tuples in a vector | Bounds only |
| `coin_change` | A quantifier over sequences | Bounds only |

- **Written:** the invariants and hints cover every goal, as far as review can tell.
- **Needs D99:** one step proves a fact for every sequence or unbounded integer, which takes D99's `forall` statement.
- **Needs D100:** one step names the witness of an ∃, which takes D100's `obtain`.
- **Bounds only:** the invariants cover bounds, overflow and termination. Correctness takes both statements, since these proofs quantify over every path, spanning tree or change, and name witnesses.

D99 and D100 are accepted. The steps that use them are written against WP5 once it reads B17-1, as each fails or passes.

Each proof is finished against WP5 once it extends to B17-1. A proof that fails then is a finding against the program, the encoding or the core library, recorded in `ACTIVITY.md` as for B17-0.

**How the ports differ from AlgoVeri's Dafny:**
- **Contracts:** kept, AlgoVeri's u64 constraints included, as `requires`. So §1's `insert` takes `(>= x 0)`.
- **Names:** B17-1 reserves `contains`, so `lca`'s `contains` is `holds` and `trie_insert`'s is `has_key`. Constructors are value names, so `bfs`'s `graph` parameter is `g`.
- **Types:** runtime fields and parameters are `i64`, and `seq<int>` parameters are slices. Ghost functions keep `int` and `seq`, and `set<int>` is `(iset int)`. Dafny's `Option` is the core library's `option`, whose field is `value`.
- **Methods inside a datatype** are top-level ghost-fns (§11).
- **Ranges (D42, §10's rule):** `discrete_logarithm` requires `g * (p - 1)` to fit, so every step's `g * cur` does. The others need none, since their own preconditions bound every value.
- **Implementations:** the simplest that meet the spec. `longest_palindrome_substring` checks every substring, since the spec asks for no particular algorithm. `kruskal` relabels components instead of keeping a union-find forest, and `bfs` uses a vector as its queue.

**Reject:** 47 programs, each with exactly one error named by its code. They cover every case §13 lists, and each new rule of §2–§9: 42 with a tier 0 code and 5 with a proof family.

**How the labels are checked:** by review for now, as B17-0's first were. The parser, checker and verifier don't read B17-1 yet, so nothing here runs. When WP3 extends to B17-1, it checks the tier 0 labels by execution, and WP5 checks the proof labels.
