"""Self-check for WP11's entry checks (D123): uv run --no-project gym/test_pool.py

Needs z3 on PATH, but not the secret: check 5's inputs here come from a made-up one. Runs the checks
on b17/abs, which passes them all; on b17/min_index, whose one differing survivor is allowed; and on
tasks made up here that each fail some. Takes about a minute.
"""
import harness as h
import pool as P
import split as S

KEY, SPLIT = b"not the real secret", S.load()


def task(requires, ensures, body):
    frozen = f"""(module same
  (header (purpose "Return x.") (invariants "None.") (failures "None."))
  (spec same (params (x i64)) (returns (y i64)) (requires {requires}) (ensures {ensures}) (effects)))"""
    return {"id": "test/same", "lang": "b17", "name": "same", "frozen": frozen,
            "solution": frozen[:-1] + f"\n  (def same (body {body})))"}


def failing(t):
    out = P.entry(t, KEY, SPLIT)
    return [k for k in range(1, 6) if not out[k]["pass"]]


assert failing(h.load_tasks(["b17/abs"])[0]) == []
assert failing(h.load_tasks(["b17/min_index"])[0]) == [1]  # (and (<= 0 m) (< m (len a))); its tie is allowed
BOUNDED = "(< -100 x) (< x 100)"
assert failing(task(BOUNDED, "(and (== y x) (< y 100))", "(return (+ x 0))")) == [1]
assert failing(task(BOUNDED, "(== y x) (< x 100)", "(return (+ x 0))")) == [2]  # true by the requires alone
assert failing(task(BOUNDED, "(== y x)", "(return (+ x 1))")) == [3, 4, 5]  # a wrong reference
assert failing(task(BOUNDED, "(== y x)", "(return x)")) == [4]  # nothing to mutate
# The interpreter can't decide a forall with no bound on its output.
assert failing(task(BOUNDED, "(== y x) (forall ((k int)) (=> (< k y) (< k (+ x 1))))", "(return (+ x 0))")) == [5]
print("entry checks self-check passed")
