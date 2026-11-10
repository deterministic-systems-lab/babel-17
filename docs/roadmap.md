# Babel-17 roadmap

Where the project stands, and what comes next. This is the state as of 2026-11-09.

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

## Where we are: Phase 1's gate has passed

### The Phase 1 gate

The owner declared it passed on 2026-11-06, so Phase 2 begins. The Phase 1 work that isn't part of the gate goes on, listed [below](#phase-1-work-outside-the-gate).

| Gate item | State |
|---|---|
| **B17-1 frozen** | Done. Version 1.0 and its suite froze on 2026-10-30 under D44, and D113 and D114 amended it to version 1.2. |
| **Every ported task verifies end to end** | Done. On 2026-11-06, from an empty cache, all 5,716 goals of the 35 accept programs, B17-0's 20 seed ports and B17-1's 15 AlgoVeri ports, proved under 10 shuffled seeds (D23). `coin_change`'s proof needed a fix first ([below](#recent-and-current-work)), and `test_verify.py` now checks all 35. |
| **Every ported task runs as emitted Rust** | Done. On the self-checks' 154 inputs, each binary printed what the interpreter prints, and each checked run was ok with the expected results. |

### The Phase 0 gate

All three items held, so Phase 1 began on 2026-10-28. Two pieces of Phase 0 that aren't part of the gate are still open, listed [below](#phase-0-work-outside-the-gate).

| Gate item | State |
|---|---|
| **WP1a frozen** | Done. B17-0 v1.0 ([b17-0.md](b17-0.md)) and the 50-program [suite](../suite/) froze on 2026-10-28 under D44, once WP3's checker agreed with every tier 0 label. D107 amended B17-0 to v1.1 on 2026-10-29, loosening only its subtyping, and D114 to v1.2 on 2026-11-02, giving `push` a goal on its vector's length. D66–D78, the readings the checker settled, are written into `b17-0.md`. |
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
- **M3's first run** (`20261029T232328Z-claude-codex`): the seed tasks in B17-0, 3 samples each. Claude verified 59 of 60 and Codex 55, against 120 of 120 each in Dafny's two seed runs. Every verdict reproduced.
  - **Every failure is on `insertion_sort` or `partition`.** The verifier knows how `set-idx` changes a vector's multiset, so a swap keeps it with no proof, but the manual didn't say so. The round-1 passes relied on it, and the failures tried to prove it themselves.
  - **What stopped them:** for Codex, multisets of `int` and `i64` not comparing (D70), which got 26 of its 104 calls rejected, and swap lemmas it couldn't prove. For Claude, a gap in the encoding: equal sequences don't give equal multisets.
  - **Tokens:** the manual then added about 11k input tokens to each of Claude's calls and 8k to Codex's. On the 18 other tasks, Claude thought about nine times as much as in Dafny, and Codex about as much.
  - [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **M3's rerun of `insertion_sort` and `partition`** (`20261030T154025Z-claude-codex`), with the fixes below: all 12 attempts verified in round 1, where the first run verified 6 of them. Every verdict reproduced.
  - **The manual made the difference.** The rerun's programs verify with the first run's `b17c` too, without D107 or D108. None states a lemma: each keeps the multiset as an invariant and swaps with two `set-idx`s, as the manual's example does.
  - **Against Dafny on the same tasks:** both languages verify all 12. Claude used about 4.6 times Dafny's tokens per verified task, and Codex about 1.2 times. The manual now adds about 14k input tokens to each of Claude's calls and 10k to Codex's.
- **M3's first B17-1 run** (`20261030T234603Z-claude-codex`): the 10 AlgoVeri ports, 3 samples each. Claude verified 30 of 30 and Codex 27, against 20 of 20 and 18 of 20 on the same tasks in Dafny's two AlgoVeri runs. Every verdict reproduced.
  - **Codex failed all 3 `kruskal` samples,** as it failed both Dafny runs. Two of them passed through the verifier's length hole, found in the next run, and aren't counted.
  - **One of Claude's `kruskal` passes is an exhaustive search,** found by D118's audit on 2026-11-04. Its proof is real, but it tries every sequence of n − 1 edges, so it can't finish on 10 vertices.
  - **Cost:** Claude used about 4.5 times Dafny's tokens per verified task and Codex about 1.9 times, mostly the manual and its supplement in the prompt. Claude also thought about 4.6 times as much.
  - **Unbalanced parentheses** failed 22 of the 120 rounds, against 2 of 175 in B17-0's seed run. A missing `)` was reported at the module's first line, or at the last item still open, so agents repeated it, for up to four rounds. The parser now names the item that probably lacks it.
  - **Counterexamples:** 4 of the 137 failed-goal diagnostics had one. Most failed goals took a data value with a sequence inside, which no model term showed then.
  - [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **M3's run of WP10's five harder ports** (`20261102T173606Z-claude-codex`): `prim`, `dijkstra`, `bellman_ford`, `edmond_karp` and `push_relabel`, 3 samples each. Claude verified 15 of 15 and Codex none, against 10 of 10 and 6 of 10 on the same tasks in Dafny's two AlgoVeri runs.
  - **A hole in the verifier:** a vector pushed past 2^63 − 1 elements made every later goal provable, since `push` had no goal and the encoding then stated both that its length was 2^63 and that no vector's was. All 8 of Codex's passes were this, as were 2 in the first B17-1 run. None of Claude's programs used it. D114 closes it with a goal at every `push` ([below](#next-on-the-critical-path)).
  - **Codex mostly looked for a way around the proof.** It attempted the algorithm in 5 of its 15 samples, and none passed.
  - **Cost:** Claude used about 3.3 times Dafny's tokens per verified task, with programs of 917 lines at the median against 548.
  - **The harness lost 5 of Claude's 35 replies.** Claude Code reported only the last part of replies that ran to 132k–142k output tokens, so the code block was missing or cut. The harness now reads every part ([below](#next-on-the-critical-path)).
  - [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **M3's rerun of the five harder ports** (`20261102T233256Z-claude-codex`), with D114 and Claude's replies read whole: Claude verified 15 of 15 and Codex none. Every verdict reproduced.
  - **Claude:** 6 in round 1, 1.73 rounds on average against 2.33, and about 2.4 times Dafny's tokens per verified task, against 3.3. No reply was lost. All 15 programs gave the right answer on 25 random valid graphs each, against independent references.
  - **D114's goal** failed in none of the 130 rounds with code. 9 of Claude's 15 verified programs push.
  - **Codex stopped trying the trick, and rarely tried the proof.** Its median round was 637 characters, against 24,383 on these tasks in Dafny. It thought about 2.4 times as much per call and wrote about a quarter as much. It wrote no loop for either maximum-flow task, returned 0 in 22 rounds, and declined in 16, saying it couldn't guarantee a pass without running the checker.
  - **Parentheses** stopped its longest attempts: 15 of its 24 `dijkstra` rounds failed to parse. 6 of the run's 15 rounds with unbalanced parentheses had two or three such items, reported one per round.
  - [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **M3's run of Codex under D115's prompt** (`20261103T171929Z-codex`): B17-1's first line worded as Dafny's, and a rule saying that diagnostics come back for repair. It verified none of 15 again. Every verdict reproduced.
  - **It still doesn't attempt the proofs.** 13 of its 15 first rounds are under 4,000 characters, and none of its 6 maximum-flow samples wrote a loop. So the wording isn't the cause. D115's rule sends the prompt back, but the owner kept it.
  - **It nearly stopped declining,** in 2 rounds against 16. On maximum flow, 27 of its 48 rounds put the task's guarantee on a helper spec instead, against 5. All 27 were caught.
  - [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **M3's run of Codex with a worked proof in the prompt** (`20261103T191348Z-codex`), D116: Codex verified 3 of 15, all of `dijkstra`, after none of 45. Every verdict reproduced, and all three programs gave the right answer on 25 random valid graphs each.
  - **It writes far more:** 8 of 15 first rounds are over 7,000 characters, against 1, and its median round is 13,412 characters, against 2,006.
  - **Not on maximum flow:** 1 of 6 samples has a loop, below D116's 3, and that one is an exhaustive search over flow matrices, not push-relabel. `edmond_karp` stayed under 1,600 characters.
  - **Parentheses are now the largest cause of rejection:** 22 of its 117 rounds have unbalanced items, and 9 of those have two to four, reported one per round.
  - **The example has come out,** as D116 provides. [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **E-PARSE-001 names every unbalanced item, and `bfs` is the supplement's worked proof (D117).** Replayed on all 769 recorded B17 rounds, no parse outcome or error position changes. Of the 98 that fail to parse, 79 get the new note, 26 of them naming two to four items, and making the fixes it names lets the reader finish in 78. None of the 18 that are grammar errors gets a false one.
- **M3's run with the worked proof in the supplement** (`20261103T220624Z-claude-codex`): Claude verified 15 of 15 and Codex none. Every verdict reproduced.
  - **Claude:** 212k tokens per verified task against 250k, about 2.0 times Dafny's against 2.4, in 1.60 rounds against 1.73. Its programs borrow lemmas from the example, but that fall isn't shown to be the example's (p of about 0.25, with tasks moving different ways). All 15 programs gave the right answer on 25 random valid graphs each.
  - **Codex's attempts stayed long, but `dijkstra`'s 3 passes didn't repeat.** Its median round was 15,306 characters, against 2,006 without the example.
  - **Maximum flow:** 4 of Codex's 6 samples wrote loops, and all 17 such rounds are exhaustive searches over flow matrices. All 4 of its final maximum-flow programs in Dafny, including its one pass, and one of Claude's passes there, are the same kind. Only 1 of Claude's 3 `push_relabel` programs in B17-1 is push-relabel, and the others find augmenting paths.
  - **E-PARSE-001's note:** in none of the 7 rounds after it were the parentheses unbalanced again, against 16 of 36 before. [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **A standing run-time audit of verified programs (D118).** `gym/audit.py` runs a run's verified B17 programs on 25 random valid inputs, with a limit of 500M steps each, against a reference written separately for each of the 34 tasks.
  - **All eight B17 runs:** of the 235 audited, 224 are right, and none gives a wrong answer. The 6 for `bfs`, no longer a task, aren't audited. The other 11 run out of steps: Codex's 10 passes through the length hole, all on the first input, and one of Claude's `kruskal` programs, an exhaustive search.
  - **Slow isn't flagged:** two other `kruskal` programs of Claude's need about 400M steps, since they scan every edge at each of 200,001 weights, and they're right. [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **M3's run of all 14 ports under one prompt** (`20261104T231447Z-claude-codex`): Claude verified 42 of 42 and Codex 25 of 42, against 28 of 28 and 22 of 28 in Dafny. Every verdict reproduced. All 67 programs are right under D118's audit, and none is near its limit.
  - **Cost:** Claude at about 2.5 times Dafny's tokens per verified task, 3.8 on the 9 easier ports and 2.0 on the 5 harder ones, and Codex at about 2.8. About a third of Claude's tokens are the fixed prompt.
  - **Codex:** 23 of 27 on the 9, against 16 of 18, and 2 of 15 on the 5, against 6 of 10, both in round 8. On maximum flow, one round used BFS, the first in B17, and the next went back to a search.
  - **A repeat of the 5:** Claude's total came out at 215k against 212k, with single tasks moving by up to about 1.7 times.
  - **Long diagnostics are cut:** the harness's limit of 6,000 characters cut 21 of Codex's 161 repair prompts, against 2 of 89 in Dafny, and hid 178 of those prompts' 450 diagnostics. [ACTIVITY.md](../ACTIVITY.md) has the full analysis.
- **B17's feedback ends at a whole diagnostic (D119).** A repair prompt holds the diagnostics that fit in 6,000 characters whole, and says how many more there are. On all 813 recorded rounds an agent read, the 744 under the limit are byte-identical. It shows no more diagnostics than before, and no run has used it yet. Dafny's track doesn't change.
- **B17-1's verification levels (WP5), D120.** `verify.py --level L0|L1|L2|L3` fails unless a module reaches that level, and `--report` gives the level and why, as `docs/b17-1.md` §10 says.
  - **L1's property tests:** the interpreter runs each def, checking on, on D88's inputs, and records each goal it evaluates. Tests run only when some goal isn't proved.
  - **L2's closure:** each proved goal is solved again without what rests on goals that don't count: earlier goals, callees' `ensures`, lemmas' claims, loop invariants and ghost-fns' equations (D91).
  - **Checked on the suite:** a program reaching every goal family has all 58 of its goals evaluated. No accept program has a goal refuted. In 10 of the 15 proof rejects a test refutes the labelled goal, and in 4 no test reaches it. The last, `E-PROOF-DIV-min-rem-minus-one`, reaches L1, since only i64's least value over −1 fails it, and it's listed as a goal that may abort.
  - **Every query is unchanged:** all 5,824 of the suite's and the core library's queries are byte-identical, and so are those of the 110 verified M3 programs that use `seq-build`, where the one change in encoding could reach. So M3's verdicts don't move, though cached ones are solved again, since the cache's key includes `b17c`'s own hash.
  - **Limits:** random inputs meet few graph tasks' `requires`, and some runs are slow, as D120 records.
- **WP4b, the spec workbench, D121.** `b17c/spec.py` runs the design spec's checks on a spec, as the owner chose them: Codex for back-translation, signatures by spec hash, and a surviving mutant one that verifies.
  - **On the worked example,** `merge_sorted`:
    - its `requires` can hold, and neither `ensures` clause is trivial;
    - each witness forbids an output that loses an element and one out of order;
    - of 23 mutants, 22 are killed and the survivor computes the same results;
    - Codex's English matches the spec, and it found two places where the header says what the spec doesn't.
  - **On the suite:** no spec's `requires` is shown vacuous, and no `ensures` clause is proved trivial. 50 of the 75 clauses are shown not to be, by an input and output that make them false, and 25 stay unknown. For 7 of B17-1's specs, 6 of them graph tasks, whether the `requires` can hold stays unknown: the solver finds no model, and random inputs don't meet them.
  - **A limit:** 15 of the 22 mutants were killed only through the def's own invariants, so a weak spec can hide behind a strong proof.
- **WP16, the core spec library,** is under way. Its first part is merged (PR #9).
  - `b17c/core.b17` holds `sorted`, `in_i64`, `seq_update`, and 33 laws as lemmas: §9's background facts with D61's derived `contains` facts, and the laws of integer order.
  - **The interpreter confirms every law** at every point of a grid of sequences and integers. That's WP16's done-when (D28).
  - **The verifier proves every law** under 10 shuffled seeds.
  - **Not in the library:** three of §9's facts. `push`'s effect is a statement fact. `set-idx`'s multiset effect would need a take-and-drop fact §9 lacks. Multiset extensionality ranges over every `int`, which the interpreter can't evaluate.
- **WP5, the verifier,** is done for B17-0: `b17c/verify.py`, with its goals from `b17c/goals.py`.
  - **What it does:** it sends canonical queries (interface 11, D63), caches every verdict under D22's key, and reports solver-trusted goals by node ID (D24, D25).
  - **Its three done-whens hold:** the worked example verifies, seed-shuffle checks pass, and the proof cache hits on unchanged code. It also hits on renamed code, and after a callee's body edit.
  - **Goals from WP3's types:** each expression's SMT sort is the type the checker gives it, where the goal spike guessed. Multisets of booleans and empty literals typed only by what they're compared with now verify. A module that fails tier 0 gets its diagnostics instead of goals.
- **B17-1 froze** on 2026-10-30 under D44: `docs/b17-1.md`, version 1.0, written as changes to B17-0's, and its suite `suite/b17-1/`. D113 corrected four of its statements the same day, to what the tools already did, making it version 1.1, and D114 made it version 1.2 on 2026-11-02, through `push`'s new goal. The tools now read B17-1 by default, and B17-0 with `--subset 0` (D101).
- **B17-1's labelled suite** is written: `suite/b17-1/`, with 15 AlgoVeri ports to accept, WP10's 5 among them, and 54 programs to reject, one per rule. The checker agrees with every tier 0 label (PR #30). Writing it found two gaps in B17's proofs: none could apply a lemma at every value of a quantifier, or name the witness of an ∃. D99's `forall` statement and D100's `obtain` close them, and are in the spec text.
- **WP15, the interpreter, reads B17-1,** by default since it froze (D101): data values, tuples, places, `match`, sets and maps, and `rank`. It runs all 15 accept programs, and shows the fault of each proof reject that has a def or ghost-fn. D102 lets a quantifier range over a finite collection its guard names, so set-based specs such as `is_bst` are checked rather than left unknown.
- **WP5, the verifier, reads B17-1,** by default since it froze, encoding it as D89 says, refined by D103, D105, D106 and D108.
  - **Proof labels:** each of the 6 proof rejects fails exactly its labelled goal.
  - **Accept programs:** all 15 verify under 10 shuffled seeds. Their proofs use D99's `forall` statement, D100's `obtain` and, for `bfs`, `coin_change` and `kruskal`, D106's folded ghost-fns, with invariants written as folded predicates. `kruskal`'s proof that no spanning tree weighs less is an exchange argument, round by round.
  - **From 2026-10-31 to 2026-11-06, `coin_change` didn't:** numbering ghost-fn parameters in queries changed no query's meaning, but one lemma then proved under only 9 of 10 seeds, and `test_verify.py` proved the suite under one. The lemma now applies a smaller one at every key, and `test_verify.py` proves both suites under 10 seeds.
  - **Soundness fixes that reach B17-0:** a review found two ways the verifier proved `false`, in B17-0 too. One was a recursive ghost-fn's equation holding outside its parameter types. The other was a `seq-build` under a quantifier being one constant. Both are fixed (D103). A later review found a third, also fixed: a binder or parameter could share its SMT name with a ghost-fn, so a definition read the wrong value. No suite proof or agent's program relied on it.
  - **B17-0's suite is unchanged:** every one of its 511 queries is byte-identical, so no suite proof relied on either hole.
  - **Open types inside values:** an empty literal nested in a map, tuple, set, sequence or constructor value used to reach goal generation with its type open, and crash it or send an ill-sorted query. After tier 0, each open type now takes its type where the value is used, or becomes an integer, as `docs/b17-1.md` §4 says. Every suite and core query is byte-identical.
    - **Tier 0 changes, in programs with such open types only:** a literal's entries and `update`'s key and value now fix the open parts of its destination or map, as §4 and §7 say, so a later use that disagrees is rejected. A value whose open types nothing fixes must be well-formed once they're integers, so a sequence put in a vector that way is rejected.
    - **Still open:** a type that only a `match` binder's use fixes. Its query is ill-sorted, so the goal fails closed.
- **WP7, the Rust backend,** is done for B17-0: `b17c/rust.py` (D95–D97).
  - **Emitted code compiles:** every module that passes tier 0 becomes a crate that forbids unsafe code and checks every runtime goal where §8 does.
  - **Runs match the interpreter:** 8,875 differential runs print exactly the interpreter's text, across the suite, corner cases and generated programs, with rustc 1.99.1 pinned. Fuzzing and a mutation check found no mismatch left.
- **WP7 reads B17-1,** by default since it froze (D110, D111).
  - **Data types become Rust enums,** with boxed recursive fields and only the type parameters a value holds. Updates through places happen in place, in the interpreter's order, and `replace` is `std::mem::replace`.
  - **Runs match the interpreter:** every accept program on its spec's inputs, the two proof rejects whose defs reach `err BOUNDS` and `err FIELD`, corner cases and generated programs. B17-0's crates are unchanged, byte for byte.
- **WP6, the agent protocol,** is done for B17-0 and B17-1: `b17c/agent.py`, with `--subset` (D112).
  - **Diagnostics** carry interface 3's fields (D93). That includes the goal over the program's names, a counterexample the interpreter replays, the slice of items needed to fix it, and how many goals depend on it.
  - **The five queries answer** (interface 8, D94). `search` finds specs by what they guarantee, by verifying a def that only calls each candidate.
  - **Not yet:** repairs, which wait for WP2's typed edits.
- **WP8, the agent reference manual,** is done for B17-0, `docs/manual.md`, and for B17-1, with its supplement `docs/manual-1.md` (D112).
  - **Every rule and every code:** it covers all 25 codes of §9, each with a minimal example and the fix, along with the rules an agent writing B17-0 needs.
  - **Every example is checked:** `test_manual.py` holds each of its 38 examples to its stated outcome, tier 0 in CI and proofs with Z3, and fails if a code loses its example or its list of `core.b17`'s items drifts from the file.
- **WP11's reward** is built: `gym/reward.py` (D123).
  - **The tiers:** a reply earns 0.05 when it parses, 0.20 when tier 0 passes, up to 0.50 for the share of its parts in L2's closure, 0.80 when verified, and 0.90 when also right within 20M steps on 25 held-out inputs.
  - **Its self-check,** `gym/test_reward.py`, gets D123's figures for the hacks it measured on `abs`. It also checks that a redeclared spec scores 0.05, a discrepancy 0, and running out of steps or a clause the interpreter can't decide 0.80.
  - **Not yet run with the real secret:** scoring needs the secret whose hash `gym/split.json` records, and the split isn't frozen yet. The self-check scores replies under a split of its own.
- **CI** runs eight `b17c` self-checks on Linux for every pull request. They include the core library's witnesses, the agent protocol's and the manual's checks that need no Z3, and the Rust backend's differential tests on rustc 1.99.1.

### Decisions waiting for the owner
- **One optional run:** more rounds for Codex on `dijkstra`, `bellman_ford` and `prim`, which wouldn't be a fair count against Dafny.

D79–D101 were accepted on 2026-10-28, D102–D108, D110 and D111 on 2026-10-29, D109, D112 and D113 on 2026-10-30, D114 on 2026-11-02, D115, D116 and D117 on 2026-11-03, D118 on 2026-11-04, D5, D7, D119, D120 and D121 on 2026-11-05, and D122 and D123 on 2026-11-09. D2–D4, D6 and D8–D10, carried over from the design spec, are still Proposed.

### Next on the critical path
1. **M3's B17-1 track (D112),** now that B17-1 is frozen. It starts with the 10 AlgoVeri ports in `suite/b17-1/accept/`, harder than the seed tasks even in Dafny, and adds WP10's further ports as they come. 50 of the 64 AlgoVeri tasks D79 surveyed need B17-1's tuples or data types. In order:
   - **`agent.py` at subset 1 (WP6): done.** B17-1's codes and goals, and counterexamples that show tuple and data values as terms the interpreter replays. Sets, maps and multisets have none yet;
   - **`docs/manual-1.md` (WP8): done.** The manual's B17-1 supplement, 39 KB: what B17-1 adds, with 28 examples whose outcomes `test_manual.py` checks at subset 1, both of B17-1's new codes among them;
   - **the harness track (WP17): done.** `--tasks b17-1/` runs every port but `bfs`, which D117 made the supplement's worked proof, each posing its first spec with the data items and ghost-fns it refers to. Every port's solution verifies, and each task alone is `no_def`;
   - **a first run: done** ([above](#recent-and-current-work)). 57 of 60 verified, as in Dafny on the same tasks, at about 1.9–4.5 times Dafny's tokens.
   - **Locating a missing `)` (WP2): done.** E-PARSE-001 names the first item still open when a later line starts at or left of its column, or else the module's last item. Replayed on M3's recorded rounds, every unclosed one now points into the agent's own lines, and in each that one `)` fixes, the fix lies in the lines named;
   - **Counterexamples for data values with a sequence inside (WP6): done.** On the run's failed goals, re-solved, 13 of 126 now get one, against 4. Most of the rest come back unknown under the quantifiers of the agents' own ghost-fns and contracts;
   - **WP10's further ports: done.** These 10 don't separate the languages, so the next are the tasks hardest in Dafny's two AlgoVeri runs. Besides `kruskal`, only `prim`, `edmond_karp` and `push_relabel` had a failure, and `bellman_ford` and `dijkstra` took Codex 6 or 7 rounds. All five are ported and verified, `push_relabel` with a real push-relabel algorithm;
   - **a run of them: done** ([above](#recent-and-current-work)). Claude verified 15 of 15, and Codex none, against 6 of 10 in Dafny, so they separate the languages for Codex. The run found a hole in the verifier, and lost 5 of Claude's replies in the harness;
   - **closing the length hole (WP5), D114: done.** `push` has an `E-PROOF-OVERFLOW` goal, ⟦len v < 2^63 − 1⟧, so a vector reaching 2^63 elements is a runtime error the verifier rules out rather than an allocation failure. Three of B17-0's accept programs now bound their output's length, `prefix_sums` with a new precondition, and B17-0 and B17-1 are version 1.2. Of the agents' 34 verified programs that push, 17 fail the goal;
   - **Claude's whole reply (WP17): done.** The harness reads Claude Code's `stream-json` output and joins the text of every message in the reply, dropping a code fence a resumed part reopens. On a real reply forced past a 400-token limit three times, it gives back all 264 lines written, in order;
   - **a rerun of the five: done** ([above](#recent-and-current-work)). Claude verified 15 of 15 and Codex none, with D114's goal never failing and no reply lost;
   - **a Codex-only run with B17-1's prompt worded as Dafny's (WP17), D115: done.** Codex verified none of 15 again, and still didn't attempt the proofs, so the wording isn't the cause. The owner kept the new wording;
   - **a Codex-only run with a worked long proof in B17-1's prompt (WP17), D116: done, and the example has come out.** Codex verified 3 of 15, all of `dijkstra`, and wrote far longer programs on three of the five tasks, but verified neither maximum-flow task;
   - **every unbalanced item at once (WP2), and `push`'s diagnostic (WP6): done.** A parse error also names every item whose parentheses don't balance, with its lines and how many are off. A failed `push` goal now reads `(in_i64 (+ (len v) 1))`;
   - **a worked long proof in the supplement (WP8), D117: done.** `docs/manual-1.md` §11 is `bfs` in full, and `bfs` is no longer an M3 task. The owner kept it after the run below;
   - **a run of Claude and Codex on the five, with that proof: done** ([above](#recent-and-current-work)). Claude verified 15 of 15, at about 2.0 times Dafny's tokens, against 2.4, and Codex none;
   - **a standing run-time audit (WP17), D118: done.** Verified B17 programs run on random valid inputs against a separate reference, so a write-up no longer rests on verdicts and reading alone;
   - **all 14 ports under one prompt: done** ([above](#recent-and-current-work)). Claude verified 42 of 42 at about 2.5 times Dafny's tokens, and Codex 25 of 42 at about 2.8;
   - **whole diagnostics in B17's feedback (WP17), D119: done.** A cut ends at a whole diagnostic and says how many more there are, so later runs differ from earlier ones;
   - **next:** this track is measured, and item 3 below is done.
2. **M3 on the seed tasks** has had its rerun ([above](#recent-and-current-work)). The first run's gap, all on `insertion_sort` and `partition`, led to three fixes, and with them a rerun of the two tasks verified 12 of 12 in round 1.
   - **The manual (WP8)** lists all 36 of `core.b17`'s items, since the prompt doesn't include the file, and states `set-idx`'s multiset effect, with a checked swap that needs no lemma. This fix alone accounts for the rerun.
   - **The checker (WP3), D107:** ghost multisets are covariant, so `(multiset i64)` compares with `(multiset int)`. A `(seq int)` given where a `(seq i64)` is declared is still rejected, by design, and the manual's §3 says to state ghost helpers over `int`.
   - **The encoding (WP5), D108:** `==` on sequences makes them the same sequence, so every function agrees on them. A query gets its axioms only where it compares sequences.
   - **Optional:** the 18 other seed tasks ran under the old manual. Rerunning them would show whether its 2–3k more input tokens per call cost anything there.
   - **Next for M3:** tasks hard enough to separate the two languages (WP10). On the seed tasks they differ only in tokens.
3. **B17-1's verification levels (WP5): done, with D120** ([above](#recent-and-current-work)). `verify --level`, the report's level fields, D88's property tests and L2's closure are built as `docs/b17-1.md` §10 says. M3 doesn't use them: it counts a task verified only when every goal is proved.
4. **WP16** grows the core library as B17-1 and the ports need it.
5. **WP4b, the spec workbench: done on the worked example, D121** ([above](#recent-and-current-work)). With it, and WP10 done with its 35 ports (D122), every dependency of WP11 is built.

6. **WP11, the training environment,** is next on both paths to the Phase 2 gate, now that Phase 1's gate has passed ([Phase 2](#phase-2)). It's the one unfinished item on either path, since WP10, which it depends on, is done (D122). D123 scopes it. Its first piece, the reward, is built ([above](#recent-and-current-work)). Next are the entry checks, `gym/pool.py`, on the 35 ports, then the frozen split with its secret, and the baseline. Growing its pool of tasks follows it in Phase 2, and needs the spec workbench's reach first, [below](#phase-1-work-outside-the-gate), since graph and tree specs can't enter the pool until then.

Off the critical path, **WP7**, the backend that emits safe Rust, is done for B17-0 and B17-1 (D95–D97, D110, D111).

### Phase 0 work outside the gate
- **The rest of WP2:** the manifest and lockfile schemas (interfaces 4 and 7, D26) and typed edit operations (interface 2).
- **The rest of the baselines:** Gemini's remaining tasks, whose quota was due to reset around 2026-11-02, and Grok's once its balance is topped up.

### Phase 1 work outside the gate
- **WP16** grows the core library as later subsets and ports need it.
- **WP6's repairs** wait for WP2's typed edits.
- **The spec workbench's reach (WP4b, WP15).** For 7 of the suite's 40 specs, `vacuity` can't show that any input meets the `requires`: `bellman_ford`, `dijkstra_shortest_paths`, `kruskal_mst`, `prim_mst`, `segmenttree_query`'s `query`, and the `max_flow_value` specs of `edmond_karp` and `push_relabel`. The specs aren't vacuous, since the self-checks' inputs meet them, checked by hand. But for the same reason, D88's property tests keep no input for those 7 defs, so none of them is tested at L1.
  - **Two causes:**
    - **The interpreter can't evaluate at least one clause of each,** 10 in all (D58, D102). The six graph specs bound weights or capacities with a quantifier whose guard calls a ghost-fn, `(=> (has_edge g u v w) …)`. `is_segment_tree` has an equivalence under `forall` with no guard. `kruskal` and `prim` also require a connected graph, an ∃ over paths. Z3 doesn't fill the gap: under the encoding's quantified axioms, it returns no model for any of the 40 specs.
    - **D88's draws rarely meet a `requires`,** even one the interpreter can evaluate. A random graph is mostly well formed only when it has no edges, and a random tree is almost never a segment tree.
  - **The plan:** four changes. A prototype of them, on 2026-11-06, closed all 7.
    1. **Unfold a ghost-fn call in a guard,** when the ghost-fn isn't recursive and has no `requires`, and each argument is a variable or a binder, so unfolding skips, repeats or delays no evaluation that could fail: its body, with the arguments substituted, replaces the call.
       - **An ∃ at the head of a `forall`'s unfolded guard** becomes one more `forall` binder, since `(=> (exists (i) C) P)` holds at every point exactly when `(=> C P)` does at every value of i.
       - **A binder that a leading conjunct equates to a term** takes that term's value, once the binders the term mentions have theirs. The conjunct can't fail, since the conjuncts before it keep the term defined (D58).
       - **Binder order:** D58 fixes binders in declaration order. This rule needs each binder fixed after those its range mentions, so it amends that order, and a quantifier with no such order stays unknown.
       - This makes the six bounds on weights and capacities evaluable.
    2. **Split `(forall (x) (== A B))` on booleans** into `(=> A B)` and `(=> B A)`, evaluating both whatever the first gives, when A and B are each a guard whose conjuncts all can't fail (D58, D102). Then no point the split skips could have been undefined. This makes `is_segment_tree` evaluable.
    3. **Search for a witness of an ∃ that no guard bounds, in the workbench only:** values built from the integers in scope, shortest first, under a fixed budget.
       - **Only where no skipped point can be undefined:** the search runs only for a clause whose definedness goals the verifier has proved, its own and those of the ghost-fns it calls. `kruskal` and `prim` qualify: the verifier proves 2 `BOUNDS` goals each for `nodes_have_path` and `path_follows_graph`.
       - **The result:** a witness shows the `requires` can hold. Running out, or a goal not proved, leaves it unknown.
       - **Not in checked runs or property tests,** where the ∃ stays unknown, since D58 evaluates every point so that an undefined one is found. So `kruskal`'s and `prim`'s defs still get no property test. The same condition could let runs use the search, which would be a further decision.
    4. **Draw an integer parameter within the `requires`' bounds:** the leading conjuncts that can't fail, given the parameters drawn before it in declaration order, bound it as D58 bounds a binder.
       - **The draw:** the range is intersected with `i64`'s. A draw takes one word from §10's stream and gives `lo + next() mod (hi − lo + 1)`. An empty range drops the draw, as a `requires` that fails does, and a parameter with no finite range is drawn as now.
       - **Which tests gain:** D88's property tests and the workbench draw from the same seed and stream, so the inputs the workbench finds are among the draws the property tests try. With rules 1, 2 and 4, that would give 5 of the 7 defs inputs to test.
  - **In the prototype:** with rules 1–3, every `requires` clause of the 7 evaluated true on the self-checks' inputs, and the draws found an input for 4 of the 7. With rule 4 they found one for all 7. Each input is a smallest case, such as a graph with no edges or a segment tree with one leaf.
  - **What it changes:** rules 1 and 2 are checking rules, in `docs/b17-1.md` §8, and rule 4 changes how §10's draws give a parameter its value. So they need a decision and an amendment to version 1.3, as D114 did. Rule 3 is the workbench's own (D121). Rules 1, 2 and 4 change which inputs the property tests keep, and so L1's results and the witness examples, but every run stays deterministic.
  - **Done when:**
    - all 40 of the suite's specs are shown satisfiable;
    - rules 1–3 each have a test where they decide a quantifier and one where they leave it unknown, such as a ghost-fn with a `requires`, which isn't unfolded;
    - rule 4 has golden draws for a fixed seed;
    - every suite label, the Rust backend's differential runs and the interpreter's other results are unchanged, and L1's results and refutations on the suite are recorded before and after.
  - **Not covered:** a `requires` whose inputs are all larger than the draws make, or whose ∃ needs a witness past the budget. A fifth change, an input the reviewer gives to `vacuity`, would cover those. The command takes none today.

## Phase 1

From D21's dependency table, as D62 and D65 amend it, two paths of the same length lead to the Phase 2 gate: WP1a, WP2, WP3, WP16, WP5, WP6, WP8, WP11, and WP1a, WP2, WP3, WP16, WP5, B17-1, WP10, WP11. WP4b and WP15 are each one step off them. WP1a, WP2, WP3, WP5, WP6 and WP8 are done for B17-0, and WP16 is under way, so what's left of the first path is WP11. B17-1 froze on 2026-10-30, and D122 made WP10 done, so what's left of the second is WP11 too.

| WP | What | Depends on | Done when |
|---|---|---|---|
| WP3 | Tier 0 checker: types, names, ghost code, ownership, effects | WP1a, WP2 | It agrees with every tier 0 label in the suite. Done (PR #15). |
| WP4a | The spec language | WP3 | Done, since WP1a is frozen and B17-0 already has a spec language (D62). B17-1 adds no data-type invariants or refinement links, since every surveyed task states its invariants in its contracts, so it stays done (D79). |
| WP16 | The core spec library: `sorted`, ranges, sequence and multiset laws | WP1a, WP15 | Every entry has witness examples that the interpreter confirms (D28). In progress: met for its 33 laws and 3 ghost-fns. |
| WP5 | The verifier: `b17c` generates its own goals and sends them to Z3 (D17) | WP3, WP1a, WP16 | The worked example verifies, seed-shuffle checks pass (D23), and the proof cache hits on unchanged code. Done for B17-0, and B17-1's verification levels are built (D120). |
| WP6 | Agent protocol and diagnostics | WP3, WP1a, WP5 | Diagnostics match interface 3, and all five queries answer (interface 8). Done for B17-0 (D93, D94) and B17-1 (D112), except repairs, which wait for WP2's typed edits. |
| WP4b | The spec workbench: back-translation, vacuity checks, witnesses, mutant rejection, signing | WP1a, WP5, WP15 | They run on the worked example. Done (`b17c/spec.py`, D121). |
| WP7 | A backend that emits safe Rust (D18) | WP3, WP15 | Emitted code compiles and matches the interpreter on differential tests. Done for B17-0 (D95–D97) and for B17-1 (D110, D111). |
| WP8 | The agent reference manual | WP3, WP5, WP6 | Every rule and error code has an example, and every example passes `b17c check`. Done for B17-0 (`docs/manual.md`) and B17-1 (`docs/manual-1.md`, D112). |
| B17-1 | The second subset: data types, tuples, collections of any type, ghost sets and maps (D79); verification levels L0 to L3 (D80) | WP1a, WP3, WP5, WP15 | Its spec and suite freeze once the checker agrees with every tier 0 label (D44). Done: frozen on 2026-10-30 at version 1.0, with D81–D92, D99, D100 and D102–D109, and amended to version 1.1 by D113 and 1.2 by D114. The interpreter and the Rust backend run its accept programs, and the verifier checks its proof labels and works out its verification levels (D120). |
| WP10 | Benchmark ports | WP1a, WP5; B17-1 for the AlgoVeri ports, since 50 of the 64 that D79 surveyed need its features | Ported tasks verify end to end and run as emitted Rust (D122, which dropped Dafny, Verus and Lean as the languages they come from). Done with 35: the 20 seed tasks, in B17-0, and 15 of AlgoVeri's, in B17-1, all checked by Phase 1's gate on 2026-11-06. None comes from Verus or Lean. |

**The head-to-head experiment** is called M3 in the activity log.
- **What it does:** agents write B17-0 and Dafny for the same frozen tasks, whose specs stay aligned across the two languages (D42). It started on B17-0's tasks, and has run B17-1's since B17-1 froze (D65, D112).
- **What it measures:** the success metrics: verified pass rate, repair rounds and tokens per verified task.
- **What it needs:** with WP5, WP6, WP8 and the harness's B17-0 track done, WP10's ports for the tasks it runs, and tasks hard enough to separate the two languages. The seed ports were enough to start, and the AlgoVeri ports followed once B17-1 froze.
- **How it's used:** its results steer the design (D14).
- **First run,** on the seed tasks, 2026-10-29: Claude verified 59 of 60 and Codex 55 of 60 in B17-0, against 120 of 120 each in Dafny. The gap came from the manual, D70's multiset rule and the encoding's missing sequence extensionality. **Rerun** of the two failed tasks, 2026-10-30, with all three fixed: 12 of 12 in round 1, so the seed tasks don't separate the two languages in what verifies, though the other 18 haven't been rerun under the new manual. On those two tasks, B17-0 cost Claude about 4.6 times Dafny's tokens per verified task, and Codex about 1.2 times.
- **B17-1 runs:** on the first 10 AlgoVeri ports, 2026-10-30, Claude verified 30 of 30 and Codex 27 of 30, as in Dafny. On WP10's five harder ports, 2026-11-02, Claude verified 15 of 15 and Codex none, against 10 of 10 and 6 of 10 in Dafny: the first tasks that separate the two languages, for Codex. Both counts leave out 10 of Codex's attempts that passed through a hole in the verifier, which the second run found. A rerun of the five with the hole closed gave the same counts, with Claude at about 2.4 times Dafny's tokens. A third run, Codex only, with the prompt worded as Dafny's (D115), verified none of 15 again. A fourth, with a complete worked proof added to the prompt for that run (D116), verified 3 of 15, all of `dijkstra`. A fifth, of Claude and Codex with that proof in the supplement (D117), gave 15 of 15 and none of 15, with Claude at about 2.0 times Dafny's tokens. A sixth, of all 14 ports under one prompt, 2026-11-04, gave Claude 42 of 42 and Codex 25 of 42, against 28 of 28 and 22 of 28 in Dafny, at about 2.5 and 2.8 times Dafny's tokens.

## Phase 2

**The training environment, WP11.** It's done when:
- rewards and anti-hacking rules are enforced;
- a held-out split is frozen;
- an in-context baseline is recorded.

Its curriculum covers every domain the language has reached by then (D65).

**D123 scopes it:**
- **The reward:** the design spec's tiers, from 0.05 for a reply that parses to 0.90 for one that's verified and right within 20M steps on 25 held-out inputs. There's no 1.00 tier until specs can state a cost (D30).
  - **Partial credit** counts each `ensures` clause whose goals are proved without resting on a goal that isn't (L2's closure), so padding, a failing `assert` and a loop that never ends earn no more than a reply without them.
  - **A discrepancy scores 0:** a verified reply that's wrong on a held-out input is recorded for triage, since it shows a hole in the verifier, a spec that says something other than the reference, or a bug in the interpreter or the reference.
- **The pool:** a task enters once its spec passes the workbench's vacuity and mutant checks, a reference def verifies, and its held-out inputs can be drawn. WP11 tests the checks on the 35 ports. In Phase 2 the pool grows from AlgoVeri's unported problems, then vericoding's Dafny tasks and FVAPPS's problems.
- **The split:** M3's 34 tasks are the gate's test set, with the pool's problems that match them and 1 in 10 of the rest.
- **The baseline:** Claude and Codex on the test set, then the pool's slice and the base model as they arrive.

Agents first learn B17-0 from the manual in context, and models are trained in Phase 2 (D8, proposed).

**A Verus baseline (WP17), D122:** agents writing Verus on AlgoVeri's Verus specs of the tasks M3 uses, so the gate has a number for models writing Verus.

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
| **B17-1** | Data types with type parameters, tuples, collections of any type, quantifiers over any ghost type, and ghost sets and maps (D79); verification levels L0 to L3, and what a goal that isn't proved does below L2 (D80) | Phase 1. Its scope (D79, D80) and its spec text's decisions D81–D92, D99 and D100 were accepted on 2026-10-28, D102–D108 on 2026-10-29, and D109 on 2026-10-30. Its spec text ([b17-1.md](b17-1.md)) and labelled suite (`suite/b17-1/`) froze on 2026-10-30, at version 1.0, D113 made it version 1.1, and D114 version 1.2. |
| **Later subsets** | From §11 and D79: mutable borrows, floats, strings, runtime sets and maps, and generic functions; mutual recursion, once there's group hashing (D22); and vector capacity, once there are allocation bounds (D30). From D64: closures and higher-order functions, interfaces or traits, asynchronous I/O, a user-interface model, and tensors with automatic differentiation. Effects for files, network and time. | Benchmarks set the order (D14), within §11's prerequisites. Growth continues past Phase 4 until D64's scope is covered. |

- **The standard library** grows with the subsets. The design spec's library covers collections, numerics, text, parsers, cryptography and time. Each subset's scope includes the library entries it makes expressible.
- **Task sets beyond algorithms** (D64) are built as the subsets that can express them arrive.

## Open questions that shape the plan

- **Hard enough tasks.** On every set before WP10's harder ports, today's models differed in rounds and tokens, but barely in what they verify. Claude and Codex verified all 28 vericoding tasks, though at most a quarter of 2025's models solved each. So M3's tasks will have to be found elsewhere or written (WP10). M3's seed tasks don't either: once the manual stated a fact it had left out, a rerun of the two tasks with a gap verified all 12 attempts in round 1. Nor do the first 10 AlgoVeri ports in B17-1: 57 of 60 attempts verified, as in Dafny. WP10's next ports tested one guess, the tasks hardest in Dafny, and they separate the languages for Codex: it verified 6 of 10 in Dafny and none of 15 in B17-1, attempting the algorithm in only 5 samples. Claude verified all of them in both. A rerun with the hole closed gave the same counts: Codex's median round was 637 characters against 24,383 in Dafny, so it mostly doesn't attempt them. A third run, with the prompt worded as Dafny's (D115), verified none of 15, and Codex still mostly didn't attempt them, so the wording isn't why. A fourth, with a complete worked proof in the prompt (D116), verified 3 of 15, all of `dijkstra`, and brought long attempts on three of the five tasks, though on maximum flow only exhaustive searches. With the proof in the supplement instead (D117), its attempts stayed long, but it verified none of 15, and 2 of 15 in the run of all 14 ports. So what Codex attempts depends on having seen a long proof, at least in part. Why maximum flow stays out of reach, whether a smaller prompt or more rounds would help, and what makes a task hard for Claude, are open.
- **Where B17-1's extra cost comes from.** On the first 10 ports, per verified task against Dafny on the same tasks, Claude's and Codex's costs split as follows. Prompt tokens are 6.0 and 2.2 times Dafny's, mostly the manual and its supplement. Output tokens are 3.6 and 1.2 times, final programs 1.7 and 1.1 times as long, and rounds about the same. Claude also thinks 4.6 times as much, and Codex about 1.1 times. So the language doesn't force much longer programs, since Codex writes about as much as in Dafny. The prompt is the cost of a language no model has seen, which training (Bet 2) or prompt caching would cut. Across all 14 ports under one prompt, the fixed prompt is about 36% of Claude's tokens, at about 36k per call against 4k in Dafny. Its input is about 4.4 times Dafny's and its output about 1.8, and its ratio falls from 3.8 on the 9 easier ports to 2.0 on the 5 harder ones. Open are whether Claude's extra thinking falls as models learn B17, and how much of a proof's length is fixable and how much is the price of B17's guarantees.
  - **Fixable:** the syntax, a core library with no sum lemmas, a `forall` statement that applies one lemma, and helpers that can't be generic.
  - **The price of the guarantees:** proofs that hold under 11 seeds, quantifiers only over types the solver models exactly (D90), and helpers that unfold only where a proof uses them (D106).
  - **What would settle it:** B17's case over Dafny needs cost parity once those are addressed, or tasks where its feedback or stable verdicts let agents verify what they can't in Dafny. Neither is shown yet. Codex's `kruskal`, 2 of 3 in B17-1 against none of 2 in Dafny, looked like one, but both of its passes went through the verifier's length hole. The one difference in pass rate runs the other way: on WP10's five harder ports, Codex verified 6 of 10 in Dafny and none of 15 in B17-1, three times, then 3 of 15 with a worked proof in the prompt, none of 15 with it in the supplement, and 2 of 15 when that was repeated in the run of all 14 ports. Its one maximum-flow pass in Dafny, though, is an exhaustive search. Under one prompt, across all 14, Claude is at about 2.5 times Dafny's tokens per verified task and Codex about 2.8, so cost parity is still not shown.
- **The cost of i64 rigor.** Ranges stated the obvious way left four suite proofs needing a hint, or a solver's luck. Stated per step (D60), all four are stable and about 80 times cheaper. How specs must be phrased for the solver is part of Bet 1's cost. In M3's first run no overflow goal failed, since the frozen specs already state ranges per step. A cost showed up in typing instead: 26 of Codex's 104 calls were rejected because multisets of `int` and `i64` didn't compare (D70). D107 has since changed that.
- **Counterexamples.** With quantified axioms, a failing goal comes back unknown rather than with a model. WP6 solves it again against only the axioms it mentions, and the interpreter replays the model (D93). That found one for each of the suite's 9 proof rejects, and 8 replayed. On harder programs it mostly doesn't. In M3's first B17-1 run, 4 of the 137 failed-goal diagnostics had one, since most failed goals took a data value with a sequence inside. Those are shown now, and 13 of the run's 126 failed goals, re-solved, get one. The rest come back unknown under the quantifiers in the agents' own ghost-fns and contracts, and writing the ghost-fns as macros found a model for 1 of 40 of them. How to find models under those quantifiers is open.
- **Algorithms specs can't see.** A functional spec can't tell Aho-Corasick from naive search. Cost contracts were deferred (D29, D30). M3 now has a live case: Codex's longest attempts at `push_relabel`, up to 41,900 characters, search every flow matrix, trying up to 100,001 values per cell. None verified, but had one, the verdict would have stood, and only running it would have shown the difference. One of Claude's `kruskal` programs did verify as just such a search, and D118's audit now runs every verified B17 program it can.
- **Training resources.** Phase 2 needs open weights and compute that the project doesn't have yet.
- **Reaching every domain.** [How the language grows](#how-the-language-grows) lists what D64 needs. What follows B17-1, and in what order, is open. Deciding it needs task sets for applications, pipelines and machine learning, but every benchmark so far is an algorithm task.
