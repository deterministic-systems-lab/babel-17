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
