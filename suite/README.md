# B17-0 accept/reject suite

WP1a's labelled programs (`docs/b17-0.md` §12). WP3's checker, WP5's verifier and WP15's interpreter must each agree with every label.

## Layout

- `accept/*.b17`: programs that pass every tier 0 check and discharge every proof goal. These are the 20 seed tasks of `gym/tasks/`, ported to B17-0. `merge_sorted.b17` is the worked example of §1, unchanged; it doubles as the `merge_sorted` seed.
- `reject/<CODE>-<what>.b17`: programs with exactly one error, whose code starts the filename. The code is either a tier 0 code from §9's table or a proof goal family (`E-PROOF-*`). Several files may share a code.

Files use the pretty layout, not canonical bytes (§2). WP2's round-trip tests own canonicalization.

## What "accept" assumes

Accept programs rely only on:
- the core library and encoding facts of §9;
- the goal conventions of §7 and §9: clauses checked in order, goals assumed once generated, and loops forgetting only what their body changes.

They contain no hints that a particular solver or seed needs. If WP5's verifier can't discharge one, that's a finding against the encoding or the core library, not a reason to edit the program. Record it in `ACTIVITY.md`.

## Ported task ranges

Seed tasks over Dafny's unbounded `int` gained ranges under D42 and §10's rule, stated per loop step (D60):

| Task | Added precondition |
|---|---|
| `abs` | `x > i64::MIN`, so `-x` fits |
| `fib` | every `fib (i - 1) + fib i` for `1 <= i < n` fits |
| `power` | every `pow b i * b` for `i < e` fits |
| `sum`, `prefix_sums` | every prefix sum plus the next element fits |
| `isqrt` | none: every `r` with `r * r <= n` already fits |

`gcd`, `count` and the index-returning tasks need none. The Dafny versions in `gym/tasks/` take the same preconditions when the M3 task set is built.

## Checking until b17c exists

No checker exists yet, so the labels were checked by review: by the author, and by an independent model reading the suite against `docs/b17-0.md`. WP3 replaces review with execution. The suite and `docs/b17-0.md` freeze once its checker agrees with every tier 0 label (D44). `E-PROOF-*` labels and the proof goals of accept programs wait for WP5's verifier.
