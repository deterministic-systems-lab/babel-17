"""Self-check for M3's B17-0 track (D98) and B17-1 track (D112): uv run --no-project gym/test_b17.py

Needs z3 on PATH, but not Dafny. The attempt loop runs against a fake CLI, so no
subscription is spent.
"""
import json
import sys
import tempfile
from pathlib import Path

import harness as h

tasks = {t["id"]: t for t in h.load_tasks(["b17/"])}
assert len(tasks) == 20, sorted(tasks)
# Each task is its program's header, its spec and the ghost-fns the spec needs; never a def or lemma.
for t in tasks.values():
    assert "(def " not in t["frozen"] and "(lemma " not in t["frozen"] and t["frozen"].endswith(")"), t["id"]
    assert h.verify_b17(t, "")[0] == "no_def", t["id"]
assert "(ghost-fn sum_of" in tasks["b17/sum"]["frozen"] and tasks["b17/fib"]["name"] == "fib_iter"

ABS = tasks["b17/abs"]
GOOD = "(def abs (body (if (< x 0) (return (neg x)) (return x))))"
assert h.verify_b17(ABS, GOOD) == ("verified", "")
stage, out = h.verify_b17(ABS, "(def abs (body (return x)))")
assert stage == "proof_failed" and json.loads(out)[0]["code"] == "E-PROOF-POST", out
# The frozen spec can't be restated, weakened or not; a helper spec needs a def; bad syntax is rejected.
stage, out = h.verify_b17(ABS, "(spec abs (params (x i64)) (returns (y i64)) (effects)) " + GOOD)
assert stage == "rejected" and "E-TYPE-002" in out, out
stage, out = h.verify_b17(ABS, "(spec cheat (params (x i64)) (returns (y i64)) (ensures (>= y 0) (or (== y x) (== y (neg x)))) (effects))"
                               " (def abs (body (let ((y i64)) (call cheat x)) (return y)))")
assert stage == "no_def" and "cheat" in out, out
assert h.verify_b17(ABS, "(def abs (body (return x)")[0] == "rejected"

# The prompt carries the manual and where the agent's lines start; a repair carries the diagnostics.
p = h.render(ABS, None)
assert h.MANUAL.read_text() in p and f"line {ABS['frozen'].count(chr(10)) + 2}" in p and "```lisp" in p
assert '"code": "E-PROOF-POST"' in h.render(ABS, None, "(def abs (body (return x)))", '[{"code": "E-PROOF-POST"}]')
assert h.extract_code("a\n```lisp\nX\n```\n```dafny\nY\n```", "b17") == "X"

# One attempt end to end: a wrong first reply, then a right one after the diagnostics.
fake = Path(tempfile.mkdtemp()) / "fake.py"
fake.write_text(f"""import json, sys
prompt = sys.stdin.read()
code = {GOOD!r} if "Your previous items" in prompt else "(def abs (body (return x)))"
print(json.dumps({{"result": "```lisp\\n" + code + "\\n```", "usage": {{"input_tokens": 1, "output_tokens": 1}},
                  "modelUsage": {{"fake": {{}}}}}}))
""")
h.CLIS["claude"] = [sys.executable, str(fake)]
recs = []
h.run_attempt(ABS, "claude", 1, 4, None, recs.append)
assert [(r["iter"], r["stage"], r["final"], r["lang"]) for r in recs] == [
    (1, "proof_failed", False, "b17"), (2, "verified", True, "b17")], [(r["iter"], r["stage"]) for r in recs]
assert "E-PROOF-POST" in recs[0]["feedback"]

# Summaries count B17-0 apart from Dafny, and a run's settings pin b17c and the manual.
run = Path(tempfile.mkdtemp())
h.RUNS = run
(run / "r").mkdir()
(run / "r" / "attempts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
stats = h.summarize("r")
assert list(stats) == ["claude/b17"] and stats["claude/b17"]["verified"] == 1, stats
s = h.settings([ABS], None)
assert "b17c_sha" in s and "b17_prompt_sha" in s and "b17c_sha" not in h.settings([], None)

# Review regressions. A checker failure is an infrastructure error, retried on resume, never a verdict.
real = h.verify_b17
h.verify_b17 = lambda task, code: ("checker_error", "RuntimeError: b17c broke")
recs = []
h.run_attempt(ABS, "claude", 1, 4, None, recs.append)
assert [(r["stage"], r["final"]) for r in recs] == [("infra_error", True)] and "b17c broke" in recs[0]["error"], recs
h.verify_b17 = real
# A B17-0 run's settings don't depend on Dafny; reverify ignores the B17-0 prompt, as it does Dafny's.
assert "dafny" not in h.settings([ABS], "4.11.0") and "dafny" in h.settings([h.load_task(h.TASKS / "abs.dfy")], "4.11.0")
# The panic guard reads the spec, not the text: a header may mention panic.
assert not h.allows_panic(dict(ABS, frozen=ABS["frozen"].replace("Return the absolute", "(effects panic) Return the absolute")))
assert h.allows_panic(dict(ABS, frozen=ABS["frozen"].replace("(effects))", "(effects panic))")))

# B17-1's track (D112): the AlgoVeri ports, each posing its first spec with the data items and
# ghost-fns it refers to; helper specs, defs and proof-only items stay hidden.
ones = {t["id"]: t for t in h.load_tasks(["b17-1/"])}
assert len(ones) == 13 and all(t["subset"] == 1 for t in ones.values()), sorted(ones)
assert all("subset" not in t for t in tasks.values())  # B17-0's tasks, and so their task_sha, are as before
for t in ones.values():
    assert "(def " not in t["frozen"] and "(lemma " not in t["frozen"] and t["frozen"].count("(spec ") == 1, t["id"]
    assert h.verify_b17(t, "")[0] == "no_def", t["id"]
LCA = ones["b17-1/lca"]
assert LCA["name"] == "lowest_common_ancestor" and "(data tree" in LCA["frozen"] and "(spec find" not in LCA["frozen"]
SEARCH = ones["b17-1/bst_search"]
DEF = SEARCH["solution"][SEARCH["solution"].index("(def search"):].rstrip()[:-1]  # the port's own def
assert h.verify_b17(SEARCH, DEF) == ("verified", ""), h.verify_b17(SEARCH, DEF)
stage, out = h.verify_b17(SEARCH, "(def search (body (return false)))")
assert stage == "proof_failed" and json.loads(out)[0]["code"] == "E-PROOF-POST", out
stage, out = h.verify_b17(SEARCH, "(data tree () (leaf)) " + DEF)  # a task item can't be restated
assert stage == "rejected" and "E-TYPE-002" in out, out
# The prompt is the manual, then the supplement; B17-0's carries no supplement.
p1 = h.render(SEARCH, None)
assert p1.startswith("Write B17-1 code") and h.MANUAL.read_text() in p1 and h.MANUAL1.read_text() in p1, p1[:200]
assert p1.index(h.MANUAL.read_text()) < p1.index(h.MANUAL1.read_text()) and "data items" in p1
assert h.MANUAL1.read_text() not in h.render(ABS, None) and h.render(ABS, None).startswith("Write B17-0 code")
# B17-1 counts as its own track, and pins the supplement and core1.b17 too.
(run / "r1").mkdir()
(run / "r1" / "attempts.jsonl").write_text(json.dumps(dict(recs[0], task="b17-1/bst_search", stage="verified", final=True)) + "\n")
assert list(h.summarize("r1")) == ["claude/b17-1"], h.summarize("r1")
s1 = h.settings([SEARCH], None)
assert "b17_1_prompt_sha" in s1 and s1["b17c_sha"] != h.settings([ABS], None)["b17c_sha"] and "b17_1_prompt_sha" not in h.settings([ABS], None)

print("B17-0 and B17-1 track self-check passed")
