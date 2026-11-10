"""WP11's entry checks (D123): whether a B17 task, with a reference def, may enter the pool.

    uv run --no-project gym/pool.py [--seeds N] [TASK ...]

A task enters when:
1. its module, with no def, passes tier 0, its spec doesn't list panic, and no ensures clause is a
   top-level and;
2. vacuity shows its requires can hold, and judges no ensures clause trivial (D121);
3. its reference def verifies under D23's seeds;
4. mutants on that def tries at least one, and each survivor whose output differs on the tests' inputs
   is an answer the spec means to allow, reviewed and listed in ALLOWED;
5. the held-out draws keep 25 inputs, and on each the reference def's checked run ends within 20M
   steps with every ensures clause decided true, as a reply's must for the reward's top tier.

Every check runs whatever the others find, and each task's results print as a JSON line. Check 5's
inputs come from the secret, so what's printed of it names none of them. With no TASK it runs the 35
ports, B17-0's 20 seed programs and B17-1's 15, bfs among them. They stay held out: running them
tests the checks. --seeds sets the seeds mutants verify under, D23's 10 by default; fewer can only
let more mutants survive, so the check is no weaker.
"""
import json
import sys

import harness as h
import reward as R
import split as S

sys.path.insert(0, str(h.B17C))
import agent
import goals as G
import hashing as H
import spec as W
import syntax
import verify as V

# Survivors whose output differs, reviewed as answers the spec allows: task -> {"change at path": why}.
ALLOWED = {
    "b17/min_index": {"(< (idx a i) (idx a m)) -> (<= (idx a i) (idx a m)) at 2.3.6.1": "the last smallest element, not the first"},
}


def entry(task, key, split, seeds=V.SEEDS):
    """The five checks on a task whose solution holds its reference def: each's evidence and verdict."""
    subset, name = task.get("subset", 0), task["name"]
    frozen, ref = (syntax.parse(task[k].encode(), subset) for k in ("frozen", "solution"))
    spec = next(it for it in frozen.items[3:] if it.items[0].text == "spec")
    spec_sha = H.hashes(frozen, subset)[name][1]
    out = {"task": task["id"], "spec_sha256": spec_sha}

    tier0 = [d["code"] for d in agent.tier0(frozen, subset)]
    ands = [syntax._print(c) for cl in G.clauses(spec, "ensures") for c in cl if syntax._head(c) == "and"]
    panic = h.allows_panic(task)
    out[1] = {"pass": not tier0 and not panic and not ands, "tier0": tier0, "panic": panic, "and": ands}

    vac = next(e for e in W.vacuity(frozen, subset) if e["item"] == f"spec {name}")
    trivial = [r["clause"] for r in vac["ensures"] if r["trivial"]]
    out[2] = {"pass": vac["requires"]["verdict"] == "satisfiable" and not trivial, "requires": vac["requires"]["verdict"],
              "trivial": trivial, "unjudged": [r["clause"] for r in vac["ensures"] if r["trivial"] is None]}

    rows = V.verify(ref, seeds=V.SEEDS, subset=subset)[0]
    failed = [f"{r['family']} {r['node']}: {r['verdict']}" for r in rows if r["verdict"] != "proved"]
    out[3] = {"pass": not failed, "goals": len(rows), "failed": failed}

    if failed:  # mutants needs a def that verifies, so a mutant's failure is its own
        out[4] = {"pass": False, "mutants": None}
    else:
        muts = W.mutants(ref, name, subset, seeds)
        differ = [m for m in muts if m["killed"] is None and m["differs_at"]]
        allowed = ALLOWED.get(task["id"], {})
        out[4] = {"pass": bool(muts) and all(f"{m['change']} at {m['path']}" in allowed for m in differ),
                  "mutants": len(muts), "by_test": sum(m["killed"] == "test" for m in muts),
                  "by_verifier": sum(m["killed"] == "verifier" for m in muts),
                  "survivors": sum(m["killed"] is None for m in muts), "differ": differ}

    try:
        wrong = R.triage(task, frozen, ref, R.inputs(task, frozen, key, spec_sha, split, pool=True))
        out[5] = {"pass": not wrong, "kept": R.INPUTS, "wrong": [(k, kind) for k, kind, _ in wrong]}  # not the inputs
    except ValueError as e:
        out[5] = {"pass": False, "kept": str(e)}
    out["enters"] = all(out[k]["pass"] for k in range(1, 6))
    return out


def main(argv):
    seeds = V.SEEDS
    if argv[:1] == ["--seeds"]:
        seeds, argv = int(argv[1]), argv[2:]
    split, key = S.load(), S.secret()
    S.check_secret(key, split)
    tasks = h.load_tasks() + [h.load_b17_task(h.SUITE1 / "bfs.b17", 1)]
    for t in tasks:
        if t.get("lang") == "b17" and (t["id"] in argv if argv else True):
            print(json.dumps(entry(t, key, split, seeds)), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
