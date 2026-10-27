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

## D21 · Work package dependencies are rewired · Accepted (WP1a edges amended by D44)
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

## D22 · Definitions get separate spec and implementation hashes · Accepted
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

## D36 · Ownership without lifetimes · Accepted
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

## D40 · Every path returns or panics · Accepted
- **Date:** 2026-10-27
- **Decision:** Every path through a `def` ends in `return` or `panic`, and early returns are allowed. `(return e1 ... en)`, one expression per declared result, is the only way to exit with results.
- **Why:** "One way to say it", while still allowing the early returns agents write naturally in search loops.
- **Touches:** `docs/b17-0.md` §7, §9.

## D41 · No shadowing · Accepted
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

## D43 · A spec may declare several results · Accepted
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

## D45 · What a B17-0 hash covers · Proposed (refines D22)
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
  - **One spec per spec hash:** tier 0's last check computes spec hashes and rejects two specs in one module with the same one (`E-TYPE-002`). Otherwise two defs that implement identical specs would be indistinguishable to their callers' implementation hashes. Lemmas and ghost-fns may coincide: a ghost-fn's hash already covers its body, and which proof of a lemma is used doesn't change any meaning. Hashes are defined only for programs that pass tier 0.
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

## D46 · B17-0 hash format · Proposed
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
