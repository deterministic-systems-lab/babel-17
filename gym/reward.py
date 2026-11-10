"""WP11's reward (D123): what a reply to a B17 task earns, from b17c's verdicts and held-out inputs.

score() gives the highest tier the reply reaches:

    0.05  it parses into the task's module
    0.20  tier 0 passes, and every spec has a def
    <0.50 0.20, plus 0.30 times the share of parts that count, below
    0.80  every goal is proved under D23's seeds, provisional while the solver is trusted (D24)
    0.90  verified, and right within 20M steps on each of 25 held-out inputs

The parts are the posed spec's ensures clauses and, as one more, the reply's other goals. A part counts
when its goals are in L2's closure (D80, D91). A clause also needs every runtime goal of the posed def,
and of the defs it calls, in the closure, so padding with asserts, an (assert false) and a loop that
never ends earn nothing.

The held-out inputs come from a secret kept outside the repository, whose hash split.json records. On
the gate's test set they're D118's, run as its audit runs them and checked by its references. On the
pool they're D88's draws from the spec alone, and a reply is right on one when its checked run (D58)
ends with every ensures clause of the posed spec true. A verified reply that's wrong, or ends in a
runtime error, is a discrepancy and scores 0. Running out of steps, or a clause the interpreter can't
decide, keeps 0.80. Each of the three is recorded for triage.
"""
import hashlib
import hmac
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import audit as a
import harness as h

sys.path.insert(0, str(h.B17C))
import agent
import goals as G
import hashing as H
import interp as I
import syntax
import verify as V

SPLIT = h.GYM / "split.json"
INPUTS, STEPS = 25, 20_000_000


def check_secret(secret, split=SPLIT):
    """Refuse to score without the secret whose hash the frozen split records."""
    if hashlib.sha256(secret).hexdigest() != json.loads(Path(split).read_text())["secret_sha256"]:
        raise ValueError(f"the secret doesn't match the one {split} records")


def seed(secret, problem, spec_sha):
    """A task's seed for its held-out inputs: an HMAC under the secret of its problem and spec hash."""
    return int.from_bytes(hmac.new(secret, b"\0".join([b"inputs", problem.encode(), spec_sha.encode()]),
                                   hashlib.sha256).digest()[:8], "big")


def parts(gen, goals, rows, check, name):
    """Whether each part counts: the posed spec's ensures clauses in order, then the reply's other goals."""
    counted = V.closure(gen, goals, {k for k, r in enumerate(rows) if r["verdict"] == "proved"}, check)
    defs, reach, todo = {n for n, d in gen.defs.items() if "def" in d}, set(), [name]
    while todo:  # the posed def and the defs it calls
        if (n := todo.pop()) not in reach:
            reach.add(n)
            todo += V._references(gen.defs[n]["def"], defs)
    safe = all(k in counted for k in V.runtime_goals(gen, goals) if goals[k][0] in reach)
    post = {}
    for k, g in enumerate(goals):
        if g[1] == "POST" and g[0] == name:
            post.setdefault(id(g[7]), set()).add(k)
    clauses = [c for cl in G.clauses(gen.defs[name]["spec"], "ensures") for c in cl]
    other = set(range(len(goals))) - set().union(*post.values())
    return [safe and post.get(id(c), set()) <= counted for c in clauses] + [other <= counted]


def held_out(task, frozen, module, secret, spec_sha):
    """A hash of the task's held-out inputs, and each one the verified module isn't right on: its
    index, discrepancy, limit or undecided, and what happened."""
    name, subset = task["name"], task.get("subset", 0)
    s = seed(secret, task["id"].rsplit("/", 1)[-1], spec_sha)
    if task["id"] in a.CASES:  # the gate's test set: D118's inputs, one in five large, and references
        r = random.Random(s)
        cases = [a.CASES[task["id"]](r, k % 5 == 4) for k in range(INPUTS)]
    else:  # the pool: D88's draws that meet the requires, and the spec as the reference
        cases = [(args, None) for args in I.spec_inputs(frozen, name, s, INPUTS, subset)]
        if len(cases) < INPUTS:
            raise ValueError(f"{task['id']}: D88's draws keep {len(cases)} of {INPUTS} inputs (entry check 5)")
    triage = []
    for k, (args, ok) in enumerate(cases):
        out = I.run(module, name, args, check=ok is None, fuel=STEPS, depth=a.DEPTH, subset=subset)
        if isinstance(out, I.Limit):
            triage.append((k, "limit", f"out of {out.kind}"))
        elif not isinstance(out, I.Ok):
            triage.append((k, "discrepancy", I.text_of(out).splitlines()[-1][:300]))
        elif ok is not None:
            try:
                good = ok(*map(a.py, out.results))
            except (IndexError, TypeError, ValueError):  # an answer not even of the expected shape
                good = False
            if not good:
                triage.append((k, "discrepancy", f"{a.py(args)} gave {a.py(out.results)}"[:300]))
        else:
            held = [v for kind, _, v in I.holds(frozen, name, args, out.results, subset) if kind == "ensures"]
            if False in held or None in held:
                triage.append((k, "discrepancy" if False in held else "undecided", f"{a.py(args)} gave {a.py(out.results)}"[:300]))
    return h.sha(repr([a.py(args) for args, _ in cases])), triage


def score(task, code, secret, split=SPLIT):
    """The reward for code, a reply to the B17 task, with what recomputing it needs: the hashes of the
    reply, the spec and the held-out inputs, and the commit it was scored at (D123)."""
    check_secret(secret, split)
    subset, name = task.get("subset", 0), task["name"]
    frozen = syntax.parse(task["frozen"].encode(), subset)
    spec_sha = H.hashes(frozen, subset)[name][1]
    commit = subprocess.run(["git", "-C", str(h.B17C), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out = {"task": task["id"], "reply_sha256": h.sha(code), "spec_sha256": spec_sha, "b17c_commit": commit or None}
    try:
        module = syntax.parse((task["frozen"][:-1] + "\n" + code + ")").encode(), subset)
    except syntax.ParseError:
        return out | {"reward": 0.0}
    defs = {it.items[1].text for it in module.items[3:] if it.items[0].text == "def"}
    if agent.tier0(module, subset) or any(it.items[0].text == "spec" and it.items[1].text not in defs for it in module.items[3:]):
        return out | {"reward": 0.05}
    with tempfile.TemporaryDirectory() as cache:  # a fresh cache, so every verdict is solved anew
        gen, goals, rows, cfg = V.verify_goals(module, V.SEEDS, Path(cache), subset)
        if bad := [r for r in rows if r["verdict"].startswith("error")]:  # Z3 itself failed: not the reply's doing
            raise RuntimeError(f"{task['id']}: {bad[0]['node']}: {bad[0]['verdict']}")
        if any(r["verdict"] != "proved" for r in rows):
            counts = parts(gen, goals, rows, V.checker(module, gen, cfg, Path(cache), subset), name)
            return out | {"reward": round(0.20 + 0.30 * sum(counts) / len(counts), 6), "parts": counts}
    inputs, triage = held_out(task, frozen, module, secret, spec_sha)
    reward = 0.0 if any(t[1] == "discrepancy" for t in triage) else 0.80 if triage else 0.90
    return out | {"reward": reward, "inputs_sha256": inputs, "triage": triage}
