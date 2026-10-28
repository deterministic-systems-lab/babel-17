# Babel-17

Babel-17 is a programming language built for LLMs to write and machines to check. People state intent in English and sign formal specs. Agents write dense, fully typed implementations that a verifier proves meet those specs, so nobody needs to read the implementation line by line. The aim is to make model-generated code faster to produce and faster to run, and trustworthy because it's proven rather than reviewed.

The goal is an all-purpose language: services, applications and their user interfaces, data pipelines, scripts and machine learning, not only verified algorithms (D64). Each module will carry a verification level: typed and memory-safe at the lowest, contracts tested above that, and proved correct against its formal spec at the highest. So code whose intent can't be stated precisely still has a place. Today's subset, B17-0, covers only integer and array algorithms, and the language grows from it in subsets chosen on evidence.

The design rests on three bets:
- **Rigor is cheap for machines.** Dependent types, effect tracking and proofs slow people down, but cost an agent in a compile-fix loop with a fast verifier very little.
- **A verifier replaces a training corpus.** No human-written Babel-17 exists, so models learn by generating code, checking it, and keeping what passes.
- **Information survives to the last step.** Types, invariants and intent reach the optimizer, so proven code can also be the fastest code.

The full design spec, *MFL: A Machine-First Language — Design Spec (Draft v0.1)*, is kept outside this repo. "MFL" was the working name (D12). Everything decided since is in [DECISIONS.md](DECISIONS.md).

## Status

**Phase 0, as of 2026-10-27.** Phase 0 builds the smallest language that can express real verified programs, and the tools to check it. Its gate (D16) has three parts:
1. WP1a's semantics and suite are frozen;
2. WP2's round-trip tests pass;
3. WP15's interpreter passes its conformance tests.

| WP | What | State |
|---|---|---|
| WP1a | B17-0 core semantics and the accept/reject suite | Drafted, v0.1 ([docs/b17-0.md](docs/b17-0.md), [suite/](suite/)). Freezes once WP3's checker agrees with the suite (D44). |
| WP2 | Canonical form and content hashes | Parser, canonical printer and hasher done ([b17c/](b17c/)). Both done-whens pass: round trips, and golden hashes reproduced on Linux CI (D46). Typed edits and the lockfile remain. |
| WP3 | Tier 0 checker: types, names, ghost code, ownership, effects | In progress, on the parser and hasher. |
| WP4a | The spec language | Done once WP1a freezes (D62): B17-0's spec language is WP1a's. |
| WP5 | Verifier: proof goals sent to Z3 | In progress: [b17c/verify.py](b17c/verify.py) caches every verdict under D22's key, sends canonical queries (interface 11, D63) and reports solver-trusted goals by node ID. The goals come from the spike, [b17c/goals.py](b17c/goals.py), with D61's encoding. It checks the suite's proof labels: all 20 accept programs prove every goal under 10 shuffled seeds (D23), and all 9 proof rejects fail as labelled. |
| WP15 | Reference interpreter | Done ([b17c/interp.py](b17c/interp.py)): passes WP1a's conformance tests. Interface 10 (traces, D56) is v0.1 Draft. |
| WP16 | Core spec library | In progress: [b17c/core.b17](b17c/core.b17) holds 3 ghost-fns and 33 laws: §9's background facts and integer order. The interpreter confirms each on a grid, and the goal spike proves each. |
| WP17 | Baseline harness: agents writing verified Dafny | Done ([gym/](gym/)). Benchmarks are running. |

[docs/roadmap.md](docs/roadmap.md) covers all five phases, what's left before the Phase 0 gate, what comes after it, and how the language grows from B17-0 toward D64's scope.

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

The full grammar, typing rules, semantics and proof goals are in [docs/b17-0.md](docs/b17-0.md).

## Repository layout

| Path | What |
|---|---|
| [`docs/b17-0.md`](docs/b17-0.md) | B17-0's semantics: interface 6 (core terms) and the B17-0 part of interface 1 (the grammar), v0.1 Draft |
| [`suite/`](suite/) | 50 labelled programs: 20 that must be accepted, and 30 that must be rejected, each with exactly one error named by its code |
| [`b17c/syntax.py`](b17c/syntax.py) | Parser and canonical printer (§2, D47–D55) |
| [`b17c/hashing.py`](b17c/hashing.py) | Spec and implementation hashes (D45, D46) |
| [`b17c/core.b17`](b17c/core.b17) | The core library (WP16): `sorted`, `in_i64`, `seq_update`, and 33 laws as lemmas |
| [`b17c/hashes.txt`](b17c/hashes.txt) | Golden hashes of every accept program |
| [`b17c/interp.py`](b17c/interp.py) | Reference interpreter: §8, with contracts checked on request (D56–D59) |
| [`b17c/goals.py`](b17c/goals.py) | Spike: proof goals for the suite, checked with Z3 (§9) |
| [`b17c/verify.py`](b17c/verify.py) | The verifier's front end: canonical queries, the proof cache, and the trusted base report (D63) |
| [`gym/harness.py`](gym/harness.py) | WP17's harness: CLI agents writing verified Dafny |
| [`gym/tasks/`](gym/tasks/) | Dafny tasks: 20 seed tasks, 65 from AlgoVeri, 28 from vericoding |
| [`gym/runs/`](gym/runs/) | One directory per run: `meta.json` holds the configuration and fingerprints, and `attempts.jsonl` every round of every attempt |
| [`DECISIONS.md`](DECISIONS.md) | Every design decision, with its status |
| [`ACTIVITY.md`](ACTIVITY.md) | What happened and the evidence for it, append-only |

## Getting started

**Requirements:**
- [uv](https://docs.astral.sh/uv/), with Python 3.11 or later. Everything runs through `uv run`, and `b17c` uses only the standard library.
- To run benchmarks: Dafny 4.11.0 with Z3 5.3.2, plus the agent CLIs you want to compare: `claude`, `codex`, `agy` or `grok`.

**Self-checks.** Each one prints a line ending in "passed". CI runs the first four on Linux for every pull request ([check.yml](.github/workflows/check.yml)).

```sh
uv run --no-project b17c/test_syntax.py    # parser: the suite round-trips, and every lexical rule is tested
uv run --no-project b17c/test_hashing.py   # hasher: golden file, worked examples, invariance under renames and edits
uv run --no-project b17c/test_interp.py    # interpreter: WP1a's conformance tests, from §8 and the suite
uv run --no-project b17c/test_core.py      # core library: every law confirmed by the interpreter (WP16's witnesses)
uv run --no-project b17c/test_verify.py    # verifier: cache hits, renames, invalidation, the report (needs Z3)
uv run --no-project gym/test_harness.py    # harness verdicts (needs Dafny)
```

**The toolchain:**

```sh
uv run --no-project b17c/syntax.py suite/accept/merge_sorted.b17     # canonical bytes, or E-PARSE-001 with line:col
uv run --no-project b17c/hashing.py suite/accept/*.b17                # MODULE KIND NAME SPEC-HASH IMPL-HASH per item
uv run --no-project b17c/interp.py --check suite/accept/abs.b17 abs -5   # the trace and outcome: ok 5
uv run --no-project b17c/verify.py suite/accept/merge_sorted.b17      # every goal, cached; --report FILE writes the trusted base part
```

Canonical bytes put the module name and header on the first line, then one item per line (D47). Hashes ignore names: binders become `$0`, `$1`, … in the order they're bound, an item's own name becomes `_`, and references become the callee's spec hash. Renames therefore change no hash, and a body edit doesn't rehash its callers (D22, D45).

**The benchmark harness:**

```sh
uv run --no-project gym/harness.py check-tasks                       # every task solvable, non-trivial and well-formed
uv run --no-project gym/harness.py run --clis claude,codex --samples 3 --tasks abs,fib
uv run --no-project gym/harness.py run --clis claude,codex,grok --samples 1 --jobs 6 --tasks algoveri/,vericoding/
uv run --no-project gym/harness.py reverify RUN_ID                   # re-check every recorded verdict
uv run --no-project gym/harness.py summary RUN_ID [RUN_ID ...]
```

An attempt is one task, one CLI and one sample: up to `--max-iters` stateless rounds of generating code, verifying it, and feeding back Dafny's raw output. `--resume RUN_ID` continues a stopped run.

## The benchmark

Babel-17's claims are measured against agents writing Dafny, the strongest existing target for verified code (WP17, D28, D32).

**How it works:**
- **Isolation:** each CLI runs through its own subscription (D13), with tools, web search, user configuration, hooks and MCP servers turned off. The exception is Grok's X search: it runs server-side and can't be disabled, so the harness counts every use.
- **Frozen contracts:** the agent's code is checked against the task's frozen contracts through a generated wrapper, so it can't weaken them.
- **Verdicts:** banned constructs (`assume`, `{:axiom}`, `{:verify false}`, `decreases *`, and similar) fail outright, and an exhausted resource budget counts as a failure, never a pass.
- **Re-checking:** `reverify` re-runs every recorded verdict, and so far each one has reproduced exactly.

**Results so far:**

| Run | Tasks | Claude | Codex | Gemini | Grok |
|---|---|---|---|---|---|
| Seed, 3 samples | 20 textbook tasks | 60/60 | 60/60 | 60/60 | 60/60 |
| AlgoVeri, 1 sample | 66 algorithm specs | 64/66 | 60/66 | 28/28 before its quota ran out | — |
| AlgoVeri and vericoding, 1 sample | 93 tasks | in progress | in progress | — | in progress |

The models are Claude `claude-opus-5-5`, Codex `gpt-5.6-sol`, Gemini `gemini-4-argon-high` and Grok `grok-4.7`, all at high effort. [ACTIVITY.md](ACTIVITY.md) has rounds, token costs and failure analyses for each run.

**What the benchmarks have changed so far.** Benchmarks steer the design, but they don't gate the language (D14).
- **`seq-build` bounds its index** (D38). In 6 of 6 first attempts, Codex's `reverse` failed because Dafny couldn't see the comprehension index's bound. In B17-0, the index is in range by construction.
- **Spec functions are ghost.** Solutions that ran the spec itself to brute-force the answer pass only when they can't call it.
- **Ported tasks state integer ranges** (D42), in the terms the proof already uses (§10).
- **An open question:** a functional spec can't tell Aho-Corasick from naive search, so the named algorithm is never enforced. That's the cost question D29 deferred.

Seed tasks and AlgoVeri are near the ceiling for current models, so the harder tasks come from vericoding: tasks that at most a quarter of the models in its published results solved.

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
- **Interfaces** between work packages are versioned and marked Draft or Frozen (D27). WP2, WP3 and WP15 may build on WP1a's draft before it freezes (D44).
