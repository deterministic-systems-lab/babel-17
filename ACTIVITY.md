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
- **Awaiting the owner:** D15–D32.
