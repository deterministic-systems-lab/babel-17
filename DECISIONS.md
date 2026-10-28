# Babel-17 decision log

Every design decision, in order. A proposed entry may be revised until the owner decides it. After that the entry is frozen: to change an accepted or rejected decision, add a new entry that supersedes it, and edit the old entry only to update its status.

**Statuses:**
- **Proposed:** awaiting the owner.
- **Accepted** or **Rejected:** the owner has decided.
- **Open:** a question with no proposal yet.
- **Superseded by Dn:** replaced by a later entry.

`grep '^## D' DECISIONS.md` lists every decision with its status.

D1–D11 come from the design spec, *MFL: A Machine-First Language — Design Spec (Draft v0.1)*, which is kept outside this repo. Section names refer to the spec's headings. "MFL" is Babel-17's former name (D12).

## D1 · Working name MFL · Superseded by D12
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** The working name is MFL.
- **Touches:** Summary.

## D2 · A typed semantic graph is the source of truth · Proposed
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** A typed semantic graph is the source of truth; S-expressions are the wire format.
- **Touches:** Program representation.

## D3 · Lean 4 hosts the core calculus · Proposed (timing changed by D16)
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** Lean 4 hosts the core calculus and its soundness proof.
- **Touches:** Roadmap.

## D4 · People sign specs, never implementations · Proposed
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** People sign specs, never implementations; an approved spec is frozen for its implementer.
- **Touches:** Specification layer.

## D5 · Every module opens with a prose header · Proposed
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** Every module opens with a prose header: purpose, invariants, failure modes.
- **Touches:** Specification layer.

## D6 · Every proof passes the kernel · Proposed (refined by D24)
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** Every proof passes the kernel; anything else is reported as solver-trusted.
- **Touches:** Verification model.

## D7 · Solver budgets count resource units, not seconds · Proposed (refined by D23)
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** Verifier budgets count solver resource units, not seconds.
- **Touches:** Verification model.

## D8 · In-context learning in Phase 1, training in Phase 2 · Proposed
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** Phase 1 relies on in-context learning from the reference manual; training starts in Phase 2.
- **Touches:** Training environment.

## D9 · Imports resolve only to lockfile hashes · Proposed
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** Imports resolve only to hashes already in the lockfile.
- **Touches:** Interop, packages and the trusted base.

## D10 · One static binary or WASM build, no other compiler · Proposed (deferred by D19)
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** The toolchain installs as one static binary or a WASM build, with no other compiler.
- **Touches:** Standard library and tooling.

## D11 · Phase 1 emits Rust or C · Superseded by D18
- **Date:** 2026-10-26 (spec v0.1)
- **Question:** From a comment on the Roadmap section: "Should Phase 1 emit Rust first (to reuse Verus and the borrow checker) or C (the F\* route)?"
- **Touches:** Roadmap.

## D12 · The language is named Babel-17 · Accepted
- **Date:** 2026-10-26 · **Supersedes:** D1
- **Decision:** The language is Babel-17. Source files use the `.b17` extension and the CLI is `b17c`, so the spec's `mfl verify`, `mfl gym` and the rest become `b17c verify`, `b17c gym` and so on.
- **Why:** Owner's call.
- **Touches:** Summary; Standard library and tooling; every `mfl` tool name.

## D13 · Experiments run on CLI subscriptions · Accepted
- **Date:** 2026-10-26
- **Decision:** For now, experiments drive models through the `claude -p` and `codex exec` CLIs on the owner's subscriptions, not through API keys.
- **Why:** Owner's call. Subscription rate limits pace large runs, so run sizes are planned around rate-limit windows. Subscription models can't be fine-tuned, so the Phase 2 gate will also need an open-weights model.
- **Touches:** Training environment; WP10; WP11.

## D14 · Benchmarks steer the design; they don't gate the language · Accepted
- **Date:** 2026-10-26
- **Decision:** Babel-17 gets built. Comparisons against Dafny and Verus decide which features to invest in, judged by their effect on verified pass rate, repair iterations and tokens per verified function. Examples are structured diagnostics, canonical S-expressions, explicit effects and ownership. No experiment outcome is read as "stop the language".
- **Why:** Owner's call. This answers the first question in Risks and open questions ("Is a new language needed at all?") with yes. The Phase 2 gate still governs when Phase 3 starts.
- **Touches:** Risks and open questions; Success metrics.

## D15 · This file and ACTIVITY.md are the authoritative logs · Accepted
- **Date:** 2026-10-26
- **Decision:** `DECISIONS.md` is the complete, authoritative decision log. `ACTIVITY.md` is the activity log and also holds the spec's handoff notes. The spec's Decision log section mirrors entries accepted here.
- **Why:** The owner asked for both logs in the repo. Keeping one authoritative copy stops the spec and the repo from drifting apart, and git gives history and review.
- **Touches:** How to use this spec; Decision log.


## D16 · WP1 splits, and the Lean proof moves after the Phase 2 gate · Accepted
- **Date:** 2026-10-26
- **Decision:** WP1 splits in two:
  - **WP1a, core semantics (Phase 0):** written typing rules and operational semantics for B17-0 (D20), the core-term interface (interface 6, D27), and an accept/reject suite of programs labelled with their expected verdicts. Done when all three are frozen.
  - **WP1b, Lean mechanization and kernel (after the Phase 2 gate):** the semantics mechanized in Lean 4, type soundness proven, and the kernel checker built.

  WP3's type checker must pass the accept/reject suite, and the reference interpreter (WP15, D28) must pass conformance tests derived from the semantics. Phase 0's gate becomes three things: WP1a frozen, WP2's round-trip tests passing, and WP15 passing its conformance tests. D3 stands; only its timing changes.
- **Why:** This is a scheduling tradeoff. Experiments start much earlier. The price is that, until the kernel exists, verdicts, rewards and repairs rest on the solver (D24), and a later kernel may reject results the solver accepted. Comparable mechanized-soundness efforts took several people several years (RustBelt, CakeML).
- **Touches:** Roadmap (Phase 0 gate); WP1; WP2; WP3; D3.

## D17 · b17c generates its own proof goals and sends them to Z3 · Accepted
- **Date:** 2026-10-26
- **Decision:** `b17c` turns programs and contracts into solver queries itself and sends them to Z3, with cvc5 optional later. Babel-17 never translates to Dafny. Dafny serves two other roles:
  - **Baseline:** the comparison language for experiments.
  - **Development oracle:** every seed task also exists in Dafny. When Dafny proves a task and `b17c` doesn't, the gap is triaged as one of: a bug in our encoding, a missing lemma, a budget too small, or a real difference between the two versions of the task.
- **Why:** Dafny reports status and resource use per assertion. It doesn't report the goal in normal form or which goals depend on it, and its source positions map back to node IDs only indirectly. The diagnostic schema needs all of these. Owning goal generation also brings three gains:
  - **Simpler encoding:** ownership lets the solver see plain values instead of a modelled heap. Verus reports speedups over Dafny-style encodings this way (from memory; not yet verified).
  - **Stability:** one goal per query with minimal context targets the brittleness the Mariposa study measured.
  - **A path to D6:** generated goals can later be exported to Lean as theorems.

  The cost is roughly two to three times the work of translating to Dafny. Early versions will also be more brittle than Dafny on quantifier-heavy specs.
- **Touches:** Verification model; WP5; WP6; Roadmap (Phase 1, "SMT verification").

## D18 · Phase 1 emits safe Rust · Accepted (answers D11)
- **Date:** 2026-10-26
- **Decision:** The Phase 1 backend (WP7) emits safe Rust:
  - every emitted crate carries `#![forbid(unsafe_code)]`;
  - arithmetic is explicitly checked;
  - differential tests against the reference interpreter (WP15) catch lowering errors on sampled inputs. Establishing that lowering preserves meaning is the job of translation validation (WP12).

  Bounds checks stay in Phase 1 output. Removing them using proven facts is the native backend's job (WP12).
- **Why:** `rustc` independently re-checks the ownership and type safety of every emitted program. It doesn't check Babel-17's contracts, or whether lowering preserved meaning. What it does catch is a bug in our ownership checker or lowering that would otherwise produce unsafe code, while there is still no kernel. Babel-17's `&[T]` and `Vec<T>` also map directly onto Rust, and `wasm32` is a standard target.

  C was the alternative, and `clang` is already installed. It would rest all memory safety on our own checker, and the emitter would have to avoid C's undefined behaviour, such as signed overflow and strict aliasing.

  Verus checks only its own subset, and only with specs attached, so plain emitted Rust isn't enough for it. A separate backend that also emits Verus specs could be added later as a cross-check. The cost of Rust is a rustup install of about 1 GB, needed only when WP7 starts.
- **Touches:** D11; WP7; WP9; WP12; Roadmap (Phase 1 gate).

## D19 · The toolchain is a Python prototype until Phase 3 · Accepted (defers D10)
- **Date:** 2026-10-26
- **Decision:** `b17c` is written in Python and run with uv through the Phase 2 gate. D10 is deferred until a Rust rewrite opens Phase 3. Until then, `b17c` needs Python and uv, `b17c build` needs `rustc` (D18), and the trusted base report names those toolchains. The rewrite is accepted when it reproduces the prototype's canonical bytes, hashes, verdicts and diagnostic codes on the benchmark corpus.
- **Why:** Z3's Python bindings are its most mature, and the gym is Python anyway. Until Phase 3 there is one user on one machine. D10 exists to protect outside users, who don't exist yet, and no Python prototype can meet it.
- **Touches:** D10; WP9; Standard library and tooling (Distribution).

## D20 · The first subset is B17-0 · Accepted
- **Date:** 2026-10-26
- **Decision:** B17-0 contains:
  - **Values:** checked integers, booleans, sequences, shared slices, owned vectors, mutable locals.
  - **Control:** `if`, and `while` with `invariant` and `decreases`.
  - **Contracts:** `requires`, `ensures` and ghost spec functions.
  - **Effects:** a flat set of `alloc`, `panic` and `io`.

  Effects say what a function may do, not how much. Allocation amounts are bounds under D30. Type parameters are instantiated at integers only. The rest of the Type system waits for evidence.
- **Why:** This is enough to express the worked example (D29) and the seed tasks, yet small enough to specify, interpret and verify in weeks. Dependent types, linear resources, information-flow labels, cost proofs and concurrency are research-grade, and they don't change what the first experiments measure.
- **Touches:** Type system; WP3; Worked example.

## D21 · Work package dependencies are rewired · Accepted (WP1a edges amended by D44, WP4a edges by D62, WP10 and WP11 edges by D65)
- **Date:** 2026-10-26
- **Decision:** WP4 splits:
  - **WP4a, the spec language:** depends on WP3.
  - **WP4b, the spec workbench:** depends on WP4a, WP5 and WP15.

  The full pre-gate dependency table, including the WPs added in D16 and D28:

  | WP | Depends on |
  |---|---|
  | WP1a | — |
  | WP2 | WP1a |
  | WP3 | WP1a, WP2 |
  | WP4a | WP3 |
  | WP4b | WP4a, WP5, WP15 |
  | WP5 | WP3, WP4a, WP16 |
  | WP6 | WP3, WP4a, WP5 |
  | WP7 | WP3, WP15 |
  | WP8 | WP3, WP5, WP6 |
  | WP10 | WP4a, WP5 |
  | WP11 | WP4b, WP5, WP6, WP7, WP8, WP10, WP17 |
  | WP13 | WP2, WP5 |
  | WP15 | WP1a, WP2 |
  | WP16 | WP4a, WP15 |
  | WP17 | — |

  WP8's examples must pass `b17c check`, and they also run through WP7 once it exists. The critical path is computed from this table rather than written by hand. To the Phase 2 gate it runs WP1a, WP2, WP3, WP4a, WP16, WP5, WP6, WP8, WP11. WP4b, WP10 and WP15 are each one step off it.
- **Why:**
  - **WP4 and WP5:** vacuity checks, witnesses and mutant rejection all run on the verifier, so as written WP4 and WP5 depend on each other.
  - **WP11:**
    - the differential and performance rewards run emitted code (WP7);
    - the in-context baseline needs the manual (WP8, D8);
    - tasks enter the curriculum only after vacuity checks (WP4b).
  - **WP8:** the manual documents error codes from WP5 and WP6.
  - **WP13:** classifying a spec diff takes implication proofs (WP5).
- **Touches:** Work packages; Specification layer.

## D22 · Definitions get separate spec and implementation hashes · Accepted (refined by D45)
- **Date:** 2026-10-26
- **Decision:**
  - **Hashes:** each definition has a spec hash, covering its signature, contracts, effects and cost, and an implementation hash, covering its body plus its own spec hash.
  - **References:** bodies refer to callees by spec hash.
  - **What's left out:** the definition's own name is excluded from the hash, and local binders are de Bruijn-indexed.
  - **Recursion:** mutually recursive definitions hash as one group, and each member is addressed as (group hash, index).
  - **Tagging:** every hash carries a prefix for its kind (spec, implementation or group) and a format version.
  - **Node IDs:** a node ID is a stable definition ID assigned at creation plus a child-index path. Labels like `loop0` and abbreviated hashes are for display only.
  - **Proof cache:** the key covers the implementation hash, the spec hashes of its dependencies, the canonical query (interface 11, D27), and the full verification configuration. That configuration is the `b17c` and prelude versions, the solver hash and options, and the seeds and budget.
- **Why:** As written, the identity scheme breaks in four ways:
  - one body edit rehashes every transitive caller;
  - recursion makes hashes circular;
  - renaming a definition changes its hash, contradicting "renames never break references";
  - node IDs built from hashes can't survive edits.

  A cache key without the verification configuration would reuse verdicts after a solver or prelude change.
- **Touches:** Program representation; Interfaces 1 and 3; Verification model (incremental and cached); D2.

## D23 · What a verdict means · Accepted (refines D7)
- **Date:** 2026-10-26
- **Decision:** A goal passes when it's proven under the canonical seed and under N shuffled seeds. N and the resource budget live in the manifest. Solving is single-threaded, and the solver's version and every option are pinned. Each supported platform gets its own pinned solver build, whose hash goes in the trusted base report. A golden-verdict suite runs on every supported platform, and a platform is supported only while its verdicts match.
- **Why:** Z3's resource count is reproducible only with the same binary and options, binaries differ by platform, and shuffling seeds changes solver behaviour. "Same verdict on any machine" therefore needs a defined verdict and checked agreement between platforms.
- **Touches:** Design principles (Determinism); Verification model; D7.

## D24 · Solver-trusted results get their own level until the kernel exists · Accepted (refines D6)
- **Date:** 2026-10-26
- **Decision:** Until the kernel exists:
  - **Levels:** a module whose goals are all discharged, some only by the solver, is reported as **L3-S**, not L3. L3 requires every goal to be kernel-checked.
  - **The report:** the trusted base report lists each solver-trusted goal by node ID.
  - **The gym:** solver-discharged goals earn the 0.80 reward tier, recorded as provisional. The anti-hacking rule "the kernel, not the solver, signs the final verdict" is suspended.

  Release builds always reject `admit` and `assume`, whatever the manifest says.
- **Why:** Reviewers report that known SMT-to-kernel proof reconstruction, lean-smt for one, doesn't yet cover sequences or multisets, and the worked example needs both (not yet verified). L3 means "full functional correctness proven". A separate label keeps that meaning honest while the kernel is missing.
- **Touches:** Verification model (levels); Training environment (reward table, anti-hacking rules); Interfaces 4 and 5; D6.

## D25 · The trusted base report lists goals instead of counting them · Accepted
- **Date:** 2026-10-26
- **Decision:** WP5 owns the report, and WP7 adds the backend fields. The report:
  - lists axioms and solver-trusted, admitted and brittle goals by node ID;
  - records the input and lockfile hashes;
  - records the `b17c`, prelude and solver versions, the solver hash (D23), the backend toolchain (D18) and the target triple;
  - gives a verification level per module.
- **Why:** Counts can't tell apart two builds with different admitted goals. The fields come from WP5 and WP4, not WP7. And the example's `x86_64-sysv` doesn't describe an arm64 Mac.
- **Touches:** Interfaces 5; Interop, packages and the trusted base; WP5; WP7.

## D26 · The manifest and lockfile move to Phase 0 · Accepted
- **Date:** 2026-10-26
- **Decision:** WP2 owns the manifest and lockfile schemas. WP13 keeps the registry and spec-diff versioning.
- **Why:** Phase 1 already needs verification levels, `allow_admit`, budgets (D23) and dependency pins, but WP13 is a Phase 3 package.
- **Touches:** Interfaces 4; WP2; WP13; D9.

## D27 · Interfaces needed before the Phase 2 gate are added, and all interfaces are versioned · Accepted
- **Date:** 2026-10-26
- **Decision:** Six interfaces are added:

  | Interface | Contents | Owner |
  |---|---|---|
  | 6 | Core terms | WP1a |
  | 7 | Lockfile and capability grants | WP2 |
  | 8 | Query protocol, with result schemas for the five queries | WP6 |
  | 9 | Spec signatures and spec challenges | WP4b |
  | 10 | Interpreter traces | WP15 |
  | 11 | Canonical solver queries: the SMT-LIB form of each goal | WP5 |

  Every interface carries a version and a status of Draft or Frozen. Interfaces for the fact-preserving IR and for kernel certificates are added when WP12 and WP1b start.
- **Why:** Work packages may only exchange the artifacts listed in Interfaces, but these six pass between pre-gate packages without being defined. "Start once frozen" can't be checked without a status. The later interfaces would only be guesses today.
- **Touches:** Interfaces; How to use this spec; Work packages.

## D28 · Unowned work gets owners · Accepted
- **Date:** 2026-10-26
- **Decision:**
  - **WP15, the reference interpreter (Phase 0):** depends on WP1a and WP2. Done when it passes WP1a's conformance tests. It also serves `simulate`, witness examples and WP7's differential tests.
  - **WP16, the core spec library:** depends on WP4a and WP15. It holds `sorted`, `multiset`, `take`, `last`, and integer order with its laws. Done when every entry has witness examples that the reference interpreter confirms. Vacuity checks on these entries run later, in WP4b.
  - **WP17, the baseline harness:** no dependencies. It holds the frozen task set, CLI adapters for `claude -p` and `codex exec`, prompts, recorded model and CLI versions, metrics, a retry and rate-limit policy, and result files that record every agent output. Done when the seed tasks run on stock Dafny through both CLIs and two checks pass:
    - re-verifying the recorded outputs reproduces their verdicts exactly;
    - a fresh rerun lands within a stated tolerance of the original pass rates, since hosted models don't produce the same output twice.

    It becomes the core of WP11.
  - **Signing** moves into WP4b.
  - **`b17c view` and `b17c prof`** are deferred.
- **Why:** The done-when tests of WP5, WP6, WP7 and WP11 depend on this work, and no package owns it.
- **Touches:** Work packages.

## D29 · The worked example is corrected and specialized to integers · Accepted (capacity clause superseded by D35)
- **Date:** 2026-10-26
- **Decision:** For B17-0, `merge_sorted` takes `&[int]` and returns `Vec<int>`. The generic version returns when generics do, and it requires `T: Copy` and an `Ord` with stated laws (total and transitive) and a pure, terminating comparison. Both versions also make these changes:
  - require that `len(a) + len(b)` fits in the index type;
  - state that allocation failure aborts, as in Rust, and list it under the header's failures;
  - add `capacity(out) >= len(a) + len(b)` as a loop invariant;
  - state in the core semantics that `and` and `or` short-circuit;
  - narrow "nothing aliases" to "`out` aliases neither input";
  - drop the vectorization claim.
- **Why:** As written, the example has six problems:
  - **Ownership:** it moves a `T` out of a shared borrow, which the spec's own ownership rules reject.
  - **Order laws:** the else branch and sortedness need laws that `Ord` doesn't state.
  - **Failures:** the header's "failures: None" ignores overflow and allocation failure.
  - **Reallocation:** "push never reallocates" is unproven without the capacity invariant. Capacity is at least the requested amount, as with Rust's `Vec::with_capacity`, not exactly it.
  - **Index safety:** it relies on short-circuit evaluation the semantics never states.
  - **Vectorization:** the merge's data-dependent branch blocks it.
- **Touches:** Worked example; Type system; WP4 and WP5 done-when tests.

## D30 · Asymptotic cost proofs and information-flow labels are deferred · Accepted
- **Date:** 2026-10-26
- **Decision:** Before the Phase 2 gate, `b17c` doesn't verify asymptotic bounds such as `O(n log n)`.
  - **Allowed:** specs may state exact operation or allocation counts, such as "at most `len(a) + len(b)` comparisons", and agents prove them with ghost counters.
  - **Not proven:** asymptotic `cost` clauses are parsed and measured only.
  - **Information-flow labels:** deferred.
- **Why:** Proving asymptotic bounds for imperative code with arbitrary comparisons is still research-grade; RAML-style analysis targets functional code. Noninterference needs relational verification or a proven-sound type system.
- **Touches:** Type system; Specification layer (resource contracts); Worked example (`cost`).

## D31 · The Phase 2 gate also compares against a model trained on Dafny · Accepted
- **Date:** 2026-10-26
- **Decision:** For the Phase 2 gate, the same base model is also trained on Dafny with equal compute. The gym-trained Babel-17 model must beat that model as well as off-the-shelf models.
- **Why:** As drawn, the gate compares a trained model with untrained ones, so a win could come from training alone rather than from the language.
- **Touches:** Roadmap (Phase 2 gate); WP11; Success metrics.

## D32 · Success-metric baselines are re-measured on our own harness · Accepted
- **Date:** 2026-10-26
- **Decision:** The Success metrics baselines are re-measured on our own harness (WP17), on the same tasks with current models (D13), rather than quoted from papers.
- **Why:** Reviewers report two problems with the quoted figures, neither verified yet. The vericoding figures (82/44/27%) count a task as solved if any model solved it; the best single model scores about 67.5/30.9/17.9%. And 2026 agentic Dafny results exceed 90% on DafnyBench. Measuring on our own harness settles the question either way.
- **Touches:** Success metrics.

## D33 · B17-0's canonical form is also its core language · Accepted
- **Date:** 2026-10-27
- **Decision:** In B17-0, the canonical S-expression form is the core language, so there is no separate surface syntax to elaborate. WP3 is a checker, not an elaborator, until a richer surface exists.
- **Why:** One representation means one parser, one printer and one thing to hash (D22). An elaborator earns its place only once there is something to elaborate.
- **Touches:** Program representation; Interfaces 1 and 6; WP2; WP3; `docs/b17-0.md` §2.

## D34 · Runtime integers are i64, with every range proven · Accepted
- **Date:** 2026-10-27
- **Decision:** Runtime integers are `i64`, and every arithmetic result's range is a proof goal. Ghost integers are unbounded `int`. `i64 <: int` holds in ghost context only, and runtime code has no implicit conversions.
- **Why:** This matches safe Rust (D18) and the "checked integers" of D20, and it keeps contracts mathematical.
- **Touches:** Type system (numeric domains); `docs/b17-0.md` §3, §4, §7.

## D35 · No vector capacity in B17-0 · Accepted (supersedes D29's capacity clause only)
- **Date:** 2026-10-27
- **Decision:** B17-0 has no vector capacity. D29's `capacity(out) >= len(a) + len(b)` invariant waits for allocation bounds (D30), and `vec-with-capacity` is dropped from the subset. D29's other clauses stand.
- **Why:** Capacity only matters for the "push never reallocates" performance claim, which needs allocation bounds that D30 defers.
- **Touches:** D29; D30; Worked example; `docs/b17-0.md` §1, §11.

## D36 · Ownership without lifetimes · Accepted (refined by D69 and D72)
- **Date:** 2026-10-27
- **Decision:**
  - Vectors are owned and move.
  - Slices are shared borrows scoped to a single call; they can't be stored or returned.
  - There is no `&mut`.
  - In-place algorithms take ownership of a vector and return it.
- **Why:** This gives aliasing freedom with no lifetimes to infer, and it lets the verifier treat every collection as a plain sequence value, which is D17's simpler-encoding gain. `rustc` re-checks all of it once Phase 1 emits Rust (D18).
- **Touches:** Type system (ownership); `docs/b17-0.md` §5.

## D37 · Division truncates toward zero · Accepted
- **Date:** 2026-10-27
- **Decision:** `/` and `%` truncate toward zero in both runtime and ghost context, as in Rust, rather than the Euclidean division Dafny uses. Both carry Rust's two panic cases as proof goals: a zero divisor, and −2^63 divided by −1.
- **Why:** The meaning stays the same from contract to emitted code (D18).
- **Touches:** `docs/b17-0.md` §7, §8.

## D38 · seq-build bounds its index · Accepted
- **Date:** 2026-10-27
- **Decision:** `(seq-build n (fn (i) e))` checks e with `0 <= i < n` assumed.
- **Why:** This is the first language change driven by a measured agent failure. In WP17, Codex's first attempt at `reverse` failed in 6 of 6 samples on exactly this point in Dafny.
- **Touches:** `docs/b17-0.md` §7.

## D39 · A def implements a named spec and never restates it · Accepted
- **Date:** 2026-10-27
- **Decision:** A `def` names the `spec` it implements and never repeats its contracts. Tasks give agents the frozen spec, so agents can't weaken contracts by construction.
- **Why:** This replaces the generated `_Check` wrapper the Dafny harness needs, and it matches D4: people sign specs, not implementations.
- **Touches:** Specification layer; `docs/b17-0.md` §1, §10.

## D40 · Every path returns or panics · Accepted (refined by D77)
- **Date:** 2026-10-27
- **Decision:** Every path through a `def` ends in `return` or `panic`, and early returns are allowed. `(return e1 ... en)`, one expression per declared result, is the only way to exit with results.
- **Why:** "One way to say it", while still allowing the early returns agents write naturally in search loops.
- **Touches:** `docs/b17-0.md` §7, §9.

## D41 · No shadowing · Accepted (refined by D66)
- **Date:** 2026-10-27
- **Decision:**
  - Item names are unique within a module, except that a `spec` and its `def` share one name.
  - Local names are unique within their item and never reuse an item name.
- **Why:** This gives every name in a diagnostic exactly one meaning.
- **Touches:** `docs/b17-0.md` §2.

## D42 · Ported tasks state integer ranges, in both languages · Accepted
- **Date:** 2026-10-27
- **Decision:** Tasks ported to B17-0 state explicit integer ranges, and their Dafny baseline versions take the same preconditions.
- **Why:** That keeps the two task sets aligned, so the comparison measures the language rather than different specs. The extra goals are what Bet 1 claims costs agents little.
- **Touches:** WP10; WP17; Success metrics; `docs/b17-0.md` §10.

## D43 · A spec may declare several results · Accepted (refined by D74)
- **Date:** 2026-10-27
- **Decision:**
  - A spec may declare several results, returned together by `(return e1 ... en)` and bound by `(let ((x T) ...) (call ...))`.
  - A result list isn't a value, so B17-0 still has no tuples.
- **Why:** Owned-in, owned-out algorithms that also compute something need it. `partition`, which returns its vector and a boundary, is the seed example.
- **Touches:** `docs/b17-0.md` §2, §7, §8.

## D44 · WP1a freezes when WP3's checker agrees with the suite · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - `docs/b17-0.md` and `suite/` stay at version 0.1, Draft. They freeze, completing WP1a, once WP3's checker agrees with every tier 0 label in the suite: each accept program passes tier 0, and each reject program with a tier 0 code fails with exactly that code.
  - WP2, WP3 and WP15 start from the draft. If building them shows the draft is wrong, a new decision fixes the draft before the freeze.
  - `E-PROOF-*` labels and the proof goals of accept programs stay checked by review until WP5's verifier exists. They don't hold up the freeze.
- **Why:** So far the labels have been checked only by review. A checker that runs the suite is their first mechanical test, and freezing before it would turn every mislabel it finds into a superseding decision.
- **Touches:** WP1a; WP2; WP3; WP15; D16; D21 (WP2, WP3 and WP15 depend on WP1a's draft, not its freeze); `docs/b17-0.md`; `suite/README.md`.

## D45 · What a B17-0 hash covers · Accepted (refines D22; refined by D78)
- **Date:** 2026-10-27
- **Decision:** D22 applied to B17-0's four item kinds.
  - **Spec and def:** the spec hash covers the `spec` item. The implementation hash covers the spec hash and the `def` item.
  - **Lemma:** its statement is a spec and its proof an implementation. The spec hash covers the lemma without its `decreases` and `body`. The implementation hash covers the spec hash and `(lemma _ (decreases e)? (body stmt*))`.
  - **Ghost-fn:** a ghost-fn's body is its meaning, so it has only a spec hash, covering the whole item. This refines D22, which gives every definition two hashes. Editing a ghost-fn rehashes every spec that mentions it, so their definitions and callers are verified again.
  - **References:** every use of another item's name (a ghost-fn call, or a `call` of a spec or lemma) is replaced by that item's spec hash in D46's text form. An item's own name is replaced by `_` wherever it appears, so a recursive ghost-fn needs no hash of itself. B17-0 rejects mutual recursion (`E-TERM-002`), so D22's recursion groups don't arise yet.
  - **Binders:** parameters, results, locals and `forall`, `exists` and `fn` variables are numbered from 0, in the order they occur in a preorder, left-to-right walk of the definition (the spec then the def, or the whole lemma).
    - Each binder, and every use that resolves to it under §2's scoping, is replaced by `$k`. That includes plain names, `borrow`, and the targets of `set`, `set-idx`, `push` and `ghost-set`.
    - A lemma's proof keeps the whole lemma's numbers, so its first local comes after the statement's binders.
    - These are de Bruijn levels rather than indices. With no shadowing (D41) they identify the same terms, and they need no scope depth.
  - **Hashed bytes:** the item's canonical bytes (§2) after these replacements, with no line ending. `_`, `$k` and hashes can't be names, so no replacement collides with a name.
  - **Example:** the suite's `abs` hashes these two lines:
    - `(spec _ (params ($0 i64)) (returns ($1 i64)) (requires (> $0 -9223372036854775808)) (ensures (>= $1 0) (or (== $1 $0) (== $1 (neg $0)))) (effects))`
    - `(def _ (body (if (< $0 0) (return (neg $0)) (return $0))))`

    `fib`'s ghost-fn hashes `(ghost-fn _ (($0 int)) int (requires (>= $0 0)) (decreases $0) (body (if (< $0 2) $0 (+ (_ (- $0 1)) (_ (- $0 2))))))`.
  - **One spec per spec hash:** once every other tier 0 check passes, a last check computes provisional spec hashes and rejects two specs in one module with the same one (`E-TYPE-002`). Otherwise two defs that implement identical specs would be indistinguishable to their callers' implementation hashes. Lemmas and ghost-fns may coincide: a ghost-fn's hash already covers its body, and which proof of a lemma is used doesn't change any meaning. A program's hashes are defined only once it passes tier 0, including this check.
  - **Left out:** the module name and the header. B17-0 has no module hashes, since nothing imports a module yet (D9, D26).
  - **Core library:** `sorted` and `in_i64` (§9) are ordinary ghost-fns in a prelude module that `b17c` ships, and references to them hash like any other. `sorted` is §9's text. `in_i64` is `(ghost-fn in_i64 ((x int)) bool (body (and (<= -9223372036854775808 x) (< x 9223372036854775808))))`.
  - **`docs/b17-0.md`:**
    - §2's "Canonical bytes put each item on one line, and they are what D22 hashes" ends instead "and D45 hashes them after replacing names";
    - §9's `E-TYPE-002` row gains "or a spec identical to another up to names";
    - the suite gains a reject program for it.
- **Why:**
  - **Exact bytes:** D22 fixes the properties a hash must have, but not B17-0's bytes, and WP2 is done only when "content hashes match across machines".
  - **Lemmas:** splitting them like specs means a proof edit doesn't re-verify the definitions that use the lemma.
  - **Core library:** hashing it like user code avoids a format change when WP16 grows it.
  - **The duplicate rule:** references by spec hash are what keep a body edit from rehashing every caller (D22). The price is that a spec hash must name one def per module.
- **Touches:** D22; interface 1; WP2; WP3; WP16; `docs/b17-0.md` §2, §9; `suite/`.

## D46 · B17-0 hash format · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - **Function:** SHA-256, as the design spec's interface 1 already says.
  - **Text form:** `spec0:` or `impl0:` (kind, format version, colon) followed by 64 lowercase hex digits. Every hash written anywhere uses this form, including D45's replaced references. B17-0 is format version 0.
  - **Preimages:** `‖` is concatenation, the prefixes and hash text are ASCII, and D45's hashed bytes are UTF-8.
    - spec hash = SHA-256(`spec0:` ‖ hashed bytes of the spec part)
    - implementation hash = SHA-256(`impl0:` ‖ spec hash text ‖ one space ‖ hashed bytes of the implementation part)
  - **Check:** a golden file lists the hashes of every item in `suite/accept/`, and a test recomputes it, so any machine that reproduces the file matches. The test also checks that:
    - renaming a local or an item leaves every hash unchanged;
    - editing a def's body or a lemma's proof changes only that definition's implementation hash;
    - editing a ghost-fn changes the spec hash of every spec that mentions it.
- **Why:** The prefix is the kind and version tag D22 asks for. Putting it in the preimage also keeps a spec hash from ever equalling an implementation hash. The checks turn D22's failure cases into tests.
- **Touches:** D22; interface 1; WP2.

## D47 · Canonical bytes: the module line holds the header, and no newline ends them · Accepted
- **Date:** 2026-10-27
- **Decision:** §2 says canonical bytes put each item on one line, but not where the module line, the header and the closing paren go, or whether a newline ends the bytes. Canonical bytes are:
  - line 1: `(module NAME (header (purpose STR) (invariants STR) (failures STR))`;
  - then each item on its own line, in source order, with no indentation;
  - the module's closing paren ends the last line, and no newline follows it.

  A module with no items is a single line.
- **Why:** The header isn't an item, and keeping it on the module's line makes the first line identify the module and its signed prose. "No trailing whitespace" read strictly excludes a final newline. D45 hashes items without the module's name, header or line endings, so this layout changes no hash; it fixes the bytes `b17c` prints and the round-trip tests compare.
- **Touches:** WP2; D45; `docs/b17-0.md` §2.

## D48 · Only four whitespace characters, and no comments · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - Tokens are separated by space, tab, line feed and carriage return. Any other character, including a byte-order mark or a non-ASCII space, is an error outside strings.
  - B17-0 has no comments. `;` in §2's grammar block is notation, and `;` outside a string is E-PARSE-001.
  - Input is UTF-8. Diagnostics give a 1-based line and a 1-based column counted in code points, where a tab counts as one column.
- **Why:** §2 doesn't define whitespace or comments. Comments would be dropped by canonicalization, so they'd be lost on every round trip, and agents get nothing from them that the header doesn't give.
- **Touches:** WP2; `docs/b17-0.md` §2.

## D49 · Adjacent list elements need whitespace between them · Accepted
- **Date:** 2026-10-27
- **Decision:** Two adjacent elements of a list must be separated by whitespace, so `(return(+ x 1))`, `(a)(b)` and `(purpose"p")` are E-PARSE-001. Whitespace after `(` and before `)` stays optional.
- **Why:** §2's canonical form always has a space there, and the stricter reading accepts only layouts that differ from canonical bytes in the amount of whitespace, never in whether it's there.
- **Touches:** WP2; `docs/b17-0.md` §2.

## D50 · Strings hold no control characters · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - A string may not contain U+0000–U+001F or U+007F, so a raw newline or tab inside a string is E-PARSE-001.
  - `\"` and `\\` are the only escapes, as §2 says, and any other backslash sequence is E-PARSE-001.
  - Strings aren't Unicode-normalized: their code points are kept as written.
- **Why:** Canonical bytes put each item on one line (§2), which a raw newline inside a string would break, and with only two escapes there's no other way to write one.
- **Touches:** WP2; `docs/b17-0.md` §2.

## D51 · A grammar word used as a name is a parse error · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - Every word in §2's grammar, from `module` to `occurrences`, plus the atoms `bool`, `i64`, `int`, `alloc`, `panic`, `io`, `true`, `false`, `and` and `or`, is E-PARSE-001 wherever the grammar requires a NAME.
  - The core library's names, `sorted` and `in_i64`, are reserved too (§9), but they lex as names because they're called as ghost-fns. Declaring one is E-TYPE-002, checked by WP3.
  - On acceptance, §9's `E-TYPE-002` row reads "reserved" as the core library's names only.
- **Why:** §2 says these words are reserved, while §9's table lists "reserved" under E-TYPE-002. A parser can't tell `(len e)` from a ghost-fn call `(NAME e*)` unless `len` is reserved, so grammar words have to be rejected while parsing. Core library names need name resolution, which is WP3's job.
- **Touches:** WP2; WP3; `docs/b17-0.md` §2, §9's tier 0 table.

## D52 · Effects are listed once each, in grammar order · Accepted
- **Date:** 2026-10-27
- **Decision:** In `(effects EFF*)`, effects appear at most once each, in the order `alloc`, `panic`, `io`. `(effects io alloc)` and `(effects alloc alloc)` are E-PARSE-001.
- **Why:** An effect list is a set. §2's "children in grammar order" read strictly gives each set exactly one spelling, so its spec hash (D45) doesn't depend on how it was written.
- **Touches:** WP2; D45; `docs/b17-0.md` §2.

## D53 · Integer literals: only canonical ones parse, at any size · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - Non-canonical integers are E-PARSE-001: a leading zero (`007`), a `+` sign (`+1`), `-0`, and `(neg INT)` for any literal INT, including `(neg -5)`. §2 calls these not canonical but doesn't say whether they parse; they don't.
  - A literal's size isn't checked when parsing. A ghost `int` literal may exceed i64, and whether a literal fits its type is WP3's job.
- **Why:** If non-canonical input parsed, one program would have several spellings, and canonical bytes would have to rewrite literals. Rejecting it means canonicalization only ever changes whitespace. Ghost integers are unbounded (D34), so rejecting large literals while parsing would wrongly reject valid ghost code. D45's `in_i64` already needs one: it writes 2^63 as `9223372036854775808`.
- **Touches:** WP2; WP3; D34; D45; `docs/b17-0.md` §2.

## D54 · An optional clause is never empty · Accepted
- **Date:** 2026-10-27
- **Decision:** `(requires)` and `(ensures)` with no expressions are E-PARSE-001 in a `spec` or `lemma`. When there's nothing to state, the clause is omitted. The required clauses `(params)`, `(returns)` and `(effects)`, and a lemma's or def's `(body)`, may still be empty. A ghost-fn's `(body e)` holds exactly one expression.
- **Why:** As written, `(requires e*)?` allows both an empty clause and a missing one, so one spec would have two canonical forms and two spec hashes (D45). The suite uses neither empty form.
- **Touches:** WP2; D45; `docs/b17-0.md` §2.

## D55 · Terms nest at most 128 deep · Accepted
- **Date:** 2026-10-27
- **Decision:** A module whose lists nest more than 128 deep, counting the module itself, is E-PARSE-001. Integer literals have no digit limit (D53).
- **Why:** §2 sets no limit, so the parser's real limit was Python's recursion depth, which varies by platform and by caller. A program could then parse, hash or print on one machine and fail on another, which D46's "hashes match across machines" rules out. A fixed limit makes every machine accept the same programs. 128 leaves room for the recursive printer, checker, hasher and tree comparison; at 253 levels, comparing two trees already overflowed. The deepest suite program nests 13 deep. Found by Codex's review of the parser.
- **Touches:** WP2; D46; `docs/b17-0.md` §2.

## D56 · Interface 10: interpreter traces and outcomes · Accepted
- **Date:** 2026-10-27
- **Decision:** Interface 10, version 0.1, Draft. D27 names it without giving its contents; these are its contents.
  - **Trace:** the values `print` produced, in execution order across all calls. B17-0 has no other observable effect, so nothing else is traced. Every outcome carries the trace up to where the run stopped.
  - **Outcomes:** §8's three, plus two outside §8:
    - `ok(results)`, one value per declared result (D43);
    - `panic(message)`;
    - `err(reason, node, detail)`. The reason is the §9 family whose goal rules the error out: `OVERFLOW` for `+`, `-`, `*` and `neg`; `DIV` for a zero divisor, `MIN / -1` or `MIN % -1`; and `BOUNDS` for `idx`, `set-idx` or a negative `seq-build` length;
    - `contract(kind, clause, node, detail)`, only when checking (D57);
    - `limit(steps | depth, node)` (D59).

    Every outcome also lists the clauses checking couldn't evaluate (D58).
  - **Nodes:** an item's kind and name, the child-index path from the item's form, and the source line and column, written `def succ/2.1.1@13:15`. The path is D22's. The item stands in for D22's stable definition ID until one exists.
  - **Order:** expressions evaluate left to right (§7), so `err` reports the first operation that fails. `set-idx` evaluates its index and then its value, then checks the index. `return` evaluates every result before checking any `ensures`.
  - **Text form:** a `print V` line per trace entry, then an `unchecked KIND CLAUSE at NODE` line per unevaluated clause, then one outcome line:
    - `ok V...`;
    - `panic "S"`;
    - `err REASON at NODE: detail`;
    - `contract KIND CLAUSE at NODE: detail`;
    - `limit steps|depth at NODE`.

    Values are B17-0 terms: decimal integers, `true` and `false`, and `(seq-lit ...)`.
  - **Refusals:** some runs can't go on, and those raise an error instead of returning an outcome:
    - the def doesn't exist;
    - an argument isn't a value of its parameter's type;
    - a call reaches a spec with no def (calls are modular, so such a program can pass tier 0);
    - a name is undefined, so the program doesn't pass tier 0.
  - **CLI:** `b17c/interp.py` takes each argument as a closed B17-0 expression evaluated in ghost context, so `(seq-lit 1 2 3)` passes a sequence. It prints the text form and exits 0 on `ok`, 1 on any other outcome, and 2 when the run can't start or is refused.
- **Why:** WP7's differential tests compare the interpreter with the Rust Phase 1 emits (D18). A Rust binary shows its prints and how it ended, and nothing else, so that is what a trace holds. `err`'s reasons are §9's families, so a concrete failure names the goal the verifier should have failed to discharge. Child-index paths survive reformatting, which line numbers don't.
- **Touches:** D22; D27 (interface 10); WP7; WP15; `docs/b17-0.md` §8.

## D57 · What checking evaluates, and what a contract outcome reports · Accepted
- **Date:** 2026-10-27
- **Decision:** With checking off, the interpreter is §8: ghost code is erased and lemma calls do nothing. With checking on, it also evaluates the following in ghost context, where integers are unbounded and division truncates (D34, D37):
  - **Each call of a def or ghost-fn:**
    - its `requires` in order (`PRE`);
    - then, at a recursive call, 0 ≤ callee measure < caller measure (`TERM`). §7 states this goal under the callee's `requires`, so the measure is evaluated only once they hold. Each half is checked whenever its own values are known, so 0 ≤ callee measure is checked even when the caller's measure is unknown.

    The call's frame is entered before its `requires` run. A recursive call inside a ghost-fn's own `requires` is therefore a recursive call too. A call with the same arguments as a call still in progress can't descend, and is `TERM` at once rather than an endless recursion.
  - **Each `return`:** every result first, then the `ensures` in order, with the parameters at their entry values and the results bound (`POST`).
  - **Each loop:**
    - the invariants on entry (`INV-ENTRY`);
    - the measure ≥ 0 at the start of each iteration whose condition holds (`TERM`);
    - after each normal pass, the invariants (`INV-KEEP`), then the measure strictly below its value at that iteration's start (`TERM`).
  - **Ghost statements:** `assert` (`ASSERT`), `ghost-let`, `ghost-let-mut` and `ghost-set`.
  - **Ghost-fn calls:** as for any call, then the body. When a ghost-fn's `requires` is unknown (D58), the call is unknown and the `requires` is recorded as unchecked. Ghost-fns are pure, so results are memoized by argument; a recursive call still checks its measure when its value is already known.
  - **Lemma calls:** the arguments, then the lemma's `requires` (`PRE`) and its `ensures` (`POST`, the lemma's claim at those arguments). The body never runs.
  - **Ghost expressions' own goals:** an index, `take`, `drop`, `last` or `seq-build` length out of range (`BOUNDS`), and a zero divisor (`DIV`).

  The first check that fails ends the run with `contract(kind, clause, node, detail)`:
  - kind is the §9 family the run refutes;
  - clause is the false expression, or for an undefined expression, the clause or ghost-fn body it sits in;
  - node is where the check happened: the call, `return`, loop, `assert` or undefined expression, or the def itself for its `requires` on entry.
- **Why:** Each check is one of §9's goals at a concrete state, so a contract outcome is a counterexample to that goal, named the way the verifier names it. Checking a lemma's claim where it's called gives WP16's witness examples something to run, and its proof stays the verifier's job. Memoizing ghost-fns changes no result and makes recursive specs such as `fib` linear to evaluate.
- **Touches:** WP15; WP16; `docs/b17-0.md` §7, §9.

## D58 · A quantifier is evaluated only over a range read off its guard · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - **Guard:** a `forall`'s guard is G when its body is `(=> G P)`. An `exists`'s guard is its body, when that's an `and`. Nested `and`s are flattened into a list of conjuncts in evaluation order.
  - **Order:** binders take values in declaration order. Each `int` binder's range is worked out once the binders before it have values. A `bool` binder ranges over `false` and `true`.
  - **Bounds:** only G's leading conjuncts that can't fail give bounds. The first conjunct that might fail ends the list, because it might fail at a point that a later conjunct rules out. A conjunct that can't fail is a comparison whose sides are each either an unassigned binder or an expression that mentions none and is defined here, such as `(len a)`, or else a conjunct that mentions no unassigned binder and is defined here. Among those:
    - `(op x E)` and `(op E x)`, where x is an `int` binder and op is `<`, `<=`, `>`, `>=` or `==`, bound x by E's value;
    - the same with E another unassigned binder y relate x and y, and bounds pass along such relations until none changes, as in `sorted`'s i < j < `(len s)`;
    - any other such conjunct bounds nothing. If it's false, the guard holds nowhere.

    Once the conjuncts read so far admit no point, the rest aren't read, because evaluation would never reach them.
  - **Evaluation:** a binder without a finite lower and upper bound makes its part of the quantifier unknown. Otherwise the body is evaluated at every point in range, even after the result is decided, so an undefined point is always found. A point out of range makes G false at a conjunct that can't fail, so skipping it changes nothing and hides nothing. Every point costs fuel (D59), so a range too large to search ends the run with `limit`.
  - **Unknown:** any operation with an unknown operand is unknown. `and`, `or` and `=>` with an unknown left operand are unknown, and their right operand isn't evaluated, since the left may guard it. A quantifier is false (`forall`) or true (`exists`) when a point decides it, and otherwise unknown if any part was. A clause that comes out unknown is neither assumed true nor reported false. The run goes on, and the outcome lists it once per clause and node as `unchecked(kind, clause, node)`.
- **Why:**
  - **The brief:** WP15's brief asks for exactly this: evaluate a quantifier only when each binder's range can be read off its guard, and never treat it as true otherwise.
  - **Leading conjuncts only:** a bound taken from a later conjunct, or a quantifier that stopped at its first witness, could pass a clause that is undefined at a point it skipped. An independent review found both in a first version.
  - **Coverage:** the rule covers every quantifier in the suite except `dedup_sorted`'s "same elements" clauses, which range over every `int`. Its `ensures` and third invariant are listed as unchecked on every run.
  - **Unknown left operands:** not evaluating the right operand costs a little precision, since `(and unknown false)` is unknown rather than false, but it never evaluates a guarded expression outside its guard.
- **Touches:** WP15; WP16; `docs/b17-0.md` §7, §9; `suite/accept/dedup_sorted.b17`.

## D59 · Runs are bounded by fuel and call depth · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - **Fuel:** a run has 1,000,000 steps by default. Each statement executed and each expression evaluated costs one step, in runtime and ghost code alike.
  - **Depth:** a run allows 1,000 nested def and ghost-fn calls by default.
  - **Outcome:** running out of either ends the run with `limit(steps)` or `limit(depth)` at the node being run. Neither is an outcome of §8, since the run didn't finish.
  - **Settings:** both are arguments of `run()`, and the CLI's `--fuel N` sets the first.
- **Why:** With checking off, nothing stops a loop whose measure doesn't drop. A checked run can meet a quantifier box too large to search. Steps and calls count the same way on every machine, so a run stops at the same node everywhere. A timeout wouldn't, and neither would Python's own recursion limit, which varies with platform and caller (D55's reasoning, applied to runs). The interpreter raises Python's limit in proportion to the depth limit, so the depth limit always stops a run first.
- **Touches:** WP7; WP15; D55.
## D60 · Ported ranges are stated per step · Accepted
- **Date:** 2026-10-27
- **Decision:**
  - §10's porting rule keeps its aim, that every value a task computes fits in i64, but states it per step: for each loop step, the value that step computes fits, written in the terms the step uses.
  - For `sum`: `(forall ((i int)) (=> (and (<= 0 i) (< i (len a))) (in_i64 (+ (sum_of (take a i)) (idx a i)))))`.
  - The prefix form `(forall ((i int)) (=> (and (<= 0 i) (<= i (len a))) (in_i64 (sum_of (take a i)))))` is replaced.
  - `fib`, `power`, `sum` and `prefix_sums` change their `requires` this way, and under D42 so do their Dafny versions when M3's task set is built. Given each ghost-fn's definition, both forms admit exactly the same inputs.
- **Why:** the goal spike (`b17c/goals.py`) found that three of these four accept programs can't prove their loop step's overflow goal without a hint. The fourth, `fib`, proves it only after 8,130 quantifier instantiations, using half the 10M-unit budget. That is a search the solver happened to win, and likely to fail under D23's shuffled seeds.
  - **The cause:** the goal at `(+ s (idx a i))` needs the prefix precondition at i + 1. The program never mentions that term before the step, so the solver never instantiates the precondition there.
  - **A hint also works,** such as `(assert (== (sum_of (take a (+ i 1))) (+ s (idx a i))))`. But it's the kind of solver hint the suite forbids (`suite/README.md`), and the kind of hand-written step §9 promises agents won't need.
  - **With the step form,** all four prove every goal with no hint, in a fraction of the budget.
  - **Under D23's shuffled seeds,** measured with 10 seeds:
    - **The prefix form is luck:** `fib`'s goal held under 7 of 10 seeds, then under all 10 after an unrelated encoding change (D61's `contains` facts). `power`'s went from 0 to 2 of 10 with the same change.
    - **The step form holds** under all 10 seeds, in both encodings. `fib`'s goal takes 9 quantifier instantiations and 21,542 units, against 4,333 and 1.74M for the prefix form.
- **Alternatives:**
  - Keep the rule and expect one unfolding `assert` per loop. That puts the cost on every agent in every task, against Bet 1.
  - Have the verifier instantiate range preconditions at the next index. That needs a heuristic with no principled trigger, and it risks matching loops.
- **Touches:** D42; `docs/b17-0.md` §10; `suite/accept/` `fib`, `power`, `sum` and `prefix_sums`; the ported-ranges table in `suite/README.md`; WP10.

## D61 · §9's encoding: axiomatized sequences, division by a variable through its truncation facts, and a resource budget · Accepted
- **Date:** 2026-10-27
- **Decision:** for WP5 and interface 11, and replacing §9's line "vectors, slices and seqs become SMT sequences":
  - **Sequences:** vectors, slices and seqs are an uninterpreted sort per element type, and §9's background facts, with triggers, are their only axioms. SMT-LIB's sequence theory isn't used.
  - **The prefix step fact,** `take s (i + 1) = concat (take s i) (seq-lit (idx s i))`, is instantiated at each `take` term the generator creates. As a trigger, it would loop.
  - **Division:** `/` and `%` by a divisor that isn't a literal are uninterpreted, with D37's truncation facts as axioms: a = b·q + r, |r| < |b|, and r has a's sign. Only queries that use them include them. A literal divisor keeps an exact, linear definition.
  - **Budget:** each goal runs under a resource budget, never a time limit (D23).
  - **Recursive ghost-fns:** each one's defining equation is an axiom that holds only under its `requires`. The ghost-fn's own goals, including its termination goal, are checked without that axiom.
  - **`contains`:** besides its definition (§9's Membership fact), it gets the facts that follow from it directly: over `concat` it is `or`, a one-element sequence contains only its element, and the empty sequence contains nothing.
- **Why:** measured on the suite with the spike.
  - **Z3's sequence theory** timed out on 9 of the 20 accept programs. A five-line version of `find`'s invariant step timed out at 60 s; with the axiomatized sort it proves in 0.01 s. The axioms are also exactly §9's promise: "the whole of what a proof may use".
  - **`gcd`'s invariant** timed out while `%` was defined by multiplication, which is nonlinear. With the truncation axioms it proves at once. Their nonlinear term slows every query that contains it, so only queries that need them get them.
  - **Wall-clock limits** made `dedup_sorted` pass or fail depending on machine load. Under a 10M-unit budget the results are stable. The most any proved suite goal needs is 4.86M, for `fib` (see D60); the next most is 0.84M.
  - **`contains`:** with only its definition, `dedup_sorted`'s invariant and `ensures` held under 6 and 7 of 10 shuffled seeds, because each proof had to find a witness index. With the derived facts, all 25 of its goals hold under every seed. The facts follow from §9's, so they change how fast a proof is found, not what can be proved.
  - **Recursive definitions:** a recursive definition given unconditionally could be contradictory where it doesn't terminate, as in `(+ (bad n) 1)`, and a contradiction proves every goal, including the termination goal that should catch it. Under its `requires` and left out of its own goals, the definition is consistent whenever its termination goal holds, and a definition that doesn't terminate fails that goal. Found while probing the spike's soundness.
- **Touches:** `docs/b17-0.md` §9 (Encoding); D17; D23; interface 11; WP5.

## D62 · For B17-0, the spec language is WP1a's, and WP4a ends when WP1a freezes · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **The spec language:** B17-0's spec language is the module header and the `spec`, `ghost-fn` and `lemma` items of `docs/b17-0.md`, with §7's well-formedness rules: clauses are checked in order, and ghost-fns are well-defined and terminate. WP4a adds nothing to it for Phase 1.
  - **Deferred:** the spec-layer features the design spec lists that B17-0 lacks each wait for what they need.
    - **Frame conditions** aren't needed. Under value semantics and ownership (D36), a def can change only what it owns, and an in-place algorithm returns what it changed (§5).
    - **Data-type invariants and refinement links** wait until B17-0 has data types (§11).
    - **Resource contracts** wait under D30.
  - **Done when:** WP1a freezes (D44), and WP5 discharges the well-formedness goals of every suite spec. The goal spike already discharges them.
  - **D21's table:** wherever a WP depends on WP4a, it depends on WP1a instead. That covers WP4b, WP5, WP6, WP10 and WP16.
    - The critical path to the Phase 2 gate becomes WP1a, WP2, WP3, WP16, WP5, WP6, WP8, WP11.
    - WP16, the core spec library, can start now: its other dependency, WP15, is merged.
- **Why:**
  - D21 split WP4 so that a spec language would exist before the verifier. B17-0 already has one.
  - Every feature it's missing needs a language change that Phase 1 doesn't plan, or isn't needed at all.
  - Keeping an empty WP4a on the critical path would hold up WP16 and WP5 for nothing.
  - When B17-0 gains data types or cost bounds, a new decision reopens WP4a for them.
- **Touches:** D21; D30; WP4a; WP4b; WP5; WP6; WP10; WP16; `docs/roadmap.md`.

## D63 · Interface 11 and the proof cache · Accepted (level rule refined by D80)
- **Date:** 2026-10-28
- **Decision:**
  - **Interface 11, version 0.1, Draft:** a goal's canonical query is the SMT-LIB 2 text `b17c` sends to Z3, in this order:
    - the versioned prelude: D61's axioms and the encoding's definitions;
    - the declarations and ghost-fns this goal uses, and the ghost-fns those use, in generation order;
    - the goal's assumptions;
    - the negated goal;
    - `(check-sat)`.

    Then every name `b17c` generated is renamed `k!0`, `k!1`, … in order of first occurrence. These names are constants, bound variables, ghost-fn parameters and ghost-fn symbols. Variables a loop iteration forgets are declared in order of first assignment, not by name. So alpha-equivalent definitions (D45) send byte-identical queries, and an edit elsewhere in the module doesn't change a goal's query. The canonical query is exactly what is solved, and what is cached.
  - **Cache key:** SHA-256 over:
    - a format tag;
    - the hash of the goal's definition: the spec hash for spec, ghost-fn and lemma-statement goals, and the implementation hash for def and lemma-proof goals;
    - the sorted spec hashes of the items that definition refers to;
    - the canonical query;
    - D22's configuration: `b17c`, which is the hash of the generator's source until there are releases; the prelude, which is the hash of its text and `core.b17`; the solver, which is its version and the SHA-256 of its resolved binary and the `libz3` beside it; the budget; and the number of shuffled seeds.

    Parts are length-prefixed before hashing.
  - **Cache entries:** each holds a verdict and the resource units spent across every seed, stored under `.b17c/cache/` in the working tree, which git ignores.
    - A verdict follows D23: proved under the canonical seed and every shuffled seed, or brittle.
    - Only verdicts reached within the resource budget are cached. A wall-clock timeout or a process error depends on the machine, so it's solved again next time.
    - Entries are published atomically, and an unreadable entry counts as a miss.
  - **Goal identity:** a goal is named by its D56-style node ID, followed by the node ID of the contract clause it checks, for a `PRE` or `POST` goal or a loop's measure drop. A node checked more than once, as a loop condition is on entry and at each iteration, is numbered `#2`, `#3` and so on.
  - **Report:** the module's trusted base report (D24, D25; WP5 owns it, and WP7 adds the backend fields) records:
    - the input's hash (SHA-256 of its canonical bytes), and the lockfile's hash, which is `null` until B17-0 has imports;
    - the configuration above;
    - the level: L3-S when every goal is proved by the solver (D24), L2-S when only the runtime-safety goals are (`BOUNDS`, `OVERFLOW`, `DIV`, `PRE` and `TERM`), and otherwise below L2;
    - the solver-trusted, brittle, failed and admitted goals, by goal identity;
    - the core library's laws and the prelude version, as the axioms the goals rest on.
- **Why:**
  - **The key:** D22 names the key's ingredients but not how they're combined.
  - **Renaming:** making the query invariant under renaming extends D22's "renames never break references" to proofs, so a renamed definition reuses every proof.
  - **Trimming each query** to what it uses makes D22's invalidation exact. Measured on a two-function module: a callee's body edit re-verifies only the callee, and a spec edit re-verifies its callers too. Trimming changed no verdict on the suite or the core library.
- **Touches:** D22–D25; D27 (interfaces 5 and 11); D45; D56; WP5; WP7.

## D64 · Babel-17 is an all-purpose language for agents · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **The goal:** Babel-17 is an all-in-one, general-purpose language for AI agents to write. Its scope is every kind of program: services and command-line tools, applications and their user interfaces, data pipelines, scripts and machine learning, as well as verified algorithms. An agent shouldn't need another language for any part of a program.
  - **Breadth through verification levels:** every module is written in Babel-17 and held to the verification level its spec supports. The levels run from L0 (typed, effect-checked and memory-safe) and L1 (contracts present and tested) to L3 (full functional correctness proved against its spec, or L3-S while the solver is trusted, D24). Code whose intent can be stated precisely is proved. Code whose intent can't, such as a layout that must look right, is held to L0 or L1.
    - L0 and L1 arrive with B17-1, so no domain is shut out for lack of a precise spec.
    - How a goal a module doesn't prove behaves below L2, for example as a runtime check, is decided with B17-1.
  - **Other languages are a bridge.** The Rust backend (WP7) and calls into C, Rust or Python let Babel-17 work alongside existing code. Wrapped libraries are replaced by verified ports over time, as the design spec's "wrap, then replace" says.
  - **Design gaps:** the design spec lacks several features that general-purpose code depends on. Each gets its own decision when evidence calls for it (D14, D20):
    - closures and higher-order functions;
    - interfaces or traits, for code that works over many types;
    - asynchronous I/O;
    - a user-interface model;
    - tensors and automatic differentiation.
  - **Benchmarks beyond algorithms:** task sets for applications, pipelines and machine learning join the algorithm sets, and steer which features come first (D14).
  - **Unchanged:** the language still grows from B17-0 in subsets, each added on evidence (D20), and the phases keep their order.
- **Why:**
  - It's the owner's goal for the language.
  - Bet 1 holds that the explicitness and proof effort that confine verified languages to a niche cost agents little. If M3 bears that out, that cost stops limiting where Babel-17 is used. The other limits remain: hard domains, missing features and libraries, which this decision and the roadmap list.
  - Verification levels let one language serve code with precise specs and code without them. Without them, Babel-17 would stay confined to the domains Dafny serves.
  - Recording the goal lets later design decisions be judged against it.
- **Touches:** D14; D20; Summary; Type system; Verification model; Standard library; Training environment; WP7; WP10; WP11; `README.md`; `docs/roadmap.md`.

## D65 · The language grows in subsets alongside the phases, and B17-1 is part of Phase 1 · Accepted (WP4a clause refined by D79)
- **Date:** 2026-10-28
- **Decision:**
  - **Two tracks:** the phases build the toolchain, and the language grows alongside them in subsets: B17-0, B17-1 and on. Each subset takes B17-0's path:
    - a decision on its scope;
    - spec text and a labelled suite;
    - the interpreter, checker and verifier extended to it;
    - a freeze once the checker agrees with every tier 0 label (D44).
  - **B17-1 is part of Phase 1.** It adds what `docs/b17-0.md` §11 assigns it: generics beyond integers, tuples, data types and nested collections. It also adds verification levels L0 and L1, and decides how a goal that isn't proved behaves below L2 (D64). Its exact scope is its own decision, made after B17-0 freezes.
    - **WP10:** its AlgoVeri ports wait for B17-1, since most AlgoVeri tasks need tuples or data types. The seed tasks don't.
    - **M3:** it can start on B17-0's tasks and add B17-1's when B17-1 freezes.
    - **WP4a:** B17-1's scope decision reopens it for data-type invariants and refinement links, as D62 foresees.
    - **The Phase 1 gate** becomes: B17-1 is frozen, and every ported benchmark task, B17-1's included, verifies end to end and runs as emitted Rust (D18). So WP7 emits B17-1 too.
    - **The critical path:** WP11 depends on WP10 (D21), which now needs B17-1 for its AlgoVeri ports. That adds a second path of the same length: WP1a, WP2, WP3, WP16, WP5, B17-1, WP10, WP11.
  - **Later subsets** cover the rest of D64's scope. Benchmarks set their order (D14), within the prerequisites §11 names, and growth continues past Phase 4 until that scope is covered.
    - **From §11:** mutable borrows, floats, strings and maps; mutual recursion, which waits for group hashing (D22); and vector capacity, which waits for allocation bounds (D30).
    - **From D64:** closures and higher-order functions, interfaces or traits, asynchronous I/O, a user-interface model, and tensors with automatic differentiation.
    - **Effects** for files, network and time.
  - **The standard library** the design spec describes grows with the subsets: collections, numerics, text, parsers, cryptography and time. Each subset's scope includes the library entries it makes expressible.
  - **Task sets beyond algorithms** (D64) are built as the subsets that can express them arrive.
  - **WP11's curriculum** covers every domain the language has reached by the Phase 2 gate.
- **Why:**
  - **No schedule for growth:** D64 sets the destination, but the phases only schedule tooling, so nothing said when the language itself grows.
  - **Why B17-1 in Phase 1:** WP10 needs it for AlgoVeri-class tasks. D64 also needs L0 and L1 early, so that domains without precise specs aren't shut out.
  - **Why later subsets stay unscheduled:** finding which features help agents is what the benchmarks are for (D14, D20).
- **Touches:** D14; D18; D20; D21; D22; D30; D44; D62; D64; WP1a; WP4a; WP7; WP10; WP11; M3; `docs/b17-0.md` §11; `docs/roadmap.md`; `README.md`.
## D66 · Locals are scoped to their block, and results share the parameters' names · Accepted (refines D41)
- **Date:** 2026-10-28
- **Decision:**
  - A local is visible from its declaration to the end of the innermost `block`, loop body or `if` branch that declares it. A branch is a single statement, so a `let` that forms a whole branch is visible nowhere after it. Using a local outside that range is `E-TYPE-002`, as for any undefined name.
  - D41's uniqueness still covers the whole item: two locals may not share a name even in separate blocks.
  - A spec's results take part in D41 with its parameters, so a result may not share a name with a parameter or another result (`E-TYPE-002`). A def's locals may still reuse result names (§2).
- **Why:** §2 says names are unique within an item, and that results are in scope only in `ensures`, but not where a local stops being visible. Without block scoping, `(if c (let y i64 1) (block)) (return y)` would read a local that only one path declares. A parameter and a result with the same name would make `ensures` ambiguous.
- **Touches:** WP3; D41; `docs/b17-0.md` §2.

## D67 · A name of the wrong kind is a type error · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Wrong kind, `E-TYPE-001`:**
    - an item used as a value, such as `(return g)` for a ghost-fn g;
    - a spec or lemma called as `(NAME e*)`;
    - a ghost-fn called with `(call ...)` in ghost code;
    - a parameter, local or binder called as either.

    In runtime code, any ghost-fn call is `E-GHOST-002`.
  - **No item or binding by that name:** `E-TYPE-002`.
  - **A def with no spec:** reported once (`E-TYPE-002`). Its body isn't checked, since the spec supplies its parameters and results, and calls to it aren't either (D78).
- **Why:** §9 files undefined names under `E-TYPE-002` but says nothing of names that exist with the wrong kind. Treating those as type errors keeps "undefined" meaning undefined. Checking an orphan def's body would report every parameter it uses as undefined, which is one error cascading into many.
- **Touches:** WP3; `docs/b17-0.md` §9's tier 0 table.

## D68 · Which types are well-formed · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Element types:** a `(vec T)` or `(ref (slice T))` holds `bool` or `i64` (§3). A `(seq T)` or `(multiset T)` holds `bool`, `i64` or `int`, so collections never nest (§11). Anything else is `E-TYPE-001`.
  - **Binders:** `forall` and `exists` bind `int` or `bool` only (§7), so an `i64` binder is `E-TYPE-001`.
  - **Ghost types in runtime places:** `int`, `(seq T)` and `(multiset T)` are `E-GHOST-002` as a spec's parameter or result type, or as the type of a `let`, `let-mut` or a call's result binding.
- **Why:** §3 gives the element types of vectors and §11 rules out nested collections, but neither names a code. A malformed type is a type error. A well-formed ghost type in a runtime place is §9's "ghost type in runtime context".
- **Touches:** WP3; `docs/b17-0.md` §3, §7, §11.

## D69 · Slices are spec parameters, and borrows are def-call arguments · Accepted (refines D36)
- **Date:** 2026-10-28
- **Decision:**
  - **Slice types:** only a spec's parameters may have one. Anywhere else is `E-OWN-002`: a result, a `let`, a ghost local, or a ghost-fn's or lemma's parameter or result.
  - **Borrows:** `(borrow v)` may appear only as an argument of a def call, whose parameter is a slice. Anywhere else, including a lemma call's arguments and ghost code, is `E-OWN-002`. The borrowed variable must be a live vector (`E-OWN-001`, or `E-TYPE-001` if it isn't a vector).
- **Why:** §3 calls slices "parameters only" and §5 lets a borrow "appear only as a call argument", without saying which parameters or which calls. Ghost code already views a vector as a `(seq T)` (§3) without a borrow, so the strict reading costs nothing.
- **Touches:** WP3; D36; `docs/b17-0.md` §3, §5.

## D70 · Ghost typing: integers, literals and multisets · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Arithmetic:** ghost arithmetic and `neg` produce `int` (§7's Arith-G), and `int` isn't an `i64`. So a ghost local, ghost-fn result or parameter declared `i64` takes only an `i64`-typed expression, such as an `i64` variable, and `(ghost-let g i64 (+ x 1))` is `E-TYPE-001`.
  - **Literals:** an integer literal takes its type from its context (§4):
    - in runtime code it is an `i64` and must fit in i64 (`E-TYPE-001`, D53);
    - in ghost code it is an `int` of any size, unless its destination is `i64`, where it must fit.
  - **Subtyping:** it is exactly §3's. In particular `(multiset T)` has none, so `(== (multiset a) (multiset (seq-lit 1)))` with `a` a vector of `i64` compares `(multiset i64)` with `(multiset int)` and is `E-TYPE-001`.
  - **Sequence operations:** `len`, `idx`, `take`, `drop`, `last`, `contains` and `occurrences` take sequences (vectors, slices or seqs), never multisets.
  - **Element types left open:** an empty `seq-lit`, and a `(vec-new)` whose context fixes no element type, take one from wherever they're used, and are never an error on their own.
    - An element read from one, by `idx` or `last`, takes its destination's type, which can't be a collection (D68). With no destination, it's an integer: `int` in ghost code and `i64` in runtime code.
- **Why:** §3 lists the subtyping rules exactly, and these are the readings that add no rule of their own. Covariant multisets and implicit `int`-to-`i64` narrowing would both be new rules.
- **Touches:** WP3; D34; D53; `docs/b17-0.md` §3, §4, §7.

## D71 · Comparing collections is ghost-only · Accepted
- **Date:** 2026-10-28
- **Decision:** `==` and `!=` on vectors, slices, seqs or multisets in runtime code are `E-GHOST-002`.
- **Why:** §7's Cmp rule allows equality on collections in ghost context only. That makes it a ghost-only operation, which is the case §9's table files under `E-GHOST-002`.
- **Touches:** WP3; `docs/b17-0.md` §7, §9.

## D72 · A vector appears in at most one argument · Accepted (refines D36)
- **Date:** 2026-10-28
- **Decision:** §5's rule 7 counts arguments. A vector variable may appear in at most one of a call's arguments, and in at most one of a return's expressions, however it appears there: owned, borrowed, or only read, as in `(len v)`. So `(call g (borrow v) (len v))` and `(return v (len v))` are `E-OWN-005`. Several appearances inside one argument count as one, as in `(+ (idx v 0) (len v))`. Lemma calls are ghost and aren't counted.
- **Why:** The rule says "at most once among a call's arguments, whether owned or borrowed", which on the strict reading covers any appearance. Counting per argument keeps the rule about aliasing between arguments. It matches Rust, which rejects `f(v, v.len())` and `(v, v.len())`.
- **Touches:** WP3; D36; `docs/b17-0.md` §5, §7.

## D73 · An owned vector argument is a variable · Accepted
- **Date:** 2026-10-28
- **Decision:** An argument for a `(vec T)` parameter must be a variable, which then moves (§7). `(vec-new)`, a `seq-build` or any other expression in that place is `E-OWN-006`.
- **Why:** §7 says "An owned vector argument must be a live variable, which then moves." `E-OWN-006` is already the code for a vector expression of the wrong form. A program writes `(let-mut v (vec i64) (vec-new))` first and passes `v`.
- **Touches:** WP3; `docs/b17-0.md` §7.

## D74 · A call's results are always bound · Accepted (refines D43)
- **Date:** 2026-10-28
- **Decision:** `(call f ...)` as a statement is only for a callee with no results, which means a lemma or a spec that returns nothing. When f's spec declares results, they must be bound by `(let ((x T) ...) (call f ...))`, one name per result, and dropping them is `E-TYPE-001`.
- **Why:** §7 binds results "one name per declared result". Never dropping them means an owned vector can't be lost by accident, and a result list stays something only a call's `let` can hold (§8, D43).
- **Touches:** WP3; D43; `docs/b17-0.md` §7.

## D75 · Which statement changes which binding · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - `set`, `set-idx` and `push` change runtime locals, and `ghost-set` changes ghost locals. Targeting the other kind is `E-GHOST-001`, since it would let ghost and runtime state mix.
  - Changing a binding that can't change is `E-OWN-003`: a parameter (of a spec, lemma or ghost-fn), a `let` or a `ghost-let`.
  - In a lemma body, `(return e ...)` with values is `E-GHOST-003`, like any other runtime statement there.
- **Why:** §5 rule 5 and §7 give the mutability rules for runtime locals, and §7 says ghost statements "act on ghost locals only", but neither names a code for crossing between the two.
- **Touches:** WP3; `docs/b17-0.md` §5, §7.

## D76 · A loop body leaves vectors exactly as it found them · Accepted
- **Date:** 2026-10-28
- **Decision:** §5's rule 6 applies both ways. A loop body whose normal end leaves an outer vector moved that was live at its start is `E-OWN-004`, and so is one that leaves an outer vector live that had moved before the loop, by giving it a new value with `set`. Vectors the body declares itself aren't outer.
- **Why:** After the loop, the vector's state would depend on how many times the body ran, which is what "in the state it found it" rules out.
- **Touches:** WP3; `docs/b17-0.md` §5, §7.

## D77 · A loop may always end, and unreachable code is still checked · Accepted (refines D40)
- **Date:** 2026-10-28
- **Decision:**
  - For `E-RET-001`, every `while` may end normally, whatever its condition, so a def body that ends with a loop needs a `return` or `panic` after it.
  - Statements after a `return` or `panic` in the same block are checked for names and types as usual, but being unreachable isn't an error.
- **Why:** Tier 0 doesn't reason about values. Rust makes the same choice for `while true`.
- **Touches:** WP3; D40; `docs/b17-0.md` §7.

## D78 · One diagnostic per error · Accepted (refines D45)
- **Date:** 2026-10-28
- **Decision:**
  - **No cascades:** an expression that fails a check takes on a type compatible with anything, so code that uses it doesn't report again.
  - **Names declared wrongly:** an item name declared twice, a core library name declared again (D51), or a def with no spec, is reported once, at the later declaration. Uses of that name, as a value or a callee, aren't checked, since which declaration they mean is unclear. A local declared twice keeps the binding already in scope.
  - **Moves:** a moved vector's first runtime use is reported (`E-OWN-001`), and later uses aren't. A vector repeated in one call or return is reported once (`E-OWN-005`), with no use-after-move report on top.
  - **Effects:** each effect a spec leaves out is reported once, at the first statement that has it (`E-EFF-001`).
  - **Recursion:** `E-TERM-001` is reported at each recursive call. `E-TERM-002` is reported once per group of mutually recursive items, a strongly connected component of the call graph, at its first call by position.
  - **Duplicate specs:** D45's check runs last, only once nothing else has failed, and its `E-TYPE-002` is placed at the later spec. `hashing.HashError` names the two specs. `hashing.hashes` hashes each spec after the items it mentions, so a long chain of references doesn't overflow Python's stack, whatever D55 says about one item's nesting.
- **Why:** The task asks for every independent error and none that merely follows from another. Positions on every diagnostic make the output usable until WP6 defines node IDs.
- **Touches:** WP3; WP6; D45; D55; `b17c/hashing.py`.

## D79 · B17-1 adds data types, tuples, collections of any type, and ghost sets and maps · Accepted (refines D65)
- **Date:** 2026-10-28
- **Evidence:** a survey of the frozen preambles and signatures of the 64 AlgoVeri tasks in `gym/tasks/algoveri/`.

  | Group | Tasks | What they need beyond B17-0 |
  |---|---|---|
  | Already B17-0 | 14 | Nothing. `longest_common_subsequence` takes `seq<char>`, ported as `i64`, as AlgoVeri's own tries store characters. |
  | Quantified sequences | 11 | Quantifiers over sequences: a sort's permutation witness, or an optimum over every selection, as in the knapsacks |
  | Pairs | 2 | Tuples, nested sequences |
  | Optional results | 2 | `Option`, nested sequences |
  | Graphs | 13 | Records holding nested sequences, tuples for weighted edges, `Option`, quantified paths; ghost sets and maps for matchings and flows |
  | Trees | 22 | Recursive data types, `Option` of them, `match`; ghost sets and maps for their views |

  - **Generics:** `Option<T>` is the only generic declaration, in 22 tasks. No task has a generic method, function or predicate outside a data type. The one inside, `lca`'s `Option.is_some`, tests a constructor.
  - **Invariants:** all 37 tasks with data types state their invariants as ghost predicates in `requires` and `ensures`, such as `well_formed(g)` and `node.is_segment_tree()`. None declares a subset type, a class invariant or a refinement link. Dafny's `nat`, in 3 tasks, is an `int` at least 0, which a port states in its `requires` (D42).
  - **Sets and maps:** 25 specs use them, all in ghost code.
    - **Sets:** membership, the empty set, singletons, union, difference and intersection. The six trie and ternary search tree tasks define their views by comprehension over all sequences, so those sets can be infinite (Dafny's `iset`). Only `max_matching` counts a set's elements.
    - **Maps:** the empty map, update, lookup, membership of a key, and union.
    - **At run time:** Claude's verified solutions from the hard run declare a runtime set in 2 tasks, `kruskal` and `prim`, both of visited vertices, which a `(vec bool)` covers. None declares a runtime map.
- **Decision:** B17-1 is B17-0 plus the following. The spec text fixes the exact forms.
  - **Data types:** `(data NAME (T*) (CTOR (FIELD type)*)+)`, a sum of products.
    - **Recursion:** a data type may contain itself, also through another type, as a trie node holds a vector of optional nodes. Mutually recursive data types wait with mutual recursion (§11).
    - **Building and reading:** a constructor call `(CTOR e*)` builds a value. `match` takes it apart, and must name every constructor. `(is CTOR e)` tests a value's constructor. `(field e FIELD)` reads a field, with a new runtime-safety goal family, `FIELD`: e was built by a constructor that has that field. Reading a field e lacks is `err` (§8). All of them work in runtime and ghost code.
  - **Generics:** data types take type parameters. Specs, defs, ghost-fns and lemmas don't, since no task needs it. The core library declares `(option T)`, with constructors `none` and `some`.
  - **Tuples:** `(tuple T1 ... Tn)` for n ≥ 2. Tuple values are built from their components, and read with `match` or a component projection by literal index.
  - **Collections of any type:** `vec`, `seq` and `multiset` take any well-formed element type, so collections nest and hold tuples and data.
  - **Runtime and ghost types:**
    - **Runtime types:** `bool`, `i64`, a vector of a runtime type, and a tuple or data type whose components are all runtime types.
    - **Ghost types:** every other type, such as a data type with an `int` field. They're used only in ghost code, as `int` and `seq` are.
    - **Slices** stay a spec's parameters only, so no other type contains one (D69).
  - **Ghost sets and maps:**
    - **Sets:** a set type whose sets may be infinite, with membership, the empty set, insertion, union, difference, intersection and comprehension over a binder. `set` is already a statement, so the spec text names the type. Counting elements is left out: `max_matching`, the only task that counts, states its matching as a sequence of distinct edges.
    - **Maps:** finite maps, with the empty map, update, lookup, membership of a key and union. Looking up a key outside the map is a ghost `BOUNDS` goal, as an index out of range is.
  - **Quantifiers** bind values of any type ghost code can use, not just `int` and `bool`. The spec text fixes which, as D68 does for B17-0.
  - **Copying and moving:** a runtime tuple or data type is copied when every type inside it is copied and it isn't recursive. Otherwise it moves, as a vector does.
  - **Places, still without lifetimes:**
    - **What a place is:** an index, a tuple projection or a field read names a place inside a value.
    - **Reading:** reading a copied value through a place copies it. A moving value can only be read further through, under `len`, `idx`, a projection, a field read or `is`, or viewed in ghost code. It's never moved out of its place.
    - **Taking a value out:** `replace` takes the moving value out of a place in a `let-mut` local and leaves a new one there, as Rust's `std::mem::replace` does.
    - **Updating:** `set-idx` takes a place in a `let-mut` local too, so a nested vector is updated where it sits.
    - **`match`:** it takes an owned value, whose fields move into the arm's names, or a value of a copied type.
    - **Borrows:** they stay as B17-0 has them: shared slices of vectors, as def-call arguments. Borrowing a data value waits for `&mut` and in-place borrows (§11).
  - **Termination:** measures stay integers. A built-in ghost `(rank e)` gives each data value an `int` at least 0 and greater than the rank of every value inside it, so recursion down a tree uses `(decreases (rank t))`.
  - **Equality:** on tuples and data it's structural, and ghost-only, as on collections (D71). Runtime `==` stays on `bool` and `i64`.
  - **Still out:** strings and characters, floats, runtime sets and maps, generic functions, `&mut`, mutual recursion and vector capacity stay where §11 and D65 put them.
- **WP4a stays done.** This refines D65, which has B17-1's scope decision reopen WP4a for data-type invariants and refinement links. B17-1 adds neither, since every surveyed task states its invariants as predicates in its contracts. A later decision reopens WP4a when a task needs an invariant that holds across a module's operations, such as an abstract type with a hidden representation.
- **Toolchain:**
  - **Extended to B17-1:** the interpreter, checker and verifier. B17-1 freezes under D44, as B17-0 did.
  - **Verifier:** it encodes tuples and data types as SMT-LIB datatypes, which Z3 supports natively, sets as arrays to `Bool`, and `rank` by axioms.
  - **Interpreter:** checking evaluates a quantifier only over a range read off its guard (D58), so a quantifier over sequences, sets or maps stays unknown there.
  - **WP7:** it emits data types as Rust enums, with recursive fields boxed.
- **Why:**
  - **Evidence for every feature:** each one is needed by tasks the survey counts, and 50 of the 64 tasks need at least one. The survey finds nothing else a task's contract needs, apart from counting a set's elements.
  - **Type parameters on data types alone** cover `Option` and keep every function monomorphic.
  - **Places** give nested reads and updates without lifetimes, as B17-0's slices do. Nothing a place names outlives the expression that uses it.
  - **Runtime types exclude ghost types and slices,** so a runtime value never holds a borrow or an unbounded integer.
  - **Ghost-only sets and maps** cover every spec that uses them. The solutions' runtime uses are dense indices.
  - **Leaving out set cardinality** spares the encoding its axioms for the sake of one task, whose matching a sequence states as well.
  - **`rank`** keeps measures integers, so §7's termination goal doesn't change.
- **Touches:** D20; D36; D42; D58; D62; D65; D68; D69; D71; WP3; WP4a; WP5; WP7; WP10; WP15; WP16; interfaces 1, 6, 10 and 11; `docs/b17-0.md` §8 and §11; `docs/roadmap.md`; `README.md`.

## D80 · Verification levels, and what an unproved goal does below L2 · Accepted (refines D63)
- **Date:** 2026-10-28
- **Decision:**
  - **Levels are cumulative:**
    - **L0:** the module passes tier 0.
    - **L1:** L0, and every goal is proved or tested (below).
    - **L2:** L1, and every runtime-safety goal (`BOUNDS`, `OVERFLOW`, `DIV`, `FIELD`, `PRE`, `TERM`) in runtime code is proved from proved goals alone (below). It's L2-S while the solver is trusted (D24).
    - **L3:** every goal is proved, so nothing is left to test. It's L3-S while the solver is trusted.
  - **Proved from proved goals:** a proof may assume things that are only tested, and then it doesn't count for L2. What a goal's proof assumes must itself be established this way:
    - the goals before it on its path, since §9 assumes each goal once it's generated;
    - the `ensures` of each def it calls, through that def's `POST` goals;
    - each lemma's claim, through the lemma's own goals.

    WP5 computes this as a closure, and solves a goal again without the assumptions that don't count.
  - **Declared and reached:**
    - **Declared:** a module declares the level it must reach, and `b17c` fails when it reaches less. The declaration goes in the manifest (interface 4, D26) once that exists. Until then it's a command-line option.
    - **Reached:** the trusted base report (D63) records the level reached, and lists each tested goal with the number of inputs that evaluated it. This replaces D63's rule for the level, which looks only at what the solver proved.
    - **Benchmark tasks** require L3-S, and L3 once the kernel checks proofs (D24).
  - **Property tests (L1):** the interpreter, with checking on (D57), runs each def on generated inputs.
    - **Inputs** are drawn for each parameter's type from a fixed seed, and kept when the `requires` hold, so a run is the same on every machine (D23).
    - **Counts are fixed:** a set number of inputs that satisfy the `requires`, from at most a set number of draws.
    - **Failures:** an `err` or a contract outcome is a failure, reported as the goal it refutes (D57).
    - **Limits:** a run that ends in a `limit` (D59) refutes nothing and tests nothing, so the input is dropped, as one whose `requires` fails is.
    - **When a goal counts as tested:** at least one kept input evaluates it, and every evaluation holds. A goal no input reaches, or one that checking can't evaluate, such as a quantifier left unknown (D58), isn't tested, so L1 needs it proved. Lemma bodies never run (D57), so their goals are always proved.
    - **The spec text** fixes the counts and the generator.
  - **Below L2, at run time:**
    - **An unproved `BOUNDS`, `OVERFLOW`, `DIV` or `FIELD` goal in runtime code** guards a state that §8 calls `err`. Emitted Rust aborts there, as safe Rust does on an index out of range, a checked overflow or a zero divisor, so the program stays memory-safe.
    - **The same goals in ghost code** can't abort, since ghost code is erased before it runs. Unproved, they leave the contract they sit in undefined at some inputs, and L1's tests evaluate them like any other goal.
    - **An unproved `PRE` goal** isn't checked. The call runs, its `ensures` may not hold, and any `err` it reaches still aborts.
    - **An unproved `TERM` goal** isn't checked either, so the code may not terminate.
    - **Effects still hold:** leaving `panic` out of a spec rules out `(panic STR)` at every level, since tier 0 checks effects. Below L2, it can't rule out an abort at `err`, which is outside the semantics, like allocation failure (D29). The report lists the goals whose failure would abort.
  - **Contracts are never checked at run time,** at any level. They're ghost code and may quantify over unbounded ranges. Checking `sorted` on each call to a binary search would also change its cost. Below L3, L1's tests exercise them instead.
  - **WP7 keeps its checks at every level:** arithmetic stays explicitly checked and indexing bounds-checked (D18), whatever is proved.
- **Why:**
  - **No domain is shut out:** D64 needs levels below L2 so that a program without a precise spec still gets types, effects, ownership and memory safety.
  - **Proved or tested:** at L1 and above, every goal has one of the two kinds of evidence, and the report says which.
  - **Proofs from proved goals:** without that rule, an L2 module could still abort, through a safety proof resting on an invariant that only tests support.
  - **Aborting on `err`** is what safe Rust already does, so memory safety never depends on a proof.
  - **Unchecked contracts** keep a program's cost the one its code states. The tests check the contracts without that cost.
  - **Fixed seeds and counts** keep D23's rule that results don't depend on the machine.
- **Touches:** D18; D23; D24; D25; D26; D29; D57; D58; D59; D63; D64; D65; interfaces 4 and 5; WP2; WP5; WP7; `docs/roadmap.md`.
