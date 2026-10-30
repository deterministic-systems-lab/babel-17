# Babel-17

Babel-17 is a programming language built for LLMs to write and machines to check. People state intent in English and sign formal specs. Agents write dense, fully typed implementations that a verifier proves meet those specs, so nobody needs to read the implementation line by line. The aim is to make model-generated code faster to produce and faster to run, and trustworthy because it's proven rather than reviewed.

The goal is an all-purpose language: services, applications and their user interfaces, data pipelines, scripts and machine learning, not only verified algorithms (D64). Each module will carry a verification level: typed and memory-safe at the lowest, contracts tested above that, and proved correct against its formal spec at the highest. So code whose intent can't be stated precisely still has a place. B17-0, the first subset, covers integer and array algorithms, and B17-1 adds data types, tuples and ghost sets and maps. The language grows in subsets chosen on evidence.

The design rests on three bets:
- **Rigor is cheap for machines.** Dependent types, effect tracking and proofs slow people down, but cost an agent in a compile-fix loop with a fast verifier very little.
- **A verifier replaces a training corpus.** No human-written Babel-17 exists, so models learn by generating code, checking it, and keeping what passes.
- **Information survives to the last step.** Types, invariants and intent reach the optimizer, so proven code can also be the fastest code.

The full design spec, *MFL: A Machine-First Language — Design Spec (Draft v0.1)*, is kept outside this repo. "MFL" was the working name (D12). Everything decided since is in [DECISIONS.md](DECISIONS.md).

## Status

**Phase 0's gate has passed, as of 2026-10-28.** Phase 0 builds the smallest language that can express real verified programs, and the tools to check it. Its gate (D16) has three parts:
1. WP1a's semantics and suite are frozen;
2. WP2's round-trip tests pass;
3. WP15's interpreter passes its conformance tests.

Phase 1, the embedded MVP, has begun. B17-1, the second subset, froze on 2026-10-30 with its labelled suite, and D113 corrected four of its statements, making it v1.1 ([docs/b17-1.md](docs/b17-1.md), [suite/b17-1/](suite/b17-1/)): its parser, hasher and checker agree with every tier 0 label, its interpreter and Rust backend run every accept program, and its verifier checks every proof label. WP6, the agent protocol, and WP8, the agent reference manual, are done for B17-0, and WP7, the Rust backend, for B17-0 and B17-1.

| WP | What | State |
|---|---|---|
| WP1a | B17-0 core semantics and the accept/reject suite | Done: frozen at v1.0 on 2026-10-28 ([docs/b17-0.md](docs/b17-0.md), [suite/](suite/)), once WP3's checker agreed with every tier 0 label (D44). D107 amended it to v1.1 on 2026-10-29, loosening only its subtyping. |
| WP2 | Canonical form and content hashes | Parser, canonical printer and hasher done ([b17c/](b17c/)). Both done-whens pass: round trips, and golden hashes reproduced on Linux CI (D46). Typed edits, and the manifest and lockfile schemas, remain (interfaces 2, 4 and 7). |
| WP3 | Tier 0 checker: types, names, ghost code, ownership, effects | Done ([b17c/check.py](b17c/check.py)): agrees with every tier 0 label in the suite. Its readings of the semantics are D66–D78, accepted. It checks B17-1 too, by default, and agrees with every tier 0 label of `suite/b17-1/`. B17-1's freeze review settled seven more readings (D109). |
| WP4a | The spec language | Done (D62, D79): B17-0's spec language is WP1a's, and B17-1 adds no data-type invariants or refinement links. |
| WP5 | Verifier: proof goals sent to Z3 | Done for B17-0: [b17c/verify.py](b17c/verify.py) caches every verdict under D22's key, sends canonical queries (interface 11, D63) and reports solver-trusted goals by node ID. [b17c/goals.py](b17c/goals.py) generates the goals from WP3's types, with D61's encoding. It checks the suite's proof labels: all 20 accept programs prove every goal under 10 shuffled seeds (D23), and all 9 proof rejects fail as labelled. It verifies B17-1 too, by default (D89, D103, D105, D106, D108): its 6 proof rejects fail as labelled, and all 10 of its accept programs prove every goal, `kruskal`'s minimum spanning tree included. A review of that work found two ways the verifier could prove `false`, in B17-0 as well, and both are fixed (D103). No B17-0 suite proof relied on them. B17-1's verification levels and property tests (`docs/b17-1.md` §10) are specified but not built yet. |
| WP6 | Agent protocol and diagnostics | Done for B17-0 ([b17c/agent.py](b17c/agent.py)). Diagnostics carry interface 3's fields (D93), with counterexamples the interpreter replays, and the five queries answer (interface 8, D94). It reads B17-0 only. Repairs wait for WP2's typed edits. |
| WP7 | Backend that emits safe Rust | Done for B17-0 and B17-1 ([b17c/rust.py](b17c/rust.py)): every program that passes tier 0 becomes a crate that forbids unsafe code, and its runs print exactly what the interpreter prints, on both suites, corner cases and generated programs. Its readings are D95–D97 for B17-0 and D110–D111 for B17-1, all accepted. It lowers B17-1 too, by default, with data types as Rust enums. |
| WP8 | Agent reference manual | Done for B17-0 ([docs/manual.md](docs/manual.md)): every rule and all 25 error codes with a minimal example, each checked against its stated outcome by `test_manual.py`. |
| WP15 | Reference interpreter | Done ([b17c/interp.py](b17c/interp.py)): passes WP1a's conformance tests. Interface 10 (traces, D56) is v0.1 Draft. It runs B17-1 too, by default since B17-1 froze, including every accept program of `suite/b17-1/`. |
| WP16 | Core spec library | In progress: [b17c/core.b17](b17c/core.b17) holds 3 ghost-fns and 33 laws: §9's background facts and integer order. The interpreter confirms each on a grid, and the verifier proves each. |
| WP17 | Baseline harness: agents writing verified Dafny | Done ([gym/](gym/)). Baselines are in for the seed, AlgoVeri and vericoding sets; Gemini and Grok have tasks left. |

[docs/roadmap.md](docs/roadmap.md) covers all five phases, the Phase 0 work left outside its gate, the Phase 1 critical path, and how the language grows from B17-0 toward D64's scope.

`b17c`, the toolchain, is a Python prototype until Phase 3 (D19). Phase 1 compiles to safe Rust (D18), and the solver is Z3, driven by goals `b17c` generates itself (D17).

## A first look at B17-0

B17-0 is the first subset (D20). Its canonical form is an S-expression, which is also its core language (D33). This is `suite/accept/abs.b17`:

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

What this shows:
- **Headers:** every module opens with a prose header: its purpose, its invariants and how it can fail.
- **Specs and defs:** a person signs the `spec`, and an agent writes the `def`. The def implements the named spec and never restates it, so an agent can't weaken the contract (D39).
- **Integers:** runtime integers are `i64`, and every operation's range is a proof goal (D34). Here, that's why `x = i64::MIN` has to be excluded.
- **Effects:** they're declared, and the empty `(effects)` promises the function never allocates, panics or does I/O.
- **Ghost code:** `ghost-fn`s and `lemma`s exist only for proofs and are erased before the program runs.
- **Ownership:** vectors are owned and move, and slices are borrows that can't escape a call. There are no lifetimes (D36).

The full grammar, typing rules, semantics and proof goals are in [docs/b17-0.md](docs/b17-0.md). B17-1, the second subset, adds data types, tuples, ghost sets and maps, and verification levels, and is frozen in [docs/b17-1.md](docs/b17-1.md). The tools read B17-1 by default, and B17-0 with `--subset 0` (D101).

## Repository layout

| Path | What |
|---|---|
| [`docs/b17-0.md`](docs/b17-0.md) | B17-0's semantics: interface 6 (core terms) and the B17-0 part of interface 1 (the grammar), v1.1 Frozen |
| [`docs/manual.md`](docs/manual.md) | The agent reference manual: B17-0 for the model writing it, every example checked (WP8) |
| [`docs/roadmap.md`](docs/roadmap.md) | The phases and their gates, what's done, and what comes next |
| [`docs/b17-1.md`](docs/b17-1.md) | B17-1's semantics, as changes to B17-0's: its parts of interfaces 1 and 6, and interface 11 v0.2; v1.1 Frozen |
| [`suite/`](suite/) | B17-0's 50 labelled programs: 20 that must be accepted, and 30 that must be rejected, each with exactly one error named by its code. `suite/b17-1/` holds B17-1's 64, 10 to accept and 54 to reject, which the checker and verifier agree with too |
| [`b17c/syntax.py`](b17c/syntax.py) | Parser and canonical printer (§2, D47–D55); B17-1's grammar by default, and B17-0's with `--subset 0` (D101) |
| [`b17c/hashing.py`](b17c/hashing.py) | Spec and implementation hashes (D45, D46); B17-1's data types and binders (D92) |
| [`b17c/check.py`](b17c/check.py) | Tier 0 checker: names, types, ghost code, ownership, effects, returns, recursion (§2–§7, D66–D78); B17-1's by default, and B17-0's with `--subset 0` |
| [`b17c/core.b17`](b17c/core.b17) | The core library (WP16): `sorted`, `in_i64`, `seq_update`, and 33 laws as lemmas |
| [`b17c/core1.b17`](b17c/core1.b17) | B17-1's addition to the core library: the `option` type |
| [`b17c/hashes.txt`](b17c/hashes.txt) | Golden hashes of B17-0's 20 accept programs |
| [`b17c/interp.py`](b17c/interp.py) | Reference interpreter: §8, with contracts checked on request (D56–D59); B17-1's by default, and B17-0's with `--subset 0` |
| [`b17c/rust.py`](b17c/rust.py) | The Rust backend: one crate per module, whose runs print what the interpreter prints (D95–D97); B17-1's by default, and B17-0's with `--subset 0` (D110, D111) |
| [`b17c/goals.py`](b17c/goals.py) | Proof goals from WP3's types, one Z3 query each (§9); also checks the suite's proof labels; B17-1's by default, and B17-0's with `--subset 0` |
| [`b17c/verify.py`](b17c/verify.py) | The verifier's front end: canonical queries, the proof cache, and the trusted base report (D63); B17-1's by default, and B17-0's with `--subset 0` |
| [`b17c/agent.py`](b17c/agent.py) | The agent protocol, for B17-0: diagnostics as JSON (interface 3), and the five queries (interface 8) |
| [`gym/harness.py`](gym/harness.py) | WP17's harness: CLI agents writing verified Dafny, and B17-0 for M3 (D98) |
| [`gym/tasks/`](gym/tasks/) | Dafny tasks: 20 seed tasks, 64 from AlgoVeri, 28 from vericoding |
| [`gym/runs/`](gym/runs/) | One directory per run: `meta.json` holds the configuration and fingerprints, and `attempts.jsonl` every round of every attempt |
| [`DECISIONS.md`](DECISIONS.md) | Every design decision, with its status |
| [`ACTIVITY.md`](ACTIVITY.md) | What happened and the evidence for it, append-only |

## Getting started

**Requirements:**
- [uv](https://docs.astral.sh/uv/), with Python 3.11 or later. Everything runs through `uv run`, and `b17c` uses only the standard library.
- To build emitted Rust: rustc 1.99.1, the version CI pins (`rustup toolchain install 1.99.1`), with the platform's linker.
- To run benchmarks: Dafny 4.11.0 with Z3 5.3.2, plus the agent CLIs you want to compare: `claude`, `codex`, `agy` or `grok`.

**Self-checks.** Each one prints a line ending in "passed". CI runs the first eight on Linux for every pull request ([check.yml](.github/workflows/check.yml)).

```sh
uv run --no-project b17c/test_syntax.py    # parser: both suites round-trip, and every lexical and grammar rule is tested
uv run --no-project b17c/test_hashing.py   # hasher: golden file, worked examples, invariance under renames and edits, B17-1's D92
uv run --no-project b17c/test_interp.py    # interpreter: WP1a's conformance tests, from §8 and both suites
uv run --no-project b17c/test_check.py     # checker: both suites' labels exactly, every tier 0 code, every ownership rule
uv run --no-project b17c/test_core.py      # core library: every law confirmed by the interpreter (WP16's witnesses)
uv run --no-project b17c/test_agent.py     # agent protocol: diagnostics and the five queries (Z3 for the queries that solve)
uv run --no-project b17c/test_rust.py      # Rust backend: emitted crates compile, and runs match the interpreter, B17-0's and B17-1's (needs rustc)
uv run --no-project b17c/test_manual.py    # agent manual: every example has its stated outcome, every code has one (Z3 for proofs)
uv run --no-project b17c/test_verify.py    # verifier: cache hits, renames, invalidation, the report, B17-1's encoding (needs Z3)
uv run --no-project gym/test_harness.py    # harness verdicts (needs Dafny)
uv run --no-project gym/test_b17.py        # the harness's B17-0 track: tasks, verdicts, one attempt against a fake CLI (needs Z3)
```

**The toolchain:**

```sh
uv run --no-project b17c/syntax.py --subset 0 suite/accept/merge_sorted.b17     # canonical bytes, or E-PARSE-001 with line:col
uv run --no-project b17c/syntax.py suite/b17-1/accept/bst_insert.b17   # the same for B17-1, the default since it froze (D101)
uv run --no-project b17c/hashing.py --subset 0 suite/accept/*.b17                # MODULE KIND NAME SPEC-HASH IMPL-HASH per item
uv run --no-project b17c/check.py --subset 0 suite/reject/E-OWN-001-use-after-move.b17   # FILE:LINE:COL: CODE: message per diagnostic
uv run --no-project b17c/check.py suite/b17-1/reject/E-OWN-007-match-on-moving-field.b17   # the same for B17-1
uv run --no-project b17c/interp.py --subset 0 --check suite/accept/abs.b17 abs -5   # the trace and outcome: ok 5
uv run --no-project b17c/interp.py --check suite/b17-1/accept/discrete_logarithm.b17 discrete_log_naive 2 8 11   # ok (some 3)
uv run --no-project b17c/rust.py --subset 0 --run suite/accept/abs.b17 abs -5       # the same, from emitted Rust: ok 5
uv run --no-project b17c/rust.py --subset 0 -o abs suite/accept/abs.b17             # the binary; with FILE alone, the Rust it's built from
uv run --no-project b17c/rust.py --run suite/b17-1/accept/bst_insert.b17 insert "(leaf)" 5   # ok (node 5 (leaf) (leaf))
uv run --no-project b17c/verify.py --subset 0 suite/accept/merge_sorted.b17      # every goal, cached; --report FILE writes the trusted base part
uv run --no-project b17c/verify.py suite/b17-1/accept/bst_insert.b17   # the same for B17-1
uv run --no-project b17c/agent.py check suite/reject/E-PROOF-OVERFLOW-unbounded-increment.b17   # diagnostics as JSON, with a counterexample
uv run --no-project b17c/agent.py explain E-OWN-005                   # a code's rule, with the suite's labelled example
```

Canonical bytes put the module name and header on the first line, then one item per line (D47). Hashes ignore names: binders become `$0`, `$1`, … in the order they're bound, an item's own name becomes `_`, and references become the callee's spec hash. Renames therefore change no hash, and a body edit doesn't rehash its callers (D22, D45).

**The benchmark harness:**

```sh
uv run --no-project gym/harness.py check-tasks                       # reference solutions verify; contracts well-formed, non-trivial
uv run --no-project gym/harness.py run --clis claude,codex --samples 3 --tasks abs,fib
uv run --no-project gym/harness.py run --clis claude,codex,grok --samples 1 --jobs 6 --tasks algoveri/,vericoding/
uv run --no-project gym/harness.py run --clis claude,codex --samples 3 --tasks b17/   # M3: the seed tasks in B17-0 (D98)
uv run --no-project gym/harness.py reverify RUN_ID                   # re-check every recorded verdict
uv run --no-project gym/harness.py summary RUN_ID [RUN_ID ...]
```

An attempt is one task, one CLI and one sample: up to `--max-iters` stateless rounds of generating code, verifying it, and feeding back Dafny's raw output. `--resume RUN_ID` continues a stopped run.

## The benchmark

Babel-17's claims are measured against agents writing Dafny, the strongest existing target for verified code (WP17, D28, D32).

**How it works:**
- **Isolation:** each CLI runs through its own subscription (D13), with tools, web search, user configuration, hooks and MCP servers turned off. The exception is Grok's X search: it runs server-side and can't be disabled, so the harness counts every use.
- **Frozen contracts:** the agent's code is checked against the task's frozen contracts through a generated wrapper, so it can't weaken them.
- **The B17-0 track (D98):** the same seed tasks, posed in B17-0 with the agent manual in the prompt. The agent's items join the task module, so restating its spec is an error.
  - **Verified:** tier 0 passes, every spec has a def, and every goal is proved under 11 seeds. A spec without a def would let a call assume anything.
  - **Feedback:** between rounds, the agent gets `agent.py check`'s JSON diagnostics.
- **Verdicts:** banned constructs (`assume`, `{:axiom}`, `{:verify false}`, `decreases *`, and similar) fail outright, and an exhausted resource budget counts as a failure, never a pass.
- **Re-checking:** `reverify` re-runs every recorded verdict, and so far each one has reproduced exactly. One did only when run alone: under load, it hit the verifier's wall-clock timeout before Dafny's resource limit, so that timeout is now a 2-hour backstop.

**Results so far:**

| Run | Tasks | Claude | Codex | Gemini | Grok |
|---|---|---|---|---|---|
| Seed, 3 samples | 20 textbook tasks | 60/60 | 60/60 | 60/60 | 60/60 |
| Seed in B17-0 (M3), 3 samples | the same 20 tasks | 59/60 | 55/60 | — | — |
| M3 rerun with the manual's fixes, 3 samples | `insertion_sort` and `partition` | 6/6 | 6/6 | — | — |
| AlgoVeri, 1 sample | 66 algorithm specs | 64/66 | 60/66 | 28/28 before its quota ran out | — |
| AlgoVeri and vericoding, 1 sample | 93 tasks | 92/93 | 90/93 | — | 49/49 before its balance ran out |

The models are Claude `claude-opus-5-5`, Codex `gpt-5.6-sol`, Gemini `gemini-4-argon-high` and Grok `grok-4.7`, all at high effort. [ACTIVITY.md](ACTIVITY.md) has rounds, token costs and failure analyses for each run.

**What the benchmarks have changed so far.** Benchmarks steer the design, but they don't gate the language (D14).
- **`seq-build` bounds its index** (D38). In 6 of 6 first attempts, Codex's `reverse` failed because Dafny couldn't see the comprehension index's bound. In B17-0, the index is in range by construction.
- **Spec functions are ghost.** Solutions that ran the spec itself to brute-force the answer pass only when they can't call it.
- **Ported tasks state integer ranges** (D42), in the terms the proof already uses (`docs/b17-0.md` §10).
- **M3's first run changed the manual and the verifier.** The manual now lists the core library and says that a `set-idx` swap keeps a vector's multiset. Ghost multisets are covariant (D107), and equal sequences are the same sequence (D108).
- **An open question:** a functional spec can't tell Aho-Corasick from naive search, so the named algorithm is never enforced. That's the cost question D29 deferred.

Every set so far is near the ceiling for current models. The vericoding tasks were picked because at most a quarter of the models in its published results solved them, yet Claude and Codex verified all 28. Both of Claude's AlgoVeri failures in the first run, and its only failure in the second, were on specs no program can verify: `matrix_multiplication` is ill-formed and `rod_cutting` unsatisfiable, and both are now removed. The models still differ in rounds and tokens, but barely in what they verify. So the tasks hard enough to compare the two languages will have to be found elsewhere or written (WP10).

M3's first run, the same seed tasks in B17-0, failed 6 of its 120 attempts, all on `insertion_sort` and `partition`. Mostly, the manual didn't say that swapping two elements with `set-idx` keeps a vector's multiset, so agents tried to prove it themselves. It says so now, and in a rerun of the two tasks all 12 attempts verified in round 1, with no lemmas of their own. The manual alone made the difference: the rerun's programs verify with the first run's verifier too. So on the seed tasks B17-0 verifies what Dafny does, though the other 18 haven't been rerun under the new manual, and the two differ in cost. On these two tasks, Claude used about 4.6 times Dafny's tokens per verified task, mostly the manual in its prompt, and Codex about 1.2 times.

## How work is recorded

- **[DECISIONS.md](DECISIONS.md)** holds every design decision, numbered and dated, with its reasoning and what it touches.
  - Its statuses are Proposed, Accepted, Rejected, Open and Superseded.
  - An accepted decision is frozen. Changing one takes a new entry that supersedes or refines it.
  - Only the owner accepts decisions. Agents propose them.
  - `grep '^## D' DECISIONS.md` lists them all.
- **[ACTIVITY.md](ACTIVITY.md)** records what happened, when, and the evidence, and new entries go at the end. An entry that hands work on names:
  - the work package it advances;
  - the interfaces it touched;
  - the proofs and tests it added;
  - anything it left admitted.
- **Interfaces** between work packages are versioned and marked Draft or Frozen (D27). WP1a's interfaces, 6 and B17-0's part of 1, are Frozen (D44), and so are B17-1's parts of 1 and 6, in `docs/b17-1.md`. The rest are Draft:
  - 3 and 8, the diagnostics and queries, at version 0.1 (D93, D94);
  - 10, interpreter traces, at version 0.1 (D56);
  - 11, solver queries, at version 0.1, with 0.2 for B17-1 implemented by WP5 (D63, D89, D103, D105, D106, D108);
  - 5, the trusted base report, which now carries WP7's backend fields (D25, D97).
