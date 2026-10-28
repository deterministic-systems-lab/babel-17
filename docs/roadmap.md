# Babel-17 roadmap

Where the project stands, and what comes next. This is the state as of 2026-10-28.

**How the plan works:**
- **The goal:** an all-purpose language for agents to write, from services and pipelines to user interfaces and machine learning, with each module held to the verification level its spec supports, from typed and memory-safe to proved correct (D64). The phases build toward it from a small verified core.
- **Two tracks:** the phases build the toolchain, and the language grows alongside them in subsets, from B17-0 to B17-1 and on (D65). See [How the language grows](#how-the-language-grows).
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
| **1. Embedded MVP** | The checker, spec language, verifier, agent diagnostics, a backend that emits safe Rust, the agent manual, the core spec library and benchmark ports; B17-1, the second language subset (D65) | B17-1 is frozen, and every ported benchmark task, B17-1's included, verifies end to end and runs as emitted Rust (D18, D65) |
| **2. Training loop** | The training environment (`b17c gym`), and a model trained in it | A gym-trained model beats off-the-shelf models writing Dafny or Verus on held-out tasks. It must also beat the same base model trained on Dafny with equal compute (D31). |
| **3. Native backend** | A native backend whose every lowering pass is checked by translation validation; the package registry; a Rust rewrite of `b17c`, shipped as one binary (D10, D19) | Verified Babel-17 matches hand-written Rust on a benchmark suite |
| **4. Optimizer and ecosystem** | An ML optimizer behind a translation validator, superoptimization, FFI and a first production service | — |

**What decisions have changed in the original plan:**
- **The Lean proof moves later (D16).** The original Phase 0 gate required type soundness proven in Lean 4. That proof is now WP1b and comes after the Phase 2 gate. Until then, verdicts rest on the solver, and the trusted base report says so (D24, D25).
- **No elaborator yet (D33).** B17-0's canonical S-expression form is also its core language. WP3 is a checker, not an elaborator, until a richer surface syntax exists.
- **Python first (D19).** `b17c` stays a Python prototype until Phase 3, so distribution (WP9) waits for the Rust rewrite.
- **Manifest and lockfile (D26).** Their schemas move into Phase 0 under WP2, and the registry stays in Phase 3 (WP13).

## Where we are: Phase 0's gate has passed

### The Phase 0 gate

All three items hold, so Phase 1 begins. Two pieces of Phase 0 that aren't part of the gate are still open, listed [below](#phase-0-work-outside-the-gate).

| Gate item | State |
|---|---|
| **WP1a frozen** | Done. B17-0 v1.0 ([b17-0.md](b17-0.md)) and the 50-program [suite](../suite/) froze on 2026-10-28 under D44, once WP3's checker agreed with every tier 0 label. D66–D78, the readings the checker settled, are written into `b17-0.md`. |
| **WP2's round-trip tests pass** | Done. The parser and canonical printer round-trip the whole suite. The hasher's golden file reproduces on Linux CI, so content hashes match across machines (D46). |
| **WP15 passes its conformance tests** | Done. The interpreter is merged (PR #2) and passes WP1a's conformance tests. |

### Recent and current work
- **WP3, the tier 0 checker,** is merged (PR #15): `b17c/check.py`.
  - **It agrees with every label** of the 50-program suite: the 20 accept programs and 9 proof rejects pass tier 0, and each of the other 21 rejects fails with exactly its code, one of them at the parser.
  - **D66–D78** record the readings it settled where §2–§9 were silent, such as block scoping, which types are well formed, and where a borrow may appear. They're accepted and written into `b17-0.md`.
  - **Review:** a Codex bug hunt ran 29,694 random modules through it with no crash, and found 4 bugs, all fixed. Two were false accepts, one a false reject and one a wrong code.
- **Proof labels, checked mechanically.** WP5's goal generator, `b17c/goals.py`, runs the suite through Z3 under 10 shuffled seeds (D23).
  - **Proof rejects:** all 9 `E-PROOF-*` programs fail exactly their labelled goal.
  - **Accept programs:** all 20 prove every goal under every seed, with no hints. Before D60, four didn't, or did only by luck.
- **Baselines (WP17).**
  - Claude, Codex, Gemini and Grok each verified all 60 seed attempts in Dafny.
  - On AlgoVeri, Claude verified 64 of 66 tasks and Codex 60 of 66.
  - On the hard run, 65 AlgoVeri and 28 vericoding tasks, Claude verified 92 of 93, Codex 90 and Grok all 49 it finished before its balance ran out.
  - Claude's only failure, `rod_cutting`, has a spec no program can satisfy, so it's removed. Every set is near the ceiling, vericoding's included.
- **WP16, the core spec library,** is under way. Its first part is merged (PR #9).
  - `b17c/core.b17` holds `sorted`, `in_i64`, `seq_update`, and 33 laws as lemmas: §9's background facts with D61's derived `contains` facts, and the laws of integer order.
  - **The interpreter confirms every law** at every point of a grid of sequences and integers. That's WP16's done-when (D28).
  - **The verifier proves every law** under 10 shuffled seeds.
  - **Not in the library:** three of §9's facts. `push`'s effect is a statement fact. `set-idx`'s multiset effect would need a take-and-drop fact §9 lacks. Multiset extensionality ranges over every `int`, which the interpreter can't evaluate.
- **WP5, the verifier,** is done for B17-0: `b17c/verify.py`, with its goals from `b17c/goals.py`.
  - **What it does:** it sends canonical queries (interface 11, D63), caches every verdict under D22's key, and reports solver-trusted goals by node ID (D24, D25).
  - **Its three done-whens hold:** the worked example verifies, seed-shuffle checks pass, and the proof cache hits on unchanged code. It also hits on renamed code, and after a callee's body edit.
  - **Goals from WP3's types:** each expression's SMT sort is the type the checker gives it, where the goal spike guessed. Multisets of booleans and empty literals typed only by what they're compared with now verify. A module that fails tier 0 gets its diagnostics instead of goals.
- **B17-1's spec text** is drafted (PR #21): `docs/b17-1.md`, version 0.1, written as changes to B17-0's, with D81–D92 accepted. Its labelled suite comes next.
- **WP7, the Rust backend,** is done for B17-0: `b17c/rust.py` (D95–D97).
  - **Emitted code compiles:** every module that passes tier 0 becomes a crate that forbids unsafe code and checks every runtime goal where §8 does.
  - **Runs match the interpreter:** 8,875 differential runs print exactly the interpreter's text, across the suite, corner cases and generated programs, with rustc 1.99.1 pinned. Fuzzing and a mutation check found no mismatch left.
- **WP6, the agent protocol,** is done for B17-0: `b17c/agent.py`.
  - **Diagnostics** carry interface 3's fields (D93). That includes the goal over the program's names, a counterexample the interpreter replays, the slice of items needed to fix it, and how many goals depend on it.
  - **The five queries answer** (interface 8, D94). `search` finds specs by what they guarantee, by verifying a def that only calls each candidate.
  - **Not yet:** repairs, which wait for WP2's typed edits.
- **CI** runs the `b17c` self-checks on Linux for every pull request, including the core library's witnesses.

### Decisions waiting for the owner
None new. D79–D97 were accepted on 2026-10-28: B17-1's scope and spec text, WP6's interfaces and WP7's readings. D2–D10, carried over from the design spec, are still Proposed.

### Next on the critical path
1. **B17-1's spec text** is drafted: `docs/b17-1.md`, version 0.1 Draft, with D81–D92. Its labelled suite in `suite/b17-1/` comes next. Then the checker, interpreter and verifier extend to it, and it freezes once the checker agrees with every tier 0 label (D44).
2. **WP8**, the agent reference manual, builds on WP6: every rule and code with an example that passes `b17c check`.
3. **WP16** grows the core library as B17-1 and the ports need it.

Off the critical path, **WP7**, the backend that emits safe Rust, is done for B17-0. It extends to B17-1 with the rest of the toolchain, emitting data types as Rust enums (D79).

### Phase 0 work outside the gate
- **The rest of WP2:** the manifest and lockfile schemas (interfaces 4 and 7, D26) and typed edit operations (interface 2).
- **The rest of the baselines:** Gemini's remaining tasks once its quota resets, around 2026-11-02, and Grok's once its balance is topped up.

## Phase 1

From D21's dependency table, as D62 and D65 amend it, two paths of the same length lead to the Phase 2 gate: WP1a, WP2, WP3, WP16, WP5, WP6, WP8, WP11, and WP1a, WP2, WP3, WP16, WP5, B17-1, WP10, WP11. WP4b and WP15 are each one step off them.

| WP | What | Depends on | Done when |
|---|---|---|---|
| WP3 | Tier 0 checker: types, names, ghost code, ownership, effects | WP1a, WP2 | It agrees with every tier 0 label in the suite. Done (PR #15). |
| WP4a | The spec language | WP3 | Done, since WP1a is frozen and B17-0 already has a spec language (D62). B17-1 adds no data-type invariants or refinement links, since every surveyed task states its invariants in its contracts, so it stays done (D79). |
| WP16 | The core spec library: `sorted`, ranges, sequence and multiset laws | WP1a, WP15 | Every entry has witness examples that the interpreter confirms (D28). In progress: met for its 33 laws and 3 ghost-fns. |
| WP5 | The verifier: `b17c` generates its own goals and sends them to Z3 (D17) | WP3, WP1a, WP16 | The worked example verifies, seed-shuffle checks pass (D23), and the proof cache hits on unchanged code. Done for B17-0. |
| WP6 | Agent protocol and diagnostics | WP3, WP1a, WP5 | Diagnostics match interface 3, and all five queries answer (interface 8). Done for B17-0 (D93, D94), except repairs, which wait for WP2's typed edits. |
| WP4b | The spec workbench: back-translation, vacuity checks, witnesses, mutant rejection, signing | WP1a, WP5, WP15 | They run on the worked example |
| WP7 | A backend that emits safe Rust (D18) | WP3, WP15 | Emitted code compiles and matches the interpreter on differential tests. Done for B17-0 (D95–D97). |
| WP8 | The agent reference manual | WP3, WP5, WP6 | Every rule and error code has an example, and every example passes `b17c check` |
| B17-1 | The second subset: data types, tuples, collections of any type, ghost sets and maps (D79); verification levels L0 and L1 (D80) | WP1a, WP3, WP5, WP15 | Its spec and suite freeze once the checker agrees with every tier 0 label (D44) |
| WP10 | Benchmark ports | WP1a, WP5; B17-1 for the AlgoVeri ports, since 50 of the 64 need its features (D79) | Ported Dafny, Verus and Lean tasks verify end to end |

**The head-to-head experiment** is called M3 in the activity log.
- **What it does:** agents write B17-0 and Dafny for the same frozen tasks, whose specs stay aligned across the two languages (D42). It can start on B17-0's tasks and add B17-1's when B17-1 freezes (D65).
- **What it measures:** the success metrics: verified pass rate, repair rounds and tokens per verified task.
- **What it needs:** WP5, WP6 and WP8, WP10's ports for the tasks it runs, and tasks hard enough to separate the two languages. The seed ports are enough to start; the AlgoVeri ports wait for B17-1.
- **How it's used:** its results steer the design (D14).

## Phase 2

**The training environment, WP11.** It's done when:
- rewards and anti-hacking rules are enforced;
- a held-out split is frozen;
- an in-context baseline is recorded.

Its curriculum covers every domain the language has reached by then (D65).

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

## How the language grows

The phases build the toolchain. The language grows alongside them in subsets (D65). A subset takes B17-0's path:
1. a decision on its scope;
2. spec text and a labelled suite;
3. the interpreter, checker and verifier extended to it;
4. a freeze once the checker agrees with every tier 0 label (D44).

| Subset | What it adds | When |
|---|---|---|
| **B17-0** | Checked integers, booleans, sequences, slices and owned vectors; contracts; the `alloc`, `panic` and `io` effects (D20) | Phase 0. Frozen on 2026-10-28, once WP3's checker agreed with the suite (D44). |
| **B17-1** | Data types with type parameters, tuples, collections of any type, quantifiers over any ghost type, and ghost sets and maps (D79); verification levels L0 to L3, and what a goal that isn't proved does below L2 (D80) | Phase 1. Its scope was accepted on 2026-10-28, and its spec text is next. |
| **Later subsets** | From §11 and D79: mutable borrows, floats, strings, runtime sets and maps, and generic functions; mutual recursion, once there's group hashing (D22); and vector capacity, once there are allocation bounds (D30). From D64: closures and higher-order functions, interfaces or traits, asynchronous I/O, a user-interface model, and tensors with automatic differentiation. Effects for files, network and time. | Benchmarks set the order (D14), within §11's prerequisites. Growth continues past Phase 4 until D64's scope is covered. |

- **The standard library** grows with the subsets. The design spec's library covers collections, numerics, text, parsers, cryptography and time. Each subset's scope includes the library entries it makes expressible.
- **Task sets beyond algorithms** (D64) are built as the subsets that can express them arrive.

## Open questions that shape the plan

- **Hard enough tasks.** Today's models differ in rounds and tokens on every set so far, but barely in what they verify. Claude and Codex verified all 28 vericoding tasks, though at most a quarter of 2025's models solved each. So M3's tasks will have to be found elsewhere or written (WP10). What makes a task hard for them, and how to show it before M3 runs, is open.
- **The cost of i64 rigor.** Ranges stated the obvious way left four suite proofs needing a hint, or a solver's luck. Stated per step (D60), all four are stable and about 80 times cheaper. How specs must be phrased for the solver is part of Bet 1's cost, and M3 will show whether agents pay it.
- **Counterexamples.** With quantified axioms, a failing goal comes back unknown rather than with a model. WP6 solves it again against only the axioms it mentions, and the interpreter replays the model (D93). That found one for each of the suite's 9 proof rejects, and 8 replayed. How often it works on harder programs is open.
- **Algorithms specs can't see.** A functional spec can't tell Aho-Corasick from naive search. Cost contracts were deferred (D29, D30).
- **Training resources.** Phase 2 needs open weights and compute that the project doesn't have yet.
- **Reaching every domain.** [How the language grows](#how-the-language-grows) lists what D64 needs. What follows B17-1, and in what order, is open. Deciding it needs task sets for applications, pipelines and machine learning, but every benchmark so far is an algorithm task.
