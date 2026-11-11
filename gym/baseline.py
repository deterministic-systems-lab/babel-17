"""WP11's in-context baseline (D123): every reply of a harness run on the B17 tasks, scored by reward.py.

    uv run --no-project gym/baseline.py score RUN_ID [--jobs N]
    uv run --no-project gym/baseline.py summary RUN_ID

score writes gym/runs/RUN_ID/rewards.jsonl, one line per reply, and resumes where it stopped. A reply
with no code earns 0, and a call that failed, with no reply, isn't scored. A reply on which Z3 itself
fails isn't either, as the harness retries its checker_error, and is printed to score again. A
verified reply's triage keeps how many held-out inputs it isn't right on, by kind, not which: the
record is in the repository, and the inputs come from the secret. Scoring it again under the secret
shows them.

summary counts each sample by the attempt the harness counts done, and prints, for each CLI and
track, the mean reward of the attempt's first reply, before any feedback, and of its last, after up
to 8 rounds; the last replies' tiers and triage; samples with no attempt done; and every reply on
which the reward and the harness disagree about whether it verified. It fails if a reply isn't scored.
"""
import concurrent.futures as cf
import json
import sys
from collections import Counter, defaultdict

import harness as h
import reward as R
import split as S


def replies(records):
    """The records that hold a reply: all but a failed call's."""
    return [r for r in records if r["stage"] != "infra_error" or r.get("code") is not None]


def score_reply(task, rec, key, split=S.SPLIT):
    try:
        out = R.score(task, rec.get("code"), key, split)
    except RuntimeError as e:  # Z3 itself failed: no verdict on the reply
        print(f"not scored, {rec['attempt']} iter {rec['iter']}: {e}", flush=True)
        return None
    if "triage" in out:
        out["triage"] = dict(Counter(kind for _, kind, _ in out["triage"]))  # how many, not which
    return {k: rec[k] for k in ("attempt", "iter", "cli", "sample", "stage", "final")} | out


def score(run_dir, key, jobs=3):
    tasks = {t["id"]: t for t in h.load_tasks(["b17/", "b17-1/"])}
    path = run_dir / "rewards.jsonl"
    done = {(r["attempt"], r["iter"]) for r in map(json.loads, path.read_text().splitlines())} if path.exists() else set()
    todo = [r for r in replies(h.read_records(run_dir)) if r["task"] in tasks and (r["attempt"], r["iter"]) not in done]
    print(f"{len(todo)} replies to score, {len(done)} already scored", flush=True)
    with open(path, "a") as out, cf.ProcessPoolExecutor(jobs) as pool:
        for rec in pool.map(score_reply, [tasks[r["task"]] for r in todo], todo, [key] * len(todo)):
            if rec is not None:
                out.write(json.dumps(rec) + "\n")
                out.flush()


def tier(r):
    if r.get("triage", {}).get("discrepancy"):
        return "discrepancy"
    return {0.0: "none", 0.05: "parses", 0.2: "checks", 0.8: "verified", 0.9: "right"}.get(r["reward"], "some goals")


def summarize(rows, records):
    """Per CLI and track: samples, the mean first and last rewards, and the last replies' tiers and triage;
    the samples with no attempt done; and the replies the reward and the harness disagree on."""
    scored = {(r["attempt"], r["iter"]): r for r in rows}
    if missing := [r for r in replies(records) if (r["attempt"], r["iter"]) not in scored]:
        raise ValueError(f"{len(missing)} replies aren't scored, the first {missing[0]['attempt']} iter {missing[0]['iter']}")
    done = {h.sample_key(r): r["attempt"] for r in records if r["final"] and r["stage"] != "infra_error"}
    out = defaultdict(lambda: {"samples": 0, "first": 0.0, "last": 0.0, "tiers": Counter(), "triage": Counter()})
    for (task, cli, _), attempt in sorted(done.items()):
        its = sorted((r for r in rows if r["attempt"] == attempt), key=lambda r: r["iter"])
        g = out[f"{cli}/{task.split('/')[0]}"]
        g["samples"] += 1
        g["first"] += its[0]["reward"]
        g["last"] += its[-1]["reward"]
        g["tiers"][tier(its[-1])] += 1
        g["triage"].update(its[-1].get("triage", {}))
    for g in out.values():
        g["first"], g["last"] = round(g["first"] / g["samples"], 3), round(g["last"] / g["samples"], 3)
    disagree = [f"{r['task']} {r['cli']} {r['attempt']} iter {r['iter']}: {r['stage']}, {r['reward']}"
                for r in rows if (r["stage"] == "verified") != ("triage" in r)]
    return dict(sorted(out.items())), sorted({h.sample_key(r) for r in records} - set(done)), disagree


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
    rows = [json.loads(line) for line in (run_dir / "rewards.jsonl").read_text().splitlines()]
    groups, undone, disagree = summarize(rows, h.read_records(run_dir))
    print(json.dumps({"groups": groups, "undone": undone, "disagree": disagree}, indent=1))
    return 1 if undone or disagree else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
