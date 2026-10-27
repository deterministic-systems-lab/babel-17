# Babel-17 decision log

Every design decision, in order. The log is append-only. To change a decision, add a new entry that supersedes it. Never edit an old entry except its status.

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

## D10 · One static binary or WASM build, no other compiler · Proposed (scoped by D19)
- **Date:** 2026-10-26 (spec v0.1)
- **Decision:** The toolchain installs as one static binary or a WASM build, with no other compiler.
- **Touches:** Standard library and tooling.

## D11 · Phase 1 emits Rust or C · Open (answered by D18)
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

## D15 · This file and ACTIVITY.md are the authoritative logs · Proposed
- **Date:** 2026-10-26
- **Decision:** `DECISIONS.md` is the complete, authoritative decision log. `ACTIVITY.md` is the activity log and also holds the spec's handoff notes. The spec's Decision log section mirrors entries accepted here.
- **Why:** The owner asked for both logs in the repo. Keeping one authoritative copy stops the spec and the repo from drifting apart, and git gives history and review.
- **Touches:** How to use this spec; Decision log.

## D16 · The Lean soundness proof moves after the Phase 2 gate · Proposed
- **Date:** 2026-10-26
- **Decision:** Phase 0's gate becomes three things for B17-0 (D20): written typing rules and semantics, a reference interpreter that executes them (WP15, D28), and an accept/reject suite for the type checker. Mechanizing the semantics in Lean and proving type soundness, which is WP1 as written, moves to after the Phase 2 gate. D3 stands; only its timing changes.
- **Why:** As written, WP1 puts years of research ahead of any evidence, and all five reviewers recommended deferring it. The kernel checks proofs after the fact and never changes what an agent writes, so building it first can't change what the experiments measure.
- **Touches:** Roadmap (Phase 0 gate); WP1; WP2; WP3; D3.

## D17 · b17c generates its own proof goals and sends them to Z3 · Proposed
- **Date:** 2026-10-26
- **Decision:** `b17c` turns programs and contracts into solver queries itself and sends them to Z3, with cvc5 optional later. Babel-17 never translates to Dafny. Dafny serves two other roles:
  - **Baseline:** the comparison language for experiments.
  - **Development oracle:** every seed task also exists in Dafny. A task Dafny proves and `b17c` doesn't is filed as a bug in our encoding.
- **Why:** The diagnostic schema needs four things that can't be recovered from Dafny's output: the goal in normal form, dependent goals, the budget spent per goal, and typed repairs. Owning goal generation also brings three gains:
  - **Simpler encoding:** ownership lets the solver see plain values instead of a modelled heap. Verus reports speedups over Dafny-style encodings this way (from memory; not yet verified).
  - **Stability:** one goal per query with minimal context targets the brittleness the Mariposa study measured.
  - **A path to D6:** generated goals can later be exported to Lean as theorems.

  The cost is roughly two to three times the work of translating to Dafny. Early versions will also be more brittle than Dafny on quantifier-heavy specs.
- **Touches:** Verification model; WP5; WP6; Roadmap (Phase 1, "SMT verification").

## D18 · Phase 1 emits Rust · Proposed (answers D11)
- **Date:** 2026-10-26
- **Decision:** The Phase 1 backend (WP7) emits Rust.
- **Why:** Rust gives three things:
  - **An independent check:** until the kernel exists, Babel-17's ownership checker is new and unverified, and `rustc` re-checks the ownership and type safety of every emitted program on its own. That catches bugs in our checker for free, applying "everything outside the kernel is checked" before there is a kernel.
  - **A direct type mapping:** `&[T]` and `Vec<T>` map straight onto Rust.
  - **WASM:** `wasm32` is a standard target.

  C was the alternative, and `clang` is already installed. It would rest all memory safety on our checker alone, and the emitter would have to avoid C's undefined behaviour, such as signed overflow and strict aliasing. Verus can be added later as a second verifier over the same output if a cross-check is wanted. The cost is a rustup install of about 1 GB, needed only when WP7 starts.
- **Touches:** D11; WP7; WP9; Roadmap (Phase 1 gate).

## D19 · The toolchain is a Python prototype until Phase 3 · Proposed (scopes D10)
- **Date:** 2026-10-26
- **Decision:** `b17c` is written in Python and run with uv through the Phase 2 gate. A Rust rewrite opens Phase 3. Until then:
  - D10 covers `b17c verify` and `b17c check` only.
  - `b17c build` may require `rustc` (D18), and the trusted base report names that toolchain.

  The rewrite is accepted when it reproduces the prototype's canonical bytes, hashes, verdicts and diagnostic codes on the benchmark corpus.
- **Why:** Z3's Python bindings are its most mature, and the gym is Python anyway. Until Phase 3 there is one user on one machine. D10 exists to protect outside users, who don't exist yet, and it can't hold while Phase 1 emits Rust or C.
- **Touches:** D10; WP9; Standard library and tooling (Distribution).

## D20 · The first subset is B17-0 · Proposed
- **Date:** 2026-10-26
- **Decision:** B17-0 contains:
  - **Values:** checked integers, booleans, sequences, shared slices, owned vectors, mutable locals.
  - **Control:** `if`, and `while` with `invariant` and `decreases`.
  - **Contracts:** `requires`, `ensures` and ghost spec functions.
  - **Effects:** a flat set of `alloc`, `panic` and `io`.

  Type parameters are instantiated at integers only, so the worked example runs with `T = int`. The rest of the Type system waits for evidence.
- **Why:** This is enough to express the worked example and the seed tasks, yet small enough to specify, interpret and verify in weeks. Dependent types, linear resources, information-flow labels, cost proofs and concurrency are research-grade, and they don't change what the first experiments measure.
- **Touches:** Type system; WP3; Worked example.

## D21 · WP4 splits in two · Proposed
- **Date:** 2026-10-26
- **Decision:**
  - **WP4a, the spec language:** depends on WP3 and comes before WP5.
  - **WP4b, the spec workbench:** depends on WP4a and WP5, and comes after.
  - WP5 depends on WP4a.
  - The critical path to the Phase 2 gate becomes WP2, WP3, WP4a, WP5, WP8, WP10, WP4b, WP11.
- **Why:** Vacuity checks, witnesses and mutant rejection all run on the verifier, so as written WP4 and WP5 depend on each other. WP8 joins the critical path because under D8 the manual is the agents' only teacher.
- **Touches:** Work packages; Specification layer.

## D22 · Definitions get separate spec and implementation hashes · Proposed
- **Date:** 2026-10-26
- **Decision:**
  - **Hashes:** each definition has a spec hash, covering its signature, contracts, effects and cost, and an implementation hash, covering its body plus its own spec hash.
  - **References:** bodies refer to callees by spec hash.
  - **What's left out:** the definition's own name is excluded from the hash, and local binders are de Bruijn-indexed.
  - **Recursion:** mutually recursive definitions hash as one group, and each member is addressed as (group hash, index).
  - **Node IDs:** a node ID is a stable definition ID assigned at creation plus a child-index path. Labels like `loop0` and abbreviated hashes are for display only.
  - **Proof cache:** the key is the implementation hash plus the spec hashes of its dependencies.
- **Why:** As written, the identity scheme breaks in four ways:
  - one body edit rehashes every transitive caller;
  - recursion makes hashes circular;
  - renaming a definition changes its hash, contradicting "renames never break references";
  - node IDs built from hashes can't survive edits.
- **Touches:** Program representation; Interfaces 1 and 3; Verification model (incremental and cached); D2.

## D23 · What a verdict means · Proposed (refines D7)
- **Date:** 2026-10-26
- **Decision:** A goal passes when it's proven under the canonical seed and under N shuffled seeds. N and the resource budget live in the manifest. The solver binary's hash, its version and every option are pinned and recorded in the trusted base report, and solving is single-threaded.
- **Why:** Z3's resource count is reproducible only with the same binary and options, and shuffling seeds changes solver behaviour. "Same verdict on any machine" therefore needs a pinned solver and a defined verdict.
- **Touches:** Design principles (Determinism); Verification model; D7.

## D24 · Solver-trusted goals are allowed until the kernel exists · Proposed (refines D6)
- **Date:** 2026-10-26
- **Decision:** Until the kernel exists:
  - An L3 module may contain solver-trusted goals, each listed by node ID in the trusted base report.
  - Gym rewards of 0.80 and above count solver-trusted goals as discharged, and the report says so.

  Release builds always reject `admit` and `assume`, whatever the manifest says.
- **Why:** No kernel pipeline today can rebuild proofs over sequences or multisets, and the worked example needs both, so `solver_trusted: 0` can't be reached before the kernel exists. Listing each goal keeps the trust story honest.
- **Touches:** Verification model; Training environment (reward table); Interfaces 4 and 5; D6.

## D25 · The trusted base report lists goals instead of counting them · Proposed
- **Date:** 2026-10-26
- **Decision:** WP5 owns the report, and WP7 adds the backend fields. The report:
  - lists axioms and solver-trusted, admitted and brittle goals by node ID;
  - records the input and lockfile hashes;
  - records the `b17c`, verifier and solver versions, the backend toolchain (D18) and the target triple;
  - gives a verification level per module.
- **Why:** Counts can't tell apart two builds with different admitted goals. The fields come from WP5 and WP4, not WP7. And the example's `x86_64-sysv` doesn't describe an arm64 Mac.
- **Touches:** Interfaces 5; Interop, packages and the trusted base; WP5; WP7.

## D26 · The manifest and lockfile move to Phase 0 · Proposed
- **Date:** 2026-10-26
- **Decision:** WP2 owns the manifest and lockfile schemas. WP13 keeps the registry and spec-diff versioning.
- **Why:** Phase 1 already needs verification levels, `allow_admit`, budgets (D23) and dependency pins, but WP13 is a Phase 3 package.
- **Touches:** Interfaces 4; WP2; WP13; D9.

## D27 · The missing interfaces are added, and all interfaces are versioned · Proposed
- **Date:** 2026-10-26
- **Decision:** Five interfaces are added:

  | Interface | Contents | Owner |
  |---|---|---|
  | 6 | Core terms and certificates | WP1 |
  | 7 | Fact-preserving IR | WP3 |
  | 8 | Lockfile and capability grants | WP2 |
  | 9 | Query protocol | WP6 |
  | 10 | Spec signatures and spec challenges | WP4b |

  Every interface carries a version and a status of Draft or Frozen.
- **Why:** Work packages may only exchange the artifacts listed in Interfaces, but these five pass between packages without being defined. "Start once frozen" can't be checked without a status.
- **Touches:** Interfaces; How to use this spec; Work packages.

## D28 · Unowned work gets owners · Proposed
- **Date:** 2026-10-26
- **Decision:**
  - **WP15, the reference interpreter (Phase 0):** it also serves `simulate`, witness examples and WP7's differential tests.
  - **WP16, the core spec library:** `sorted`, `multiset`, `take`, `last`, and `Ord` with its laws.
  - **Signing** moves into WP4b.
  - **`b17c view` and `b17c prof`** are deferred.
- **Why:** The done-when tests of WP5, WP6 and WP7 depend on this work, and no package owns it.
- **Touches:** Work packages.

## D29 · The worked example is corrected · Proposed
- **Date:** 2026-10-26
- **Decision:** In `merge_sorted`:
  - require `T: Copy`;
  - give `Ord` stated laws (total and transitive) and a pure, terminating comparison;
  - require that `len(a) + len(b)` fits, or declare a `panic` effect;
  - add `capacity(out) == len(a) + len(b)` as a loop invariant;
  - state in the core semantics that `and` and `or` short-circuit;
  - narrow "nothing aliases" to "`out` aliases neither input";
  - drop the vectorization claim.
- **Why:** As written, the example has six problems:
  - **Ownership:** it moves a `T` out of a shared borrow, which the spec's own ownership rules reject.
  - **Order laws:** the else branch and sortedness need laws that `Ord` doesn't state.
  - **Failures:** the header's "failures: None" ignores overflow and allocation failure.
  - **Reallocation:** "push never reallocates" is unproven without the capacity invariant.
  - **Index safety:** it relies on short-circuit evaluation the semantics never states.
  - **Vectorization:** the merge's data-dependent branch blocks it.
- **Touches:** Worked example; Type system; WP4 and WP5 done-when tests.

## D30 · Cost proofs and information-flow labels are deferred · Proposed
- **Date:** 2026-10-26
- **Decision:** Before the Phase 2 gate, `cost` clauses are parsed and measured but not proven. Bounds are stated as counts, such as "at most `len(a) + len(b)` comparisons", and proved with ghost counters where needed. Information-flow labels are deferred.
- **Why:** No existing tool proves big-O bounds for generic imperative code. Noninterference needs relational verification or a proven-sound type system.
- **Touches:** Type system; Specification layer (resource contracts); Worked example (`cost`).

## D31 · The Phase 2 gate also compares against a model trained on Dafny · Proposed
- **Date:** 2026-10-26
- **Decision:** For the Phase 2 gate, the same base model is also trained on Dafny with equal compute. The gym-trained Babel-17 model must beat that model as well as off-the-shelf models.
- **Why:** As drawn, the gate compares a trained model with untrained ones, so a win could come from training alone rather than from the language.
- **Touches:** Roadmap (Phase 2 gate); WP11; Success metrics.

## D32 · Success-metric baselines are re-measured on our own harness · Proposed
- **Date:** 2026-10-26
- **Decision:** The Success metrics baselines are re-measured on our own harness, on the same tasks with current models (D13), rather than quoted from papers.
- **Why:** Reviewers report two problems with the quoted figures, neither verified yet. The vericoding figures (82/44/27%) count a task as solved if any model solved it; the best single model scores about 67.5/30.9/17.9%. And 2026 agentic Dafny results exceed 90% on DafnyBench. Measuring on our own harness settles the question either way.
- **Touches:** Success metrics.
