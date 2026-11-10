"""Self-check for WP11's reward (D123): uv run --no-project gym/test_reward.py

Needs z3 on PATH. Scores replies to b17/abs at each tier, with the hacks D123 measured, and the pool's
path on tasks made up here: a right reply, and one whose output the interpreter can't judge. Takes
about a minute.
"""
import hashlib
import json
import tempfile
from pathlib import Path

import harness as h
import reward as R

SECRET = b"not the real secret"
ABS = h.load_tasks(["b17/abs"])[0]
GOOD = "(def abs (body (if (< x 0) (return (neg x)) (return x))))"
SLOW = """(def abs (body (if (< x 0) (return (neg x)) (block)) (let-mut y i64 0)
  (while (< y x) (invariant (and (<= 0 y) (<= y x))) (decreases (- x y)) (set y (+ y 1))) (return y)))"""


def pool_task(ensures):
    return {"id": "test/same", "lang": "b17", "name": "same", "frozen": f"""(module same
  (header (purpose "Return x.") (invariants "None.") (failures "None."))
  (spec same (params (x i64)) (returns (y i64)) (requires (< -100 x) (< x 100)) (ensures {ensures}) (effects)))"""}


with tempfile.TemporaryDirectory() as d:
    split = Path(d, "split.json")
    split.write_text(json.dumps({"secret_sha256": hashlib.sha256(SECRET).hexdigest()}))
    score = lambda task, code: R.score(task, code, SECRET, split)

    # No scoring without the split's secret.
    for wrong in (b"a guess", SECRET + b" "):
        try:
            R.score(ABS, GOOD, wrong, split)
            raise AssertionError("scored with the wrong secret")
        except ValueError as e:
            assert "doesn't match" in str(e), e

    # Each tier, with what recomputing it needs.
    best = score(ABS, GOOD)
    assert best["reward"] == 0.90 and best["triage"] == [], best
    assert best["spec_sha256"] == R.H.hashes(R.syntax.parse(ABS["frozen"].encode(), 0), 0)["abs"][1], best
    assert best["reply_sha256"] == h.sha(GOOD) and len(best["inputs_sha256"]) == 64 and best["b17c_commit"], best
    assert score(ABS, GOOD)["inputs_sha256"] == best["inputs_sha256"]  # the same inputs every time
    assert score(ABS, "(def abs (body (return x)")["reward"] == 0.0
    assert score(ABS, "(spec abs (params (x i64)) (returns (y i64)) (effects)) " + GOOD)["reward"] == 0.05  # E-TYPE-002
    assert score(ABS, "(spec cheat (params (x i64)) (returns (y i64)) (effects)) " + GOOD)["reward"] == 0.05  # no def
    zero = score(ABS, "(def abs (body (return 0)))")
    assert (zero["reward"], zero["parts"]) == (0.40, [True, False, True]), zero  # (>= y 0), but not y = ±x

    # D123's hacks earn no more than returning 0.
    pad = " ".join(f"(assert (== {k} {k}))" for k in range(20))
    for code, want in [(f"(def abs (body {pad} (return 0)))", 0.40),
                       ("(def abs (body (assert false) (return 0)))", 0.30),
                       ("(def abs (body (while true (invariant true) (decreases 0)) (return 0)))", 0.20),
                       ("(def abs (body (let z i64 (+ x 9223372036854775807)) (return x)))", 0.20),
                       ("(lemma bad (params (x int)) (ensures (== x 0)) (body)) (def abs (body (call bad x) (return 0)))", 0.30)]:
        assert score(ABS, code)["reward"] == want, (code, score(ABS, code))

    # A verified reply that runs out of steps keeps 0.80, and is recorded.
    steps, R.STEPS = R.STEPS, 100_000
    slow = score(ABS, SLOW)
    R.STEPS = steps
    assert slow["reward"] == 0.80 and {t[1] for t in slow["triage"]} == {"limit"}, slow

    # A verified reply the reference says is wrong is a discrepancy, and scores 0.
    case = R.a.CASES["b17/abs"]
    R.a.CASES["b17/abs"] = lambda r, big: ((5,), lambda y: y == 6)
    wrong = score(ABS, GOOD)
    R.a.CASES["b17/abs"] = case
    assert wrong["reward"] == 0.0 and wrong["triage"][0][1] == "discrepancy", wrong

    # On the pool, the spec is the reference; a clause it can't decide on the output leaves 0.80.
    assert score(pool_task("(== y x)"), "(def same (body (return x)))")["reward"] == 0.90
    undecided = score(pool_task("(== y x) (forall ((k int)) (=> (< k y) (< k (+ y 1))))"), "(def same (body (return x)))")
    assert undecided["reward"] == 0.80 and {t[1] for t in undecided["triage"]} == {"undecided"}, undecided
print("reward self-check passed")
