"""Self-check for the frozen split (D123): uv run --no-project gym/test_split.py

Needs the secret, at ~/.config/babel-17/gym-secret. Checks that split.json records it, that the
test set is M3's 34 tasks, and that tasks the table names as one problem are held out together.
Being held out depends on a task's problem alone, so no problem is both held out and trained on;
what can go wrong is two tasks posing one problem under two names. Only review finds that in
general, but tasks whose specs are the same text, but for the method's name, must share a problem.
"""
import re

import harness as h
import split as S

split, key = S.load(), S.secret()
S.check_secret(key, split)
try:
    S.check_secret(key + b"\0", split)
    raise AssertionError("a different secret passed")
except ValueError:
    pass

loaded = h.load_tasks()
tasks = [t["id"] for t in loaded]
assert split["test"] == sorted(t for t in tasks if t.startswith(("b17/", "b17-1/"))) and len(split["test"]) == 34
assert set(split["problems"]) <= set(tasks), set(split["problems"]) - set(tasks)  # the table names real tasks
# The same problem under another name is held out, as D123's three are and the test set's Dafny versions.
for t in ["algoveri/binary_search", "algoveri/gcd", "algoveri/insertion_sort", "algoveri/linear_search",
          "algoveri/quick_sort", "algoveri/fast_exponential", "vericoding/DV0015", "vericoding/DT0555", "vericoding/DD0369",
          "algoveri/prim", "abs"]:
    assert S.held_out(split, key, t), t
assert not S.held_out(split, key, "algoveri/bfs")  # the supplement's worked proof, in every prompt (D117)

same = {}  # a Dafny task's spec, with its comments and its method's name taken out -> the tasks with it
for t in loaded:
    if t.get("lang") != "b17":
        code = "".join(" " if k[:2] in ("//", "/*") else k for k in h.TOKEN.findall(t["preamble"] + "\n" + t["signature"]))
        text = re.sub(r"\s+", " ", re.sub(rf"\b{re.escape(t['name'])}\b", "NAME", code))
        same.setdefault(text, []).append(t["id"])
for ids in same.values():
    assert len({S.problem(split, t) for t in ids}) == 1, ids
held = {S.problem(split, t) for t in tasks if S.held_out(split, key, t)}
train = {S.problem(split, t) for t in tasks if not S.held_out(split, key, t)}
# The slice holds out 1 problem in 10, by the secret.
names = [f"problem {k}" for k in range(10_000)]
share = sum(S.held_out(split, key, n) for n in names) / len(names)
assert 0.09 < share < 0.11, share
assert [S.held_out(split, key, n) for n in names] != [S.held_out(split, b"another", n) for n in names]
print(f"split self-check passed: {len(held)} problems held out, {len(train)} to train on")
