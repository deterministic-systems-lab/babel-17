"""Self-check for the run-time audit (D118): uv run --no-project gym/test_audit.py

Every B17 task has a case, and its suite solution passes, so the references and inputs agree with
programs known to verify. With contracts checked, no case's input breaks the spec's requires, as far
as the interpreter can evaluate them (D58). It also fails what it's for: a wrong answer, the length
trick and an exhaustive search, the last two from real runs. Those two use up the limit, so this
takes minutes.
"""
import json
import random

import audit as a
import harness as h

tasks = {t["id"]: t for t in h.load_tasks(["b17/", "b17-1/"])}
assert set(tasks) == set(a.CASES), set(tasks) ^ set(a.CASES)
modules = {k: a.syntax.parse(t["solution"].encode(), t.get("subset", 0)) for k, t in tasks.items()}
for k, t in tasks.items():
    assert a.audit(t, modules[k]) == ("right", a.INPUTS, ""), (k, a.audit(t, modules[k]))
    r = random.Random("valid")
    for big in (False, False, True):
        args, _ = a.CASES[k](r, big)
        out = a.i.run(modules[k], t["name"], args, check=True, fuel=20_000_000, depth=a.DEPTH, subset=t.get("subset", 0))
        assert not isinstance(out, a.i.Contract), (k, a.i.text_of(out)[:300])


def recorded(run, task, cli, sample, round_):
    """The module of a recorded round."""
    for line in (h.RUNS / run / "attempts.jsonl").read_text().splitlines():
        r = json.loads(line)
        if (r["task"], r["cli"], r["sample"], r["iter"]) == (task, cli, sample, round_):
            t = tasks[task]
            return t, a.syntax.parse((t["frozen"][:-1] + "\n" + r["code"] + ")").encode(), t.get("subset", 0))
    raise KeyError((run, task, cli, sample, round_))


ek = tasks["b17-1/edmond_karp"]
zero = a.syntax.parse((ek["frozen"][:-1] + "\n(def max_flow_value (body (return 0))))").encode(), 1)
assert a.audit(ek, zero)[0] == "wrong"
assert a.audit(*recorded("20261103T220624Z-claude-codex", "b17-1/push_relabel", "codex", 2, 8))[0] == "stuck"  # exhaustive_score
assert a.audit(*recorded("20261102T173606Z-claude-codex", "b17-1/prim", "codex", 1, 7))[0] == "stuck"  # the length trick
print("run-time audit self-check passed")
