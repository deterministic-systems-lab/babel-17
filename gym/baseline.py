"""WP11's in-context baseline (D123): every reply of a harness run on the B17 tasks, scored by reward.py.

    uv run --no-project gym/baseline.py score RUN_ID [--jobs N]
    uv run --no-project gym/baseline.py summary RUN_ID

score writes gym/runs/RUN_ID/rewards.jsonl, one line per reply, and resumes where it stopped. A reply
with no code earns 0, and a call that failed (infra_error) isn't a reply. A reply's triage keeps each
failing held-out input's index and kind, not the input, since the record is in the repository and
the inputs come from the secret: scoring the reply again under the secret shows them.

summary prints, for each CLI and track, the mean reward of each attempt's first reply, before any
feedback, and of its last, after up to 8 rounds; the last replies' tiers; and every reply on which
the reward and the harness disagree about whether it verified.
"""
import concurrent.futures as cf
import json
import sys
from collections import Counter, defaultdict

import harness as h
import reward as R
import split as S


def score_reply(task, rec, key, split=S.SPLIT):
    out = R.score(task, rec["code"], key, split) if rec["code"] is not None else {"task": task["id"], "reward": 0.0}
    if "triage" in out:
        out["triage"] = [(k, kind) for k, kind, _ in out["triage"]]  # not the input
    return {"attempt": rec["attempt"], "iter": rec["iter"], "cli": rec["cli"], "stage": rec["stage"], **out}


def score(run_dir, key, jobs=3):
    tasks = {t["id"]: t for t in h.load_tasks(["b17/", "b17-1/"])}
    path = run_dir / "rewards.jsonl"
    done = {(r["attempt"], r["iter"]) for r in map(json.loads, path.read_text().splitlines())} if path.exists() else set()
    todo = [r for r in h.read_records(run_dir)
            if r["task"] in tasks and r["stage"] != "infra_error" and (r["attempt"], r["iter"]) not in done]
    print(f"{len(todo)} replies to score, {len(done)} already scored", flush=True)
    with open(path, "a") as out, cf.ProcessPoolExecutor(jobs) as pool:
        for rec in pool.map(score_reply, [tasks[r["task"]] for r in todo], todo, [key] * len(todo)):
            out.write(json.dumps(rec) + "\n")
            out.flush()


def tier(r):
    if any(kind == "discrepancy" for _, kind in r.get("triage", [])):
        return "discrepancy"
    return {0.0: "none", 0.05: "parses", 0.8: "verified", 0.9: "right"}.get(r["reward"], "checks")


def summarize(rows):
    """Per CLI and track: attempts, the mean first and last rewards, the last replies' tiers and triage."""
    attempts = defaultdict(list)
    for r in rows:
        attempts[r["attempt"]].append(r)
    out = defaultdict(lambda: {"attempts": 0, "first": 0.0, "last": 0.0, "tiers": Counter(), "triage": Counter()})
    for replies in attempts.values():
        replies.sort(key=lambda r: r["iter"])
        first, last = replies[0], replies[-1]
        g = out[f"{last['cli']}/{last['task'].split('/')[0]}"]
        g["attempts"] += 1
        g["first"] += first["reward"]
        g["last"] += last["reward"]
        g["tiers"][tier(last)] += 1
        g["triage"].update(kind for _, kind in last.get("triage", []))
    for g in out.values():
        g["first"], g["last"] = round(g["first"] / g["attempts"], 3), round(g["last"] / g["attempts"], 3)
    disagree = [f"{r['task']} {r['cli']} {r['attempt']} iter {r['iter']}: {r['stage']}, {r['reward']}"
                for r in rows if (r["stage"] == "verified") != ("triage" in r)]
    return dict(sorted(out.items())), disagree


def main(argv):
    if len(argv) not in (2, 4) or argv[0] not in ("score", "summary") or argv[2:3] not in ([], ["--jobs"]):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    run_dir = h.RUNS / argv[1]
    if argv[0] == "score":
        split, key = S.load(), S.secret()
        S.check_secret(key, split)
        score(run_dir, key, *map(int, argv[3:]))
        return 0
    groups, disagree = summarize([json.loads(line) for line in (run_dir / "rewards.jsonl").read_text().splitlines()])
    print(json.dumps({"groups": groups, "disagree": disagree}, indent=1))
    return 1 if disagree else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
