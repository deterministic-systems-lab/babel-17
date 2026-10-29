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

## 2026-10-27 · Owner accepts D33–D43; the B17-0 accept/reject suite
- **Owner:** "I accept the decisions." D33–D43 are Accepted. D29's status now notes that D35 supersedes its capacity clause. The owner left the choice of harder tasks to Claude.
- **Built:** `suite/`, with:
  - **20 accept programs:** the seed tasks ported to B17-0. `merge_sorted` is §1's worked example, unchanged.
  - **29 reject programs,** covering every tier 0 code and every `E-PROOF-*` family. Each has exactly one error, whose code starts the filename.
- **Clarified in `docs/b17-0.md`:** writing the suite exposed rules that two checkers could read differently. Interface 6 is still Draft, so these are refinements, not new decisions.
  - **Names:**
    - result names are scoped to `ensures`, since the worked example's local `out` broke §2 as written;
    - binders are scoped to their bodies;
    - items may refer to one another in any order, or mutual recursion would read as an undefined name.
  - **Goals:**
    - clauses are checked in order, each assuming the ones before;
    - every goal is assumed once generated, so each reject program reports one code;
    - a loop forgets only what its body changes.
  - **Codes:** a tier 0 code table adds `E-PARSE-001`, `E-TYPE-001`, `E-TYPE-002`, `E-GHOST-002`, `E-GHOST-003` and `E-TERM-001`.
  - **Core library:** `sorted` is now defined, and `in_i64` is added.
  - **Porting ranges (§10):** a task requires its results, and every value its ghost definitions compute on the way to them, to fit in i64. `(<= n 92)` states the same range for `fib`, but a proof from it has to evaluate fib(92).
- **Reviewed by Codex (`gpt-5.6-sol`):** it checked all 49 files and found 4 label problems and 4 ambiguities. All are fixed:
  - **Background facts:** §9 said "such as", so an accept verdict depended on the checker. The facts are now listed exhaustively, including the multiset effect of `set-idx`, which the in-place sorts need.
  - **Lemma calls:** their arguments are checked in ghost context.
  - **Lengths:** they are bounded by 2^63, and growing past that is an allocation failure.
  - **Slice results:** a spec that declares one is `E-OWN-002`.
  - **Bounds reject:** it needed a non-empty input, so that only one bounds goal fails.
- **Correction:** the B17-0 draft entry above called the document interface 1 (the semantics). It defines interface 6 (core terms) and the B17-0 part of interface 1 (the grammar).
- **Interfaces touched:** 1 and 6, both still Draft.
- **Proofs and tests added:** the suite. It is checked by review only until WP3 runs it.
- **Left admitted:** none.
- **Not yet done:** D42's Dafny side, which gives the seed tasks in `gym/tasks/` the ported ranges. It is due when the M3 task set is built.

## 2026-10-27 · Grok joins the harness; the vericoding hard set
- **Grok setup:**
  - **Upgrade:** the CLI went from 0.2.112 to 1.0.70 via Homebrew, because the server rejected versions below 1.0.13.
  - **Isolation:**
    - **User config:** headless `grok` loads `~/.claude`: `CLAUDE.md`, 57 skills, 4 plugins with prompt-injecting hooks, and an MCP server. It ignores its own `GROK_CLAUDE_*_ENABLED` opt-outs. The harness therefore runs it with `HOME=/var/empty`, while `GROK_HOME` keeps the login.
    - **Tools:** `--tools ""` and `--tools none` remove nothing, so all 24 client tools are disallowed by name.
    - **X search:** it runs server-side and can't be removed. Streaming JSON reports each use as a `tool_call` event, which `calls_using_tools` counts.
    - **`--verbatim`:** keeps Dafny's `@` from being read as a file mention.
    - **Checked:** Grok's own session record shows a 4,159-byte system prompt and no tools.
  - **Served model:** `grok-4.7` at high effort, reported as `grok-4.7-build`.
  - **Speed:** on `algoveri/gcd` it reasoned past the 15-minute call limit, twice. At medium effort it took 10.5 minutes and 52k reasoning tokens. The call limit is now 30 minutes for every CLI.
- **Hard tasks:** class-based AlgoVeri is out. B17-0 has no classes (§11), and M3 needs tasks both languages can express. Instead, `gym/import_vericoding.py` selects from vericoding (MIT, commit `387cd6999679`), using its published results for nine 2025 models:
  - **Selected:** Dafny tasks with one method, no vericoding QA issue, and only int, nat, bool, `seq<int>` and `array<int>`. Each was solved by at least one model but by at most a quarter of them. 47 tasks qualify.
  - **Kept:** the solving model's code is the reference solution, and a task is kept only if that solution passes this harness as is. 31 are kept.
  - **Dropped (16):**
    - 13 are rejected: most of these solutions run a spec function that is now ghost, and 2 of the specs are ill-formed;
    - 1 fails to verify under Dafny 4.11;
    - 1 runs out of resource;
    - 1 uses a banned construct.
- **`check-tasks`:** it now also rejects a reference solution that uses a banned construct.
- **Runs started:**
  - `20261027T161708Z-grok`: the seed tasks, 3 samples.
  - `20261027T161710Z-claude-codex-grok`: the 96-task hard set (AlgoVeri with ghost preambles, plus vericoding), 1 sample. Claude and Codex are re-run because the AlgoVeri preambles changed.

## 2026-10-27 · The hard run restarted on 28 vericoding tasks
- **Found by Codex** (`gpt-5.6-sol`), reviewing the Grok and vericoding changes: in three kept tasks (DD0370, DD0371, DD0423), the frozen preamble holds helper methods whose body is `assume {:axiom} false`. Each reference solution verified by calling those unproved helpers, and any agent could have done the same. `check-tasks` scanned only solutions for banned constructs, never preambles.
- **Fixed:** `check-tasks` and the vericoding importer now reject banned constructs in preambles too. No seed or AlgoVeri preamble has any. 28 vericoding tasks remain.
- **Also from the review:** the importer's docstring now lists the types it actually admits: sequences and arrays of int, nat and bool, plus ghost multisets.
- **Runs:**
  - the hard run `20261027T161710Z-claude-codex-grok` was stopped after 10 minutes and deleted, along with its orphaned model calls;
  - its replacement, `20261027T162910Z-claude-codex-grok`, covers 93 tasks (65 AlgoVeri and 28 vericoding);
  - the Grok seed run `20261027T161708Z-grok` continues, since its tasks are unaffected.

## 2026-10-27 · WP1a's freeze waits for WP3 (D44)
- **Owner decision:** `docs/b17-0.md` and `suite/` stay at version 0.1, Draft, until WP3's checker agrees with the suite's tier 0 labels, rather than freezing now. Recorded as D44, accepted.
- **Updated:** D21's status notes the amendment, and the b17-0 status line and the suite README state the freeze condition.
- **Grok seed run finished:** `20261027T161708Z-grok` verified 60 of 60 attempts, in 1.18 iterations on average, with no tool calls and no infrastructure errors. `reverify` reproduced all 71 recorded verdicts. The analysis comes with the hard run's entry.

## 2026-10-27 · B17-0 hashing proposed (D45, D46)
- **Why now:** WP2 is done when parse-print round-trips hold on every node and content hashes match across machines. A separate session is building the parser and canonical printer on branch `wp2-syntax`. D22 sets what a hash must achieve, but not B17-0's exact bytes.
- **Proposed:** D45 says what each item kind hashes, and D46 gives the format and its tests.
- **Checked by Codex** (`gpt-5.6-sol`), twice:
  - **First pass, 7 defects, all fixed:**
    - defs implementing identical specs were indistinguishable to their callers, so D45 now rejects duplicate specs;
    - uses of binders weren't said to be replaced;
    - numbering's start, and the numbering inside lemma proofs, were unspecified;
    - the text form of a reference hash was unspecified;
    - preimage boundaries and line endings were unspecified;
    - `docs/b17-0.md` §2 says raw canonical bytes are hashed;
    - ghost-fns have one hash, which wasn't marked as refining D22.
  - **Second pass:** the duplicate check was circular, using hashes that only exist after tier 0 passes, so it now computes provisional hashes. Codex confirmed the other fixes and the worked `abs` and `fib` examples.
- **On acceptance:** edit `docs/b17-0.md` §2 and the §9 table, and add a duplicate-spec reject program to the suite.

## 2026-10-27 · D45 and D46 accepted
- **Owner decision:** accepted both. D22 is marked "refined by D45".
- **`docs/b17-0.md`:**
  - §2 now says D45 hashes canonical bytes after replacing names;
  - §9's `E-TYPE-002` row adds a spec identical to another up to names;
  - the implements list names D45.
- **Suite:** `reject/E-TYPE-002-duplicate-spec.b17` was added. Its specs `max_of` and `larger` normalize to the same bytes, and each def would verify on its own.
- **Next:** the hasher will be built on the parser from branch `wp2-syntax` once that merges.

## 2026-10-27 · WP2 begins: the B17-0 parser and canonical printer
- **Added:** `b17c/syntax.py`, standard library only (D19):
  - `parse(text)` takes str or UTF-8 bytes and returns an S-expression tree (`Form`, `Sym`, `Int`, `Str`). Source positions are kept but don't count toward equality. Any input that isn't a term of §2's grammar, or that breaks §2's name, integer or string rules, fails with `E-PARSE-001`, a line and column, and a one-line reason.
  - `canonical(tree)` returns canonical bytes (D47).
  - `uv run --no-project b17c/syntax.py FILE` prints FILE's canonical bytes, or `FILE:LINE:COL: E-PARSE-001: reason` on stderr with exit status 1.
- **Scope:** grammar and lexical rules only. Types, ownership, name resolution and uniqueness are WP3's. D45 and D46's hasher comes next, on this parser.
- **Suite result:** the 20 accept programs and 29 of the 30 reject programs parse, including D45's new `E-TYPE-002-duplicate-spec`, and each round-trips: `parse(canonical(t)) == t`, and canonicalization is idempotent. `E-PARSE-001-while-without-decreases` fails with `E-PARSE-001` at 17:9, the first statement where the `decreases` should be. No suite label disagreed with the parser.
- **Proposed D47–D54** for what §2 leaves ambiguous or unsaid, taking the stricter reading each time:
  - D47: canonical layout;
  - D48: whitespace and comments;
  - D49: whitespace between siblings;
  - D50: control characters in strings;
  - D51: grammar words as names are `E-PARSE-001`, and core library names are `E-TYPE-002`;
  - D52: effect order;
  - D53: non-canonical integers and `(neg INT)`;
  - D54: empty optional clauses.

  The parser already implements all eight. If the owner rejects one, the parser changes with it. They were drafted as D45–D52 on the branch and renumbered when D45 and D46 (hashing) were accepted first.
- **Tooling:** uv 0.13.6 was installed with Astral's installer into `~/.local/bin`, because `brew install uv` needs the Xcode command line tools to build `pkgconf`.
- **Interfaces touched:** 1 (the grammar), as an implementation of the Draft. `docs/b17-0.md` and `suite/` are unchanged.
- **Proofs and tests added:** `b17c/test_syntax.py` covers the suite round trip, an exact canonical golden, whitespace layouts, and negative cases for every rule above. It also checks that the reserved words equal the words of §2's grammar block. Mutating any of six checks in the parser makes it fail.
- **Left admitted:** none.
- **Not yet done:** the rest of WP2: D45 and D46's hashes and their golden file, then typed edits. WP3's checker for §3–§9.

## 2026-10-27 · Parser merged and reviewed; the hasher completes WP2's hash half
- **Merged:** branch `wp2-syntax` (`1ef7d70`) fast-forwarded into main once its self-check passed and all 50 suite files behaved as labelled.
- **Codex review of the parser** (`gpt-5.6-sol`) found 4 issues, all fixed:
  - **Large integers:** a literal over 4,300 digits crashed on Python's digit limit, against D53. The limit is now off.
  - **Nesting:** acceptance depended on Python's recursion depth, which varies by machine. Proposed D55 caps nesting at 128 levels, and the recursion handler that depended on it is gone.
  - **D54:** it said every `(body)` may be empty, but a ghost-fn's holds one expression. The text now says so.
  - **D51:** the proposal now says how §9's `E-TYPE-002` row changes if it's accepted.
- **Added the hasher:**
  - `b17c/hashing.py` implements D45 and D46.
  - `b17c/core.b17` is the core library prelude (`sorted`, `in_i64`).
  - `b17c/hashes.txt` is the golden file: 27 items across the 20 accept programs.
  - `b17c/test_hashing.py` checks:
    - the golden file;
    - D45's worked `abs` and `fib` bytes through D46's preimages;
    - that renames change no hash (three programs, covering locals, results, quantifier binders and items);
    - that body edits and lemma-proof edits change only their own implementation hash;
    - that a ghost-fn edit reaches the specs that mention it;
    - that the duplicate-spec reject fails with `E-TYPE-002`, and mutual recursion with `E-TERM-002`.
  - Breaking how references are replaced makes the test fail.
- **Observed:** `sum_of` in `sum` and in `prefix_sums` gets the same hash, so identical definitions in different modules share one identity.
- **WP2 status:** both done-when tests now run: parse-print round trips, and hashes reproduced from a golden file. A second platform (Linux) hasn't reproduced the file yet. Typed edits (interface 2) and the lockfile (interface 7) remain.

## 2026-10-27 · Hasher review: clean
- **Codex** (`gpt-5.6-sol`) reviewed `040d891` against D45, D46 and §2 and found no defects. It walked every production, probed a result and a def local sharing a name, sibling quantifiers sharing a name, and lemma-proof numbering, and confirmed that the duplicate-spec reject fails for the intended reason.

## 2026-10-27 · D47–D55 accepted
- **Owner decision:** accepted all nine of the parser's readings of §2.
- **`docs/b17-0.md`, still a v0.1 Draft:**
  - §2's canonical rules now give the layout (D47), effect order (D52), `-0` and empty optional clauses (D54);
  - a new "Reading" block lists what parses (D48–D50, D53–D55);
  - the Names list makes grammar words `E-PARSE-001` and core library names `E-TYPE-002` (D51);
  - §9's `E-PARSE-001` and `E-TYPE-002` rows match;
  - the implements list names D47–D55.
- **Code:** unchanged. `b17c/syntax.py` already implements all nine, and both self-checks pass.

## 2026-10-27 · WP15: the reference interpreter
- **Added, on branch `wp15-interp`:**
  - **`b17c/interp.py`,** standard library only (D19). `run(module, name, args, check=False)` executes a def per §8 and returns one of `ok`, `panic` or `err`, each carrying the print trace. Ghost code is erased unless `check=True`, which also evaluates contracts, invariants, measures, asserts, ghost locals, ghost-fn calls and lemma claims, and reports the first failure as a `contract` outcome (D57). A step limit and a call-depth limit give a `limit` outcome, which is outside §8 (D59). The CLI `uv run --no-project b17c/interp.py [--check] [--fuel N] FILE NAME ARG...` prints the trace and outcome in interface 10's text form (D56).
  - **`b17c/test_interp.py`:** WP1a's conformance tests, derived from §8 and the suite.
  - **`syntax.parse_expr`,** which reads one expression, for the CLI's arguments. `test_syntax.py` covers it.
  - **README:** the interpreter, its self-check and a CLI example.
- **Core library:** read from `b17c/core.b17`, the same prelude the hasher uses.
- **Conformance tests:**
  - **Accept programs:** all 20 return `ok` with `check=True` on 3 to 9 hand-picked inputs each, including empty sequences and the i64 edges their requires allow, such as `abs(MIN + 1)`, `fib(92)`, `power(-2, 63) = MIN`, `sum((MAX, MIN))` and `gcd` of fib 92 and fib 91. Each also matches its `check=False` run exactly. 15 of them also run on 40 seeded random inputs each, filtered by their requires, and 13 of those are compared with an independent Python oracle.
  - **Requires:** 15 inputs that a requires rules out, such as `fib(93)` and `power(3, 40)`, stop on entry with `PRE`.
  - **§8, rule by rule:**
    - every `err` case, with the in-range edges beside each, and overflow in every runtime position: `let`, `print`, `push`, call arguments and a `seq-build` body;
    - left-to-right evaluation of operands, call arguments and `set-idx`;
    - truncating `/` and `%` in both contexts;
    - short-circuiting `and`, `or`, `=>` and `if`;
    - `panic`;
    - the print trace's order across calls;
    - several results (D43);
    - early return (D40);
    - `seq-build`'s index range (D38);
    - each check-mode rule of D57, each quantifier rule of D58, and both limits of D59.
  - **Reject programs:** every `E-PROOF-*` program shows its labelled fault on a concrete input:
    - `OVERFLOW`: `succ(MAX)`;
    - `DIV`: `rem(MIN, -1)`;
    - `BOUNDS`: `first_nonneg((-1))`;
    - `POST`: `bad_abs(-1)`;
    - `PRE`: `caller(-1)`;
    - `ASSERT`: `hopeful(0)`;
    - `INV-ENTRY`: `loop_entry(n)` for every n;
    - `INV-KEEP`: `loop_keep(1)`;
    - `TERM`: `spin(1)`.

    The first three are §8 `err`s with or without checking, and the other six are `contract` outcomes that disappear when ghost code is erased. Every label except `INV-ENTRY` also has an input that runs clean. No suite label disagreed with the interpreter.
- **Independent review** of the interpreter against §7–§9 found 7 problems. All are fixed, and each now has a test:
  - **Quantifier ranges:** bounds were taken from any conjunct of a guard, so a clause undefined at a skipped point could pass, such as `(idx a i)` sitting before `(< i (len a))`. An `exists` also stopped at its first witness, missing an undefined point after it. D58 now reads bounds only from the guard's leading conjuncts that can't fail, works ranges out binder by binder, and evaluates every point.
  - **Crashes:**
    - a `bool` binder used in an `int` binder's bound;
    - a recursive call inside a ghost-fn's own `requires`, which is now `TERM`;
    - a call to a spec with no def, which is now a clear refusal;
    - a `(borrow ...)` command-line argument.
  - **Missed `TERM`:** 0 ≤ callee measure wasn't checked when the caller's measure was unknown.
  - **Unrecorded unknowns:** a ghost-fn whose `requires` was unknown wasn't listed as unchecked.
  - **Order:** bound expressions were evaluated even where the guard's earlier conjuncts already ruled every point out, which evaluation from left to right never does.

  The review also listed plausible bugs the tests didn't catch at the time. Each is now one of the mutants below.
- **Mutation check:** 56 deliberate bugs in `interp.py`, one at a time. 55 make the tests fail, or hang where fuel was the only thing stopping a loop. The other pops one call frame where the code cuts the stack back to its depth before the call. The two differ only once the depth limit has already ended the run.
- **Findings:**
  - **`dedup_sorted` can't be fully checked.** Its `ensures` clause `(forall ((x int)) (== (contains a x) (contains r x)))` and the matching invariant range over every `int`, so D58 lists them as unchecked on every run. The rest of its contract is checked, and its results match the oracle. If the owner wants the clause checkable, an equivalent bounded statement is `(forall ((i int)) (=> (and (<= 0 i) (< i (len a))) (contains r (idx a i))))` together with the same over `r`'s indices and `a`. The suite isn't changed.
  - **`isqrt` can't be run at its i64 edge.** Its loop is linear in √n, so `n = MAX` takes about 3 billion iterations. The largest input tested is 10,000.
- **Proposed D56–D59:**
  - D56: interface 10 — the trace, the outcomes, node IDs, evaluation order and the text form;
  - D57: what checking evaluates and what a contract outcome reports;
  - D58: the quantifier range rule, and unknown clauses;
  - D59: fuel and call-depth limits.

  The brief numbered them from D55, but D55, the nesting cap, was taken first.
- **Interfaces touched:** 10, defined at version 0.1, Draft. `docs/b17-0.md` and `suite/` are unchanged.
- **Proofs and tests added:** `b17c/test_interp.py`, and `parse_expr` cases in `b17c/test_syntax.py`.
- **Left admitted:** none.
- **Second review (Codex, `gpt-5.6-sol`)** found one defect, now fixed with a test: checking evaluated a call's measure before its `requires`, against D57. A ghost-fn whose measure is costly or undefined outside its `requires` then hit `limit` instead of `PRE`. A caller's measure is now evaluated only once its `requires` hold, or when a recursive call inside them first needs it. No other defects were found in §8's semantics, value semantics, D56–D59, the tests or `parse_expr`.
- **Not yet done:** WP7's differential tests against emitted Rust, which interface 10 is shaped for; WP16's witness examples; WP3's checker, without which the interpreter trusts that its input passes tier 0.
## 2026-10-27 · WP5 spike: the suite's proof labels checked with Z3
- **Why:** under D44, WP1a freezes once WP3's checker agrees with the suite. A checker can't test the proof labels:
  - that accept programs prove without hints, using §9's facts alone;
  - that each `E-PROOF-*` program fails exactly its labelled goal.

  Until now, both had been checked only by review.
- **Built:** `b17c/goals.py`, a spike. It generates §7 and §9's goals for well-typed programs and runs each as its own Z3 5.3.2 query.
  - It isn't WP5: it does no type checking, and its encoding is one guess at interface 11.
  - It's on branch `wp5-goals-spike`, because main now accepts changes only through reviewed pull requests.
- **Result:**

  | Set | Result |
  |---|---|
  | Accept, every goal proved | 16 of 20 (406 goals) |
  | Accept, one overflow goal not proved | `fib`, `power`, `sum`, `prefix_sums` |
  | `E-PROOF-*`, failing exactly their labelled family | 9 of 9 |

  - **No vacuous proofs:** none of the 406 accept goals has contradictory assumptions, as far as Z3 can tell within the budget.
  - **Speed and stability:** the whole run takes 46 s under a 10M-unit budget per goal, and repeats exactly.
- **Findings:**
  - **The porting rule (§10, D42) needs a hint in 4 programs.**
    - The overflow goal at a loop step needs the range precondition at the next index, a term the program never mentions before the step.
    - Stating the range per step proves all four with no hint. Proposed as D60.
  - **The encoding matters more than the facts.**
    - Z3's own sequence theory timed out on 9 accept programs. The same §9 facts as axioms of an uninterpreted sequence sort prove them in milliseconds.
    - Division by a variable stalls Z3 unless it's encoded through D37's truncation facts.
    - Wall-clock limits made verdicts depend on load.
    - Proposed as D61.
  - **Failing goals come back `unknown`, never `sat`.** With quantified axioms, Z3 can't build a counterexample, so WP6's `counterexample` field will usually be empty for these goals. Each failing goal also costs the whole budget.
- **Not yet:**
  - D23's shuffled-seed runs;
  - checking the spike against the interpreter's traces, once WP15 lands.

  Codex is reviewing the spike for soundness.

## 2026-10-27 · Goal spike: recursive ghost-fns made sound
- **Found** while probing the spike's soundness, a probe Codex's review had started before OpenAI's content filter ended it.
  - The spike gave Z3 each recursive ghost-fn as an unconditional recursive definition.
  - A body like `(+ (bad n) 1)` makes that definition contradictory, and a contradiction proves every goal, including the termination goal that should reject it.
  - On the suite, no ghost-fn had this problem.
- **Fixed:** a recursive ghost-fn's equation is now an axiom that holds only under its `requires`, and its own goals are checked without it. The probe's termination goal now fails, and so does a wrong postcondition next to a well-defined ghost-fn. Proposed in D57.
- **Rerun:**
  - **Accept:** 17 of 20 prove every goal, with no contradictory assumptions among their 406.
  - **`fib`:** it now proves too, but only after 8,130 quantifier instantiations and 4.86M of the 10M-unit budget. That's likely to fail under shuffled seeds, so D56's step form still applies to it.
  - **Still not proved:** `power`, `sum` and `prefix_sums`.
  - **Proof rejects:** 9 of 9 still fail exactly their labelled family.

## 2026-10-28 · Correction: decision numbers in the soundness entry
- When #2 merged, the goal spike's proposals were renumbered from D56–D57 to D60–D61. The entry "Goal spike: recursive ghost-fns made sound" predates that: its "Proposed in D57" means D61, and "D56's step form" means D60. D61's own text now cites D60.
- **Merged on 2026-10-28:**
  - #2, the interpreter;
  - #3, the spike's soundness fix;
  - #4, the roadmap.

  Merging a PR doesn't accept the decisions it proposes, so D56–D61 are still Proposed.

## 2026-10-28 · Goal spike: proof stability under shuffled seeds
- **Added:** `b17c/goals.py --seeds N`. A goal counts as proved only if it is also proved under N shuffled seeds of Z3's SMT and SAT cores (D23). Otherwise it's reported as brittle.
- **First run, 10 seeds:**
  - 15 accept programs held under every seed.
  - `fib`'s overflow goal held under 7 of 10.
  - Two of `dedup_sorted`'s goals held under 6 and 7 of 10: the invariant and the `ensures` that its output has the same elements as its input.
- **`dedup_sorted`'s cause:** `contains` is an existential, so each proof had to find a witness index.
  - Restating the clauses over indices, as WP15's activity entry suggests, makes them checkable by the interpreter but stays brittle (8 and 5 of 10).
  - Giving `contains` the facts that follow directly from §9's makes all 25 of its goals hold under every seed: over `concat` it is `or`, a one-element sequence contains only its element, and the empty sequence contains nothing. Proposed as part of D61.
- **Final run, 10 seeds:**

  | Set | Result |
  |---|---|
  | Accept, every goal under every seed | 17 of 20 |
  | Accept, failing | `power` (2 of 10 seeds), `sum` and `prefix_sums` (no seed) |
  | Proof rejects, failing exactly their labelled family | 9 of 9 |
  | Accept goals with contradictory assumptions | 0 of 406 |

  The full run takes 2 minutes.
- **`fib` and `power` are luck under the prefix form.** The `contains` change, which has nothing to do with them, moved `fib` from 7 to 10 seeds and `power` from 0 to 2. With D60's step form, all four range programs hold under every seed in both encodings. `fib`'s goal then takes 9 quantifier instantiations and 21,542 units, against 4,333 and 1.74M before.

## 2026-10-28 · CI on Linux; hashes match across machines
- **Added:** `.github/workflows/check.yml`. It runs `test_syntax`, `test_hashing` and `test_interp` on Ubuntu with Python 3.12, for every pull request and every push to main.
- **WP2's last done-when:** on its first run (Actions run 40609086707), `test_hashing` reproduced `b17c/hashes.txt` exactly. The file was written on macOS with Python 3.11. Content hashes therefore match across machines (D46). With the parse-print round trips, both of WP2's done-whens now pass.
- **Left out of CI:** the Dafny harness and the Z3 goal spike need their pinned solver builds (D23).
- **WP2 still to do,** though neither item is part of its done-when: the manifest and lockfile schemas (interface 7, D26), and typed edit operations (interface 2).

## 2026-10-28 · WP4a's scope proposed (D62)
- **Why:** the roadmap noted that WP4a, next after WP3 on D21's critical path, had no definition or test.
- **Finding:** B17-0 already defines a spec language: headers, specs, ghost-fns, lemmas, and §7's well-formedness rules. The goal spike discharges the well-formedness goals of every suite spec. The design spec's other spec features either aren't needed (frames, given ownership) or need language growth Phase 1 doesn't plan (data-type invariants, refinement links, resource contracts).
- **Proposed D62:** WP4a ends when WP1a freezes, and WP1a takes its place in D21's table. That shortens the critical path and lets WP16 start now.
- **On acceptance:** update `docs/roadmap.md`'s Phase 1 table and critical path.

## 2026-10-28 · WP16: the core spec library
- **Started** on the assumption that D62 is accepted. Under D62, WP16 depends on WP1a and WP15, and both are in place.
- **`b17c/core.b17`** now holds:
  - **Ghost-fns:** `sorted`, `in_i64` and `seq_update`, a functional `set-idx`.
  - **30 laws as lemmas,** each with an empty body:
    - §9's length, element, prefix, sequence-equality, membership and multiset facts;
    - D61's derived `contains` facts;
    - the update facts, stated over `seq_update`;
    - the laws of integer order.
  - **Names:** every law is named `law_*`, and as core library names they're reserved (D51).
- **`b17c/test_core.py`:** WP16's witness examples (D28).
  - **Laws:** the reference interpreter evaluates every law at every point of a grid: 40 sequences over {0, 1, 2} of length 0 to 3, and integers from -1 to 4. A law must hold wherever its `requires` does, and at 3 points or more, so it isn't vacuous.
  - **Ghost-fns:** each has inputs where it's true and inputs where it's false.
  - **Teeth:** a law made false fails, and so does a law made vacuous.
  - **Speed:** about 1 s. CI runs it on Linux.
- **Cross-check:** the goal spike proves all 66 of the library's goals under 10 shuffled seeds, so the encoding implies every law, and the interpreter confirms each law is true.
  - **Dropped law:** one stated that a functional update swaps one count of the old value for one of the new. The interpreter confirmed it, but the encoding couldn't prove it, since §9 gives that multiset effect only for the `set-idx` statement. A lemma can't state a statement's effect, so the law was dropped, and the library's header says so.
- **Suite results unchanged:** 17 of 20 accept programs and 9 of 9 rejects under 10 seeds.
  - `power`'s brute-force proof shifted again, with no change to `power` itself. That's more evidence for D60.
  - Adding a take-and-drop fact, `concat (take s k) (drop s k) = s`, to try to save the dropped law also flipped `fib`, so it was reverted.

## 2026-10-28 · WP16 review: 33 laws
- **Codex** (`gpt-5.6-sol`) reviewed the library and its witness test, and found 9 issues.
  - **Added:**
    - `law_i64_range` and `law_vec_len_range`, for §9's range facts;
    - `law_multiset_occurrences`, which says equal multisets have equal counts.
  - **Strengthened:** `law_take_none` now states `take s 0` equals the empty sequence, not only that its length is 0.
  - **The test** now checks:
    - the exact list of law names;
    - that every law claims something;
    - a grid with negative elements, two longer sequences and the i64 edges.

    Three laws false only outside the old grid now fail it: `last s >= 0`, `len s <= 3`, and an empty claim.
  - **Not added, with the reasons in the library's header:**
    - **Bool versions of the laws:** B17-0 has no polymorphism, and the encoding applies the same facts at bool.
    - **Multiset extensionality:** its precondition ranges over every `int`, so the interpreter can't give it witness examples (D58).
    - **`set-idx`'s multiset effect over `seq_update`:** the interpreter confirms it, but the encoding can't prove it without `concat (take s k) (drop s k) = s`, which §9 doesn't have.
- **Result:** the interpreter confirms all 33 laws on the grid in under 2 s, and the goal spike proves all 69 of the library's goals under 10 seeds.
- **Open:** §9 has no take-and-drop decomposition fact. Adding one would let a library law state `set-idx`'s multiset effect. Once D60 removes the suite's brute-force proofs, the fact is cheap to add; until then it flips `fib`.

## 2026-10-28 · D56–D62 accepted; D60 and D61 applied
- **Owner decision:** accepted D56–D62. D21 is marked as amended by D62.
- **D60 applied:**
  - **Suite:** `fib`, `power`, `sum` and `prefix_sums` state their ranges per loop step.
  - **Docs:** §10's porting rule says so, and so does the suite README's ranges table.
  - **Hashes:** the golden file is regenerated. Only those four programs' hashes changed.
- **D61 applied:** §9's Encoding text now gives the axiomatized sequences, count-map multisets, division by a variable, guarded recursive definitions and the resource budget. Its Membership fact now lists the derived `contains` facts.
- **`docs/b17-0.md`:** its implements list names D60 and D61. It stays at v0.1 Draft until WP3's checker agrees with the suite (D44).
- **Result:** under 10 shuffled seeds, all 20 accept programs now prove every goal with no hints, and all 9 proof rejects fail exactly their labelled family. Every proof label in the suite is now confirmed mechanically, not only by review.
- **Checks:** `test_syntax`, `test_hashing`, `test_interp` and `test_core` all pass.
- **README and roadmap:**
  - no decisions are waiting;
  - D62's dependency table and critical path, which now runs WP1a, WP2, WP3, WP16, WP5, WP6, WP8, WP11;
  - the suite results above.
- **Still open, for M3:** D42's Dafny side. The four Dafny seed tasks take the same per-step preconditions when M3's task set is built.

## 2026-10-28 · WP5's front end: canonical queries, the proof cache, the report (D63)
- **Added:**
  - **`b17c/verify.py`:** `verify(module)` checks every goal from the goal spike.
    - Each goal goes out as its canonical query (interface 11): generated names renamed in order of first occurrence.
    - Each verdict is cached under D22's key: the definition's hash, the spec hashes of what it refers to, the canonical query, and the configuration.
    - `report()` gives the run's trusted base part (D24, D25): solver-trusted, brittle and failed goals by D56-style node ID, and the axioms they rest on.
    - The CLI prints the goals that aren't proved and a summary.
  - **`b17c/test_verify.py`:** a local check, since it needs Z3.
- **Changed in the spike:**
  - each goal now records its node and its part (spec or implementation);
  - a goal's query holds only the declarations and ghost-fns it uses;
  - a loop's forgotten variables are declared in order of first assignment, not by name;
  - `solve_stats` reports resource units.
- **Found while building it:**
  - **Renaming:** declaring forgotten variables in name order made a renamed program's queries differ.
  - **Untrimmed queries:** declaring every constant and ghost-fn in every query made a callee's body edit invalidate its callers.

  Both are fixed, and the test covers both.
- **Evidence:**
  - **The worked example** verifies in 1.4 s with 10 seeds, and a second run takes every verdict from the cache, at 0 units.
  - **A renamed `merge_sorted`** (`out`, `i` and the item renamed) hits the cache for every goal.
  - **Two-function module:** editing `one`'s body re-verifies only `def one`, and editing its spec re-verifies `def two`.
  - **Rerun after trimming:** 20 of 20 accept programs, 9 of 9 rejects, all 69 core-library goals, and both soundness probes give the same results as before.
- **WP5's done-whens:** the worked example verifies, seed-shuffle checks pass (D23), and the proof cache hits on unchanged code. All three hold for the spike's goals. Generating goals from WP3's types instead of the spike's sort guesses is still to do.
- **Proposed D63:** interface 11 v0.1, the cache key and entries, and the report's contents.
- **Codex review** (`gpt-5.6-sol`) found 8 issues, all fixed and tested:
  - **Solver hash:** it covered only the `z3` wrapper, truncated. It now hashes the resolved binary and its `libz3`, as full SHA-256 digests.
  - **Timeouts:** a wall-clock timeout or process error could be cached, against D23. Only verdicts reached within the budget are cached now.
  - **Atomic writes:** cache writes now go to a temporary file that's renamed into place, and an unreadable entry counts as a miss.
  - **D25's fields:** the report lacked the input hash, lockfile hash and level. It now records them, and the level is L3-S or L2-S per D24.
  - **Duplicate node IDs:** several `POST` or `PRE` goals at one node shared an ID. Goals now name their contract clause, and repeated checks of one node are numbered.
  - **Units:** shuffled seeds' resource units weren't counted. They are now.
  - **Untested key:** the cache key's dependency hashes weren't tested on their own. The key is now a function with its own test.
  - **D63's wording:** it said interface 5 stays WP7's, but D25 gives the report to WP5. The text is corrected.
- **Not found:** Codex found no trimming defect: closure is transitive, and a recursive ghost-fn keeps its declaration and `requires` while losing its own equation. No canonical-name collision either.

## 2026-10-28 · Proposed D64: Babel-17 is an all-purpose language for agents
- **Why:** the owner stated the goal: an all-in-one, all-purpose language for AI to use. Neither the README nor the decisions said so.
- **Proposed D64:**
  - the goal, covering services, applications and their user interfaces, pipelines, scripts and machine learning;
  - breadth through verification levels, with L0 and L1 arriving in B17-1;
  - other languages as a bridge, not the end state;
  - five design gaps, each to be decided separately;
  - benchmarks beyond algorithm tasks.
- **Updated:**
  - **`README.md`:** the introduction states the goal, and what B17-0 covers today.
  - **`docs/roadmap.md`:**
    - the goal, under "How the plan works";
    - D63 and D64 under decisions waiting, since D63 was listed nowhere;
    - a new open question on reaching every domain;
    - WP5's front end (PR #11) and WP16's first part (PR #9) marked merged.
- **Codex review** (`gpt-5.6-sol`) found 3 issues, all fixed:
  - **Overclaiming:** the README said modules are "fully correct" where intent is precise, and folded contract testing into L0. It now names the levels in order and says what each gives. D64 says L3 means L3-S while the solver is trusted (D24).
  - **Bet 1 as fact:** D64's rationale said the reason verified languages stay niche "doesn't apply". It now depends on M3 bearing Bet 1 out, and names the limits that remain.
  - **Stale date:** the roadmap said 2026-10-27 while adding 2026-10-28 status.
- **Not found:** no contradiction with D14 or D20, and the WP and PR numbers check out.

## 2026-10-28 · D63 and D64 accepted
- **Owner decision:** accepted D63 (interface 11 and the proof cache) and D64 (Babel-17 is an all-purpose language for agents).
- **README and roadmap:** D64 is no longer marked proposed, and no decisions are waiting.

## 2026-10-28 · Proposed D65: the language grows alongside the phases
- **Why:** the owner asked whether the roadmap reflects D64. It did only partly. It stated the goal and listed the missing features, but:
  - its phases scheduled only tooling;
  - B17-1, where D64 puts L0 and L1, appeared in no phase;
  - the standard library had no place;
  - every benchmark stayed an algorithm task.
- **Proposed D65:**
  - **Two tracks:** the language grows in subsets alongside the phases, each following B17-0's path to a D44 freeze.
  - **B17-1 in Phase 1,** with §11's data types, tuples, generics and nested collections, and L0 and L1. WP10's AlgoVeri ports wait for it, and M3 can start on B17-0.
  - **Later subsets** are ordered by benchmarks and continue past Phase 4.
  - **The standard library** grows with the subsets.
  - **Task sets beyond algorithms** arrive with the subsets that can express them.
  - **WP11's curriculum** covers every domain reached.
- **`docs/roadmap.md`:**
  - a "Two tracks" line under "How the plan works";
  - B17-1 in Phase 1's row and table;
  - WP10's dependency on B17-1, and M3's start on B17-0;
  - WP11's curriculum;
  - a new section, "How the language grows";
  - the "Reaching every domain" question narrowed to what follows B17-1;
  - D65 listed as waiting.
- **`README.md`:** its pointer to the roadmap mentions how the language grows.
- **Codex review** (`gpt-5.6-sol`) found 6 issues, all fixed:
  - **Phase 1 gate:** it didn't require B17-1. It now requires B17-1 frozen and its tasks emitted as Rust.
  - **WP4a:** data types reopen it under D62. D65 now says B17-1's scope decision does, and the WP4a row says so.
  - **Freeze rule:** "every label" contradicted D44, which needs only the tier 0 labels. It now says tier 0.
  - **Critical path:** it still put WP10 off the path. A second path of the same length now runs through B17-1 and WP10, and M3's needs separate the seed ports from the AlgoVeri ports.
  - **Prerequisites:** the later-subset list dropped §11's: mutual recursion waits for group hashing (D22), and vector capacity for allocation bounds (D30). Both are restored.
  - **One subset at a time:** the roadmap said each subset freezes before the next starts, which D65 doesn't decide. Removed.

## 2026-10-28 · D65 accepted
- **Owner decision:** accepted D65. B17-1 is part of Phase 1 and its gate, and the language grows in subsets alongside the phases.
- **Records:** D21 is marked as amended by D65. That covers WP10's dependency on B17-1 for its AlgoVeri ports, and through it WP11's.
- **Roadmap:** D65 is no longer marked proposed, and no decisions are waiting.
## 2026-10-28 · WP3: the tier 0 checker
- **Added, on branch `wp3-check`:**
  - **`b17c/check.py`,** standard library only (D19), built on the parser's tree. `check(module)` returns diagnostics ordered by position, each with a §9 tier 0 code, a line and column, and a one-line message. It covers:
    - names and scoping (§2), including core library names (D51);
    - types and literal ranges (§3, D53);
    - runtime and ghost code (§4);
    - every ownership rule (§5);
    - effects (§6);
    - returns (D40);
    - recursion (§7);
    - last, D45's duplicate specs, through `hashing.hashes`.

    `uv run --no-project b17c/check.py FILE` prints `FILE:LINE:COL: CODE: message` per diagnostic, a parse error included, and exits 1 if there are any.
  - **`b17c/test_check.py`:** the suite's labels, a case of its own for every tier 0 code, a case for every ownership rule, and the accept-side cases most easily over-applied.
  - **README:** the checker, its self-check and a CLI example.
  - **CI:** `b17c/test_check.py` joins the Linux self-checks in `.github/workflows/check.yml`.
- **Suite agreement (D44's condition for the freeze):**
  - all 20 accept programs and all 9 `E-PROOF-*` programs pass tier 0 with no diagnostics;
  - the 20 tier 0 rejects each fail with exactly the code their filename starts with, and nothing else;
  - the `E-PARSE-001` reject fails in the parser.

  No label disagrees with the checker.
- **Independent review** of the checker against §2–§9 and the readings below reported 8 problems. Seven are fixed, each with a test:
  - **Callees:** a parameter, local or binder used as a callee passed silently, as in `(call x)` or `(x 1)`. It is now `E-TYPE-001` (D67).
  - **Crashes:** `check()` could raise RecursionError in two ways:
    - `hashing.hashes` recurses along chains of item references, and D55 bounds only one item's nesting;
    - the checker's own cycle search was recursive.

    The checker now hands `hashes` the items in dependency order and searches iteratively (D78). Tests cover a 400-item chain and a 1,500-lemma chain.
  - **Cascades:**
    - a call to a def with no spec;
    - uses of a name declared twice, whose diagnostics depended on declaration order;
    - a slice `let` initialized by a borrow;
    - a local declared twice;
    - one `E-EFF-001` per statement.
  - **Wrong code:** a borrow passed to a parameter that isn't a slice was `E-OWN-002`. It is now `E-TYPE-001`.
  - **Literals:** `seq-lit` elements ignored an `i64` destination, against D70.

  The eighth stays as it is: statements after a `return` don't accumulate moves, since §7 defines nothing after ⊥ (D77). The review also confirmed moves, ghost separation, effects, returns, scoping and positions, and 70,000 random parseable modules raised no other exception.
- **Mutation check:** each of the checker's 65 diagnostic sites was disabled in turn, along with 24 changes to its logic. Among them are the move join at an `if`, the loop's outer-variable filter, block and branch scoping, the per-argument vector count, `i64 <: int`, ghost literals, lemma arguments, the D45 step, the dependency order for hashing, and each of the review's fixes. 88 of the 89 make the self-check fail. The other disables the fallback for a `HashError` other than a duplicate spec, which can't happen once the rest of tier 0 passes. 28 were caught only after tests were added for them.
- **Mutation tool fix:** the first mutation run reported false misses. Python trusts a cached `.pyc` whose source has the same size and modification second, and mutants of one site differ in neither, so the tests sometimes ran a stale mutant. Runs now clear `__pycache__` and set `PYTHONDONTWRITEBYTECODE`. Re-run that way on `83fafcc`, the version logged, WP15's mutation check still gives 55 of 56.
- **For `hashing.py`,** two changes the checker works around (D78):
  - `HashError` should carry the item, since the checker now reads specs' names from its message;
  - `hashes` should follow references in dependency order, since in source order a long chain of references overflows Python's stack.

  `syntax.py` and `hashing.py` are unchanged.
- **Proposed D66–D78,** the stricter readings where §2–§9 are silent:
  - D66: block scoping, and results share D41 with parameters;
  - D67: names of the wrong kind;
  - D68: well-formed types;
  - D69: slices and borrows;
  - D70: ghost integers, literals and multisets;
  - D71: comparing collections;
  - D72: one argument per vector;
  - D73: owned arguments are variables;
  - D74: results are always bound;
  - D75: which statement changes which binding;
  - D76: the loop rule both ways;
  - D77: loops may always end, and unreachable code is checked;
  - D78: one diagnostic per error.

  They were drafted as D60–D75 and renumbered on rebase, after D56–D62 reached main.
- **Interfaces touched:** none. Diagnostics carry codes and positions only, until WP6 defines the schema and node IDs.
- **Proofs and tests added:** `b17c/test_check.py`.
- **Left admitted:** none.
- **Not yet done:** WP5's proof goals and solver. WP6's diagnostic schema. The freeze of `docs/b17-0.md` and `suite/`, which is now the owner's call (D44).

## 2026-10-28 · WP3 rebased onto main; hashing's workarounds moved into `hashing.py`
- **Rebased:** WP3's commit (`wp3-check`) was based on PR #8, before PRs #9–#14 merged. It's rebased onto main as `wp3-checker`. Its decisions are renumbered from D63–D75 to D66–D78, since main's D63–D65 are taken.
- **Checked on main:**
  - all five self-checks pass;
  - the checker agrees with every label of the 50-program suite, including D60's per-step programs;
  - main's core library, with its 33 laws and `seq_update`, which WP3 had never seen, has no diagnostics.
- **D78's workarounds, fixed where they belong:**
  - **The stack overflow:** `hashing.hashes` recursed through every item a spec refers to. With references in reverse order, 200 chained ghost-fns overflowed Python's stack. It now hashes each spec after the items it mentions, using an explicit stack, so a 3000-item reverse chain hashes in a fraction of a second, with the same hashes as in calling order. The golden hashes are unchanged.
  - **`HashError.names`:** a duplicate-spec error now names both specs.
  - **The checker** passes the module unchanged and drops its reordering pass and its parsing of error messages, 33 lines in all. D78's text is updated to match.
- **Codex review of the checker** (`gpt-5.6-sol`): it ran 29,694 random modules through the checker, with no crash, and found 4 bugs, all fixed and tested:
  - **False accept, `idx` and `last`:** reading an element from an empty literal gave a type compatible with anything, so `(return (idx (vec-new) 0))` passed as a `(vec i64)`. The element now takes its destination's type, which can't be a collection, or is an integer when nothing fixes it. D70 records the rule.
  - **False accept, `contains` and `occurrences`:** with an empty literal, they accepted a collection to look for, a nested-sequence type D68 forbids. That's now `E-TYPE-001`.
  - **False reject, move records:** a local's move record outlived its block, so a later `fn` binder reusing the name was reported as a use after move. Records now end with their scope (D66).
  - **Wrong code:** `(borrow v)` for a non-slice parameter was `E-TYPE-001`, and its test expected that. D69 makes any borrow outside a slice parameter `E-OWN-002`, so code and test now follow D69.
- **After the fixes:** all five self-checks pass, and the suite still matches 50 of 50.
- **Roadmap:** WP3's checker is listed under work in progress, D66–D78 under decisions waiting, and the steps left before the Phase 0 gate are now: merge WP3, decide D66–D78 and write them into `b17-0.md`, then freeze WP1a.


## 2026-10-28 · The hard run: AlgoVeri and vericoding
- **Run `20261027T162910Z-claude-codex-grok`:** 65 AlgoVeri and 28 vericoding tasks × 3 CLIs × 1 sample, up to 8 rounds, 6 jobs, from 2026-10-27 16:29 UTC to 2026-10-28 11:09 UTC.

  | CLI | AlgoVeri | vericoding | Mean rounds | Tokens per verified task |
  |---|---|---|---|---|
  | Claude (`claude-opus-5-5`) | 64/65 | 28/28 | 1.28 | 17,094 |
  | Codex (`gpt-5.6-sol`) | 62/65 | 28/28 | 2.03 | 48,872 |
  | Grok (`grok-4.7`) | 49/49 finished | — | 2.18 | 207,684 |
- **Grok's balance ran out** at `algoveri/prim`: from there its calls returned `402 Payment Required: Grok Build usage balance exhausted`, and 41 attempts ended on that error. 3 more (`dijkstra`, `edmond_karp`, `kruskal`) ended in their first round, every retry timing out at 30 minutes. On the 49 tasks Grok finished, Claude and Codex also verified 49/49, so these results can't rank it. Its calls averaged 22 minutes, against Claude's 75 seconds, and no call used X search.
- **Grok's seed run** (`20261027T161708Z-grok`, from the earlier entry): 60/60 in 1.18 rounds, 41,134 tokens per verified task.
- **`reverify`:** 447/448 recorded verdicts reproduced. The other, Claude's first `bfs` round, recorded as out of resource, hit the verifier's 30-minute timeout instead under 6 parallel jobs. Alone, it ran out of resource again, after 18 minutes. Dafny's resource limit is deterministic but the wall clock isn't, so load could change a verdict.
- **Failures (all after 8 rounds):**
  - **Claude:** `rod_cutting` (proof failed).
  - **Codex:**
    - `rod_cutting` (rejected, every round);
    - `kruskal` (rejected, a parse or resolution error in 6 rounds; in the other 2, a bodyless method and then `{:axiom}`, which the harness counts as failures);
    - `edmond_karp` (rejected, then out of resource).
- **Findings:**
  - **`rod_cutting`'s spec is unsatisfiable.** Codex said so in its first reply: `n` has no lower bound, and at `n = -1` every precondition holds but no strategy of positive cuts sums to `-1`, so the existence postcondition is false. A Dafny lemma confirms it. AlgoVeri's Verus and Lean versions take `n` as a `usize` and a `Nat`, and its Dafny version dropped the bound. `check-tasks` can't catch this: a body of `assume {:axiom} false` proves the contracts well-formed, not satisfiable. Claude's and Codex's `rod_cutting` failures in the earlier run came from it too.
  - **The harness had no way to hear it.** Codex answered with the missing precondition instead of a program, 8 times, and got a parse or resolution error back each time. An agent that finds a spec bug needs a way to report one, in Babel-17 too.
  - **Vericoding's difficulty doesn't carry over.** Its tasks were picked because at most a quarter of the 2025 models in its published results, eight or nine per task, solved each, yet Claude verified 27 of 28 in its first round and Codex 21. With `rod_cutting` out, Claude verified every solvable AlgoVeri task, and Codex all but `kruskal` and `edmond_karp`. The models differ in rounds (72 against 54 tasks verified in the first round) and tokens, but barely in what they verify: 92/92 against 90/92 solvable tasks. M3's hard tasks will have to be found elsewhere or written (WP10).
  - **Codex spends 2.9× Claude's tokens** per verified task. On the 49 tasks Grok finished, Grok spent 186,021 per task against Claude's 14,745, 12.6×.
  - **Codex improved on two tasks** it failed in the first AlgoVeri run, `prim` and `push_relabel`, and failed the same two others, `kruskal` and `edmond_karp`.
- **Fixed after the run:**
  - **`rod_cutting`:** `import_algoveri.py` lists it as broken, and its task file is removed. 64 AlgoVeri tasks remain.
  - **The verifier's timeout** is now 2 hours, a backstop for a hang. The resource limit bounds the work.
- **Consequences:** the task files no longer match this run's fingerprint, so it can't be resumed or re-verified in place. Grok's 43 remaining tasks (44, less `rod_cutting`) run as a new run once its balance is topped up, as Gemini's will after its quota resets.
- **Updated:** the README's results, task counts, date, `check-tasks` comment, WP17 row and re-checking note, and the roadmap's baselines, remaining Phase 0 work and "Hard enough tasks" question.
- **Interfaces touched:** none.
- **Proofs and tests added:** none.

## 2026-10-28 · D66–D78 accepted; WP1a frozen, and Phase 0's gate passes
- **Owner decision:** accepted D66–D78, WP3's readings of B17-0, and merged WP3's checker (PR #15).
- **Written into `docs/b17-0.md`**, each in the section it reads:
  - §2: block scoping, and results sharing D41's uniqueness with parameters (D66);
  - §3: element types, no nested collections, and no multiset subtyping (D68, D70);
  - §4: ghost types in runtime places, and how literals take their type (D68, D70);
  - §5: where slices and borrows may appear (D69), which statement changes which binding (D75), loop bodies leaving vectors as found (D76), and one argument per vector (D72);
  - §7: ghost arithmetic producing `int`, collection equality being ghost-only, sequence operations, open element types, `i64` binders, owned vector arguments, bound results, `return` in a lemma, and `E-RET-001`'s view of loops and unreachable code (D68, D70, D71, D73–D75, D77);
  - §9: names of the wrong kind in the tier 0 table (D67), and how errors are reported once each (D78).
  - D78's note on how `hashing.py` orders its work is about the implementation, so it stays in DECISIONS.md only.
- **Refinements recorded:** D66 refines D41, D69 and D72 refine D36, D74 refines D43, D77 refines D40, and D78 refines D45. Each earlier entry names its refinement.
- **WP1a frozen under D44:** WP3's checker agrees with every tier 0 label in the suite, so `docs/b17-0.md` and `suite/` are Frozen at version 1.0. Interface 6 and B17-0's part of interface 1 are Frozen with them (D27). Changing them now takes a new decision.
- **Phase 0's gate passes:** WP1a is frozen, WP2's round-trip tests pass, and WP15 passes its conformance tests (D16). Phase 1 begins. Its next steps are B17-1's scope decision (D65), which reopens WP4a, and WP5's goals from WP3's types.
- **Updated:**
  - the README's status, the WP1a, WP3 and WP4a rows, the layout row for `b17-0.md`, and the note on interfaces;
  - the roadmap's gate table, work in progress, decisions waiting, next steps, the WP3 and WP4a rows, and the B17-0 and B17-1 rows;
  - `suite/README.md`'s note on how labels are checked;
  - `b17c/goals.py`'s docstring.
- **Codex review** (`gpt-5.6-sol`) found 8 issues, all fixed:
  - **A checker bug:** a malformed collection type in a runtime place, such as a `(seq (seq int))` parameter, was `E-GHOST-002`. D68 makes it `E-TYPE-001`, and only a well-formed ghost type is `E-GHOST-002`. `check.py` now checks element types first, and §4 says "well-formed".
  - **§5:** it said Rust requires binding `(len v)` before `(call g (borrow v) (len v))`. Rust allows that call, and rejects only the owned case, `f(v, v.len())`, which is what D72 cites.
  - **§12 and the suite README:** the accept suite is 20 programs, the worked example among them. And only WP3 checks tier 0 labels: WP5 checks proof labels, and WP15 runs the accept programs and shows each proof reject's fault.
  - **Roadmap:** WP3 sat under "Work in progress", now "Recent and current work". "No decisions waiting" now notes that D2–D10, from the design spec, are still Proposed.
  - **README:** its roadmap pointer still mentioned what's left before the Phase 0 gate.
  - **Suite README:** its "Checking until b17c exists" heading is now "How labels are checked".
- **Interfaces touched:** 6 and B17-0's part of 1, now Frozen at version 1.0.
- **Proofs and tests added:** a `test_check.py` case for the malformed runtime type. Every `b17c` self-check passes.
- **Left admitted:** none.

## 2026-10-28 · README and roadmap after the freeze
- **Checked** both against the repository once PR #17 merged.
- **README:** CI runs five self-checks, not four: `test_check.py` joined it with WP3. The status section now says Phase 1 has begun, and names its next steps.
- **Roadmap:** WP7, the Rust backend, is unblocked now that WP3 and WP15 are done, and the next steps say so.
- **Interfaces touched:** none.
- **Proofs and tests added:** none.
- **Left admitted:** none.

## 2026-10-28 · B17-1's scope proposed (D79, D80)
- **Survey:** the frozen preamble and signature of each of the 64 AlgoVeri tasks, read for the features its contract needs. Claude's verified solutions from the hard run were read for runtime sets and maps.
  - **Already B17-0 (14):** `binary_search`, `bracket_matching`, `fast_exponential`, `gcd`, `integer_exponential`, `kmp`, `linear_search`, `longest_common_subsequence` (characters as `i64`), `maximum_subarray_sum`, `polymul_naive`, `sieve_method`, `string_search_naive`, `trial_division_naive`, `trial_division_optimized`.
  - **Quantified sequences (11):** `bubble_sort`, `insertion_sort`, `merge_sort`, `quick_sort` and `k_smallest` (a permutation witness), and `coin_change`, `house_robber`, `jump_game`, `knapsack_01`, `knapsack_unbounded` and `longest_increasing_subsequence` (an optimum over every selection).
  - **Pairs (2):** `ac_automata`, `longest_palindrome_substring`.
  - **Optional results (2):** `discrete_logarithm`, `linearsys_gf2`.
  - **Graphs (13):** `bfs`, `dfs`, `bipartite_check`, `cycle_detection`, `topological_sort`, `scc_tarjan`, `bellman_ford`, `dijkstra`, `kruskal`, `prim`, `edmond_karp`, `push_relabel`, `max_matching`.
  - **Trees (22):** the six `bst_*` tasks, `splaytree_splay`, `lca`, the five `llrbt_*`, three `segmenttree_*`, three `ternarysearchtree_*` and three `trie_*` tasks.
- **Proposed:**
  - **D79, B17-1's language:** data types with type parameters, tuples, collections of any element type, quantifiers over any ghost type, ghost sets and maps, places instead of lifetimes for nested values, and `rank` for termination over data. WP4a stays done, refining D65.
  - **D80, verification levels:** cumulative levels where, from L1, every goal is proved or tested; L1's property tests; L2's safety proofs resting only on proved goals, refining D63; and below L2, aborts at `err` with contracts unchecked at run time.
- **Updated:** the roadmap's decisions waiting and next steps.
- **Codex review** (`gpt-5.6-sol`) found 11 issues, all fixed before the PR:
  - **The survey:** 11 tasks counted as already B17-0 quantify over sequences, which B17-0's binders can't. The tries' views are infinite sets defined by comprehension, and specs also use set difference, intersection and, once, cardinality. Dafny's `nat` is a subset type, and `lca` has a generic member predicate.
  - **D79:** runtime aggregates could have held slices or ghost types; field reads needed a goal family of their own (`FIELD`); and keeping WP4a done refines D65.
  - **D80:** tests didn't cover every goal, and couldn't evaluate unknown quantifiers or lemma bodies; an L2 safety proof could rest on a goal that's only tested; dropping overflow checks contradicted D18; D63's level rule and D24's L3-S needed amending; and leaving out `panic` still rules out explicit panics at every level.
  - **Touches:** interfaces 1, 5, 6 and 10 were missing.
- **Codex re-review** found 4 more, all fixed:
  - **L2:** a caller's safety proof could still rest on a callee's `ensures` that's only tested. D80 now defines "proved from proved goals" as a closure over earlier goals, callees' `POST` goals and lemmas' goals.
  - **Ghost goals:** a `BOUNDS`, `DIV` or `FIELD` goal in ghost code can't abort a run, since ghost code is erased. Only runtime ones guard `err`.
  - **Limits:** a run that hits D59's limit refutes no goal, so its input is dropped.
  - **Interfaces:** the manifest is interface 4 (D26); interface 7 is the lockfile. The roadmap's WP2 line had the same slip.
- **Interfaces touched:** none yet. Once accepted, D79 changes interfaces 1, 6, 10 and 11, and D80 interfaces 4 and 5.
- **Proofs and tests added:** none.
- **Left admitted:** none.

## 2026-10-28 · WP5's goals from WP3's types
- **The change:** `b17c/goals.py` takes each expression's SMT sort from the type WP3's checker gives it, where the goal spike guessed.
  - `check.types(module)` returns the type of every expression of the module and the core library, by node.
  - `goals.Gen` builds on it, and refuses a module that fails tier 0. `verify.py` prints that module's diagnostics instead of goals.
- **Defects the guesses caused, each found by a probe and now fixed:**
  - **Multisets of booleans:** `ms` was declared only over integer sequences, so `(multiset r)` for a `(vec bool)` was mis-sorted. Its 2 goals ran to the resource limit unproved; they're now proved in 3,079 units. The prelude has `ms.I` and `ms.B`, and `set-idx`'s multiset fact now holds for both.
  - **Empty literals:** in `(== r (seq-lit))` or `(concat (seq-lit) r)` with `r` a bool vector, the literal defaulted to an integer sequence, which Z3 rejected as a sort error. Now an expression whose type an empty literal leaves open takes its context's sort: the other side of a comparison, the parameter or result of a ghost-fn, or the sequence or multiset around it.
  - **Ill-typed modules:** an undefined name crashed `verify.py` with a `KeyError`. It now prints `E-TYPE-002`.
- **Codex review** (`gpt-5.6-sol`) found 5 bugs, all fixed:
  - **Context sorts:** they didn't reach `take`, `drop` and `concat`, or a ghost-fn's arguments and body. The fix is one rule at the top of `Gen.expr`, rather than a case per operator.
  - **`verify.py core.b17`** reported every core name as redeclared. `goals.read` now gives both entry points the core library's own object.
  - **A parse error** crashed `verify.py`. It now prints `E-PARSE-001`.
  - The output's first finding was cut off. The probes written for the rest found two more, both fixed:
    - **Borrowed arguments:** the checker typed `(borrow v)` without passing it through `expr`, so goals had no type for it. It's now recorded.
    - **Comparing a sequence-valued `if`:** it put an `ite` in a trigger pattern, which Z3 rejects. The old code failed the same way. A fuzzer found the same for any logical operator, as in a literal of comparisons, so a side holding one now gets no pattern.
  - **A re-review** found two more open-literal cases, both fixed: `idx` and `last` now give an open sequence the sort of their element's context, and `occurrences` the sort of the value it counts, as `contains` already did.
- **Suite results unchanged:** under 10 shuffled seeds, all 20 accept programs prove every goal, all 9 proof rejects fail exactly their labelled family, and the core library's 69 goals are proved.
- **WP5 is done for B17-0.** Its three done-whens held already, and generating goals from WP3's types was what remained. B17-1 extends it (D65).
- **Updated:** the README's status, WP5 and WP16 rows and its `goals.py` entry; the roadmap's work in progress, next steps and WP5 row; `suite/README.md`'s note on how proof labels are checked.
- **Interfaces touched:** interface 11's prelude, v0.1 Draft: `ms` becomes `ms.I`, and `ms.B` is added. The prelude's hash is in every cache key, so old entries miss.
- **Fuzzing:** random ghost expressions full of empty literals, in 1,462 modules that pass tier 0, over three seeds. The old code broke on 5 of its first 7; the new code breaks on none.
- **Proofs and tests added:** `test_verify.py` cases for boolean multisets, empty literals typed by their context, a borrowed argument, a sequence-valued `if` in a comparison, and a module that fails tier 0. Every `b17c` self-check passes.
- **Left admitted:** none.

## 2026-10-28 · D79 and D80 accepted
- **Accepted by the owner:** D79, B17-1's scope, and D80, its verification levels (PR #19).
- **Refinements recorded:** D79 refines D65's WP4a clause, and D80 refines D63's rule for the level a module reaches. Both headings say so.
- **WP4a stays done.** B17-1 adds no data-type invariants or refinement links (D79).
- **Updated:**
  - the README's status and WP4a row;
  - the roadmap's decisions waiting, next steps, and its WP4a, B17-1 and WP10 rows;
  - the roadmap's B17-1 and later-subsets rows under How the language grows.
- **Next:** B17-1's spec text and labelled suite, as B17-0's were, then the checker, interpreter and verifier extend to it.
- **Interfaces touched:** none yet. B17-1's spec text will change interfaces 1, 6, 10 and 11 (D79), and 4 and 5 (D80).
- **Proofs and tests added:** none.
- **Left admitted:** none.

## 2026-10-28 · B17-1's spec text drafted (D81–D92)
- **`docs/b17-1.md`, version 0.1 Draft:** B17-1 as changes to `docs/b17-0.md`, section by section.
  - **Contents:** the grammar, types, ownership, effects, typing rules, semantics and proof goals, plus D80's levels and the porting rules.
  - **Worked example:** AlgoVeri's `bst_insert`.
  - **Compatibility:** every B17-0 program stays a B17-1 program with the same meaning. No suite program or core law uses a word B17-1 reserves; that was checked against every token in `suite/` and `core.b17`.
- **Proposed:** D81–D92, the readings the text makes within D79 and D80:
  - D81, the syntax: `data`, `match` with ordered arms, `is`, `field`, `tuple` and `get`;
  - D82, separate namespaces for types and values;
  - D83, runtime types, copying, well-formed data types and ghost covariance;
  - D84, places, `replace` and `E-OWN-007`;
  - D85, ghost sets and maps;
  - D86, `alloc` for boxed fields;
  - D87, `rank` as height;
  - D88, the property-test generator;
  - D89, interface 11 version 0.2;
  - D90, which types a quantifier may bind;
  - D91, ghost-fns in L2's closure, refining D80;
  - D92, how data items and the new binders are hashed, refining D45.
- **Codex review** (`gpt-5.6-sol`) found 11 issues, all fixed:
  - **Soundness:**
    - quantifiers over maps, multisets or types holding `i64` let the encoding prove an `exists` with a witness no program has, so binders are restricted (D90). As a result, the `edmond_karp` and `push_relabel` ports state flows as sequences;
    - `replace` lacked its place's `BOUNDS` and `FIELD` goals;
    - moves inside `if` and `match` expressions and `seq-build` bodies had no join, so moves now happen only in owned positions, and a `seq-build` body moves nothing outer;
    - a mutation's value could move its own place's root.
  - **The L2 closure** missed the ghost-fn equations a proof unfolds (D91).
  - **Data types:** a data type inside an `iset`, `map` or `multiset` of itself has no Z3 datatype. Blanket covariance let a wrapper around a map pass for another.
  - **Contradictions with D79:** slices aren't runtime types, and `rank` applies to every data value, which LLRB trees need for `(option node)`.
  - **Gaps:** the map operations' types, and the exact random stream of D88, now pseudocode.
- **Codex re-review** found 7 more, all fixed:
  - exactness for binders now recurses through data fields, so `(data d () (c (x i64)))` can't be bound;
  - D91's closure covers every goal of an unfolded ghost-fn, its `requires` and measure included;
  - variance is a fixpoint, so a parameter passed on to an invariant one is invariant;
  - D87's title and D89's `rank` now say every data value;
  - hashing had no rule for data items, so D92 adds one;
  - D88's seed is now exact about the hash's text form;
  - D90's evidence now counts `max_matching`'s tuple binders.
- **A targeted check** found 4 more spec issues, all fixed: a type recursive through `seq` isn't exact, since uninterpreted sequences admit cycles; variance follows a type's own recursive applications; hashing resolves names per namespace; and D91's closure is defined over the equations a query includes. It also noted that `hashing.py` doesn't implement D92 yet, which comes with the toolchain's extension to B17-1.
- **A limit, recorded in §5 and §12:** a data value can't be borrowed (D79), so a recursive read of a tree consumes it, or rebuilds it at the cost of allocation.
- **Updated:** the README's status, language note and layout; the roadmap's work in progress, decisions waiting and next steps, which now also say WP7 is under way in a separate session.
- **Interfaces touched:** B17-1's parts of interfaces 1 and 6, interface 10's values and `err` reasons, and interface 11 version 0.2, all Draft.
- **Proofs and tests added:** none yet. The suite comes next (§13).
- **Left admitted:** none.

## 2026-10-28 · WP6, the agent protocol (D93, D94)
- **`b17c/agent.py`:** diagnostics in interface 3's schema, and interface 8's five queries, each answered as JSON.
  - **`check`:** every tier 0 error with its D56 node ID, or every unproved goal with these fields:
    - the goal, written over the program's names;
    - a counterexample, with whether the interpreter reproduces it;
    - its context, its dependents and its budget.
  - **`obligations`:** every goal of an item.
  - **`explain`:** a code's rule, from `docs/b17-0.md` §9, with the suite's labelled program.
  - **`impact`:** the goals a changed spec breaks, callers first.
  - **`search`:** specs found by what they guarantee. A probe def that only calls the candidate is verified, so the proof is the match.
  - **`simulate`:** a checked run, as interface 10 reports it.
- **Counterexamples:** the full prelude's quantifiers keep Z3 from answering `sat`, so a failing goal had none, which the roadmap listed as an open question. WP6 solves the goal again against only the prelude axioms its own part mentions. Each of the suite's 9 proof rejects gets a model, and the interpreter reproduces 8. The ninth, `E-PROOF-BOUNDS-loop-condition`, is flagged as not reproduced. Verdicts still come from the full query.
- **Hooks in existing code:**
  - the checker's diagnostics carry their node;
  - the goal generator records each item's parameter terms and which nodes are ghost;
  - `verify.verify_goals` returns the goals behind the rows.

  None of these changes a verdict or a hash.
- **Latency:** tier 0 checks the suite's 20 defs in 7 ms, about 0.4 ms each, against the design spec's target of 100 ms per definition.
- **Codex review** (`gpt-5.6-sol`) found 9 bugs, all fixed, each with a regression test:
  - **Goal text:** a ghost-fn's `PRE` printed the call, not its `requires`. `DIV` printed SMT's `(- 9223…)`. A loop's measure drop is now documented as the one goal that isn't a B17-0 expression.
  - **Counterexamples:** they left out parameters the goal doesn't mention, so none could replay. Those now take a default, and a def with no parameters gets `{}`.
  - **Dependents:** they counted equal goal text in unrelated items.
  - **Search:**
    - it ignored failed goals of the probe's own spec, so it could report a match that doesn't hold;
    - the probe's name could clash with FILE's items;
    - its fresh result names had a bound and could crash.
  - **Impact:** it matched goals by positions, so moving an item looked like a change.
  - **Refusals:** a parse error in a query returned success, where D94 says exit 2.
- **Not done:** repairs stay empty until WP2's typed edits exist (interface 2).
- **Proposed:** D93, interface 3 version 0.1, and D94, interface 8 version 0.1.
- **Updated:**
  - the README's status, its WP table, its layout, and its self-checks, now six in CI;
  - the roadmap's work in progress, decisions waiting, next steps, WP6 row, and its open question on counterexamples, and that WP7 is under way in a separate session;
  - the README's toolchain examples, which now show `agent.py`;
  - CI now runs `test_agent.py`, without the queries that need Z3.
- **Interfaces touched:** 3 and 8, version 0.1 Draft.
- **Proofs and tests added:** `test_agent.py`, covering every query, a reproduced counterexample, a recursive call's `TERM` goal, impact on a caller, and search by guarantee. Every `b17c` self-check passes.
- **Left admitted:** none.

## 2026-10-28 · WP7: the Rust backend
- **Added, on branch `wp7-rust`:**
  - **`b17c/rust.py`,** standard library only (D19). `emit(module)` turns a module that passes tier 0 into the source of one Rust crate (D95):
    - the crate carries `#![forbid(unsafe_code)]` and erases ghost code;
    - every runtime goal of §9 is checked where §8 checks it, so a failed check stops the run with the interpreter's `err`, at the same node and with the same detail;
    - every expression has the type WP3 gives it, from `check.types`;
    - the crate's `main` runs one def and prints interface 10's text form, as `interp.py` does, one run per command or many with `--batch` (D96).

    `uv run --no-project b17c/rust.py FILE` prints the Rust, and `-o BINARY` builds it. `--report JSON` adds the backend's fields to the module's trusted base report (D25). `--run FILE NAME ARG...` builds once per source and runs like `interp.py`.
  - **`b17c/test_rust.py`:** WP7's done-when, and the corner cases below. CI installs rustc 1.99.1 and runs it.
  - **README:** the backend, its requirement and self-check, CLI examples, and a WP7 row.
  - **Roadmap,** added in review: WP7 under work in progress, D95–D97 under decisions waiting, and the WP7 row's state.
- **The toolchain:** rustc 1.99.1 (`58cf8f9c3`, 2026-10-13, LLVM 23.1.1), host `x86_64-apple-darwin`, from rustup's minimal profile. It's the install D18 put off until WP7 started.
- **For the owner, about the Intel Mac this was built on:** linking fails with its current settings. The arm64 Mac the branch was later reviewed on already uses the Command Line Tools.
  - **The cause:** `xcode-select` points at Xcode 26.6, whose `xcodebuild` is built for arm64 only, so on this Intel machine `cc` can't find the SDK.
  - **The workaround:** the Command Line Tools in `/Library/Developer/CommandLineTools` work. Every build here ran with `DEVELOPER_DIR` set to them.
  - **The fix:** `sudo xcode-select --switch /Library/Developer/CommandLineTools` would fix it for every tool, and may also explain Homebrew's earlier failure.
- **WP7's done-when holds: emitted code compiles, and matches the interpreter on differential tests.**
  - **Compiles:** 36 crates, with warnings denied: the 29 suite programs that pass tier 0, a module of corner cases, a module that recurses as deep as D59 allows, 4 generated modules and a module with no defs.
  - **Matches:** 8,875 runs print exactly the interpreter's text: every print, and the outcome with its node and detail. 6,205 end `ok`, 2,426 `err` and 244 `panic`. 250 more, which the interpreter can't finish in 20,000 steps, are skipped (D97).
  - **Corner cases:** 80 runs state the text both must print. They cover:
    - every runtime goal's failure, with its detail;
    - `set-idx`'s order, and short-circuits;
    - prints across calls, and `panic` strings with quotes, backslashes, a bidirectional control character and line separators;
    - names Rust reserves, and open element types;
    - code after a `return` that rustc would reject;
    - arguments the binary must refuse.
- **Fuzzing:** two campaigns of 40 generated modules each, 1,200 defs and about 30,000 runs per campaign. Neither found a mismatch.
  - **The first** found that a valid program comparing a literal with `9223372036854775807` didn't build with warnings denied, because of rustc's `unused_comparisons` lint. Valid programs may trigger it, so crates now allow it. Going through rustc's warn-by-default lints then found one more, `non_snake_case`, for a name such as `a__b`.
  - **The second** ran once the emitter took its types from WP3.
- **Mutation check:** 77 changes to `rust.py`, in its emitter and in the Rust runtime it writes.
  - **Caught:** 76 make the self-check fail. 8 were caught only after tests were added for them, and 4 more put back the review's bugs below.
  - **The 77th** turns off `-C overflow-checks=on`. No code path can show it, since every operation that could overflow is already checked.
  - **Redundant code:** two earlier survivors showed code that wasn't needed, now removed: a special case for writing `i64::MIN`, which rustc reads as written, and a path remapping that builds by relative paths don't need.
- **Builds are reproducible:** two builds of one source differed only in the output's name, which the binary records. `build()` now links under a fixed name, and the self-check compares two builds byte for byte.
- **Independent review** of `rust.py` against §2–§8, D56–D59 and the interpreter, with its own programs and its own generator, found 5 bugs. All are fixed, each with a test:
  - **Valid modules refused:**
    - **The bug:** a module with an item named `i` or `j` passes tier 0, but `emit()` refused it.
    - **The cause:** `check.types()` checked the core library in the module's scope, where `sorted`'s binders `i` and `j` met the module's items. WP5's goal generator refused the same modules.
    - **The fix:** `types()` now types the core library in its own scope, as `check()` leaves it, with a case in `test_check.py`.
    - **WP5 is unaffected:** its 511 goals for the suite and the core library are byte for byte the same before and after. Z3 isn't installed here, so `test_verify.py` didn't run.
  - **A stack overflow:** a def whose frame holds 450 vectors, recursing 999 deep, a run the interpreter finishes, overflowed the main thread's 8 MiB stack and killed the process. Runs now get a thread with a 1 GiB stack, room for D59's 1,000 calls at up to 1 MiB a frame (D96).
  - **`batch()` split lines wrongly:** it split output at U+2028, U+2029 and U+0085, which strings may hold (D50). It splits at `\n` only now.
  - **A non-UTF-8 argument** made the binary panic with exit 101. It's now refused with exit 2, on the command line and in a batch.
  - **Unicode whitespace** around an argument, such as a no-break space, was trimmed. Now only B17-0's four whitespace characters are (D48).

  Also fixed:
  - `emit()`'s docstring now names `ParseError`, and says an unreachable call isn't refused;
  - the build cache names its temporary files uniquely, so two builds in one process can't collide.

  What the review confirmed, comparing exact text and exit codes:
  - 150 names in every position, among them every Rust keyword B17-0 admits and the crate's own names;
  - about 400 hand-written edge runs, and 26 command-line comparisons;
  - two random campaigns, with no mismatch and no build failure:
    - its own generator: 202 modules, 28,847 runs;
    - this test's generator on fresh seeds: 70 modules, 52,347 runs.
- **Validated on review, after rebasing onto main:**
  - **CI** reproduced the figures above on rustc 1.99.1: 36 crates built with warnings denied, and 8,875 runs matched (6,205 `ok`, 2,426 `err`, 244 `panic`, 250 skipped at the step limit).
  - **WP5 is unaffected:** all 511 goal queries over the suite and the core library are byte-identical to main's. The suite holds under 10 seeds, and `test_verify.py` passes on a machine with Z3.
  - **A second Codex review** (`gpt-5.6-sol`) of `rust.py` and `test_rust.py` found no further bugs, and confirmed that the tests compare whole outputs and fail without rustc.
- **D80 already fits:** accepted while this was in progress, it says emitted Rust stops at an unproved `err` and keeps its checks at every level, which D95 does.
- **Proposed D95–D97,** numbered after B17-1's D81–D92 and WP6's D93–D94. The branch first proposed them as D93–D95, and its rebase onto main renumbered them:
  - D95: how B17-0 lowers to safe Rust;
  - D96: the emitted binary prints what the interpreter prints;
  - D97: what the differential tests compare, and the pinned toolchain.
- **Interfaces touched:** 5, the trusted base report, which gains WP7's `backend` fields (D25). Interface 10 doesn't change: the binary is a second producer of its text form.
- **Proofs and tests added:** `b17c/test_rust.py`, run in CI, and a `test_check.py` case for `types()`. Every `b17c` self-check passes except `test_verify.py`, which needs Z3.
- **Left admitted:** none.
- **Not yet done:**
  - B17-1's lowering, with data types as Rust enums (D79), once B17-1's spec text exists;
  - WP11's use of the binary for its differential and performance rewards;
  - translation validation, which is WP12's.

## 2026-10-28 · D81–D97 accepted
- **Accepted by the owner:**
  - D81–D92, B17-1's spec text (PR #21);
  - D93 and D94, WP6's interfaces 3 and 8 (PR #22);
  - D95–D97, WP7's readings (PR #23).
- **Refinements recorded:** D91 refines D80's closure for L2, and D92 refines D45's hashing. The headings of D80 and D45 now say so.
- **Still Draft:** `docs/b17-1.md` stays version 0.1 until it freezes with its labelled suite (D44). Interfaces 3, 8 and 11 stay at their Draft versions.
- **Updated:**
  - `docs/b17-1.md`'s status and §14;
  - the roadmap's decisions waiting, now none, and its B17-1 entry;
  - the README's WP7 row.
- **Interfaces touched:** none.
- **Proofs and tests added:** none.
- **Left admitted:** none.

## 2026-10-28 · Documentation audit after WP6, WP7 and D81–D97
- **Checked:** every Markdown file in the repository against the state after PRs #21–#23.
- **README:** the interfaces note listed only the frozen ones. It now gives every Draft interface and its version: B17-1's parts of 1 and 6, 3 and 8 (D93, D94), 10 (D56), 11 with 0.2 drafted (D63, D89), and 5 with WP7's backend fields (D97).
- **Roadmap:**
  - B17-1's row under How the language grows still said its spec text was next. It now says the text is drafted and its decisions accepted, and the suite is next. The Phase 1 table's B17-1 row says the same.
  - The critical-path paragraph now says which work packages are done, and what's left of each path.
  - M3 needed WP5 and WP6, which are done, so its needs are WP8 and the ports.
  - The CI entry now counts seven self-checks, among them WP6's and WP7's.
- **`suite/README.md`:** it now says WP7's differential tests and WP6's `explain` use the suite.
- **Already current:** `docs/b17-0.md` (frozen), `docs/b17-1.md`, DECISIONS.md and the rest of the README.
- **Interfaces touched:** none.
- **Proofs and tests added:** none.
- **Left admitted:** none.

## 2026-10-28 · WP8, the agent reference manual
- **`docs/manual.md`:** B17-0 written for the model that writes it, as the design spec asks of WP8.
  - **What it covers:** how a task is posed; names, types, specs and calls, expressions and statements; ghost code; the seven ownership rules; effects; returns and recursion; every proof goal with its fix; stating ranges (D60); the core library; the toolchain and D93's diagnostic fields; and an index of codes.
  - **The source:** `docs/b17-0.md` stays the semantics. The manual cites it, and a disagreement between them is a bug in the manual.
- **`b17c/test_manual.py`:** WP8's done-when, that every rule and error code has an example, and every example passes `b17c check`.
  - **Each example** is a block after `<!-- expect: OUTCOME -->`, where the outcome is `ok`, a tier 0 code, or a proof family. A block that isn't a whole module is checked inside one.
  - **Proof outcomes:** with Z3, `ok` means every goal is proved, and `E-PROOF-X` means exactly family X fails.
  - **Coverage:** it fails if any code in §9's tables has no example.
  - **The results:** all 37 examples have their stated outcomes, and all 25 codes are covered.
  - **The test can fail:** a mutation check confirmed it. A wrong expectation, an example broken so its proof fails, and a code with its only example removed were each reported. CI runs the tier 0 part.
- **Codex review** (`gpt-5.6-sol`) of the prose against `docs/b17-0.md` found 21 problems, all fixed. The examples were already consistent.
  - **Wrong or misleading:**
    - "operators are binary", though `not` takes one operand;
    - an overflow goal on every operator, where `/` and `%` have `DIV` instead;
    - an `INV-KEEP` fix that suggested an invariant already present;
    - a claim that the manual can't drift, though only its examples are checked;
    - a claim that every proof diagnostic carries a counterexample;
    - advice that a counterexample not reproduced means a weak invariant, when it may just be spurious.
  - **Added:**
    - the fixed clause order and the reading rules;
    - result and binder naming;
    - multiset and sequence subtyping;
    - `let-mut` call bindings, owned arguments and argument order;
    - ordered clauses;
    - mutation kinds and D75's codes;
    - loop measures on normal passes only;
    - lemma bodies;
    - the move-join and slice pass-through rules;
    - effects outside `panic`;
    - D77, and recursive calls' `TERM` goals;
    - each family's full scope;
    - `impact`, `search` and `rust.py`;
    - D93's full fields;
    - the triggers the code table doesn't name.
- **Next on the roadmap:** with WP5, WP6 and WP8 done, M3 can start on the seed tasks, which the suite has already ported. It needs a B17-0 track in the harness.
- **Updated:** the README's status, WP table, layout and self-checks, now eight in CI; the roadmap's work in progress, next steps, critical path, WP8 row and M3's needs; CI.
- **Interfaces touched:** none.
- **Proofs and tests added:** `test_manual.py`, in CI.
- **Left admitted:** none.

## 2026-10-28 · M3's B17-0 track proposed (D98)
- **Proposed:** D98, how M3 poses the seed tasks in B17-0. It uses the same harness, CLIs, round limit and recording as the Dafny baselines, with the manual in the prompt, and verdicts from tier 0 and every goal under 11 seeds. Between rounds, the agent gets `agent.py check`'s JSON.
- **Why it's a decision:** the setup decides what M3 measures, so it goes to the owner before the harness changes.
- **Checked:** every seed program in `suite/accept/` has exactly one spec, so each task's spec is unambiguous. Only `isqrt` carries a proof lemma, which its task leaves out.
- **Updated:** the roadmap's decisions waiting and next steps.
- **Interfaces touched:** none.
- **Proofs and tests added:** none.
- **Left admitted:** none.

## 2026-10-28 · M3's B17-0 track (D98 accepted)
- **Accepted by the owner:** D98.
- **`gym/harness.py`:** the B17-0 track D98 describes, in the same loop as the Dafny track.
  - **Tasks:** `b17/NAME`, one per seed program in `suite/accept/`. `load_b17_task` keeps the program's header, its one spec and the ghost-fns that spec reaches, cut from the source so its layout stays readable. Each task takes its difficulty from the matching Dafny task.
  - **The prompt:** the manual, the task module, and the line the agent's items start on, since diagnostics count lines across the whole module.
  - **`verify_b17`:** the agent's items join the task module. It's verified when tier 0 passes, every spec has a def, and `agent.py`'s diagnostics are empty, with every goal proved under 11 seeds.
  - **The def rule:** specs are modular, so a helper spec with no def would let a call assume its `ensures`. `test_b17.py` shows that such a cheat is refused.
  - **A `b17c` crash** is recorded as `checker_error` instead of stopping the run.
  - **Records** carry `lang`, and summaries count B17-0 as `CLI/b17`, so Dafny summaries, old ones included, don't change.
  - **Settings:** a run with B17-0 tasks also pins `b17c`'s sources, the prompts and the manual, so `resume` and `reverify` refuse if those changed.
- **Checked:**
  - `check-tasks --tasks b17/`: all 20 reference programs verify, and each task with no def is refused;
  - `gym/test_b17.py`: the verdicts, the prompt, and one attempt end to end against a fake CLI, which fails, gets the diagnostics, and verifies in round 2;
  - `gym/test_harness.py`: still passes, so the Dafny track is unchanged.
- **Codex reviews** (`gpt-5.6-sol`), with all findings fixed and tested:
  - **The first** confirmed that the joined module resists stray closing parens and a second module, since the parser takes one module and tier 0 rejects duplicate names. OpenAI's filter then stopped it. It had found that grading and `reverify` trusted the persistent proof cache, so a re-check wasn't independent. Each verdict now gets a fresh cache, as each Dafny verdict is solved anew.
  - **The second**, framed as QA, found no way around the frozen spec in the 20 tasks. It found three bookkeeping faults:
    - a `b17c` crash or a Z3 process error was scored against the agent. Both are now `infra_error`, retried on resume and left out of pass rates;
    - a B17-0 run's settings recorded Dafny's version, so a Dafny upgrade blocked resuming it, and `reverify` didn't ignore the B17-0 prompt as it does Dafny's. Settings are now per language;
    - the `panic` guard read the text, so a header could trip it. It now reads the spec's effects.
- **A guard added:** `ensures` bind only normal returns, so a task spec that allows `panic` would be met by a def that always panics. `check-tasks` flags any such task. None of the 20 seed tasks allows it.
- **Not run:** M3 itself, which spends the agents' subscriptions. It starts when the owner runs `harness.py run --clis claude,codex --samples 3 --tasks b17/`.
- **Updated:** the README's layout, benchmark notes, commands and self-checks; the roadmap's decisions waiting, next steps and M3's needs; D98's status.
- **Interfaces touched:** none.
- **Proofs and tests added:** `gym/test_b17.py`.
- **Left admitted:** none.

## 2026-10-28 · B17-1's labelled suite (D99 and D100 proposed)
- **`suite/b17-1/`:** B17-1's accept/reject suite, as `docs/b17-1.md` §13 describes.
  - **Accept:** 10 AlgoVeri ports, one per feature, each with its frozen contracts and a def.
    - Proofs written in full: `bst_insert`, `bst_search`, `discrete_logarithm` and `longest_palindrome_substring`.
    - `trie_insert` and `lca` each have one step that needs D99, and `segmenttree_query` one that needs D100.
    - `bfs`, `kruskal` and `coin_change` have invariants for bounds, overflow and termination only. Their correctness proofs wait for D99 and D100.
  - **Reject:** 42 programs with one error each. They cover every case §13 lists, and give each new rule of §2–§9 a program.
- **Checked:**
  - **By review.**
  - **Reading:** a scratch check that every file reads as one S-expression module.
  - **Names:** a scratch lint for names that D41 makes unique within an item. It found a case binder used twice in `segmenttree_query`'s `is_segment_tree`.
  - **Neither check is committed.** The parser and checker check these files for real once they read B17-1.
- **Spec text fixed** (`docs/b17-1.md`), where the rules left a label undecided:
  - **§1:** `insert` takes AlgoVeri's `(>= x 0)`, as every other port keeps its u64 constraints;
  - **Arm order:** a misplaced arm is `E-TYPE-001`, not `E-PARSE-001`, since only the checker knows a type's constructor order;
  - **Finite values:** a sequence stops a type's recursion, as a vector does;
  - **`seq-build`:** a runtime `seq-build`'s body is an owned position, so §7's `(seq-build n (fn (i) (vec-new)))` is legal under rule 7;
  - **Slices:** a place rooted at a slice is `E-OWN-003`. A slice is only ever a parameter, so the `E-OWN-002` clause could never apply;
  - **Codes that were missing:**
    - a wrong field or constructor is `E-TYPE-001`;
    - runtime equality on any type but `bool` and `i64` is `E-GHOST-002`;
    - a moving `match`-expression scrutinee is `E-OWN-006`;
    - a ghost type as a spec's parameter or result, or as a runtime binding's type, is `E-GHOST-002`.
- **Found:** a B17 proof can't apply a lemma at every value of a quantifier, which Dafny's `forall` statement does.
  - **The count:** all 24 verified Dafny solutions of `bfs`, `coin_change`, `kruskal`, `lca` and `trie_insert` use that statement, 3 to 53 times each. They come from Claude, Codex, Gemini and Grok.
  - **Why it can't be avoided:** in four of the five tasks, some of those statements range over an unbounded type, which a ghost `while` can't reach.
  - **Proposed:** D99, a `forall` statement over one lemma call.
- **Found, second:** a B17 proof can't name the witness of an ∃, which Dafny's `:|` does.
  - **The count:** 102 of the 327 verified AlgoVeri solutions use `:|`, across 32 of the 64 tasks, among them every solution of `segmenttree_query`, `bfs` and `kruskal`.
  - **Proposed:** D100, an `obtain` statement that proves an ∃ and binds its witness as ghost locals.
- **Codex review** (`gpt-5.6-sol`), against both spec documents and the Dafny originals:
  - **Labels:** no wrong label. Every reject has exactly its labelled error, and every accept passes tier 0. Every port's contracts match its Dafny task, apart from the differences `suite/README.md` lists.
  - **`segmenttree_query`:** its proof isn't complete. Lifting a child's witness to the parent needs a named witness, so it's now marked as needing D100.
  - **`bst_insert` and `bst_search`:** flagged as leaving set reasoning to the solver. Left as they are: each step is one quantifier instantiation, triggered by terms the goal already has, and accept programs carry no hints until the verifier shows a need.
  - **Spec text:** the finite-value rule is now a least fixed point. `E-TERM-002` now names distinct data items, so `(option node)` inside `node` is self-recursion.
  - **D99:** sound, but the arguments' own goals, such as an `idx`'s bounds, were missing. They are now goals for every binder value. D99 also now says how its clauses combine, and that the fact holds along the path.
- **Ponytail review:** four invariants restated facts the loop never changes (b17-0 §9), and `trie_insert`'s one-caller `fresh` helper is folded into `node_of`. All cut, 12 lines.
- **CI caught:** `test_syntax.py` and `test_check.py` collected `suite/` recursively, so they picked up B17-1's files, which B17-0's parser rejects. Both now read only `suite/accept/` and `suite/reject/`. The B17-1 checker will read `suite/b17-1/` once it exists.
- **Updated:** the README's status and layout; the roadmap's progress, decisions waiting, next steps and B17-1 rows; `suite/README.md`.
- **Interfaces touched:** none yet. D99 and D100 would each add a statement to interface 1.
- **Proofs and tests added:** the suite's 52 programs.
- **Left admitted:** none.

## 2026-10-28 · D99 and D100 accepted, and in B17-1's spec text
- **Accepted by the owner:** D99, the `forall` statement, and D100, `obtain`. PR #27, the suite, was merged.
- **`docs/b17-1.md`:**
  - **§2:** both statements in the grammar. `obtain` is now reserved, and their binders are hashed as D92's other binders are.
  - **§7:** their checking, goals and facts, as D99 and D100 state them. A `forall` statement that names something other than a lemma is `E-TYPE-001`. Both may appear in lemma bodies.
  - **§8:** with checking on, a `forall` statement checks nothing, and an `obtain`'s witnesses are unknown (D58).
  - **§9:** their goal families.
  - **§14:** both decisions listed.
- **`suite/b17-1/reject/`:** five programs for the new rules:
  - an `i64` binder;
  - a ghost-fn where a lemma belongs;
  - a returned witness;
  - an `obtain` with no witness;
  - an argument whose bounds don't hold for every binder value.
- **The accept programs' proofs:** the steps that use the new statements wait for WP5 to read B17-1. Then each can be written against the verifier as it fails or passes.
- **Updated:** the roadmap's decisions waiting, next steps and B17-1 row; the README's suite count; `suite/README.md`.
- **Interfaces touched:** interface 1's B17-1 part gains the two statements.
- **Proofs and tests added:** five reject programs.
- **Left admitted:** none.

## 2026-10-28 · B17-1's parser (D101 accepted)
- **`b17c/syntax.py`:** reads B17-1's grammar (`docs/b17-1.md` §2) when given subset 1, and B17-0's exactly as before by default.
  - **The B17-1 forms:**
    - data items;
    - B17-1's types;
    - places in `set-idx` and `push`;
    - `replace`, only as a `let` or `let-mut` initializer;
    - `match`, both as a statement and as an expression;
    - `is`, `field`, `tuple`, `get` with a literal index, and `rank`;
    - the set and map forms;
    - D99's `forall` statement and D100's `obtain`.
  - **Reserved words:** B17-1's 20 new words are reserved only in subset 1, so a B17-0 program may still name a parameter `map`.
  - **The CLI** takes `--subset 1`.
- **D101, proposed here and accepted by the owner:** each tool takes the subset, 0 by default until B17-1 freezes. The reason: B17-1 reserves words that B17-0 programs may use, and it accepts types that B17-0's frozen labels reject.
- **Checked by `test_syntax.py`:**
  - **The suite:** every `suite/b17-1/` file parses and round-trips to the same canonical bytes, except its two `E-PARSE-001` rejects, which fail as labelled.
  - **B17-0's programs:** every B17-0 suite program gives the same tree under subset 1.
  - **Reserved words:** subset 1's are exactly the words `docs/b17-1.md` §2 lists.
  - **Misuse:** each B17-1 form misused once fails at the right line and column.
  - **B17-0 unchanged:** B17-0's tests pass as before, and B17-0 still rejects places.
- **Codex review** (`gpt-5.6-sol`), with all findings fixed and tested:
  - **B17-0 unchanged:** it compared the new parser with the old one, in subset 0, on 100,004 generated valid and malformed inputs. Decisions, canonical bytes, messages and positions were all identical.
  - **Type parameters rejected:** every data type with type parameters, such as `(data box (t) ...)`, was refused. A test had expected a valid declaration to fail, which hid it.
  - **Operators as type names:** a type such as `(+ i64)` was accepted.
  - **Shared state:** the subset was module state, so two threads could read under each other's. The harness parses in a thread pool, so the subset is now per thread.
  - **Untested forms:** `diff`, `update`, tuple patterns, `get` places and `replace` in a `let-mut` had no test. Each now has one.
- **Ponytail review:** places read through a shape table, and `iset-lit` shares `seq-lit`'s branch.
- **Updated:** the README's layout, commands and self-check line; the roadmap's decisions waiting and next steps.
- **Interfaces touched:** interface 1, B17-1's part, now implemented by the parser.
- **Proofs and tests added:** B17-1's cases in `test_syntax.py`.
- **Left admitted:** none.

## 2026-10-28 · B17-1's hasher and tier 0 checker
- **`b17c/hashing.py`** hashes B17-1 under D92, with `subset=1`.
  - **What becomes what:** a data item becomes `_` in its own spec hash, with type parameters `$k`, constructors `#i` and fields `.k`. A reference to a data type becomes its hash, a constructor `H#i`, and a field its index in its operand's type.
  - **The checker's types:** those indexes come from them.
  - **Namespaces:** types and values are apart (D82), so a data type's key is `("data", NAME)`.
  - **B17-0 unchanged:** every B17-0 item hashes as before under subset 1.
- **`b17c/core1.b17`:** the core library's `option` (docs/b17-1.md §9). It's a file of its own, since B17-0's parser can't read a data item.
- **`b17c/check.py`** checks B17-1 with `subset=1`, and B17-0 exactly as before by default (D101).
  - **Names (D82):** types and values are apart. Constructors are value names, and field names are per type.
  - **Well-formed types (D83, §3):**
    - arity;
    - vectors of runtime types;
    - finite values, as a least fixed point;
    - no type inside a set, map or multiset of itself, through other types too;
    - no two types containing each other;
    - variances, with ghost subtyping by them.
  - **Derived properties:** whether a type is runtime, whether it moves, whether it's exact, and which arguments a vector field needs to be runtime.
    - Each is a fixed point over the module's types, with a base and the parameters it depends on.
    - So a type recursing at a growing instance, such as `(d (option a))`, or a chain of 1,100 types, is never expanded.
  - **Expressions and statements:** all of B17-1's.
    - **Constructor calls:** type arguments are inferred from every argument, then the destination. With neither, they default to `int` or `i64` (§4).
    - **`match`:** arms are checked by constructor order and field count.
    - **The rest:** places, `replace`, `forall` and `obtain`.
  - **Ownership (§5):**
    - every moving value moves, not only vectors;
    - a moving value can't come whole out of a place (`E-OWN-007`);
    - a place's root outlives its value;
    - a `match` statement's arms join as an `if`'s branches do;
    - a `seq-build` body moves no outer variable;
    - a new vector is never read as a temporary (rule 7).
  - **Effects (§6):** a constructor with a boxed field allocates.
  - **Duplicate data types:** two identical up to names are `E-TYPE-002` (D92).
- **Readings, recorded here:**
  - **A copy of `option`:** a module's data type identical to the core library's `option` is `E-TYPE-002` too. References to the two would hash alike, which is D92's reason for the rule.
  - **Owned call arguments:** an owned call argument of a moving type is still a variable, as D73 says for B17-0. Rule 7 doesn't widen what a call takes.
  - **Branches:** a moving value inside an `if` or `match` expression's branch is reported once, at the `if` or `match` (D78).
  - **Type parameters:** a type parameter may reuse another data type's name, since D82 bars only its own item's type names.
- **Spec text fixed:** `docs/b17-1.md`'s opening said every B17-0 program is a B17-1 program. Not quite: B17-0 allows `(len (vec-new))`, which rule 7 rejects. It now says this holds for the suite and the core library, and why D101 keeps the subsets apart.
- **Checked:**
  - **The labels:** the checker agrees with all 57 labels of `suite/b17-1/`, each reject with exactly one diagnostic.
  - **B17-0's suite:** all 50 programs give the same codes and positions under subset 1.
  - **Each new rule:** `test_check.py` holds cases for every one, valid and invalid. `test_hashing.py` holds D92's properties.
  - **Unchanged:** every B17-0 self-check, `gym/test_b17.py` and `test_verify.py` pass.
- **Codex review** (`gpt-5.6-sol`), all findings fixed and tested:
  - **First pass:** 12 findings, and no D92 hashing defect.
    - **Silent acceptances:**
      - a vector of a ghost type, or a set of itself, reached through a generic type;
      - an ill-formed inferred type;
      - an open parameter left unresolved;
      - a new vector read as a temporary.
    - **Wrong diagnostics:**
      - `E-OWN-005` in ghost code;
      - inference that depended on argument order;
      - `(call c)` on a constructor reported as undefined;
      - one error reported twice.
    - **A crash:** infinite recursion on `(data d (a) (base) (next (x (d (option a)))))`.
    - **A B17-0 regression:** a ghost-fn named `field` was misread in subset 0.
    - **Declined:** one finding read D82 as barring a type parameter from reusing any type's name. Its order-dependence had already been removed.
  - **Second pass:** OpenAI's filter cut it off. Its log showed two more faults:
    - field vectors were checked before the type summaries were known;
    - `moving()` and `exact()` still expanded instances, so a long chain overflowed Python's stack.
    Both are now fixed points.
  - **Third pass:** five findings. Four were fixed:
    - **Finite values** ignored type arguments, so `(loopc (x (box loop)))` passed. They are now a fixed point over which parameters' arguments need values. A type has a value when any one of its constructors has one.
    - **A nested open constructor,** such as `(hold (empty))`, didn't default. Open parameters now always default when nothing fixes them. A literal operand of `==`, `union`, `diff` or `inter` takes the other operand's type, as §4 says.
    - **Exactness** missed a sequence reached through a generic type. It now tracks which parameters a type holds under a sequence.
    - **A mismatched `if` or `match`** dropped the ownership error of a moving branch.
  - **Declined from the third pass:** that a type argument a data type never stores, as in `(phantom b)`, shouldn't count toward mutual containment, recursion or boxing. The checker counts every type a declaration mentions, for three reasons:
    - §3's containment rule and §6's boxed fields are written in terms of mention;
    - D92 hashes a type over every type it mentions, so two types that mention each other have no hash;
    - a boxed field moves in the emitted Rust.
- **Ponytail review:** the unused field table and a duplicated ownership tail were cut.
- **D44's condition for B17-1 to freeze is met:** the checker agrees with every tier 0 label. Freezing is the owner's call. It would make subset 1 the default (D101), so the B17-0 track and B17-0's tests would then name subset 0.
- **Updated:** the README's status, WP3 row, layout, commands and self-check lines; the roadmap's next steps and B17-1 row; `suite/README.md`'s checking notes.
- **Interfaces touched:** none. Interfaces 1 and 6, B17-1's parts, are now implemented by the checker.
- **Proofs and tests added:** B17-1's cases in `test_check.py` and `test_hashing.py`.
- **Left admitted:** none.

## 2026-10-29 · B17-1's interpreter (D102 proposed)
- **`b17c/interp.py`** runs B17-1 with `subset=1`, or `--subset 1` on the command line, and B17-0 exactly as before by default (D101).
  - **Values (§8):**
    - tuples and data values, printed as `(tuple 1 false)` and `(some 3)` in interface 10's text form;
    - finite sets and maps, as values;
    - a set built by `iset-of`, kept as its predicate. Membership evaluates the body, and equality with it is unknown. So is any set, map or multiset that would hold it.
  - **Places:** `set-idx`, `push` and `replace` take places through `idx`, `get` and `field`. They evaluate the indices in source order and then the value, and check each step on the way down, as B17-0's `set-idx` does. An update builds the new root with one part replaced.
  - **Expressions and statements:** `match`, `is`, `field`, `tuple`, `get`, `rank` as height, and the set and map operations.
    - A field the constructor lacks is `err FIELD` in runtime code and a `FIELD` contract outcome in ghost code. A lookup outside a map is a ghost `BOUNDS`.
    - A `forall` statement checks nothing.
    - `obtain` records its ∃ as an unchecked `ASSERT`, and its binders are unknown.
  - **B17-0's words stay free in subset 0:** a B17-0 ghost-fn named `union` still runs.
- **D102, proposed:** a leading guard conjunct `(contains E x)`, with E a finite set, a sequence or a map, ranges binder x over E's members, for x of any type but `bool`, which already ranges over both values. An empty E makes the guard hold nowhere. It applies in both subsets.
  - **Why:** without it, `bst_insert`'s `is_bst` was unknown on every tree but a leaf, so every precondition went unchecked. A non-search-tree input then failed the def's `ensures`, not the `requires`.
  - **Effect:** every clause of `bst_insert` and `bst_search` is now evaluated on the suite's inputs.
  - **B17-0:** its suite has no such guard, so its outcomes are unchanged.
- **The suite:**
  - **Accept programs:** all 10 run, on one to four inputs each, with the results the specs fix. The same runs with checking off agree.
  - **Unchecked clauses:** these are the ones that quantify over paths, sequences, every int, or a ghost-fn's predicate.
  - **Proof rejects:** of the five, three have a def or ghost-fn, and each shows its fault on a concrete input: `replace` out of range, a field the constructor lacks, and a lookup outside the map. The other two are lemmas, whose bodies never run (D57).
  - **B17-0's suite** gives the same outcomes under subset 1.
- **Codex review, first pass:** five findings. Three were fixed:
  - **A recursive ghost-fn call** with a set built by `iset-of` as its argument ran to the depth limit, instead of failing `TERM` at once (D57). Such arguments now key the memo by identity, and the key keeps its value alive, so no other value takes its id.
  - **Arguments with the wrong number of fields,** such as `(some 1 2)`, were accepted as data values.
  - **An empty membership collection** for a later binder left the quantifier unknown. It now makes the guard hold nowhere, as an empty range from comparisons does.
- **Declined from the first pass:**
  - **That `(== s s)` should be unknown** when s holds an `iset-of` set. The two sides are the same value, so the clause holds by reflexivity. A predicate set is now equal to itself directly too, as it already was inside a tuple.
  - **That D102 should bound `bool` binders.** Their two values are always listed, and a point outside the guard makes `=>` false before the body runs, so bounding them saves only fuel. D102 now names `bool` as the exception.
- **Codex review, second pass:** six findings, all fixed:
  - **A set built by `iset-of` lost its context.** A member is often tested after the ghost-fn that built the set has returned. A recursive call inside its body then wasn't seen as recursive, and ran to the step limit instead of failing `TERM`. A failure there was also charged to the clause that tested the member, not to that ghost-fn's body (D57). Testing a member now runs inside the calls and the clause that built the set.
  - **The identity key was shallow:** a new sequence holding the same predicate set wasn't seen as the same argument. Only the predicate sets inside a value are now keyed by identity.
  - **Membership didn't reach comparisons:** in `(and (== x y) (contains (seq-lit 1) y))`, y's members didn't bound x. Members now bound an `int` binder's range like a comparison does.
  - **A sequence of predicate sets** couldn't bound a binder, since its members were deduplicated by hashing. A sequence's members are now taken in order. A repeated member is evaluated twice, which changes nothing.
  - **`--subset 0` was refused** by `interp.py`, `check.py` and `hashing.py`, though D101 names both values. All four tools now take it, as `syntax.py` already did.
- **Codex review, third pass:** four findings, all fixed:
  - **The calls in progress:** a set's restored context brought back the frames but not the calls in progress. With an unknown measure, a same-argument call inside the set still ran to the step limit. It now restores those too.
  - **Shared frames counted twice:** testing a member in the call that built the set counted the calls both stacks share twice, and could reach the depth limit early. They now count once.
  - **Map values:** a map's values can hold a predicate set, since only its keys are hashed when it's built. The memo key now reaches them.
  - **`hashing.py --subset 0`** still chose subset 1. `test_hashing.py` and `test_check.py` now run both CLIs with each subset.
- **Updated:** the README's status, WP15 row, layout and commands; the roadmap's status, decisions waiting, next steps and B17-1 row; `suite/README.md`'s checking notes; `docs/b17-1.md` §8 and §14.
- **Interfaces touched:** interface 10 gains tuple and data values and the `FIELD` reason, as `docs/b17-1.md` §8 already said.
- **Proofs and tests added:** B17-1's section of `test_interp.py`: the suite, each §8 rule, D102, every review finding, the text form, argument checks and the command line. `test_check.py` and `test_hashing.py` run their CLIs with `--subset 0` and `--subset 1`.
- **Left admitted:** none.

## 2026-10-29 · D102 accepted
- **The owner accepted D102:** membership in a finite collection bounds a quantifier's binder, of any type but `bool`, when the interpreter checks a run. It extends D58, in both subsets.
- **Updated:** D102's status in `DECISIONS.md`; `docs/b17-1.md`'s status line and §14; the roadmap's status and decisions waiting.
- **Interfaces touched:** none.
- **Proofs and tests added:** none. `test_interp.py` already covers D102.
- **Left admitted:** none.

## 2026-10-29 · B17-1's verifier (D103 and D104 proposed)
- **`b17c/goals.py` and `b17c/verify.py`** verify B17-1 with `subset=1`, or `--subset 1` on the command line, and B17-0 exactly as before by default (D101).
  - **B17-0 is byte-identical:** every one of the 511 queries of B17-0's suite and core library is the same as before. The sequence prelude is now a template per element sort, and it reproduces B17-0's prelude exactly.
  - **The encoding (D89, refined by D103):**
    - each data-type instance is a datatype, declared together with the instances it refers back to;
    - tuples are a datatype per arity;
    - sequences of any element sort get §9's facts;
    - sets are arrays to `Bool`, with `iset-of`, `union`, `inter` and `diff` as lambdas;
    - maps are arrays to `option`;
    - `rank` is a function per data sort, with D89's axioms through tuples and sequence elements.
  - **New goals:** `FIELD` guards every selector of a type with more than one constructor. Places carry `BOUNDS` for each `idx` and `FIELD` for each `field`, and a map lookup carries `BOUNDS`. `FIELD` counts toward L2's runtime families.
  - **`match`:** each arm's binders are the scrutinee's selectors, under its constructor's test. Statement arms join as an `if`'s branches do.
  - **Updates through places:** `set-idx`, `push` and `replace` rebuild the root with one part replaced. Indices run first, then the value, then each step's goal.
  - **D99's `forall` statement:**
    - its arguments' goals hold at every point;
    - a lemma applying itself through one gets ∀x. requires ⇒ its measure drops;
    - the fact is ∀x. requires ⇒ ensures.
  - **D100's `obtain`:** its body's goals hold at every point, then ∃x. e is an `ASSERT`, and its names become constants with e assumed.
  - **Names:** B17-1's sorts, constructors and functions get generated names, which the canonical form renames. Renaming a data type, constructor or field leaves every proof in the cache, and a query declares only what it uses.
- **`b17c/check.py`:** a `match` statement's scrutinee is now typed when it's a variable. `types()` had left it out, and WP5 needs every expression's type.
- **The suite:**
  - **Proof rejects:** all 5 fail exactly their labelled goal.
  - **Written proofs:** `bst_insert`, `bst_search` and `discrete_logarithm` prove every goal under 10 shuffled seeds.
  - **Mutants:** breaking a written proof, such as inserting into the wrong subtree or dropping `is_bst` from the `requires`, leaves its goal unproved. So the encoding isn't vacuous.
- **Findings:**
  - **`bst_insert` was brittle:** with array maps for set operations, its `is_bst` postcondition proved under 6 of 11 seeds. As lambdas it proves under all 11, using about 2% of the units, so D103 makes them lambdas.
  - **`longest_palindrome_substring`:** one invariant of its outer loop proves under 9 of 10 shuffled seeds, using up to 7M of the 10M-unit budget. Its query uses only B17-0's encoding, so a B17-0 program could meet the same limit. The program is left without hints, as the suite's rules say.
  - **`bfs`:** its measure and one invariant count `-1`s in a vector built by `seq-build`. §9's multiset facts don't cover such a vector, so those goals don't prove.
  - **Not finished:** the correctness proofs of `bfs`, `kruskal` and `coin_change`, and the D99 and D100 steps of `trie_insert`, `lca` and `segmenttree_query`. They come next.
- **Codex review, first pass:** seven findings, all fixed. Two were soundness holes that reached B17-0 too: the verifier proved `false`.
  - **Recursive ghost-fns:** a recursive ghost-fn's equation held for every SMT value of its parameter sorts, while its measure was proved only for values of its parameter types. So a ghost-fn recursing on an `i64` outside `i64`'s range, which SMT allows, proved `bad(x) = not bad(x)`, and so `false`. The equation now holds only for arguments of the parameter types (D103).
  - **`seq-build` under a binder, or in a ghost-fn's body,** was one global constant whose facts were dropped, the same for every binder value. An `exists` over its length, or two calls of a ghost-fn built on it, proved false claims. It's now a function of the bound variables, with its facts quantified over them (D103).
  - **B17-0's queries:** both B17-0 cases are in `test_verify.py`. No B17-0 suite query changed, so no suite proof relied on either hole.
  - **Growing recursion** like `(data nest (a) (stop) (more (next (nest (option a)))))` sent the verifier into endless expansion. D104 makes tier 0 reject it, with `suite/b17-1/reject/E-TYPE-001-growing-recursion.b17` as its label.
  - **Missing facts:**
    - a data value's `i64` fields now fit, through a validity predicate per data type;
    - nested sequences now compare by elements;
    - an update through a place now keeps §9's multiset fact;
    - a multiset of an empty sequence of data no longer gives an ill-sorted query.
- **Codex review, second pass:** OpenAI's content filter cut off the first attempt. A rerun with plainer wording found nothing that proves a false claim.
  - **Confirmed:** the validity predicate's axioms are consistent, and no fact mentions a variable outside its binder. All 29 B17-0 suite files give byte-identical queries.
  - **Two findings, both fixed:**
    - **A recursive call in a ghost-fn's own `requires` or measure** had no `TERM` goal, since the caller's measure was set only after them. This was a gap in B17-0 too, which the interpreter already closed (D57).
    - **A lifted `seq-build` that calls its own recursive ghost-fn** was declared before that function, so the query was malformed.
- **Updated:** the README's status, WP5 row, layout, commands and self-check lines; the roadmap's status, decisions waiting, next steps and B17-1 row; `suite/README.md`'s verdicts and checking notes; `docs/b17-1.md` §9 and §14.
- **Interfaces touched:** interface 11 v0.2, as D103 refines it.
- **Proofs and tests added:** B17-1's section of `test_verify.py`:
  - the suite's written proofs and proof labels, and two mutants;
  - each encoding rule with a passing case and a failing one: `rank`, `FIELD`, tuples, sets, maps, places, `match` statements;
  - D99 with and without its statement, and a lemma that applies itself;
  - D100's witness;
  - cache hits after renaming;
  - each review finding, the soundness holes in both subsets, and a true claim built the same way, which proves.
- **`test_check.py`:** D104's rule, and two older tests that used growing recursion incidentally.
- **Left admitted:** none.

## 2026-10-29 · D103 and D104 accepted
- **The owner accepted D103 and D104:**
  - **D103:** how the verifier encodes B17-1, refining D89 and, through its two soundness rules, D61.
  - **D104:** a data type's recursion is regular.
- **Headings:** following the log's convention, they now record each refinement: D61 and D89 are refined by D103, and D83 by D104. D58 now records that D102 refines it, which its acceptance earlier today left out.
- **Updated:**
  - D103's touches gain D61;
  - `docs/b17-1.md`'s status line and §14;
  - the roadmap's decisions waiting, next steps and B17-1 row;
  - the roadmap's WP5 status, now that the soundness fixes reach B17-0 and the suite's queries are unchanged;
  - the README's WP5 row, which now says so too, its `verify.py` row and interface 11's line;
  - `docs/b17-1.md` §9's encoding heading, which now names D103.
- **Interfaces touched:** none.
- **Proofs and tests added:** none. `test_verify.py` and `test_check.py` already cover both decisions.
- **Left admitted:** none.

## 2026-10-29 · WP7 for B17-1: the Rust backend under subset 1 (D110 and D111 proposed)
- **Asked by the owner:** extend the Rust backend to B17-1 under `--subset 1` (D101), with B17-0's output byte-identical by default, checked like B17-0's on the accept programs, the runnable proof rejects, corner cases and generated programs.
- **`b17c/rust.py`** lowers B17-1 with `subset=1`, or `--subset 1` on the command line (D110):
  - **Data types** become enums in a module of their own, `data`, so their names can't clash with the program's, or with names Rust and the runtime use, such as `str`, `std` and `rt`, which B17-1 allows as type names.
    - **Type parameters:** only those a value can hold are Rust's, since Rust rejects a parameter no field uses. Tier 0 already computes that set.
    - **Boxes:** a field that mentions its own type outside a vector is a `Box` (D86), and a `match` binder for one takes the value out of it.
    - **Copying:** a type that moves only through its arguments, or never, derives `Clone` and `Copy`. So `(option i64)` is copied and `(option tree)` moves, as §5 rule 1 says.
  - **Reading:** `field` calls a method of the type that stops the run with `err FIELD` and the interpreter's detail when the constructor lacks the field. `idx`, `field` and `get` read a moving value through a reference, so it never leaves its place.
  - **Updating through a place:** the place's indices, then the statement's index and value, are evaluated into temporaries. The place is then walked from its root as `&mut` references, checked on the way down as the interpreter does, and changed where it is. `replace` is `std::mem::replace`.
  - **`match`** is Rust's `match`. Constructors name their type arguments, and every literal is typed `i64`.
  - **The binary** reads arguments as interface 10's terms, nested values included, under the parser's lexical rules (D48, D49, D55), and prints results as the interpreter does.
  - **B17-0 unchanged:** without a subset, the runtime and every crate are the same bytes as before. This was checked after every change on 235 modules: B17-0's 29 suite programs that pass tier 0, the corner and deep modules, and 204 generated modules.
- **D112, drafted and withdrawn:** Rust compiles generics one instance at a time, so a data type that recurses at a growing instance, such as `(data d (a) (base (v a)) (next (x (d (option a)))))`, has no finite set of Rust types, and rustc refuses it (E0320). The branch first proposed D112, an `emit()` refusal. On rebasing, main's D104 already rejects such types in tier 0 for the verifier's sake, so D112 and its check are gone, and every module that passes tier 0 builds.
- **WP7's done-when holds for B17-1:**
  - **Compiles:** every B17-1 module that passes tier 0 builds with warnings denied and unsafe code forbidden, across every module below. The self-check builds 58 crates, 22 of them B17-1's: the 15 suite programs that pass tier 0, the corner module and 6 generated modules.
  - **Matches:** 12,666 runs print exactly the interpreter's text, 3,791 of them B17-1's. B17-0's 8,875 are unchanged. B17-1's runs cover:
    - **the accept programs,** on `test_interp.py`'s inputs, both the spec's examples and the inputs outside its `requires`;
    - **the two proof rejects whose defs reach their faults:** `err BOUNDS` from `replace` and `err FIELD`;
    - **random inputs,** 40 per def;
    - **72 corner runs** that state the text both must print;
    - **96 generated defs.**
  - **The corners cover:**
    - names Rust reserves or uses, and parameters no value holds;
    - `FIELD` and `BOUNDS` in expressions and through places;
    - the order of a place update: indices, then value, then the checks from the root out;
    - `replace`, `match`, tuples and open type arguments;
    - 24 arguments the binary must refuse, as the interpreter does;
    - a list a million long, which only the binary runs, and which Rust drops on the run's own stack.
  - **The command line:** `rust.py --subset 1 --run` prints what `interp.py --subset 1` prints, with the same exit code, in 9 cases.
- **Fuzzing,** with the self-check's generator, 12 defs and 20 inputs a module:
  - **120 modules, 28,473 runs:** found one generator bug. A constructor inside an `assert` typed its literal as `int`.
  - **400 modules, 95,779 runs.**
  - **300 more, 71,793 runs,** on the simplified code.
  - **100 more, 23,959 runs,** on the rebased branch.

  No mismatch and no build failure.
- **Mutation check:** 33 changes to B17-1's lowering and runtime, all caught by the self-check. Two were caught only after tests were added: an argument holding two terms, and a nesting limit off by one. One targeted D112's check, since removed.
- **QA review,** an independent bug hunt, found one bug, now fixed and tested: the binary accepted argument text the interpreter's parser refuses, with no whitespace between a list's elements (`(cons 1(nil))`, D49) or nested past 128 (D55). `rust.py --run` wasn't affected, since it re-reads arguments through the interpreter. What it confirmed:
  - **Its own type-directed fuzzer:** 391 modules, 133,356 runs. It used generic and phantom parameters, recursion through `option`, tuples, vectors and other generics, and random deep places.
  - **The self-check's generator on new seeds:** 420 modules, about 167,000 runs.
  - **That generator's statements over random declarations:** 384 modules, 38,238 runs.
  - **B17-0's programs under subset 1:** 161 modules, 32,792 runs.
  - **Targeted cases:** about 90, plus 85 argument texts and 14 command-line runs.
  - **B17-0 byte identity:** confirmed on 111 modules.
- **Ponytail review:** 20 simplifications, all applied, with the self-check's counts unchanged.
  - **What changed:** reading and changing a place became one walk. Patterns name their type through the constructor. Helpers are shared with `check.py` and B17-0's generator, and the B17-1 generator reads its types from its own declarations.
  - **Size:** `rust.py` lost 87 lines and gained 62, and `test_rust.py` lost 139 and gained 72.
- **Codex review: not run.** Codex.app's bundled CLI was killed by macOS with "Code Signature Invalid", and the app had left `/Applications` by the next check. The owner chose to have the branch pushed without a pull request and to run the Codex review before one is opened.
- **For the owner, about the interpreter:** `interp.py` prints values by recursion, so a value nested about 600 deep, such as a list of 600, can't be printed: `text_of` raises `RecursionError`, and the command line exits with a traceback. The binary prints it. The interpreter isn't this task's file, so this is only reported.
- **This Mac still links Rust only with `DEVELOPER_DIR=/Library/Developer/CommandLineTools`,** as WP7's entry describes.
- **Updated:** `DECISIONS.md` (D110 and D111, proposed); the README's status, WP7 row, `rust.py` row, self-check line and a B17-1 example; the roadmap's recent work, decisions waiting, next steps, and WP7 and B17-1 rows.
- **Interfaces touched:** none. Interface 10's B17-1 values (`docs/b17-1.md` §8) are now the binary's text too.
- **Proofs and tests added:** B17-1's section of `b17c/test_rust.py`, which CI already runs. Every `b17c` self-check passes except `test_verify.py`, which needs Z3.
- **Left admitted:** none.
- **Not yet done:** the Codex review, and the pull request.

## 2026-10-29 · Review of WP7 for B17-1, and its pull request
- **Asked by the owner:** review the branch `b17-1-rust` and open a pull request once it passes.
- **The branch:** five commits on current main. Each is authored as the owner, with no attribution lines. D110 and D111 are numbered in the range kept for this work.
- **Checked here:**
  - **Every self-check but `test_rust.py`:** syntax, hashing, interpreter, core library, checker, agent protocol, manual, verifier, and the B17-0 track. All pass.
  - **`test_rust.py`** needs rustc 1.99.1, which this arm64 Mac doesn't have. It runs in CI on the pull request.
  - **Emission:** every B17-1 accept program emits a crate.
  - **B17-0 unchanged:** all 50 of B17-0's suite files give the same output as main's backend: crates for those that pass tier 0, diagnostics for the rest.
- **Codex review:** the one the branch's entry left to run. Run as QA against `interp.py` and `docs/b17-1.md` §3, §5, §6 and §8, it found no output that would differ from the interpreter and no checker-accepted module that would fail to compile. It confirmed B17-0's output is unchanged. It reasoned from the code, since it couldn't compile either, so CI's differential tests are the check that runs it.
- **Ponytail review:** one finding, applied. `rust.py`'s `_type` and `goals.py`'s `ttype` converted type forms the same way, and were written in parallel. They're now one function in `check.py`, the type authority, which both import. Every B17-0 query, every B17-0 crate, and every B17-1 crate is the same, byte for byte, before and after.
- **Also fixed:** a missing blank line before D110's heading.
- **Still for the owner:** the branch's entry reports that `interp.py` can't print a value nested about 600 deep, since `text_of` recurses. That's the interpreter's, so it's left for its own change.
- **Updated:** `DECISIONS.md`'s spacing; nothing else in the docs needed changing.
- **Interfaces touched:** none.
- **Proofs and tests added:** none. The refactor is covered by the existing self-checks and the byte comparisons above.
- **Left admitted:** none.
