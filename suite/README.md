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

`b17-1/accept/` and `b17-1/reject/` hold B17-1's labelled programs (`docs/b17-1.md` §13), in the same layout and under the same assumptions. Its suite froze with B17-1 on 2026-10-30, at version 1.0, once WP3's checker agreed with every tier 0 label (D44). D113's version 1.1 left it unchanged.

**Accept:** a port of the smallest AlgoVeri task for each feature, from `gym/tasks/algoveri/`.

| Program | Shows | Proof |
|---|---|---|
| `bst_insert` | §1's program: data types, `match`, `rank`, allocation | Verified |
| `bst_search` | A recursive read, which consumes its tree | Verified |
| `discrete_logarithm` | An optional result | Verified |
| `longest_palindrome_substring` | A tuple result | Verified |
| `segmenttree_query` | Ghost maps; `replace` on a node's fields | Verified, with D100's `obtain` naming each witness |
| `trie_insert` | A vector of optional nodes, places, `replace`, a runtime `seq-build` of nodes | Verified, with D99 applying a lemma at every key |
| `lca` | `option` throughout | Verified, with D99 applying three induction lemmas at every value |
| `bfs` | A graph record, nested vectors, a quantifier over paths | Verified, with its invariants as folded predicates and each update a lemma |
| `kruskal` | Tuples in a vector | Verified, with an exchange argument for its minimum weight |
| `coin_change` | A quantifier over sequences | Verified, with witnesses in a ghost map and the same structure as `bfs` |

- **Verified:** WP5 proves every goal under 10 shuffled seeds (D23).

D99 and D100 are accepted, and WP5 reads B17-1. A proof that fails is a finding against the program, the encoding or the core library, recorded in `ACTIVITY.md` as for B17-0.

**Findings so far:**
- **Encoding gaps, now closed (D105):**
  - `trie_insert`'s view of its keys, and `insert`'s use of it, needed a set literal of sequences to compare members by their elements.
  - `bfs`'s invariant counting the `-1`s in its `dist` vector needed the multiset of a constant `seq-build`.
- **Bounds that review had missed, now proved:**
  - **`bfs`:** its measure stays at least 0 only if the count of `-1`s never goes negative. Two lemmas prove, by induction over `take` prefixes, that a count is never negative and that an element counts at least once. Its inner loop also needed invariants keeping `dist[u]` fixed and the queue from shrinking.
  - **`kruskal`:** the insertion sort's inner loop needed an invariant that `cands` keeps its length. That loop is gone now; see below.
- **`kruskal`'s implementation was wrong for its spec.**
  - **The bug:** AlgoVeri's spec calls the graph undirected, but never requires an edge to be listed from both ends, so a graph whose edges run one way satisfies every `requires`. The port collected only edges `(u, v)` with `u < v` from `u`'s list, so it ignored an edge listed only from its larger end. On the cycle `0 → 2 → 1 → 0` it returned one edge for three vertices.
  - **The fix:** it now adds, round by round, the lightest edge joining two components. It scans each stored entry once, and treats it as joining its two endpoints whichever way it's listed. That's Kruskal's greedy rule without a separate sort. It's a test case in `test_interp.py`.
- **How `kruskal`'s proof goes:**
  - **Spanning tree:** the loop keeps component labels, and an invariant that vertices with the same label are joined by the tree so far. When one label is left, every pair of vertices is connected.
  - **Minimum weight:** the loop also keeps the invariant `good`. For every spanning tree o, some spanning tree no heavier than o starts with the tree so far. It holds for the empty tree, with o itself.
  - **One round:** the scan picks an edge (a, b) no heavier than any edge between two components. Take the spanning tree that `good` gives, and a path in it from b to a. Where that path first enters a's component, it uses some edge f between two components, so f weighs at least as much. Putting the new edge at the tree's next index, and moving the edge that was there into f's place, gives a spanning tree that is no heavier and starts with the extended tree. The path's earlier steps avoid f, so f's ends stay connected.
  - **The end:** the result has n − 1 edges, so the spanning tree that starts with it is the result itself, and it weighs no more than any spanning tree.
  - **No change to the language:** the proof needed none. Its first version left 4 goals unproved. Three were `forall` statements passing indexed terms, where D99 wants binders, and one was an invariant that needed an earlier `assert`. Mutants then showed that 13 of its `assert`s, two lemmas and one invariant were redundant, and they were removed.
- **How the large proofs fit (D106):**
  - **First attempt:** `bfs`'s first full proof didn't verify. Each of its loop's goals carried some twenty quantified invariants, with `is_path` inlined into each, and Z3 ran out of budget.
  - **Two changes made it verify.** In B17-1, a non-recursive ghost-fn is folded, so it unfolds only where a proof applies it (D106). And each invariant became a folded predicate, such as `(sorted_q dist queue)`, with each update's effect on it proved by a small lemma.
  - **`coin_change`** follows the same pattern.
  - **The old finding is gone:** `longest_palindrome_substring`'s brittle invariant proves under every seed with D106.
- **Restated without changing its meaning:** `trie_insert`'s `well_formed` now states a child's length before calling `is_empty` on it. A recursive ghost-fn's own goals can't use its own definition (D61), so `is_empty`'s `requires` couldn't otherwise be shown there.

**How the ports differ from AlgoVeri's Dafny:**
- **Contracts:** kept, AlgoVeri's u64 constraints included, as `requires`. So §1's `insert` takes `(>= x 0)`.
- **Names:** B17-1 reserves `contains`, so `lca`'s `contains` is `holds` and `trie_insert`'s is `has_key`. Constructors are value names, so `bfs`'s `graph` parameter is `g`.
- **Types:** runtime fields and parameters are `i64`, and `seq<int>` parameters are slices. Ghost functions keep `int` and `seq`, and `set<int>` is `(iset int)`. Dafny's `Option` is the core library's `option`, whose field is `value`.
- **Methods inside a datatype** are top-level ghost-fns (§11).
- **Ranges (D42, §10's rule):** `discrete_logarithm` requires `g * (p - 1)` to fit, so every step's `g * cur` does. The others need none, since their own preconditions bound every value.
- **Implementations:** the simplest that meet the spec. `longest_palindrome_substring` checks every substring, since the spec asks for no particular algorithm. `kruskal` applies Kruskal's rule, adding the lightest edge between two components, by scanning every edge each round, with components as relabelled vertex labels instead of a union-find forest. `bfs` uses a vector as its queue.

**Reject:** 54 programs, each with exactly one error named by its code. They cover every case §13 lists, and each new rule of §2–§9: 48 with a tier 0 code and 6 with a proof family. The freeze review added six, for rules none covered.

**How the labels are checked:**
- **By review first,** as B17-0's were. Codex reviewed every label against both spec documents, and found no wrong label. The six programs B17-1's freeze review added were checked by a fresh Claude reviewer instead, since Codex's quota had run out.
- **Tier 0 labels by execution:** WP3's checker, `b17c/check.py`, now checks them with `--subset 1`, and agrees with all 64.
- **Proof labels:** WP5's verifier, `b17c/verify.py --subset 1`, checks them. Each of the 6 fails exactly its labelled goal.
- **Rust:** WP7's differential tests build each B17-1 program that passes tier 0 as a Rust crate, with `--subset 1`, and compare its runs with the interpreter's (D111). They cover the accept programs on the interpreter's inputs, and the two proof rejects whose defs reach `err BOUNDS` and `err FIELD`.
- **Runs:** WP15's interpreter runs every accept program on inputs its `requires` allows, with `--subset 1`. It shows the fault of the three proof rejects that have a def or ghost-fn on a concrete input. The other three are lemmas, whose bodies never run (D57), so only WP5 can show theirs.
