# Babel-17 roadmap

Where the project stands, and what comes next. This is the state as of 2026-10-27.

**How the plan works:**
- **Phases, ordered by risk:** Babel-17 is built in five phases, ordered by risk rather than by date.
- **Gates:** each phase ends at a gate, and the next phase doesn't start until that gate passes.
- **Benchmarks:** they steer the design, by showing which features help agents and which only cost tokens. They don't decide whether the language gets built (D14).
- **Records:**
  - Decisions are numbered in [DECISIONS.md](../DECISIONS.md).
  - Evidence for every step is in [ACTIVITY.md](../ACTIVITY.md).
  - The full design spec is kept outside this repo.

## The phases

| Phase | What it builds | Gate to leave it |
|---|---|---|
| **0. Core semantics** | B17-0's written semantics and accept/reject suite (WP1a); the canonical form and content hashes (WP2); the reference interpreter (WP15); the baseline harness (WP17) | WP1a is frozen, WP2's round-trip tests pass, and WP15 passes its conformance tests (D16) |
| **1. Embedded MVP** | The checker, spec language, verifier, agent diagnostics, a backend that emits safe Rust, the agent manual, the core spec library and benchmark ports | Every ported benchmark task verifies end to end and runs as emitted Rust (D18) |
| **2. Training loop** | The training environment (`b17c gym`), and a model trained in it | A gym-trained model beats off-the-shelf models writing Dafny or Verus on held-out tasks. It must also beat the same base model trained on Dafny with equal compute (D31). |
| **3. Native backend** | A native backend whose every lowering pass is checked by translation validation; the package registry; a Rust rewrite of `b17c`, shipped as one binary (D10, D19) | Verified Babel-17 matches hand-written Rust on a benchmark suite |
| **4. Optimizer and ecosystem** | An ML optimizer behind a translation validator, superoptimization, FFI and a first production service | — |

**What decisions have changed in the original plan:**
- **The Lean proof moves later (D16).** The original Phase 0 gate required type soundness proven in Lean 4. That proof is now WP1b and comes after the Phase 2 gate. Until then, verdicts rest on the solver, and the trusted base report says so (D24, D25).
- **No elaborator yet (D33).** B17-0's canonical S-expression form is also its core language. WP3 is a checker, not an elaborator, until a richer surface syntax exists.
- **Python first (D19).** `b17c` stays a Python prototype until Phase 3, so distribution (WP9) waits for the Rust rewrite.
- **Manifest and lockfile (D26).** Their schemas move into Phase 0 under WP2, and the registry stays in Phase 3 (WP13).

## Where we are: Phase 0

### The Phase 0 gate

| Gate item | State |
|---|---|
| **WP1a frozen** | B17-0 v0.1 ([b17-0.md](b17-0.md)) and the 50-program [suite](../suite/) are drafted, and owner decisions are applied through D62, including D60's per-step ranges. Under D44, they freeze once WP3's checker agrees with every tier 0 label. That waits for WP3. |
| **WP2's round-trip tests pass** | Done. The parser and canonical printer round-trip the whole suite. The hasher's golden file reproduces on Linux CI, so content hashes match across machines (D46). |
| **WP15 passes its conformance tests** | Done. The interpreter is merged (PR #2) and passes WP1a's conformance tests. |

### Work in progress
- **WP3, the tier 0 checker,** is being built in a separate session, on the parser and hasher. It's the next step on the critical path.
- **Proof labels, checked mechanically.** A spike of WP5's goal generator, `b17c/goals.py`, runs the suite through Z3 under 10 shuffled seeds (D23).
  - **Proof rejects:** all 9 `E-PROOF-*` programs fail exactly their labelled goal.
  - **Accept programs:** all 20 prove every goal under every seed, with no hints. Before D60, four didn't, or did only by luck.
- **Baselines (WP17).**
  - Claude, Codex, Gemini and Grok each verified all 60 seed attempts in Dafny.
  - On AlgoVeri, Claude verified 64 of 66 tasks and Codex 60 of 66.
  - Both sets are near the ceiling for current models, so a harder set from vericoding is running now, against Claude, Codex and Grok.
- **WP16, the core spec library,** is under way (PR #9).
  - `b17c/core.b17` holds `sorted`, `in_i64`, `seq_update`, and 33 laws as lemmas: §9's background facts with D61's derived `contains` facts, and the laws of integer order.
  - **The interpreter confirms every law** at every point of a grid of sequences and integers. That's WP16's done-when (D28).
  - **The goal spike proves every law** under 10 shuffled seeds.
  - **Not in the library:** three of §9's facts. `push`'s effect is a statement fact. `set-idx`'s multiset effect would need a take-and-drop fact §9 lacks. Multiset extensionality ranges over every `int`, which the interpreter can't evaluate.
- **CI** runs the `b17c` self-checks on Linux for every pull request, including the core library's witnesses.

### Decisions waiting for the owner
None. D56–D62 were accepted on 2026-10-28.

### Left before the Phase 0 gate
1. Build WP3's checker until it agrees with every tier 0 label in the suite.
2. Freeze WP1a under D44.

These belong to Phase 0 but aren't part of its gate:
- **The rest of WP2:** the manifest and lockfile schemas (interface 7, D26) and typed edit operations (interface 2).
- **The hard baseline:** finish the vericoding run and analyse it. Re-run Gemini once its quota resets, around 2026-11-02.

## Phase 1

From D21's dependency table, as D62 amends it, the critical path to the Phase 2 gate is WP1a, WP2, WP3, WP16, WP5, WP6, WP8 and WP11. WP4b, WP10 and WP15 are each one step off it.

| WP | What | Depends on | Done when |
|---|---|---|---|
| WP3 | Tier 0 checker: types, names, ghost code, ownership, effects | WP1a, WP2 | It agrees with every tier 0 label in the suite |
| WP4a | The spec language | WP3 | Done when WP1a freezes (D62), since B17-0 already has a spec language |
| WP16 | The core spec library: `sorted`, ranges, sequence and multiset laws | WP1a, WP15 | Every entry has witness examples that the interpreter confirms (D28). In progress: met for its 33 laws and 3 ghost-fns. |
| WP5 | The verifier: `b17c` generates its own goals and sends them to Z3 (D17) | WP3, WP1a, WP16 | The worked example verifies, seed-shuffle checks pass (D23), and the proof cache hits on unchanged code. The goal spike is its starting point. |
| WP6 | Agent protocol and diagnostics | WP3, WP1a, WP5 | Diagnostics match interface 3, and all five queries answer (interface 8) |
| WP4b | The spec workbench: back-translation, vacuity checks, witnesses, mutant rejection, signing | WP1a, WP5, WP15 | They run on the worked example |
| WP7 | A backend that emits safe Rust (D18) | WP3, WP15 | Emitted code compiles and matches the interpreter on differential tests |
| WP8 | The agent reference manual | WP3, WP5, WP6 | Every rule and error code has an example, and every example passes `b17c check` |
| WP10 | Benchmark ports | WP1a, WP5 | Ported Dafny, Verus and Lean tasks verify end to end |

**The head-to-head experiment** is called M3 in the activity log.
- **What it does:** agents write B17-0 and Dafny for the same frozen tasks, whose specs stay aligned across the two languages (D42).
- **What it measures:** the success metrics: verified pass rate, repair rounds and tokens per verified task.
- **What it needs:** WP5, WP6, WP8 and WP10, and tasks hard enough to separate the two languages.
- **How it's used:** its results steer the design (D14).

## Phase 2

**The training environment, WP11.** It's done when:
- rewards and anti-hacking rules are enforced;
- a held-out split is frozen;
- an in-context baseline is recorded.

Agents first learn B17-0 from the manual in context, and models are trained in Phase 2 (D8, proposed).

**The gate** compares a gym-trained model against off-the-shelf models, and against the same base model trained on Dafny with equal compute (D31). Passing it needs open model weights and training compute. The CLI subscriptions used so far (D13) can run agents but can't train them.

**After the gate:** WP1b mechanizes the semantics in Lean 4, proves type soundness, and builds the kernel checker (D3, D16).

## Phases 3 and 4

- **Phase 3:**
  - `b17c` is rewritten in Rust. The rewrite is accepted when it reproduces the prototype's canonical bytes, hashes, verdicts and diagnostic codes on the benchmark corpus (D19).
  - Distribution as one binary or a WASM build (WP9, D10).
  - The native backend (WP12).
  - The package registry, where imports resolve only to lockfile hashes (WP13, D9).
- **Phase 4:** an ML optimizer whose transformations each pass translation validation (WP14), superoptimization, FFI and a first production service.

## Open questions that shape the plan

- **Hard enough tasks.** The seed tasks and AlgoVeri barely separate today's models in Dafny. If the vericoding set doesn't either, M3's tasks will have to be written (WP10).
- **The cost of i64 rigor.** Ranges stated the obvious way left four suite proofs needing a hint, or a solver's luck. Stated per step (D60), all four are stable and about 80 times cheaper. How specs must be phrased for the solver is part of Bet 1's cost, and M3 will show whether agents pay it.
- **Counterexamples.** With quantified axioms, a failing goal comes back unknown rather than with a counterexample, so WP6's diagnostics will often have none to show.
- **Algorithms specs can't see.** A functional spec can't tell Aho-Corasick from naive search. Cost contracts were deferred (D29, D30).
- **Training resources.** Phase 2 needs open weights and compute that the project doesn't have yet.
