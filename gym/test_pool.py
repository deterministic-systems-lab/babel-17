"""Self-check for WP11's entry checks (D123): uv run --no-project gym/test_pool.py

Needs z3 on PATH, but not the secret: check 5's inputs here come from a made-up one. Runs the checks
on b17/abs, which passes them all; on b17/min_index, whose one differing survivor is allowed; and on
tasks made up here that each fail some. Takes about a minute.
"""
import harness as h
import pool as P
import reward as R
import split as S

KEY, SPLIT = b"not the real secret", S.load()


def task(requires, ensures, body):
    frozen = f"""(module same
  (header (purpose "Return x.") (invariants "None.") (failures "None."))
  (spec same (params (x i64)) (returns (y i64)) (requires {requires}) (ensures {ensures}) (effects)))"""
    return {"id": "test/same", "lang": "b17", "name": "same", "frozen": frozen,
            "solution": frozen[:-1] + f"\n  (def same (body {body})))"}


def checks(t):
    """The entry checks' results, and the checks that fail."""
    out = P.entry(t, KEY, SPLIT)
    return out, [k for k in range(1, 6) if not out[k]["pass"]]


ABS = h.load_tasks(["b17/abs"])[0]
out, failing = checks(ABS)
assert failing == [] and out["enters"]
# Check 5 draws from the spec on a test-set task too, not D118's references.
assert all(ok is None for _, ok in R.inputs(ABS, R.syntax.parse(ABS["frozen"].encode()), KEY, out["spec_sha256"], SPLIT, pool=True))
out, failing = checks(h.load_tasks(["b17/min_index"])[0])  # (and (<= 0 m) (< m (len a))), and a tie it allows
assert failing == [1] and [m["path"] for m in out[4]["differ"]] == ["2.3.6.1"]
BOUNDED = "(< -100 x) (< x 100)"
assert checks(task(BOUNDED, "(and (== y x) (< y 100))", "(return (+ x 0))"))[1] == [1]
out, failing = checks(task(BOUNDED, "(== y x) (< x 100)", "(return (+ x 0))"))
assert failing == [2] and out[2]["trivial"] == ["(< x 100)"]  # true by the requires alone
assert checks(task(BOUNDED, "(== y x)", "(return (+ x 1))"))[1] == [3, 4, 5]  # a wrong reference
out, failing = checks(task(BOUNDED, "(== y x)", "(return x)"))
assert failing == [4] and out[4]["mutants"] == 0  # nothing to mutate
# The interpreter can't decide a forall with no bound on its output; what's kept of it names no input.
out, failing = checks(task(BOUNDED, "(== y x) (forall ((k int)) (=> (< k y) (< k (+ x 1))))", "(return (+ x 0))"))
assert failing == [5] and out[5]["wrong"] == [(k, "undecided") for k in range(25)]
try:
    P.entry(task(BOUNDED, "(== y x)", "(return x)") | {"solution": task(BOUNDED, "(>= y x)", "(return x)")["solution"]}, KEY, SPLIT)
    raise AssertionError("a reference with a spec of its own passed")
except ValueError:
    pass
print("entry checks self-check passed")
