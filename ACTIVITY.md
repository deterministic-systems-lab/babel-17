# Babel-17 activity log

What happened, when, and the evidence for it. Append new entries at the end.

An entry that hands work on to someone else doubles as the spec's handoff note. It states:
- the WP it advances;
- the interfaces it touched;
- the proofs and tests it added;
- anything it left admitted.

Decisions themselves live in [DECISIONS.md](DECISIONS.md).

## 2026-10-26 · Spec draft v0.1
- **The spec:** the owner wrote *MFL: A Machine-First Language — Design Spec (Draft v0.1)* in Claude Docs, with a copy in Google Docs. The spec stays outside this repo. A local copy lives in `private-docs/`, which is gitignored.
- **Decisions:** the spec recorded D1–D11. D11 was left open in a comment on the Roadmap section.

## 2026-10-26 · Spec review
- **Reviews:** five independent, read-only reviews, each with its own lens:
  - sequencing and the first slice;
  - formal-methods feasibility;
  - internal consistency and interfaces;
  - a contrarian case on whether a new language is needed;
  - a cross-model review by Codex (`gpt-5.6-sol`).
- **Consensus:**
  - The decisive experiment comes too late. As written, the spec's first open question gets answered only after WP1–WP10.
  - WP1 as written, a mechanized soundness proof for the full type system, is multi-year research.
  - WP4 and WP5 depend on each other.
  - D10 can't hold while Phase 1 emits Rust or C.
  - The worked example breaks the spec's own ownership rules.
  - The identity scheme contradicts itself: content hashes change on every edit, but node IDs are meant to survive edits.
- **Split:** the reviewers disagreed on the Phase 1 verifier:
  - Dafny: two reviewers.
  - Verus: one.
  - `b17c` generating its own goals for Z3: one.

  The owner asked whether owning the proof layer could beat Dafny, and the answer is proposed as D17.
- **Outcome:** the findings became proposed decisions D15–D32.
- **Not yet verified:** reviewer-reported figures attributed to vericoding, AlgoVeri, AxDafny, VeruSAGE, lean-smt and the Verus papers.

## 2026-10-26 · Owner decisions
- **Accepted:**
  - The name is Babel-17, with the `.b17` extension and the `b17c` CLI (D12).
  - Experiments run on CLI subscriptions (D13).
  - Benchmarks steer the design rather than gate the language (D14).
- **Requested:** complete decision and activity logs in this repo (D15).
- **Supplied:** the architecture and roadmap diagrams, plus the D11 comment. Text exports of the spec drop all three.

## 2026-10-26 · Repository
- **Created:** `deterministic-systems-lab/babel-17`, private.
- **Gitignored:** `private-docs/` and `.DS_Store`.
- **First commit:** `.gitignore` and the Claude Code guard hooks in `.claude/`.
- **Added:** `DECISIONS.md` and this log.
- **State:** nothing is built yet.
  - **Installed:** uv, node, clang, codex, claude.
  - **Not installed:** Dafny, Z3, Rust, Lean.

## 2026-10-26 · Decision log review
- **Review:** before publication, Codex (`gpt-5.6-sol`) checked `DECISIONS.md` against the spec, read-only. It confirmed that D1–D11 match the spec's Decision log.
- **Revised before publication:**
  - **Overclaims removed:**
    - D17: Dafny does report per-assertion status, and an oracle gap now gets triaged rather than called a bug outright.
    - D18: `rustc` doesn't check that lowering preserves meaning, and Verus can't verify arbitrary Rust.
    - D24: the claim about the state of proof reconstruction is narrowed.
    - D30: the contradiction about which cost bounds get proven is fixed.
  - **Errors fixed:**
    - D29: `Vec::with_capacity` guarantees *at least* the requested capacity.
    - D22: the proof-cache key now covers the solver and prelude configuration.
    - D23: cross-platform determinism now needs per-platform solver builds and a golden-verdict suite.
  - **Contradictions resolved:**
    - D24: solver-trusted results get their own level, L3-S, instead of counting as L3.
    - D19: D10 is deferred rather than scoped, since a Python prototype can't meet it.
    - D16: WP1 splits into WP1a (now) and WP1b (later), because WP2 and WP3 depended on it.
    - D21: the critical path is now computed from the dependency table.
  - **Gaps filled:**
    - D28: WP17, the baseline harness, gets an owner.
    - D27: interfaces for interpreter traces and canonical solver queries are added, and interfaces for Phase 3 and later are dropped until that work starts.
- **Re-check:** a second Codex pass reviewed the fixes and found five more problems, all fixed:
  - **D16:** the claim that a kernel can't change what agents write was still there. It's now framed as a scheduling tradeoff.
  - **D16, D21, D28:** two dependency loops. WP1a's done-when needed WP15, and WP16's done-when needed the verifier. Each now has a done-when it can meet on its own.
  - **D21:** WP11 was missing its dependency on WP4b, for vacuity-checked tasks.
  - **D18:** differential tests sample inputs; they don't prove that lowering preserves meaning.
  - **D28:** WP17 now requires exact verdicts on recorded outputs, and only statistical agreement on reruns, since hosted models don't produce the same output twice.
- **Awaiting the owner:** D15–D32.

## 2026-10-26 · Owner accepts D15–D32, and the build starts
- **Goal, restated by the owner:** Babel-17 is a language optimized for LLM coding. It exists to speed up development of model-generated code and to improve how that code performs.
- **Accepted:**
  - D15–D32. D11 is superseded by D18.
  - Activity entries may name the models that did each piece of work.
- **Next:** WP17, the baseline harness on stock Dafny. Dafny is being installed via Homebrew.

## 2026-10-27 · WP17 baseline harness: done
- **WP advanced:** WP17 (D28), done.
- **Built:**
  - `gym/harness.py`, with four commands: `check-tasks`, `run`, `reverify` and `summary`.
  - `gym/test_harness.py`, a self-check.
  - 20 seed tasks in `gym/tasks/*.dfy` (8 easy, 8 medium, 4 hard), each with a hidden reference solution.
- **Setup:**
  - **Verifier:** Dafny 4.11.0 on Z3 5.3.2 (Homebrew), with a limit of 100M Z3 resource units on one core.
  - **Claude:** `claude-opus-5-5` via `claude -p`, at high effort, with no tools, user hooks, plugins or MCP servers.
  - **Codex:** `gpt-5.6-sol` via `codex exec`, at high reasoning, with the user config ignored and the shell disabled.
  - **Loop:** up to 8 stateless rounds. Each round carries the task, the previous code and Dafny's raw output.
- **Done-when evidence:**
  - **`check-tasks`:** all 20 reference solutions verify, and an empty body fails all 20.
  - **Run `20261027T034550Z-claude-codex`:** both CLIs verified 60/60 attempts.

    | CLI | Mean rounds | Tokens per verified task |
    |---|---|---|
    | Claude | 1.00 | 3,814 |
    | Codex | 1.17 | 16,570 |
  - **Run `20261027T035814Z-claude-codex`:** both CLIs again verified 60/60. Pass rates differ by 0 points, against a tolerance of 15.

    | CLI | Mean rounds | Tokens per verified task |
    |---|---|---|
    | Claude | 1.00 | 3,797 |
    | Codex | 1.08 | 15,132 |
  - **`reverify`:** 130/130 and 125/125 recorded verdicts reproduced exactly.
- **Fixed during review, before any real run:** the review was Codex plus a self-review. Fixes:
  - attributes are allow-listed, after `@Axiom lemma` verified a body-less assumption cleanly;
  - an out-of-resource result was counted as verified;
  - `"//"` inside a string hid the code after it from the scanner;
  - tasks could be solved by calling the spec's own function, so preambles are now `ghost`;
  - Codex's token count included its reasoning tokens twice;
  - resume could mix configurations.
- **Findings:**
  - **Ceiling:** the seed tasks are textbook problems, and both models saturate them, so they can't tell languages apart. The M3 experiment needs harder, less familiar tasks (WP10).
  - **CLI overhead dominates tokens:** Codex adds about 13k prompt tokens per call and Claude about 3k. Compare token costs within a CLI, not across CLIs.
  - **First design signal for B17-0:** in 6 of 6 first attempts at `reverse`, Codex wrote `seq(|a|, i => a[|a| - 1 - i])`. Dafny can't see that `i < |a|` inside the lambda, so the proof fails. A comprehension whose index is typed `i < n` would make this correct by construction.
- **Interfaces touched:** none of 1–11. The task file format and the run record format are internal to WP17.
- **Proofs and tests added:** `test_harness.py` and `check-tasks`.
- **Left admitted:** none.
- **Known limits,** marked with `ponytail:` comments:
  - one resource limit for all tasks;
  - nested comments and identifiers like `x'a'` can be falsely flagged, never falsely passed;
  - a flat 15-point rerun tolerance, to be replaced by a paired bootstrap for M3;
  - one process per run ID.
- **Next on the critical path (D21):** WP1a (B17-0 core semantics) and WP2 (canonical form).

## 2026-10-27 · Gemini joins the harness; AlgoVeri imported
- **Asked by the owner:** use Grok and Antigravity too ("Please do").
- **Built:**
  - **A `gemini` CLI in the harness:** `agy -p` running `gemini-4-argon-high`, with JSON output. agy takes the prompt as an argument rather than on stdin. Its output token count already includes thinking.
  - **`gym/import_algoveri.py`:** ports AlgoVeri's Dafny specs (commit `8e313b0e8110`, Apache-2.0) into the task format, with the license alongside. AlgoVeri has no reference solutions, so ported tasks have none.
  - **Signature parsing** now balances parentheses, for tuple return types.
- **Ported:** 66 of 77 tasks. Skipped:
  - 10 class-based tasks (heap, queue, ring buffer, stack, union-find), because the generated check wrapper calls a top-level method;
  - `polymul_karatsuba`, which applies `<<` to an `int` and so doesn't type-check in Dafny 4.11.
- **Run `20261027T043411Z-gemini`** (seed tasks): 60/60 verified, mean rounds 1.00, 9,013 tokens per verified task. `reverify` reproduced 60/60.
- **Antigravity for porting:** not needed. AlgoVeri's sections are regular enough for a script. It stays in reserve for messier sources (vericoding, DafnyBench).
- **Grok:** waits for the owner to sign in.

## 2026-10-27 · B17-0 core semantics drafted (WP1a), for owner review
- **WP advanced:** WP1a (D16, D20), in progress.
- **Written by Claude (`claude-opus-5-5`):** `docs/b17-0.md`. It covers:
  - the worked example (`merge_sorted`);
  - grammar and canonical form;
  - types;
  - runtime and ghost contexts;
  - ownership;
  - effects;
  - typing rules;
  - semantics;
  - proof goals;
  - how a task is posed;
  - what's left out;
  - the accept/reject suite plan.
- **Reviews and fixes:**
  - **Codex (`gpt-5.6-sol`), full review:**
    - `%` and `/` at MIN/−1;
    - ghost variables used at runtime;
    - untyped `set`;
    - returns and panics inside loops;
    - modular calls and lemmas;
    - aliasing through `g(v, v)`;
    - termination measures;
    - effects;
    - a name conflict;
    - D29's precondition;
    - `partition`;
    - `count`, renamed `occurrences`;
    - `neg`.
  - **Gemini (`gemini-4-argon-high`):**
    - aliasing through `if`;
    - proof goals for loop conditions;
    - signed literals;
    - exact goals for ghost operations;
    - core-library scope;
    - weakest-precondition (wp) formulas written out.
  - **Codex delta re-check:**
    - `while` in ghost context;
    - result lists in the semantics;
    - left-to-right moves on `return`.
- **Proposed:** D33–D43, in DECISIONS.md.
- **Interfaces touched:** interface 1 (the semantics) is drafted, not frozen.
- **Proofs and tests added:** none yet. The accept/reject suite (§12) follows acceptance.
- **Awaiting the owner:** `docs/b17-0.md` and D33–D43.

## 2026-10-27 · AlgoVeri three-way baseline
- **Run `20261027T043958Z-claude-codex-gemini`:** 66 AlgoVeri tasks × 3 CLIs × 1 sample, up to 8 rounds, 6 jobs, from 04:40 to 14:38 UTC.

  | CLI | Verified | Mean rounds | Tokens per verified task |
  |---|---|---|---|
  | Claude (`claude-opus-5-5`) | 64/66 | 1.41 | 27,344 |
  | Codex (`gpt-5.6-sol`) | 60/66 | 2.05 | 62,388 |
  | Gemini (`gemini-4-argon-high`) | 28/28 finished | 1.07 | 30,926 |
- **Gemini ran out of quota after 28 tasks.** Antigravity returned `429 Individual quota reached … Resets in 158h`, so 38 attempts ended as infra errors (2 timeouts, 36 quota). On the 28 tasks Gemini finished, Claude and Codex also verified 28/28, so these results can't rank the three models.
- **`reverify`:** 314/314 recorded verdicts reproduced exactly, every round that produced code (one Codex reply had none).
- **Failures (all after 8 rounds):**
  - **Claude:** `matrix_multiplication` and `rod_cutting` (proof failed).
  - **Codex:**
    - `matrix_multiplication`, `prim` and `push_relabel` (proof failed);
    - `kruskal` and `rod_cutting` (rejected: a parse error);
    - `edmond_karp` (out of resource).
- **Findings:**
  - **AlgoVeri is near the ceiling too.** About 40% was the reported figure for frontier models; here Claude verifies 97% and Codex 91%, with feedback rounds. Hard tasks for M3 must come from elsewhere, or be written (WP10).
  - **One upstream spec is unsolvable:** `matrix_multiplication`. Its `dot_product` fails its own well-formedness check (index out of range), so no solution can verify. Both failing models spent all 8 rounds on it. `check-tasks` didn't catch this, because for a task without a solution it only required that an empty body fail, and a broken preamble also fails.
  - **The import didn't make preamble functions ghost,** unlike the seed tasks. Re-checked with ghost preambles and no chance to repair, 17 of the 85 affected verified solutions fail (Claude 6, Codex 10, Gemini 1). Most of those declare their own helper predicate without `ghost`, which one round of feedback fixes. About 5 genuinely evaluate the spec at runtime to brute-force the answer:
    - `linearsys_gf2` (both): try every vector;
    - `discrete_logarithm` (Codex): test each exponent with the spec's power function;
    - `ac_automata` (Claude) and `kmp` (Codex): naive matching instead of the named algorithm.
  - **Design signal:** a functional spec can't tell Aho-Corasick from naive search, so the named algorithm is never enforced. That is the cost question deferred in D29. Making the spec ghost only forces the brute force to be written out.
  - **Codex spends 2.3× Claude's tokens** per verified task, and needs more rounds.
- **Fixed after the run:**
  - **`check-tasks`:** a body of `assume {:axiom} false` must now verify. That proves the frozen preamble and contracts are well-formed, so each task is solvable in principle.
  - **Importer:** preamble functions and predicates are made `ghost`, and `matrix_multiplication` is marked BROKEN. Re-imported: 65 tasks.
  - **`call_cli`:** a quota that resets after the whole retry budget now fails at once. Gemini's 38 lost attempts spent about an hour each in retries, which stretched the run from about 4 hours to 10.
  - **Reviewed by Codex.** Two fixes came out of it: the ghost rewrite now also covers `static` and `opaque` declarations, and the reset time now counts minutes. A `by method` declaration made ghost no longer parses, so `check-tasks` reports it rather than missing it.
- **Consequences:**
  - The task files no longer match this run's fingerprint, so it can't be resumed or re-verified in place; git history keeps the task files it ran against.
  - Gemini's remaining tasks run as a new run after its quota resets (around 2026-11-02).
- **Interfaces touched:** none.
- **Proofs and tests added:** the quota case in `test_harness.py`, and the well-formedness check in `check-tasks`.
- **Left admitted:** none.
