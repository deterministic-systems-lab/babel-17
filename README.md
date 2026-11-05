# Babel-17

Babel-17 is a programming language built for LLMs to write and machines to check. People state intent in English and sign formal specs. Agents write dense, fully typed implementations that a verifier proves meet those specs, so nobody needs to read the implementation line by line. The aim is to make model-generated code faster to produce and faster to run, and trustworthy because it's proven rather than reviewed.

The goal is an all-purpose language: services, applications and their user interfaces, data pipelines, scripts and machine learning, not only verified algorithms (D64). Each module carries a verification level: typed and memory-safe at the lowest, contracts tested above that, and proved correct against its formal spec at the highest. So code whose intent can't be stated precisely still has a place. B17-0, the first subset, covers integer and array algorithms, and B17-1 adds data types, tuples and ghost sets and maps. The language grows in subsets chosen on evidence.

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

Phase 1, the embedded MVP, has begun. B17-1, the second subset, froze on 2026-10-30 with its labelled suite, D113 corrected four of its statements, making it v1.1, and D114 gave `push` a goal on its vector's length, making it v1.2 ([docs/b17-1.md](docs/b17-1.md), [suite/b17-1/](suite/b17-1/)): its parser, hasher and checker agree with every tier 0 label, its interpreter and Rust backend run every accept program, and its verifier checks every proof label. WP6, the agent protocol, WP7, the Rust backend, and WP8, the agent reference manual, are done for B17-0 and B17-1.

| WP | What | State |
|---|---|---|
| WP1a | B17-0 core semantics and the accept/reject suite | Done: frozen at v1.0 on 2026-10-28 ([docs/b17-0.md](docs/b17-0.md), [suite/](suite/)), once WP3's checker agreed with every tier 0 label (D44). D107 amended it to v1.1 on 2026-10-29, loosening only its subtyping, and D114 to v1.2 on 2026-11-02, giving `push` a goal on its vector's length. |
| WP2 | Canonical form and content hashes | Parser, canonical printer and hasher done ([b17c/](b17c/)). Both done-whens pass: round trips, and golden hashes reproduced on Linux CI (D46). Typed edits, and the manifest and lockfile schemas, remain (interfaces 2, 4 and 7). |
| WP3 | Tier 0 checker: types, names, ghost code, ownership, effects | Done ([b17c/check.py](b17c/check.py)): agrees with every tier 0 label in the suite. Its readings of the semantics are D66–D78, accepted. It checks B17-1 too, by default, and agrees with every tier 0 label of `suite/b17-1/`. B17-1's freeze review settled seven more readings (D109). |
| WP4a | The spec language | Done (D62, D79): B17-0's spec language is WP1a's, and B17-1 adds no data-type invariants or refinement links. |
| WP4b | Spec workbench: checks that a spec says what's meant | Done on the worked example ([b17c/spec.py](b17c/spec.py), D121): vacuity checks, witness examples, mutant rejection, back-translation by Codex, and signatures on spec hashes, which the trusted base report lists as `unsigned_specs`. A `requires` no input meets, or an input no output serves, comes with a spec challenge (interface 9). |
| WP5 | Verifier: proof goals sent to Z3 | Done for B17-0: [b17c/verify.py](b17c/verify.py) caches every verdict under D22's key, sends canonical queries (interface 11, D63) and reports solver-trusted goals by node ID. [b17c/goals.py](b17c/goals.py) generates the goals from WP3's types, with D61's encoding. It checks the suite's proof labels: all 20 accept programs prove every goal under 10 shuffled seeds (D23), and all 9 proof rejects fail as labelled. It verifies B17-1 too, by default (D89, D103, D105, D106, D108): its 6 proof rejects fail as labelled, and all 15 of its accept programs prove every goal, `kruskal`'s minimum spanning tree and the maximum flows of `edmond_karp` and `push_relabel` included. A review of that work found two ways the verifier could prove `false`, in B17-0 as well, and both are fixed (D103). No B17-0 suite proof relied on them. A later review found a third: a binder or parameter could share its SMT name with a ghost-fn, so a definition read the wrong value. It's fixed too, and no suite proof or agent's program relied on it. B17-1's verification levels are built (`docs/b17-1.md` §10, D120): `--level L0|L1|L2|L3` and the report give the level a module reaches, from proofs, from D88's property tests in the interpreter, and from L2's closure, which solves a proof again without what rests on a goal that's only tested. |
| WP6 | Agent protocol and diagnostics | Done for B17-0 and B17-1 ([b17c/agent.py](b17c/agent.py)). Diagnostics carry interface 3's fields (D93), with counterexamples the interpreter replays, and the five queries answer (interface 8, D94). In B17-1 a counterexample shows tuple and data values as terms, with any sequence inside as a `seq-lit`, but none yet for sets, maps or multisets (D112). Repairs wait for WP2's typed edits. |
| WP7 | Backend that emits safe Rust | Done for B17-0 and B17-1 ([b17c/rust.py](b17c/rust.py)): every program that passes tier 0 becomes a crate that forbids unsafe code, and its runs print exactly what the interpreter prints, on both suites, corner cases and generated programs. Its readings are D95–D97 for B17-0 and D110–D111 for B17-1, all accepted. It lowers B17-1 too, by default, with data types as Rust enums. |
| WP8 | Agent reference manual | Done for B17-0 ([docs/manual.md](docs/manual.md)) and B17-1, with its supplement ([docs/manual-1.md](docs/manual-1.md)): every rule and all 25 error codes with a minimal example, each checked against its stated outcome by `test_manual.py`. The supplement's 27 examples cover what B17-1 adds, and are checked the same way (D112). |
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
| [`docs/b17-0.md`](docs/b17-0.md) | B17-0's semantics: interface 6 (core terms) and the B17-0 part of interface 1 (the grammar), v1.2 Frozen |
| [`docs/manual.md`](docs/manual.md) | The agent reference manual: B17-0 for the model writing it, every example checked (WP8) |
| [`docs/manual-1.md`](docs/manual-1.md) | The manual's B17-1 supplement, for M3's B17-1 track: what B17-1 adds, every example checked (D112), and one worked long proof (D117) |
| [`docs/roadmap.md`](docs/roadmap.md) | The phases and their gates, what's done, and what comes next |
| [`docs/b17-1.md`](docs/b17-1.md) | B17-1's semantics, as changes to B17-0's: its parts of interfaces 1 and 6, and interface 11 v0.2; v1.2 Frozen |
| [`suite/`](suite/) | B17-0's 50 labelled programs: 20 that must be accepted, and 30 that must be rejected, each with exactly one error named by its code. `suite/b17-1/` holds B17-1's 69, 15 to accept and 54 to reject, which the checker and verifier agree with too |
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
| [`b17c/spec.py`](b17c/spec.py) | The spec workbench (WP4b, D121): vacuity checks, witnesses, mutants, back-translation and signatures |
| [`b17c/agent.py`](b17c/agent.py) | The agent protocol: diagnostics as JSON (interface 3), and the five queries (interface 8); B17-1's by default, and B17-0's with `--subset 0` |
| [`gym/harness.py`](gym/harness.py) | WP17's harness: CLI agents writing verified Dafny, and B17-0 and B17-1 for M3 (D98, D112) |
| [`gym/audit.py`](gym/audit.py) | The run-time audit: a run's verified B17 programs, on random valid inputs, against a separate reference (D118) |
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
uv run --no-project b17c/test_interp.py    # interpreter: WP1a's conformance tests, from §8 and both suites; D88's generator and property tests
uv run --no-project b17c/test_check.py     # checker: both suites' labels exactly, every tier 0 code, every ownership rule
uv run --no-project b17c/test_core.py      # core library: every law confirmed by the interpreter (WP16's witnesses)
uv run --no-project b17c/test_agent.py     # agent protocol: diagnostics and the five queries (Z3 for the queries that solve)
uv run --no-project b17c/test_rust.py      # Rust backend: emitted crates compile, and runs match the interpreter, B17-0's and B17-1's (needs rustc)
uv run --no-project b17c/test_manual.py    # agent manual and its B17-1 supplement: every example has its stated outcome, every code has one (Z3 for proofs)
uv run --no-project b17c/test_spec.py      # spec workbench: vacuity, witnesses, mutants, back-translation against a fake CLI, signing (needs Z3)
uv run --no-project b17c/test_verify.py    # verifier: cache hits, renames, invalidation, the report, B17-1's encoding, the levels (needs Z3)
uv run --no-project gym/test_harness.py    # harness verdicts (needs Dafny)
uv run --no-project gym/test_b17.py        # the harness's B17-0 and B17-1 tracks: tasks, verdicts, one attempt against a fake CLI (needs Z3)
uv run --no-project gym/test_audit.py      # run-time audit: each task's reference against the suite; it catches a wrong answer, the length trick, a search
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
uv run --no-project b17c/verify.py --level L2 --report r.json suite/b17-1/reject/E-PROOF-FIELD-wrong-constructor.b17   # fails: L0, a test refutes FIELD
uv run --no-project b17c/spec.py --subset 0 witness suite/accept/merge_sorted.b17 merge_sorted   # inputs, the output, and outputs it forbids
uv run --no-project b17c/spec.py --subset 0 mutants suite/accept/merge_sorted.b17 merge_sorted   # each small bug, killed or surviving
uv run --no-project b17c/spec.py --subset 0 english suite/accept/merge_sorted.b17   # Codex's English for each spec, and where it disagrees with the header
uv run --no-project b17c/agent.py --subset 0 check suite/reject/E-PROOF-OVERFLOW-unbounded-increment.b17   # diagnostics as JSON, with a counterexample
uv run --no-project b17c/agent.py check suite/b17-1/reject/E-PROOF-FIELD-wrong-constructor.b17   # the same for B17-1: t is (leaf)
uv run --no-project b17c/agent.py explain E-OWN-005                   # a code's rule, with the suite's labelled example
```

Canonical bytes put the module name and header on the first line, then one item per line (D47). Hashes ignore names: binders become `$0`, `$1`, … in the order they're bound, an item's own name becomes `_`, and references become the callee's spec hash. Renames therefore change no hash, and a body edit doesn't rehash its callers (D22, D45).

**The benchmark harness:**

```sh
uv run --no-project gym/harness.py check-tasks                       # reference solutions verify; contracts well-formed, non-trivial
uv run --no-project gym/harness.py run --clis claude,codex --samples 3 --tasks abs,fib
uv run --no-project gym/harness.py run --clis claude,codex,grok --samples 1 --jobs 6 --tasks algoveri/,vericoding/
uv run --no-project gym/harness.py run --clis claude,codex --samples 3 --tasks b17/   # M3: the seed tasks in B17-0 (D98)
uv run --no-project gym/harness.py run --clis claude,codex --samples 3 --tasks b17-1/   # M3: the AlgoVeri ports in B17-1 (D112)
uv run --no-project gym/harness.py reverify RUN_ID                   # re-check every recorded verdict
uv run --no-project gym/audit.py RUN_ID                              # run a run's verified B17 programs on random valid inputs (D118)
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
- **The B17-1 track (D112):** the AlgoVeri ports in `suite/b17-1/accept/`, except `bfs`, whose whole proof the supplement shows as a worked example (D117), posed in B17-1 with the manual and its B17-1 supplement in the prompt. Each task gives its first spec and the data items and ghost-fns that spec refers to. Its defs, helper specs and proof-only items stay hidden. It's verified and fed back as the B17-0 track is, at subset 1.
- **Verdicts:** banned constructs (`assume`, `{:axiom}`, `{:verify false}`, `decreases *`, and similar) fail outright, and an exhausted resource budget counts as a failure, never a pass.
- **Re-checking:** `reverify` re-runs every recorded verdict, and so far each one has reproduced exactly. One did only when run alone: under load, it hit the verifier's wall-clock timeout before Dafny's resource limit, so that timeout is now a 2-hour backstop.

**Results so far:**

| Run | Tasks | Claude | Codex | Gemini | Grok |
|---|---|---|---|---|---|
| Seed, 3 samples | 20 textbook tasks | 60/60 | 60/60 | 60/60 | 60/60 |
| Seed in B17-0 (M3), 3 samples | the same 20 tasks | 59/60 | 55/60 | — | — |
| M3 rerun with the manual's fixes, 3 samples | `insertion_sort` and `partition` | 6/6 | 6/6 | — | — |
| AlgoVeri ports in B17-1 (M3), 3 samples | 10 of the AlgoVeri tasks | 30/30 | 27/30 | — | — |
| WP10's harder ports in B17-1 (M3), 3 samples | 5 of the AlgoVeri tasks | 15/15 | 0/15 | — | — |
| The same ports, rerun with the hole closed (M3), 3 samples | the same 5 tasks | 15/15 | 0/15 | — | — |
| The same ports, Codex only, with the prompt worded as Dafny's (M3), 3 samples | the same 5 tasks | — | 0/15 | — | — |
| The same, with a complete worked proof added to the prompt (M3), 3 samples | the same 5 tasks | — | 3/15 | — | — |
| The same, with that proof in the manual's supplement instead (M3), 3 samples | the same 5 tasks | 15/15 | 0/15 | — | — |
| All 14 ports in B17-1, under one prompt (M3), 3 samples | 14 of the AlgoVeri tasks | 42/42 | 25/42 | — | — |
| AlgoVeri, 1 sample | 66 algorithm specs | 64/66 | 60/66 | 28/28 before its quota ran out | — |
| AlgoVeri and vericoding, 1 sample | 93 tasks | 92/93 | 90/93 | — | 49/49 before its balance ran out |

The models are Claude `claude-opus-5-5`, Codex `gpt-5.6-sol`, Gemini `gemini-4-argon-high` and Grok `grok-4.7`, all at high effort. [ACTIVITY.md](ACTIVITY.md) has rounds, token costs and failure analyses for each run. The first two B17-1 rows leave out 10 of Codex's attempts that passed through a hole in the verifier, described below.

**What the benchmarks have changed so far.** Benchmarks steer the design, but they don't gate the language (D14).
- **`seq-build` bounds its index** (D38). In 6 of 6 first attempts, Codex's `reverse` failed because Dafny couldn't see the comprehension index's bound. In B17-0, the index is in range by construction.
- **Spec functions are ghost.** Solutions that ran the spec itself to brute-force the answer pass only when they can't call it.
- **Ported tasks state integer ranges** (D42), in the terms the proof already uses (`docs/b17-0.md` §10).
- **M3's first run changed the manual and the verifier.** The manual now lists the core library and says that a `set-idx` swap keeps a vector's multiset. Ghost multisets are covariant (D107), and equal sequences are the same sequence (D108).
- **`push` has a goal on its vector's length** (D114). In M3's run of the harder ports, all 8 of Codex's passes pushed onto a vector of 2^63 − 1 elements, after which every goal proved. A push now needs room for one more element.
- **Claude's long replies are read whole.** The same run lost 5 of Claude's 35 replies: past the output limit, Claude Code resumes a reply in a new message, and the harness read only the last.
- **A missing `)` is located.** In M3's first B17-1 run, 22 of 120 rounds failed on unbalanced parentheses, and the parser put a missing `)` at the module's first line, in the part the agent didn't write. It now names the item that probably lacks it, and every other item that doesn't balance, so an agent can fix them in one round.
- **The supplement shows a whole long proof** (D117). With only the manuals' short examples, Codex rarely attempted the harder ports. With a complete proof in its prompt, its first rounds ran past 7,000 characters in 8 of 15 attempts, against 1 of 15, and it verified 3 of 15 after none of 45. With the proof in the supplement, its attempts stayed long, but it verified none of 15.
- **An open question:** a functional spec can't tell Aho-Corasick from naive search, so the named algorithm is never enforced. That's the cost question D29 deferred.

Every set before WP10's harder ports was near the ceiling for current models. The vericoding tasks were picked because at most a quarter of the models in its published results solved them, yet Claude and Codex verified all 28. Both of Claude's AlgoVeri failures in the first run, and its only failure in the second, were on specs no program can verify: `matrix_multiplication` is ill-formed and `rod_cutting` unsatisfiable, and both are now removed. The models still differ in rounds and tokens, but barely in what they verify. So the tasks hard enough to compare the two languages will have to be found elsewhere or written (WP10).

M3's first run, the same seed tasks in B17-0, failed 6 of its 120 attempts, all on `insertion_sort` and `partition`. Mostly, the manual didn't say that swapping two elements with `set-idx` keeps a vector's multiset, so agents tried to prove it themselves. It says so now, and in a rerun of the two tasks all 12 attempts verified in round 1, with no lemmas of their own. The manual alone made the difference: the rerun's programs verify with the first run's verifier too. So on the seed tasks B17-0 verifies what Dafny does, though the other 18 haven't been rerun under the new manual, and the two differ in cost. On these two tasks, Claude used about 4.6 times Dafny's tokens per verified task, mostly the manual in its prompt, and Codex about 1.2 times.

M3's first B17-1 run posed 10 of the AlgoVeri tasks, ported to B17-1, and 57 of its 60 attempts verified. Claude verified all 30, and Codex 27, failing all 3 of its `kruskal` attempts. In Dafny's two AlgoVeri runs, Claude verified all 10 of these tasks both times, and Codex 9, failing `kruskal` both times. So these tasks don't separate the languages either, though they differ in cost. Claude used about 4.5 times Dafny's tokens per verified task, mostly the manual and its supplement in the prompt, and Codex about 1.9 times. Codex's output was only 1.2 times Dafny's, so the language itself doesn't force much longer programs. Claude's was 3.6 times, with 4.6 times the thinking. And B17-1 has a cost Dafny doesn't: 22 of the 120 rounds failed on unbalanced parentheses, and for a missing `)` the parser's message didn't say where. It now names the item that probably lacks it.

So the next ports are the AlgoVeri tasks that were hardest in Dafny. Besides `kruskal`, only `prim`, `edmond_karp` and `push_relabel` had a Dafny failure in the two runs, and `bellman_ford` and `dijkstra` took Codex 6 or 7 rounds. All five are ported and verified, and join the B17-1 track, `push_relabel` with a real push-relabel algorithm.

In M3's run of the five, Claude verified all 15 attempts and Codex none. In Dafny's two runs, Codex verified 6 of these 10. So these are the first tasks that separate the two languages, though only for Codex. Codex wrote an attempt at the algorithm in only 5 of its 15 samples, and otherwise tried to get around the proof. Claude used about 3.3 times Dafny's tokens per verified task, and wrote programs of 917 lines at the median, against 548 in Dafny.

The run also found a hole in the verifier. A vector pushed past 2^63 − 1 elements made every later goal provable. The language counted that push as an allocation failure, which aborts and is outside the semantics, so `push` had no proof goal, and the encoding then stated both that the vector's length was 2^63 and that no vector's was. All 8 of Codex's passes in the run were this trick, and so were 2 in the first B17-1 run, all left out above. No Claude program used it. Now `push` has a proof goal that its vector has room for one more element, as an `i64` operation has one that it doesn't overflow (D114). Of the agents' 34 verified programs that push, 17 fail it, and would need their vector's length bounded, as three of the suite's programs now do.

M3 then reran the five with the hole closed and Claude's replies read whole. Claude again verified all 15, in 1.73 rounds on average against 2.33, at about 2.4 times Dafny's tokens per verified task, with no reply lost. Run on 25 random valid graphs each, all 15 of its programs gave the right answer every time. The new goal on `push` failed in none of the 130 rounds with code.

Codex again verified none, against 6 of 10 in Dafny. It no longer tried the trick, but it rarely tried the proof either. Its median round was 637 characters, against 24,383 on these tasks in Dafny, and it wrote no loop at all for either maximum-flow task. In 16 rounds it declined, saying it couldn't guarantee a pass without running the checker. Its longest attempts, on `dijkstra`, failed to parse in 15 of 24 rounds. Why it attempts so little is open: it writes programs about as long as Dafny's on the first 10 ports, and long attempts at these same tasks in Dafny, with no tools in either case. A further run tested one explanation, the prompt (D115). With B17-1's first line worded as Dafny's, and a rule saying that diagnostics come back for repair, Codex again verified none of 15. It declined in only 2 rounds, but 13 of its 15 first rounds stayed under 4,000 characters, and it still wrote no loop for either maximum-flow task. There, most rounds put the task's guarantee on a helper spec instead, which the checker, the harness or the verifier caught every time. So the wording isn't the cause, though the new wording stays.

A last run added one complete port to the prompt, `bfs`, as a worked example of a long proof (D116). That changed a lot. Codex verified 3 of 15, all three of its `dijkstra` samples, in 6 to 8 rounds, against 6 and 7 in Dafny, at about 2.2 times Dafny's tokens per verified task. All three gave the right answer on 25 random valid graphs each. 8 of its 15 first rounds ran past 7,000 characters, against 1 of 15. Maximum flow stayed out of reach, though: `edmond_karp` stayed under 1,600 characters, and the longest `push_relabel` attempts, up to 41,900 characters, were exhaustive searches over flow matrices, which the spec can't tell from push-relabel. Long programs also fail to parse more often, in 27 of 117 rounds. That example gave away a task, so it came out after the run. The manual's supplement now has `bfs` in full, and `bfs` is no longer a task (D117).

The next run tested that with both agents. Claude again verified all 15, at about 2.0 times Dafny's tokens per verified task, down from 2.4, and all 15 programs gave the right answer on 25 random valid graphs each. Its programs borrow lemmas from the example, but that fall isn't shown to be the example's, since `bellman_ford` nearly halved, `prim` didn't move and `push_relabel` rose. Codex verified none of 15, and its `dijkstra` passes didn't repeat, though one sample came within a single failed goal. Its median round stayed long, at 15,306 characters against 2,006 without the example. 4 of its 6 maximum-flow samples now wrote loops, but every one is an exhaustive search over flow matrices. So is its one maximum-flow pass in Dafny, and one of Claude's there, so a verified program on these tasks isn't always a usable one. E-PARSE-001's new note reached 8 rounds, and in none of the 7 that had a next round were the parentheses unbalanced again, against 16 of 36 in the three earlier Codex runs.

Since a verdict can't show any of that, M3's write-ups now run the verified B17 programs, on 25 random valid inputs against a reference written separately (D118). Across all eight B17 runs, 224 of the 235 audited gave the right answer every time, and the other 11 ran out of steps. None gave a wrong answer. The 6 for `bfs`, no longer a task, weren't audited. 10 of the 11 are Codex's passes through the length hole. The other is one of Claude's `kruskal` programs from the first B17-1 run, and its proof is real, but it tries every sequence of n − 1 edges, so it can't finish on 10 vertices. These specs state no cost, so a verdict alone doesn't say whether a program is usable.

The most recent run put all 14 ports under one prompt, so it's the one to read for where B17-1 stands. Against Dafny on the same tasks, Claude verified 42 of 42 against 28 of 28, at about 2.5 times the tokens per verified task, and Codex 25 of 42 against 22 of 28, at about 2.8 times. All 67 programs gave the right answer on 25 random valid inputs each, and none came near the step limit.

- **What verifies:** the two languages differ only for Codex, and mostly on the 5 harder ports, where it verified 2 of 15 against 6 of 10. On the other 9, it verified 23 of 27 against 16 of 18.
- **Cost:** Claude's ratio falls as tasks get harder, from 3.8 times on the 9 to 2.0 on the 5, since about a third of its tokens are the fixed prompt, about 36k per call against about 4k in Dafny. So cost parity isn't shown, and that's what B17-1's case over Dafny still needs. A repeat of the 5 harder ports under the same setup gave nearly the same total for Claude, though single tasks moved by up to about 1.7 times.
- **A limit in the harness:** feedback is cut at the same 6,000 characters in both languages, but B17's diagnostics are much wordier. So 21 of the 161 repair prompts Codex got were cut, against 2 of 89 in Dafny, and about 40% of the diagnostics in those prompts never reached it. Whether that accounts for any of the gap isn't measured. B17's cut now ends at a whole diagnostic and says how many more there are (D119), though it shows no more of them, and no run has used it yet.

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
  - 3 and 8, the diagnostics and queries, at version 0.1 (D93, D94), with 0.2 for B17-1's counterexample terms (D112);
  - 9, spec signatures and spec challenges, at version 0.1 (D121);
  - 10, interpreter traces, at version 0.1 (D56);
  - 11, solver queries, at version 0.1, with 0.2 for B17-1 implemented by WP5 (D63, D89, D103, D105, D106, D108);
  - 5, the trusted base report, which now carries WP7's backend fields (D25, D97), B17-1's level fields (D80, D120) and `unsigned_specs` (D121).
