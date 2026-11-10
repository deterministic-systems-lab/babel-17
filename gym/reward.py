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
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import audit as a
import harness as h
import split as S

sys.path.insert(0, str(h.B17C))
import agent
import goals as G
import hashing as H
import interp as I
import syntax
import verify as V

INPUTS, STEPS = 25, 20_000_000


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


def inputs(task, frozen, key, spec_sha, split, pool=False):
    """The task's held-out inputs, each with D118's reference for it, or None where the spec is the reference,
    as on the pool or with pool set. Their seed is the secret's HMAC of the task's problem and spec hash."""
    s = S.mac(key, "inputs", S.problem(split, task["id"]), spec_sha)
    if task["id"] in a.CASES and not pool:  # the gate's test set: D118's inputs, one in five large, and references
        r = random.Random(s)
        return [a.CASES[task["id"]](r, k % 5 == 4) for k in range(INPUTS)]
    # the pool: D88's draws that meet the requires
    cases = [(args, None) for args in I.spec_inputs(frozen, task["name"], s, INPUTS, task.get("subset", 0))]
    if len(cases) < INPUTS:
        raise ValueError(f"{task['id']}: D88's draws keep {len(cases)} of {INPUTS} inputs (entry check 5)")
    return cases


def triage(task, frozen, module, cases):
    """Each held-out input the verified module isn't right on: its index, discrepancy, limit or
    undecided, and what happened."""
    name, subset, out = task["name"], task.get("subset", 0), []
    for k, (args, ok) in enumerate(cases):
        run = I.run(module, name, args, check=ok is None, fuel=STEPS, depth=a.DEPTH, subset=subset)
        if isinstance(run, I.Limit):
            out.append((k, "limit", f"out of {run.kind}"))
        elif not isinstance(run, I.Ok):
            out.append((k, "discrepancy", I.text_of(run).splitlines()[-1][:300]))
        elif ok is not None:
            try:
                good = ok(*map(a.py, run.results))
            except (IndexError, TypeError, ValueError):  # an answer not even of the expected shape
                good = False
            if not good:
                out.append((k, "discrepancy", f"{a.py(args)} gave {a.py(run.results)}"[:300]))
        else:
            held = [v for kind, _, v in I.holds(frozen, name, args, run.results, subset, STEPS) if kind == "ensures"]
            if False in held or None in held:
                out.append((k, "discrepancy" if False in held else "undecided", f"{a.py(args)} gave {a.py(run.results)}"[:300]))
    return out


def score(task, code, key, split=S.SPLIT):
    """The reward for code, a reply to the B17 task, with what recomputing it needs: the hashes of the
    reply, the spec and the held-out inputs, and the commit it was scored at (D123)."""
    split = S.load(split)
    S.check_secret(key, split)
    subset, name = task.get("subset", 0), task["name"]
    frozen = syntax.parse(task["frozen"].encode(), subset)
    spec_sha = H.hashes(frozen, subset)[name][1]
    cases = inputs(task, frozen, key, spec_sha, split)  # drawn before the reply is parsed
    commit = subprocess.run(["git", "-C", str(h.B17C), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out = {"task": task["id"], "reply_sha256": h.sha(code), "spec_sha256": spec_sha, "b17c_commit": commit or None,
           "inputs_sha256": h.sha(repr([a.py(args) for args, _ in cases]))}
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
            return out | {"reward": 0.20 + 0.30 * sum(counts) / len(counts), "parts": counts}
    wrong = triage(task, frozen, module, cases)
    return out | {"reward": 0.0 if any(t[1] == "discrepancy" for t in wrong) else 0.80 if wrong else 0.90, "triage": wrong}
