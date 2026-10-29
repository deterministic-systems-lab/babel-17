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

## D45 · What a B17-0 hash covers · Accepted (refines D22; refined by D78 and D92)
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

## D58 · A quantifier is evaluated only over a range read off its guard · Accepted (refined by D102)
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

## D61 · §9's encoding: axiomatized sequences, division by a variable through its truncation facts, and a resource budget · Accepted (refined by D103)
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

## D80 · Verification levels, and what an unproved goal does below L2 · Accepted (refines D63; refined by D91)
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

## D81 · B17-1's syntax for data types, tuples and match · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Data types:** `(data D (A*) (C (F type)*)+)` declares a type with its parameters and constructors. A constructor call is `(C e*)`, the same form as a ghost-fn call.
  - **`match`:** `(match e (case (C x*) X)+)` is an expression or a statement, as `if` is. It has one arm per constructor, in declaration order, with no wildcards and no nested patterns. A missing, repeated or misplaced arm is `E-TYPE-001`. A tuple has one arm, `(case (tuple x+) X)`.
  - **Reading one part:** `(is C e)` tests a constructor, and `(field e F)` reads a field, with a `FIELD` goal unless every constructor has F.
  - **Tuples:** `(tuple e e+)` builds one, and `(get e K)` reads a component, with K a literal.
- **Why:**
  - **One way to write each match:** a fixed arm order and no wildcards mean one canonical form per match, as D47 wants of layout, and an agent can't forget a constructor.
  - **No nested patterns:** they'd need an exhaustiveness check over pattern trees. A nested match does the same job.
  - **The form of a constructor call:** it matches the ghost-fn call agents already write, and the name tells them apart.
- **Touches:** D47; D79; `docs/b17-1.md` §2, §7; interfaces 1 and 6.

## D82 · Types and values have separate namespaces · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Type names:** data types and type parameters are unique within a module. They may not be a built-in type word or the core library's `option`.
  - **Value names:** they follow D41. Constructors are value names, unique among items and constructors.
  - **Field names:** they're unique within one data type, across its constructors, and may repeat across types. `field` looks a field up in its operand's type.
  - **A name may be both kinds,** so a parameter `tree` of type `tree` is allowed, and a single-constructor type may share its constructor's name.
- **Why:** AlgoVeri's ports name parameters after their types (`graph: Graph`), and Dafny's `datatype Graph = Graph(...)` shares a type's name with its constructor. Names here are lowercase only, so one namespace would force renames on every such port. Types and values never appear in the same position, so keeping them apart costs no ambiguity.
- **Touches:** D41; D51; `docs/b17-1.md` §2.

## D83 · Runtime types, copying, well-formed data types and ghost subtyping · Accepted (refined by D104)
- **Date:** 2026-10-28
- **Decision:**
  - **Runtime types:** `bool`, `i64`, and a vector, tuple or data type whose components are all runtime types, as D79 lists them. A slice is a spec's parameter type only, and never sits inside another type. Every other type is a ghost type. A vector's element is a runtime type.
  - **Copying:** a tuple or data value is copied when every type inside it is copied and its type isn't recursive. Everything else moves.
  - **Well-formed data types:**
    - every data type has a finite value;
    - a data type is applied to as many types as it has parameters;
    - two data types may not contain each other (`E-TERM-002`);
    - a data type never contains itself inside an `iset`, `map` or `multiset`.
  - **Subtyping, in ghost code:** tuples are covariant in their components, as `seq` is. `iset` and `map` have no rule, as `multiset` has none (D70). A data type is covariant in some parameters and invariant in the rest:
    - a parameter is invariant when one of its occurrences in the fields sits inside an `iset`, `map` or `multiset`, or is the argument for an invariant parameter of any data-type application, the type's own recursive ones included;
    - the module's variances are the largest assignment that satisfies this, found by starting with every parameter covariant.
- **Why:**
  - **Runtime types:** D79 asks that no runtime value hold a borrow or an unbounded integer. This is that rule stated over types.
  - **Copying:** it matches what Rust can `Copy`. A recursive type holds a `Box`, which Rust never copies implicitly.
  - **A finite value:** a type with none can't be constructed, and the property-test generator (D88) needs a smallest value to stop at.
  - **Covariance:** `(option i64)` must compare with `(option int)` in specs, which the encoding gets for free, since `i64` and `int` share SMT's `Int`. A parameter used inside a set, map or multiset can't be covariant, or a wrapper around `(map i64 bool)` would pass for one around `(map int bool)`.
  - **No recursion under arrays:** those three are arrays in the encoding (D89), and Z3 has no well-founded datatype that contains itself inside an array.
- **Touches:** D34; D36; D68; D69; D70; D79; `docs/b17-1.md` §3, §5.

## D84 · Places, replace, and what match may take · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Places:** a place is a variable, `(idx p i)`, `(get p K)` or `(field p F)`. Reading a copied value through one copies it. A moving value in a place can only be read further, under `len`, `idx`, `get`, `field` or `is`, or in ghost code.
  - **Updating:** `set-idx` and `push` take a place rooted at a live `let-mut` local, and never one through a slice.
  - **Taking a value out:** `(let x T (replace p e))` moves p's value into x and leaves e there. It's allowed only as a `let` or `let-mut` initializer, and it's the only way to move a value out of a place.
  - **`match` in runtime code** takes a variable, which moves when its type does, or an expression of a copied type. Its arms bind the fields as owned locals.
  - **`E-OWN-007`:** a moving value moved out of a place, whether used whole in an owned position or as a `match`'s scrutinee.
  - **Generalized rules:** D72's one-argument rule and `E-OWN-006` now cover every moving value, constructor and `tuple` arguments included.
  - **Moves only in owned positions:** in runtime code, a moving expression other than a variable appears only as an owned position's whole value, or as an argument of a constructor or `tuple` that does. So `if` and `match` expressions and loop conditions never move anything, and a `match` expression's scrutinee has a copied type.
  - **Repeated bodies:** a runtime `seq-build`'s body may not move a variable declared outside it (`E-OWN-004`), as a loop body may not.
  - **The root outlives the value:** in `set-idx`, `push` and `replace`, the indices and value are evaluated first, and the place's root must still be live after them (`E-OWN-001`).
  - **Goals:** `replace` carries the same `BOUNDS` and `FIELD` goals as `set-idx`, for each `idx` and `field` its place passes through.
- **Why:**
  - **No lifetimes:** nested vectors and trees need reads and updates in place. A place lasts no longer than the statement that names it, so none is needed, as D36 intends.
  - **`replace` as an initializer:** binding the old value to a name keeps expressions free of side effects, as in B17-0. Rust's `std::mem::replace` behaves the same way.
  - **Moves at statement level:** move state then never needs joining inside an expression, so the checker tracks moves per statement as B17-0's does.
  - **The other three rules** close holes a review found: a `seq-build` moving one value into every element, `(push (field x kids) x)` moving x into itself, and a `replace` at an unchecked index.
- **Touches:** D36; D72; D73; D76; D79; `docs/b17-1.md` §5, §7; `b17c/check.py`.

## D85 · Ghost sets and maps · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Types:** `(iset T)` is a set that may be infinite, and `(map K V)` a finite map.
  - **Set operations:** `(iset-lit e*)`, `(iset-of ((x T)) e)`, `union`, `diff` and `inter`.
  - **Map operations:** `(map-lit (k v)*)`, `(update m k v)`, `(lookup m k)` with a ghost `BOUNDS` goal that k is a key, and `(union m n)`, where n's value wins on a shared key. Each is typed over `(map K V)`, as `docs/b17-1.md` §7 states.
  - **`contains`** tests membership in a sequence, a set or a map's keys.
  - **Literals** take their element types from their destination when they have one.
- **Why:**
  - **The name `iset`:** `set` is already a statement, and `iset` is Dafny's name for exactly this type, which the ported tries use.
  - **One `contains`:** a single membership word for all three keeps the vocabulary small.
  - **A right-biased union:** it matches Dafny's `+` on maps, which the segment tree tasks use.
  - **Literals from their destination:** without it, `(iset-lit v)` with v an `i64` couldn't be an `(iset int)`, since sets have no subtyping (D83).
- **Touches:** D70; D79; `docs/b17-1.md` §2, §4, §7.

## D86 · A constructor with a boxed field allocates · Accepted
- **Date:** 2026-10-28
- **Decision:** a field is boxed when its type mentions its own data type other than inside a vector. A constructor call has effect `alloc` when its constructor has a boxed field. `tuple`, `match`, `is`, `field`, `get` and `replace` have no effect.
- **Why:** WP7 emits a boxed field as a Rust `Box`, which allocates. A vector already holds its elements on the heap, so a field that reaches its type only through one isn't boxed. An effect says what a function may do (D20), so the constructor carries `alloc` even when the field it fills is `none`.
- **Touches:** D20; D30; D79; WP7; `docs/b17-1.md` §6.

## D87 · rank is height, on every data value · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Where it applies:** `(rank e)` is defined for e of any data type, as D79 says. A tuple or any other type is `E-TYPE-001`.
  - **Interpreter:** it computes height. A value with no data value inside it has rank 0, and any other value is one more than the greatest rank among the data values directly inside it, reached through tuple components and sequence elements.
  - **Verifier:** it states only that rank is at least 0, and that a data value reached from a constructor's field, through tuple components and sequence elements, has a smaller rank than the value the constructor builds.
- **Why:**
  - **Agreement:** height satisfies every axiom, so the interpreter and the verifier agree.
  - **Integer measures:** they keep §7's termination goal unchanged (D79).
  - **Every data value:** an LLRB tree recurses on `(option node)`, which isn't itself recursive, so `rank` must reach it too.
- **Touches:** D57; D79; `docs/b17-1.md` §7, §8, §9.

## D88 · The property-test generator · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Generator:** SplitMix64. Its state starts at the first 16 hex digits after `spec0:` in the def's spec hash (D46), read as an unsigned 64-bit integer. `docs/b17-1.md` §10 gives the exact stream: the order of draws, how each value consumes it, and each type's smallest value.
  - **Counts:** 100 inputs that satisfy the `requires`, from at most 10,000 draws. A draw whose `requires` is unknown is dropped.
  - **Values:**
    - **`bool`:** each value equally likely.
    - **`i64`:** half the time uniform on [−10, 10]; a quarter of the time one of seven boundary values; otherwise uniform over all values.
    - **Vectors:** a length uniform on [0, 8].
    - **Tuples and data:** each part drawn independently. Data takes a constructor chosen uniformly, and at depth 4 its smallest finite value.
- **Why:**
  - **Seeding from the spec hash:** inputs depend only on what the spec says, so editing a body never changes which inputs test it. The same inputs on every machine keep D23's rule.
  - **Small values and boundaries:** they find most contract failures in small programs, and the boundaries catch overflow.
  - **Fixed counts:** they bound a test run's cost, as D59's fuel bounds a run.
- **Touches:** D22; D23; D57; D59; D80; WP15; `docs/b17-1.md` §10.

## D89 · Interface 11 version 0.2 encodes B17-1 · Accepted (refined by D103)
- **Date:** 2026-10-28
- **Decision:**
  - **Datatypes:** tuples and data types are SMT-LIB datatypes, generic ones parametric.
  - **Sequences:** D61's encoding, instantiated for each element sort a query uses.
  - **Arrays:**
    - multisets are count arrays;
    - sets are arrays to `Bool`, with `iset-of` as a lambda;
    - maps are arrays from keys to `(option V)`.
  - **Equality** is extensional everywhere. Sequences, and values holding them, compare through a per-sort equality predicate that implies SMT equality.
  - **`rank`** is an uninterpreted function per data sort, with D87's axioms.
  - **`match` and `is`:** in each arm, the scrutinee equals its constructor applied to the arm's binders.
- **Why:**
  - **Datatypes:** Z3 decides them natively, and array theory decides the set and map operations, so neither needs laws in the core library.
  - **Maps as arrays to `option`:** `none` outside a map's keys makes array equality map equality.
  - **The sequence equality predicate:** D61's sequences are uninterpreted, so SMT equality alone isn't extensional. Dafny's `Seq#Equal` solves the same problem.
- **Touches:** D17; D61; D63; D79; WP5; interface 11; `docs/b17-1.md` §9.

## D90 · Quantifiers bind only types the encoding states exactly · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Allowed binder types:** a binder of `forall`, `exists` or `iset-of` has an exact type. `bool` and `int` are exact; a `seq`, `iset` or tuple is exact when its parts are; a data type is exact when every field type of every constructor is, after substitution, with its own recursive occurrences counting as exact unless reached through a `seq`, where D61's uninterpreted sequences would admit a cyclic value.
  - **Rejected:** any other binder is `E-TYPE-001`, so `i64`, a vector, a slice, a `multiset` or a `map` anywhere inside, a data type's fields included, makes a binder fail. D68's `i64` binder rule is the same rule for B17-0's types.
  - **Ports:** `edmond_karp` and `push_relabel`, which quantify over flows stated as maps, state a flow as a sequence of sequences of `int` instead.
- **Why:**
  - **Soundness:** the encoding admits values outside the rejected types. A map is an array to `option`, so it may have infinitely many keys. An `i64` field shares SMT's `Int`, so `(some 2^63)` is an `(option i64)` there. An `exists` over such a type could be proved with a witness no program has.
  - **Exactness:** the allowed types' values are exactly the encoding's, since datatypes are finite trees, arrays to `Bool` are all sets, and D61's sequences are all finite sequences.
  - **Evidence:** the surveyed specs quantify over sequences in 28 tasks, counting the tries' comprehensions over keys, and over flows in 2 and a matching in 1, which rewrite to sequences. `max_matching` also binds tuple edges, which are exact as `(tuple int int)`.
- **Touches:** D61; D68; D79; D89; WP10; `docs/b17-1.md` §7, §11, §12.

## D91 · L2's closure covers the ghost-fns a proof unfolds · Accepted (refines D80)
- **Date:** 2026-10-28
- **Decision:** a goal's canonical query includes the defining equations of the ghost-fns it uses (D63), and a proof may rest on any of them. It counts for L2 only once every goal of each such ghost-fn counts too: the well-definedness of its `requires`, its measure and its body, and its termination, and likewise, transitively, for the ghost-fns those goals' queries include. WP5 solves a goal again without an equation that doesn't count. This adds a fourth item to D80's list of what a proof may assume, after earlier goals on the path, callees' `ensures` and lemmas' claims.
- **Why:** a ghost-fn is transparent (`docs/b17-0.md` §7), so its equation is an assumption like any other. If its `BOUNDS` or `TERM` goal were only tested, a safety proof resting on it could still be wrong, and an L2 module could abort.
- **Touches:** D63; D80; WP5; `docs/b17-1.md` §10.

## D92 · How B17-1's data items and binders are hashed · Accepted (refines D45)
- **Date:** 2026-10-28
- **Decision:** the format stays version 0 (D46). B17-0's items hash as before, and these rules cover B17-1's new forms.
  - **Data items** have only a spec hash, covering the whole item, as ghost-fns do. Inside one, its own name becomes `_`, its type parameters `$0`, `$1`, … in order, its constructors `#0`, `#1`, … in order, and its fields `.0`, `.1`, … across all its constructors in declaration order.
  - **References:** a data type's name becomes its spec hash H, a constructor H's `#i`, and a field `.k`, wherever they're used.
  - **Binders:** case-pattern names and `iset-of` variables are numbered with D45's other binders.
  - **Namespaces:** names resolve in their own namespace (D82), so a data type and a ghost-fn named alike hash apart.
  - **One data type per hash:** two data items with the same spec hash in a module are `E-TYPE-002`, as two specs are.
- **Why:**
  - **References by hash:** editing a data type then rehashes every spec that mentions it, as editing a ghost-fn does. A layout change must re-verify what depends on it.
  - **Positions for names:** renaming a type, constructor or field changes no hash, as D22 asks of renames.
  - **No coinciding types:** two types identical up to names would get one hash, and the references in specs couldn't tell them apart.
- **Touches:** D22; D45; D46; WP2; `b17c/hashing.py`; `docs/b17-1.md` §2.

## D93 · Interface 3 version 0.1: the diagnostic schema · Accepted
- **Date:** 2026-10-28
- **Decision:** `b17c/agent.py check FILE` prints a JSON array of diagnostics. It lists every tier 0 error or, once tier 0 passes, every goal that isn't proved, and exits 1 when the array isn't empty. Each diagnostic has the design spec's fields:
  - **`code`:** a §9 tier 0 code, or `E-PROOF-` and the goal's family.
  - **`severity`:** always `error`, since B17-0 has no warnings.
  - **`node`:** D56's node ID. For a goal it's D63's goal identity, and for a parse error `module@LINE:COL`.
  - **`message`:** the checker's text, or the goal's family and verdict.
  - **`goal`:** a B17-0 ghost expression over the program's own names:
    - a `BOUNDS`, `OVERFLOW` or `DIV` goal is written out, as `(and (<= 0 i) (< i (len a)))` or `(in_i64 (+ x 1))`;
    - a `PRE` goal is the callee's `requires` at the call's arguments, unless a binder in it would capture an argument's name;
    - a `TERM` goal is `(<= 0 D)` for a loop's measure D, or a recursive call's measure at its arguments below the caller's. The drop across a pass is written `(decreases D)`, the one goal that isn't a B17-0 expression, since B17-0 can't name a value from before the pass;
    - any other goal is the clause it checks, as written.
  - **`counterexample`:** values of every parameter of the goal's item. One the goal doesn't mention takes 0, `false` or the empty sequence, since any value will do. A sequence is a list, or `{len, prefix}` beyond 8 elements.
    - It's offered for failed and unknown goals, found by solving the goal's query with only the prelude axioms its own part mentions.
    - `reproduced` says whether a checked run of the def on those values fails too (D57). It's `null` when no run is possible, as for a goal of a spec.
  - **`context`:** the goal's item and each item it refers to, as `kind name`.
  - **`repairs`:** empty until interface 2's typed edits exist (WP2).
  - **`dependents`:** the later goals of the same item and part whose assumptions include it, since §9 assumes each goal once generated.
  - **`budget_used`:** its resource units across every seed (D63).
- **Why:**
  - **Representations:** the design spec names the fields but not how each is written. These are the ones B17-0 can fill today.
  - **Goals in B17-0 terms:** an agent writes B17-0, not SMT-LIB, and the program's own names let it find the spot.
  - **Counterexamples:** the full prelude's quantifiers keep Z3 from ever answering `sat`, so a failing goal had none to show. That was an open question in the roadmap.
    - Solving against only the axioms a goal mentions finds a model for every one of the suite's 9 proof rejects.
    - The interpreter reproduces 8 of them, and flags the ninth as not reproduced.
    - A model from fewer axioms can be spurious, so it's reported with that check, never trusted alone. The goal's verdict still comes from the full query (D63).
  - **Dependents:** they show which failure to fix first, as the design spec asks.
- **Touches:** D23; D56; D57; D63; interface 3; WP2; WP6; `docs/b17-0.md` §9.

## D94 · Interface 8 version 0.1: the five queries · Accepted
- **Date:** 2026-10-28
- **Decision:** `b17c/agent.py` answers each query with one JSON document. When a query can't run, it exits 2 with `{"error": ...}`.
  - **`obligations FILE NAME`:** every goal of the item, with its node, family, goal, verdict, whether it came from the cache, and its budget.
  - **A query on a file that doesn't parse** is refused, like any query that can't run.
  - **`explain CODE`:** the code's row in `docs/b17-0.md` §9, the list items that state its rule with the code, and the suite's labelled program for it.
  - **`impact FILE CHANGED`:** CHANGED's items replace FILE's of the same kind and name, and the module is verified again.
    - It reports each goal that was proved before and isn't now: first the callers', then the changed items' own. Goals are matched by node path without positions, so moving an item isn't a change (D56).
    - If the change fails tier 0, it reports those errors instead.
  - **`search FILE QUERY`:** QUERY holds one spec, and the candidates are FILE's specs with the same parameter and result types in order.
    - For each candidate, a probe implements the query spec by calling the candidate, and is verified. The probe gets a name none of FILE's items has. A query whose parameter or result names are FILE's items is refused (D41).
    - Its `PRE` goal is that the query's `requires` imply the candidate's. Its `POST` goals are that the candidate's `ensures` imply the query's. Tier 0 checks that the candidate's effects fit the query's.
    - A candidate guarantees the query when every goal of the probe, its spec's included, is proved, or when D45 finds it identical. The others come with the goals or codes that failed.
  - **`simulate FILE NAME ARG...`:** a checked run in the interpreter (D57), with interface 10's outcome as JSON fields, its trace, its unchecked clauses and its text form (D56).
- **Why:**
  - **Search by guarantee is a proof:** a def that only calls the candidate verifies exactly when the candidate meets the query's contract. The verifier already decides that, so search needs no logic of its own.
  - **Impact by re-verification:** the proof cache keys each goal by what it depends on (D63), so only the goals the change touches are solved again.
  - **Examples from the suite:** every code already has a labelled program, which WP3 and WP5 check. WP8's manual can reuse them.
- **Touches:** D45; D56; D57; D63; interface 8; WP6; WP8; `suite/`.

## D95 · How B17-0 lowers to safe Rust · Accepted (extended by D110)
- **Date:** 2026-10-28
- **Decision:** WP7's backend, `b17c/rust.py`, turns each module that passes tier 0 into one Rust crate.
  - **Safety:** the crate carries `#![forbid(unsafe_code)]` and holds no unsafe code (D18).
  - **Erasure:** ghost-fns, lemmas, contracts, invariants, measures and ghost statements are left out, and so are lemma calls, whose arguments never run. The crate runs §8 as the interpreter does with checking off (D57).
  - **Types:** `bool` and `i64` stay themselves, `(vec T)` becomes `Vec<T>` and `(ref (slice T))` becomes `&[T]`. A def becomes a function with its spec's parameters, returning one result as itself and several as a tuple. `(borrow v)` becomes `&v`. Every expression's type is the one WP3's checker gives it (`check.types`), so an element type that a `(vec-new)` leaves open is D70's: its destination's, or `i64`.
  - **Runtime goals:** each of §9's runtime goals is checked where §8 checks it, at every verification level (D80):
    - `+`, `-`, `*` and `neg` use Rust's checked operations;
    - `/` and `%` check for a zero divisor, then for `MIN` by `-1`, and truncate as Rust does (D37);
    - `idx`, `set-idx` and `seq-build` check their index or length.

    A failed check stops the run with the interpreter's `err` outcome: the same reason, node and detail (D56). Rust's own bounds checks stay too (D18).
  - **Evaluation order:** the interpreter's.
    - Operands are evaluated left to right, and `and`, `or` and `=>` short-circuit.
    - `set-idx` evaluates its index, then its value, and then checks the index.
    - `set-idx` and `push` are method calls, so their operands may read the vector they change, as B17-0 allows. Rust's two-phase borrows accept that.
    - `seq-build` computes its elements in order, growing its vector as it goes, so an element's `err` comes before any allocation the length implies.
  - **Names:** a B17-0 name stays as it is in Rust unless Rust reserves it. Then it becomes a raw identifier, such as `r#match`, or `_crate`, `_self` or `_super` for the three that Rust can't write raw. B17-0 names never start with `_`, so these can't clash. Defs live in a module of their own and the crate's helpers in another, so a def may be named `main`, `rt` or `dispatch`.
  - **Literals:** a comparison of two literals gives the first the type `i64`, since Rust would make both `i32`.
  - **Unreachable code:** statements after one that never continues normally (§7's ⊥) are left out. None of them can run, and rustc rejects some of them, such as a use of a vector a `return` moved, which D77 allows.
  - **Lints:** the crate allows the lints valid programs trigger:
    - a helper the module doesn't use, a local or an assigned value it never reads, and a `let-mut` it never sets;
    - `(while true ...)`, and recursion that only a proof bounds;
    - a comparison with an `i64` limit, and a name with two underscores in a row.

    Any other warning is a backend bug, so the self-check builds with warnings denied.
- **Why:**
  - **Every goal at its node:** an unverified program fails where the verifier's goal would fail, with the outcome the interpreter gives. A differential test can then compare whole outcomes, and not only whether a run failed.
  - **WP3's types:** one typing, so the backend can't disagree with tier 0 about an open element type.
  - **Names:** B17-0's grammar admits 43 of Rust's 51 keywords and reserved words as names, such as `type`, `match`, `loop` and `self`. A single `type` parameter would otherwise break a build.
  - **Unreachable code:** D77 makes it legal, and rustc rejects some of it.
  - **The lints:** a fuzz run found `unused_comparisons` on a valid program. Going through rustc's warn-by-default list then found `non_snake_case` too.
- **Touches:** D18; D36; D37; D56; D57; D70; D77; D80; WP7; `docs/b17-0.md` §5, §7, §8.

## D96 · The emitted binary prints what the interpreter prints · Accepted
- **Date:** 2026-10-28
- **Decision:**
  - **Running:** the crate's `main` runs one def. `BINARY NAME ARG...` takes each argument as a canonical B17-0 value of its parameter's type: a decimal integer, `true` or `false`, or a `(seq-lit ...)` of them, with only B17-0's four whitespace characters around it (D48). It prints the run's trace and outcome in interface 10's text form (D56), as `interp.py` does, and exits as `interp.py` does: 0 on `ok`, 1 on `panic` or `err`, and 2 when the run can't start, such as for an unknown def, an argument that isn't UTF-8, or one that isn't a value of its parameter's type.
  - **Batch:** `BINARY --batch` reads one `NAME ARG...` per line of input and prints each run's lines in turn, with a run that can't start as a `refused: why` line.
  - **Stack:** runs get a thread whose stack is 1 GiB, reserved rather than used, which is room for D59's 1,000 nested calls at up to 1 MiB a frame. A run that recurses past what its stack holds aborts, as allocation failure does (§6).
  - **Stopping:** a B17-0 `panic` and every `err` stop the run by unwinding, as safe Rust stops on a failed check (D80), and `main` prints the outcome. Any other Rust panic would be a backend bug: `main` prints `internal error` and exits 3.
  - **Building:** a call to a spec with no def can't be built, so `emit()` refuses the module, unless the call is in code that can't run, which is left out (D95). The interpreter refuses such a run only when it reaches the call (D56). A spec with no def that no def calls is fine.
  - **What the binary doesn't show:** checking (D57) and `limit` (D59). It runs §8 with ghost code erased, and has no fuel or depth limit of its own.
  - **`rust.py --run FILE NAME ARG...`** builds the binary once per source and toolchain under `.b17c/rust/`, which git ignores, evaluates each ARG as `interp.py` does, and runs it.
  - **Interface 10** doesn't change: the binary is a second producer of its text form.
- **Why:**
  - **The same text:** a Rust binary shows its prints and how it ended (D56). Printing the interpreter's text makes WP7's differential test a comparison of strings, down to the node and the detail. WP11's differential and performance rewards run the same binary (D21).
  - **Batch mode:** the self-check's runs, thousands of them, each take a process otherwise.
  - **The stack:** a main thread's 8 MiB overflowed at depth 999 through a frame of 450 vectors, a run the interpreter finishes. A frame's size depends on the def, so no stack fits every def at every depth. 1 GiB allows frames about a hundred times that one.
  - **Refusing at build time:** a binary can't call a function that doesn't exist. A stub that refused at run time would let a module build that can't run its own calls.
- **Touches:** D21; D29; D48; D56; D57; D59; D80; WP7; WP11; interface 10.

## D97 · What WP7's differential tests compare, and the pinned toolchain · Accepted (extended by D111)
- **Date:** 2026-10-28
- **Decision:**
  - **What's compared:** for every run, the interpreter's text, with checking off, and the binary's must be equal line for line: each `print`, then the outcome with its reason, node and detail. A run the interpreter can't finish in 20,000 steps is skipped, since a binary has no `limit` to show (D59).
  - **Programs and inputs,** in `b17c/test_rust.py`:
    - the 29 suite programs that pass tier 0, with 150 sampled inputs per def;
    - a module of corner cases, each with the text both must print: every runtime goal's failure, evaluation order, prints across calls, names Rust reserves, open element types, unreachable code and refused arguments;
    - 120 generated defs, from random programs that pass tier 0 by construction and use every runtime statement and expression, with 25 inputs per def.

    Inputs are small integers, `i64`'s edges and random `i64`s, and vectors of up to 8 elements, often sorted. They needn't satisfy `requires`: outside it, with checking off, runs reach the `err` paths.
  - **Builds:** every crate is compiled with warnings denied (D95).
  - **The toolchain:** rustc 1.99.1, edition 2021, with `-O` and `-C overflow-checks=on`, so that unchecked arithmetic in the runtime itself would panic rather than wrap. A build compiles and links under fixed names in a temporary directory, so the same source and toolchain give the same binary. CI installs 1.99.1.
  - **The report:** `rust.py -o BINARY --report JSON` adds a `backend` object to the module's trusted base report (D25). It records rustc's version line, commit and LLVM version, the target triple, the flags, and the SHA-256 of the emitted source and of the binary. It refuses a report written for a different input, before building. `verify.py --report` writes a whole report, so it runs first.
- **Why:**
  - **Whole texts:** comparing only whether a run failed would miss a lowering that fails at the wrong node, or with the wrong value.
  - **Skipping `limit`:** with checking off nothing bounds a loop, and the interpreter's fuel has no counterpart in Rust.
  - **Generated programs** reach combinations the suite and the corner cases don't.
  - **Pinning:** D23 pins the solver for the same reason. A newer rustc can add lints or change code generation, and the report must name the toolchain a binary came from (D25).
- **Touches:** D18; D23; D25; D59; WP7; `.github/workflows/check.yml`.

## D98 · M3's B17-0 track in the harness · Accepted
- **Date:** 2026-10-28
- **Decision:** `gym/harness.py` gains a B17-0 track. It runs the same CLIs, isolation, samples and round limit as the Dafny track (WP17), so only the language differs.
  - **Tasks:** the 20 seed tasks, from `suite/accept/`. Each poses:
    - the module's header;
    - its one spec;
    - the ghost-fns that spec refers to, transitively.

    Its def, and any lemma or ghost-fn only a proof uses, are left out. `isqrt`'s lemma is the one such item today. The Dafny seed tasks already take the same preconditions (D42).
  - **The prompt:** `docs/manual.md` in full, then the task, then the rules:
    - write the def for the spec, with any lemmas, ghost-fns, and spec-and-def pairs for helpers;
    - don't restate the task's items;
    - reply in one ```lisp block.
  - **Verified:** the task's items and the agent's, in one module, pass tier 0, and every goal is proved under the canonical seed and 10 shuffled seeds (D23).
    - Redeclaring a task item is `E-TYPE-002`, so the frozen spec can't be weakened.
    - B17-0 has no `assume` or `admit`, so nothing needs banning.
  - **Feedback:** between rounds, the agent gets `agent.py check`'s JSON (D93), truncated as Dafny's output is.
  - **Recorded:** as for Dafny: the verdict, rounds, tokens and time per attempt, in the same `attempts.jsonl`, with the language as a field.
  - **Running it** spends the agents' subscriptions, so the owner starts each run.
- **Why:**
  - **The comparison M3 needs:** the same tasks, CLIs, round limit and recording as the Dafny baselines (D28, D32). A difference in pass rate, rounds or tokens is then the language's.
  - **The manual in context:** it tests D8, that agents learn a new language from its manual in context.
  - **Structured feedback:** it's part of what Babel-17 offers agents. Dafny's track gives Dafny's raw output, which is what Dafny offers.
  - **The seed tasks first:** the suite already ports them, and they verify. The AlgoVeri ports wait for B17-1 (D65).
- **Touches:** D8; D13; D23; D28; D32; D42; D65; D93; WP10; WP17; M3; `gym/harness.py`.

## D99 · Universal introduction: a lemma applied at every value · Accepted
- **Date:** 2026-10-28
- **Decision:** B17-1 gains a ghost statement, `(forall ((x T) ...) (call L e*))`. It applies the lemma L at every value of its binders. Afterwards the verifier assumes ∀x. ⟦L's requires⟧ ⇒ ⟦L's ensures⟧, with the arguments e substituted.
  - **Binders:** each has an exact type (D90) and is scoped to the call. Names follow §2's binder rules.
  - **Goals:** only the arguments' own. Each argument is checked in ghost context with the binders in scope, and its goals, such as an `idx`'s bounds, become ⟦∀x. goal⟧. L's `requires` becomes the antecedent instead of a goal, so a proof passes the binders themselves and lets L's `requires` guard them: `(forall ((i int)) (call l s i))`, not `(call l (idx s i))`.
  - **The fact:** L's `requires` and `ensures` clauses are each conjoined, and the arguments substituted without capture. Like a lemma call's `ensures`, the fact holds from the statement on, along that path.
  - **Where it may appear:** wherever a lemma call may, in def and lemma bodies. Like a lemma call, it's ghost, has no effects and moves nothing.
  - **Recursion:** a use inside L's own body carries the measure goal for every binder value, ⟦∀x. requires ⇒ 0 ≤ callee measure < caller measure⟧, under the path's assumptions, so induction stays sound.
  - **Syntax and hashing:** `forall` is already reserved, so no word is added. The binders are numbered with D45's other binders, in the same walk (D92).
- **Why:**
  - **A missing kind of proof.** A lemma proves a fact about its parameters. A ∀ in an `ensures`, invariant or `assert` is proved by the solver alone, since nothing applies a lemma at a value a quantifier binds. A ghost `while` reaches only a bounded range of integers.
  - **The evidence:** writing B17-1's accept suite found it. All 24 verified Dafny solutions of `bfs`, `coin_change`, `kruskal`, `lca` and `trie_insert` in the AlgoVeri runs use Dafny's `forall` statement, 3 to 53 times each, from all four agents. In four of the five tasks some range over an unbounded type: every path, every valid change, every common ancestor and every key. `kruskal`'s range over vertex indices and weights, which a ghost `while` could reach at much greater length.
  - **The smallest form that covers it:** one lemma call, rather than Dafny's statement with its own `ensures` and body. A body can always become a lemma, and a lemma already scopes its goals.
  - **Sound by construction:** L is proved once, for every argument that meets its `requires`, and exact binders range only over real values of their types (D90).
- **Alternatives:**
  - **Dafny's form, with a body:** more to specify, and its goals need a scope of their own, which is what a lemma already is.
  - **Nothing:** agents would have to phrase each such proof so that the solver instantiates a quantified `ensures` unaided. In the Dafny proofs above, no agent managed without the statement.
  - **An "arbitrary x" block,** as in Lean's `intro`: the same power, with a new kind of scope.
- **Touches:** D80; D90; D91; D92; B17-1 §2, §7 and §9; WP3; WP5; WP8; WP10.

## D100 · Existential elimination: naming a witness · Accepted
- **Date:** 2026-10-28
- **Decision:** B17-1 gains a ghost statement, `(obtain ((x T) ...) e)`. Its goal is ⟦∃x. e⟧. It then binds each x as an immutable ghost local, with e assumed.
  - **Binders:** each has an exact type (D90). They are locals: unique within the item (D41), and visible to the end of the enclosing block, loop body or branch.
  - **Goals:** e's own goals, under the binders, then ∃x. e, in the `E-PROOF-ASSERT` family.
  - **Where it may appear:** in def and lemma bodies, wherever a ghost statement may. A ghost local never flows into a runtime value (`E-GHOST-001`), so a witness can't change what the program computes.
  - **The word:** `obtain` joins the reserved words (D51). The binders are numbered with D45's other binders (D92).
- **Why:**
  - **A missing kind of proof.** The solver can use an ∃ that a `requires` or a callee's `ensures` gives, but a proof can't name its witness, to assert something about it or pass it to a lemma. A lemma can't return values (`E-GHOST-003`), so it can't hand one back either.
  - **The evidence:**
    - **How often:** Dafny's `:|` names a witness in 102 of the 327 verified AlgoVeri solutions in the runs, across 32 of the 64 tasks.
    - **In B17-1's suite:** every verified solution of `segmenttree_query`, `bfs` and `kruskal` uses it.
    - **What `segmenttree_query` needs it for:** the parent's witness is a child's, and the proof has to name it to relate the two views. Codex's review of the suite found that step missing.
  - **Today's workaround:** compute the witness at runtime and return it. That costs a result, and works only when the witness is computable.
- **Alternatives:**
  - **A `choose` expression,** Hilbert's ε: its goal would arise wherever it appears, and two uses with the same body would have to denote the same value. A statement scopes the witness to one place.
  - **Lemmas with results:** every call would bind them, and lemmas would stop being pure facts.
- **Touches:** D41; D51; D90; D92; D99; B17-1 §2, §7 and §9; WP3; WP5; WP8; WP10.

## D101 · How the toolchain picks a subset · Accepted
- **Date:** 2026-10-28
- **Decision:** each `b17c` entry point takes the subset it reads, 0 or 1: `subset=` in Python, and `--subset N` on the command line.
  - **Subset 0** is B17-0 exactly as frozen: its reserved words, grammar, types and labels. **Subset 1** is B17-1's.
  - **The default** is 0 until B17-1 freezes. It then becomes 1, the newest frozen subset, and so on for later subsets. Whatever relies on B17-0 then names subset 0: M3's B17-0 track, the manual's checks and B17-0's tests.
  - **Later,** the manifest (interface 4) declares a module's subset, and the tools read it from there.
  - **In order:** the parser takes it first. The hasher, checker, interpreter, verifier, backend and agent protocol take it as each extends to B17-1.
- **Why:**
  - **B17-1 isn't a superset of B17-0 as written.**
    - **Reserved words:** B17-1 reserves 20 words that a B17-0 program may use as names, such as `map` and `field`.
    - **Types:** it accepts types that B17-0 rejects. One is `(seq (seq int))`, for which B17-0's frozen tests and the manual expect `E-TYPE-001`.
  - **B17-0's outcomes must not change:** B17-0 is frozen (D44), and M3's B17-0 track measures agents writing B17-0.
  - **A draft's rules shouldn't change what the tools do by default.**
- **Alternatives:**
  - **Always the newest subset:** that breaks B17-0's frozen tests and the manual, and changes M3's track mid-experiment.
  - **The subset in the module text:** that changes B17-0's frozen grammar and every hash.
  - **A toolchain per subset:** that duplicates every tool.
- **Touches:** D44; D65; D98; interface 4; WP2; WP3; WP5; WP7; WP8; WP15; M3.

## D102 · Membership in a finite collection bounds a quantifier's binder · Accepted (refines D58)
- **Date:** 2026-10-29
- **Decision:** D58 gains one kind of conjunct that can't fail and gives bounds, in both subsets.
  - **The conjunct:** `(contains E x)`, where x is an unassigned binder, E mentions no unassigned binder, and E is defined here, with a finite set, a sequence or a map as its value.
  - **The bound:** x takes only E's members, or a map's keys, intersected across such conjuncts. For an `int` binder, the comparisons' bounds apply too. The binder may have any type but `bool`, which ranges over both its values already (D58), so this is how a quantifier over a type B17-1 adds is evaluated.
  - **What doesn't bound:** a set built by `iset-of` is kept as its predicate (`docs/b17-1.md` §8), and evaluating its membership might fail, so a conjunct testing membership in one ends the list, as any conjunct that might fail does.
  - **No members:** an empty E makes the guard hold nowhere, whichever binder it names, as an empty range from comparisons does (D58).
  - **Evaluation:** members are taken in a fixed order, the value order the interpreter prints sets in, so a run stops at the same point everywhere.
- **Why:**
  - **The suite:** B17-1's specs say what a tree or trie holds as a set, and quantify over its members: `bst_insert`'s `is_bst` reads `(forall ((x int)) (=> (contains (view l) x) (< x v)))`. D58 reads no range off that guard, so `is_bst` was unknown on every tree but a leaf.
    - Every `insert` and `search` precondition went unchecked.
    - An input that isn't a search tree then ran, and its failure was charged to the `def`'s `ensures` instead of the input.
    - With D102, every clause of `bst_insert` and `bst_search` is evaluated on the suite's inputs, and so is `trie_insert`'s range for its key's bytes.
  - **Sound by D58's argument:** the conjunct can't fail once E is defined and finite, and a point outside E makes it false. So skipping the point changes nothing and hides nothing.
  - **L1 needs it:** D80 counts a goal as tested only when checking evaluates it, so without D102 no property test could cover a set-based spec.
- **Alternatives:**
  - **B17-1 only:** B17-0's spec text says nothing about checking, which D57 and D58 define for the tools. No B17-0 suite program has such a guard, so its outcomes are unchanged, and an agent writing B17-0 gets the same precision.
  - **Enumerating whole types:** booleans and tuples of them are finite, but data and sequence types aren't, and a bound read off the guard covers what the suite needs.
- **Touches:** D57; D58; D80; WP15; `docs/b17-1.md` §8.

## D103 · How the verifier encodes B17-1, refining D89 · Accepted (refines D61 and D89)
- **Date:** 2026-10-29
- **Decision:** WP5 implements interface 11 v0.2 as D89 says, with four changes.
  - **A datatype per instance:** each instance of a data type, such as `(option int)` or `(option node)`, is a monomorphic SMT datatype, not one parametric datatype per data item. Instances are keyed by their sorts, so `i64` is `int` and vectors and slices are sequences. An instance is declared together with the instances it refers to and that refer back to it, as `node` and `(option node)` do. Tuples stay one parametric datatype per arity.
  - **Set operations are lambdas:** `union`, `inter` and `diff` of sets are lambdas over their arrays, not array maps. Maps' `union` is a lambda too.
  - **`match` binders are selectors:** in each arm the scrutinee passes its constructor's test, and the binders are its selectors. By the datatype axioms, the scrutinee then equals its constructor applied to them, which is what D89 asks for. Selectors also work in ghost-fn definitions, which are expressions, with no place for fresh constants.
  - **Equality of values holding sequences:** a tuple or data value that holds a sequence is compared by SMT equality, not by a predicate per sort. A sequence itself is still compared by length and elements, and so are the sequences inside it.
- **Three rules D89 left unsaid,** the first two in both subsets:
  - **Recursive ghost-fns:** a recursive ghost-fn's defining equation holds only for arguments of its parameter types that satisfy its `requires`. That is exactly where its measure was proved. An SMT integer or field outside `i64` isn't a value of its type, and the recursion needn't descend there.
  - **`seq-build` under binders:** a `seq-build` under a quantifier's or statement's binders, or in a ghost-fn's body, is a function of those variables, not one constant. Its length and elements are facts at every point where its length is at least 0.
  - **A validity predicate per data type:** it says a value's `i64`s and vector lengths fit, through tuples and sequences too. Parameters, call results and `match` binders assume it, as B17-0's `i64` values assume they fit.
- **Unchanged from D89:**
  - sequences per element sort, with §9's facts;
  - multisets as count arrays, sets as arrays to `Bool`, and maps as arrays to `option`;
  - `rank` as a function per data sort with its axioms;
  - `FIELD` guarding every selector.
- **Names:** B17-1's sorts, constructors, selectors and functions get generated names, such as `d!3`, `c!4`, `f!5`, `s!6`, `len!6` and `rank!7`. Interface 11's canonical form renames them, so renaming a data type, constructor or field changes no query and keeps every proof in the cache (D63). A query declares only the sorts, datatypes, sequence facts and `rank` axioms its names use, so an edit elsewhere in the module leaves it unchanged.
- **Why:**
  - **Per instance:** a type parameter under a sequence, as in `(data stack (a) (stack (items (vec a))))`, would need sequence functions over a parametric sort. SMT-LIB 2.6 can't declare those, so D89's parametric datatypes can't hold such a field. With one datatype per instance, every field has a concrete sort.
  - **Lambdas:** `bst_insert`'s `is_bst` postcondition proved under 6 of 11 seeds with array maps, and under all 11 with lambdas, using about 2% of the resource units. Z3 reduces a lambda at each `select`.
  - **The first two rules are soundness fixes.** Without them, the verifier proved `false` in B17-0 as well as B17-1. A ghost-fn `bad` on an `i64` with `(if (> x 9223372036854775807) (not (bad x)) true)` proved `bad(x) = not bad(x)`. An `exists` over a quantified `seq-build` length proved, because the sequence was one constant whatever the binder. No B17-0 suite query changes.
  - **SMT equality:** it is sound. Program values that are equal are the same SMT value in the intended model, so assuming SMT equality assumes nothing false. It is incomplete: it can't prove two values equal when their sequences are different terms with the same elements. No suite program compares such values, and the predicate D89 describes can be added when a proof needs it.
- **Touches:** D61; D63; D89; D92; WP5; interface 11; `docs/b17-1.md` §9.

## D104 · A data type's recursion is regular · Accepted (refines D83)
- **Date:** 2026-10-29
- **Decision:** a data type uses itself only as itself applied to its own parameters, in their order. Any other use is `E-TYPE-001`. So `(data nest (a) (stop) (more (next (nest (option a)))))` is rejected, and `(data tree (a) (leaf) (node (val a) (kids (vec (tree a)))))` is not. This adds to D83's well-formed types (`docs/b17-1.md` §3).
- **Why:**
  - **Infinitely many instances:** a `nest i64` holds a `nest (option i64)`, which holds a `nest (option (option i64))`, and so on.
  - **The verifier:** D103's datatype per instance never finishes declaring them, and SMT-LIB's parametric datatypes reject such a type too. Codex found the verifier recursing without end on one.
  - **The backend:** Rust compiles generics one instance at a time, so the emitted crate would meet the same infinite expansion.
  - **Little use in B17-1:** functions take no type parameters, so a function over `nest i64` couldn't recurse into its field anyway.
  - **Distinct types already can't cycle:** E-TERM-002 rules out two data items containing each other. With D104, a module's instances are finite.
- **Alternatives:** a verifier error for such a module. That would be a type the checker accepts but no other tool can handle.
- **Touches:** D83; D103; WP3; WP5; WP7; `docs/b17-1.md` §3 and §13; `suite/b17-1/`.

## D110 · How B17-1 lowers to safe Rust · Accepted (extends D95)
- **Date:** 2026-10-29
- **Decision:** with subset 1 (D101), `b17c/rust.py` turns each B17-1 module that passes tier 0 into one crate, as D95 does for B17-0. Without a subset, its output is the same, byte for byte, as before B17-1.
  - **Data types:** each data type the program uses becomes an enum in a module of its own, `data`, with a variant per constructor and its fields in order. Names Rust reserves become raw identifiers, as D95 says for values.
  - **Type parameters:** a parameter is a Rust type parameter only when a value can hold a value of its type, through fields, vectors, tuples and other data types. Tier 0 already computes that set for D90. The others are dropped, so `(ph int)` is the Rust type `ph`. Since D104 makes recursion regular, a module uses finitely many instances, and each is a Rust type.
  - **Boxed fields:** a field whose type mentions its own data type other than inside a vector is a `Box` (D86). A `match` arm's binder for one takes the value out of its box, since the binder owns it (§5 rule 4).
  - **Copying:** a data type that moves only through its arguments, or never, derives `Clone` and `Copy`. Rust bounds each parameter by `Copy`, so `(option i64)` is copied and `(option tree)` moves, as §5 rule 1 says. A type that moves whatever its arguments, being recursive or holding a vector, derives neither. Tuples are Rust tuples, of any arity.
  - **Reading:** `field` calls a method of the data type that matches the value's constructor, and stops the run with `err FIELD` and the interpreter's detail where the constructor lacks the field. `idx`, `field` and `get` read a moving value through a reference, so it never leaves its place (§5 rule 3), and copy a copied one. `is` is `matches!`.
  - **Constructors** name their type arguments, as tier 0 inferred them, so `(none)` with no destination is `option::<i64>::none` (§4). Every integer literal is typed `i64`, since a tuple or a type argument may give it no type of its own.
  - **Updating through a place:** `set-idx`, `push` and `replace` first evaluate the place's indices in source order, then the statement's index and value, into temporaries. They then walk the place from its root as a chain of `&mut` references, checking each `idx` and `field` on the way down, as the interpreter does, and change the part where it is. `replace` is `std::mem::replace`. A place that is a variable keeps D95's form.
  - **`match`** becomes Rust's `match`, as a statement or an expression.
  - **The binary's values:** an argument is read as a term of interface 10's text form, so `(some 3)`, `(tuple 1 false)` and nested values are values. Results print as the interpreter prints them. Each data type, each tuple arity the crate uses, and `Box` read and print their own values.
  - **Lints:** B17-1's types and constructors are lowercase, so `non_camel_case_types` joins D95's list.
- **Why:**
  - **Enums:** D79 says data types become Rust enums. A module of their own keeps type names apart from value names, as D82 does, and from the names Rust and the runtime use, such as `str`, `std` and `rt`, which B17-1 allows as type names.
  - **Only the parameters a value holds:** Rust rejects a parameter that no field uses (E0392). Dropping it needs no marker field, which every `match` would then have to skip.
  - **Copying by derive:** a derive's `Copy` bound on each parameter is §5 rule 1 applied to each instance.
  - **Places through references:** they update in place, as §8 says Rust does. The temporaries keep the interpreter's order, so an index's or a value's own `err` comes before any check on the place's way down.
  - **One method per field:** the data type is the one place that knows which constructors have a field, and it gives the interpreter's message.
  - **Literals:** without a type, `(tuple 1 9223372036854775807)` would be a tuple of `i32`, which rustc rejects.
- **Touches:** D18; D79; D82; D83; D84; D86; D90; D95; D96; D101; D104; WP7; `docs/b17-1.md` §3, §5, §6, §8.

## D111 · What WP7's differential tests compare for B17-1 · Accepted (extends D97)
- **Date:** 2026-10-29
- **Decision:** `b17c/test_rust.py` checks B17-1 under subset 1 as D97 checks B17-0, comparing the interpreter's text with checking off and the binary's, line for line. B17-0's part is unchanged.
  - **The suite:** the 15 programs of `suite/b17-1/` that pass tier 0, which are the 10 accept programs and the 5 proof rejects.
    - **Their own inputs:** each accept program runs on `test_interp.py`'s inputs, its spec's examples and the inputs outside its `requires`.
    - **The proof rejects:** two have defs that show their fault, and run into it: `err BOUNDS` from `replace` and `err FIELD`.
    - **Random inputs:** 40 per def.
  - **Corners:** a module of cases, each with the text both must print:
    - names Rust reserves or uses, as types, constructors and fields;
    - parameters no value holds, and recursion through `option`, which is boxed;
    - `FIELD` and `BOUNDS` in expressions and through places, and the order of a place update's evaluation and checks;
    - `replace`, `match`, tuples, open type arguments, and arguments that must be refused;
    - a list a million long, which only the binary runs, since the interpreter's steps can't reach it.
  - **Generated programs:** 96 defs, from random B17-1 programs that pass tier 0 by construction, with 25 inputs per def. Their data types are copied, recursive and boxed, holding vectors, and generic, and their bodies use places, `replace`, `match`, constructors, tuples, `seq-build` of data and calls.
  - **Inputs** are drawn for each type, with data values a few levels deep.
  - **Refusals:** `emit()` refuses every tier 0 reject of `suite/b17-1/`, D104's recursion at a growing instance among them.
  - **The command line:** `rust.py --subset 1 --run` prints what `interp.py --subset 1` prints, with the same exit code.
- **Why:** the same as D97's. Places and data values add failures at new nodes, `FIELD` among them, and a new order of evaluation, which only whole texts compare.
- **Touches:** D97; D101; D104; D110; WP7; `.github/workflows/check.yml`.

## D105 · Literals of sequences compare by elements, and other refinements of D103 · Proposed (refines D103)
- **Date:** 2026-10-29
- **Decision:** three refinements of D103's encoding, each found while finishing the suite's proofs.
  - **Literals of sequences:** a set literal whose elements are sequences is a lambda. Its members are the sequences equal to one of its elements, compared by length and elements as `==` compares sequences. A map literal or `update` with sequence keys matches a key the same way. Literals of other element types keep D103's stores.
  - **A constant `seq-build`:** when a `seq-build`'s body doesn't use its index, every element is the body. So its multiset is the body counted `n` times, and the verifier says so.
  - **Validity covers `i64`s only:** D103's validity predicate says a data value's `i64`s fit, through tuples and sequences, and no longer says its vectors' lengths fit. A data type with no `i64` inside, such as a trie's `node`, has none, and its recursive ghost-fns' equations aren't guarded by one. A vector parameter still has its own length fact, as in B17-0.
- **Why:**
  - **Literals:** a store keyed by an SMT sequence term holds that term, but sequences are equal by their elements. So `(iset-lit (drop key 0))` and `(iset-lit key)` couldn't be proved equal, and `trie_insert`'s view of its keys couldn't be proved at all. With members compared by elements, both prove.
  - **Constant `seq-build`:** `bfs` counts the `-1`s in a vector built by `(seq-build n (fn (j) -1))`. §9's multiset facts cover only empty, one-element and concatenated sequences, so the count had no value. With this fact, its invariant holds on entry.
  - **Validity:** guarding a recursive ghost-fn's equation by a vector-length fact made `trie_insert`'s `well_formed` unprovable on a newly built node, since showing a node valid meant proving a quantified fact about its vector. The guard has to match only the facts the ghost-fn's termination proof used. Those now leave out lengths inside data values, so soundness is unchanged.
- **Unchanged:** B17-0's queries. All 511 of its suite's queries are byte-identical, since B17-0 has no sets, maps or data values, and its one `seq-build` uses its index.
- **Touches:** D61; D89; D103; WP5; `docs/b17-1.md` §9; `suite/b17-1/accept/`.
