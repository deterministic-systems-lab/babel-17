"""Self-check for the verifier's cache and report (D22-D25, D63): uv run --no-project b17c/test_verify.py

Needs z3 on PATH, so it runs locally rather than in CI.
"""
import re
import tempfile
from pathlib import Path

import verify as v
from syntax import parse

SUITE = Path(__file__).resolve().parent.parent / "suite"
CACHE = Path(tempfile.mkdtemp())


def run(text, seeds=1):
    return v.verify(parse(text), seeds, CACHE)[0]


def src(name):
    return (SUITE / "accept" / f"{name}.b17").read_text()


# canonical() renames generated names in order of first occurrence, and only those.
q = "(declare-const x!12 Int) (declare-const n!p SI) (assert (= (g!fib x!12) (len.I n!p))) (assert (forall ((i!b3 Int)) (p!fib i!b3)))"
assert v.canonical(q) == "(declare-const k!0 Int) (declare-const k!1 SI) (assert (= (k!2 k!0) (len.I k!1))) (assert (forall ((k!3 Int)) (k!4 k!3)))"
assert v.canonical(v.canonical(q)) == v.canonical(q)

# The worked example verifies; run again, every verdict comes from the cache (WP5's done-when).
first = run(src("merge_sorted"))
assert all(r["verdict"] == "proved" for r in first) and not any(r["cached"] for r in first)
assert all(r["cached"] for r in run(src("merge_sorted")))

# A renamed definition sends the same canonical queries, so its proofs are reused (D45, D63).
renamed = src("merge_sorted")
for old, new in [("out", "res"), ("merge_sorted", "merge"), ("i", "k")]:
    renamed = re.sub(rf"\b{old}\b", new, renamed)
assert all(r["cached"] for r in run(renamed))

# A body edit re-verifies only that definition; its callers see only its spec (D22).
CALLS = """(module calls (header (purpose "p") (invariants "i") (failures "f"))
  (spec one (params) (returns (r i64)) (ensures (== r 1)) (effects))
  (def one (body (return 1)))
  (spec two (params) (returns (r i64)) (ensures (== r 2)) (effects))
  (def two (body (let ((x i64)) (call one)) (return (+ x 1)))))"""
run(CALLS)
edited = run(CALLS.replace("(return 1)", "(let y i64 1) (return y)"))
assert {r["node"].split("/")[0] for r in edited if not r["cached"]} == {"def one"}, edited
# A spec edit re-verifies its callers too.
respec = run(CALLS.replace("(ensures (== r 1))", "(ensures (>= r 1) (<= r 1))"))
assert {"def two"} <= {r["node"].split("/")[0] for r in respec if not r["cached"]}, respec

# The key's own parts: changing only the dependency hashes changes it (D22, D63).
cfg = {"seeds": 1}
assert v.cache_key("d", ["a", "b"], "q", cfg) == v.cache_key("d", ["b", "a"], "q", cfg)
assert v.cache_key("d", ["a", "b"], "q", cfg) != v.cache_key("d", ["a", "c"], "q", cfg)
assert v.cache_key("d", [], "q", cfg) != v.cache_key("d", [], "q", {"seeds": 2})

# A failing goal is reported by node ID, contract clause and family; the report gives the
# level, input hash and goals D24 and D25 ask for.
bad = (SUITE / "reject/E-PROOF-POST-wrong-result.b17").read_text()
rows, cfg = v.verify(parse(bad), 1, CACHE)
failed = [r for r in rows if r["verdict"] != "proved"]
assert [r["family"] for r in failed] == ["POST"] and failed[0]["node"].startswith("def bad_abs/2.1@14:7 spec bad_abs/"), rows
rep = v.report(parse(bad), rows, cfg)
assert rep["level"] == "L2-S" and rep["lockfile_sha256"] is None and rep["admitted"] == []
assert rep["input_sha256"] == v.sha256(v.canonical_bytes(parse(bad))) and len(rep["solver_sha256"]) == 64
assert rep["failed"] == [{"node": failed[0]["node"], "family": "POST", "verdict": failed[0]["verdict"]}]
assert rep["solver_trusted"] == [r["node"] for r in rows if r["verdict"] == "proved"]
assert "law_take_step" in rep["axioms"]["core"]
assert v.report(parse(src("abs")), run(src("abs")), cfg)["level"] == "L3-S"

# Every goal has its own node ID: one per ensures clause at a return, and a number for a
# node checked twice, as a loop condition is on entry and at each iteration.
TWO = """(module two (header (purpose "p") (invariants "i") (failures "f"))
  (spec f (params (a (ref (slice i64)))) (returns (r i64)) (requires (> (len a) 0)) (ensures (== r 0) (== r 1)) (effects))
  (def f (body (let-mut i i64 0) (while (< (idx a 0) i) (decreases i) (set i (- i 1))) (return 0))))"""
ids = [r["node"] + " " + r["family"] for r in run(TWO)]
assert len(ids) == len(set(ids)), ids
assert any(n.endswith("#2 BOUNDS") for n in ids), ids

# Sorts come from WP3's types: multisets of booleans, and empty literals whose element type
# only their context fixes: a comparison, concat, take, a ghost-fn's parameter or result.
SORTS = """(module sorts (header (purpose "p") (invariants "i") (failures "f"))
  (ghost-fn none ((s (seq bool))) bool (body (== s (seq-lit))))
  (ghost-fn empty () (seq bool) (body (take (seq-lit) 0)))
  (ghost-fn chosen () bool (body (if false (last (seq-lit)) (if false (idx (seq-lit) 0) true))))
  (spec same (params (a (vec bool))) (returns (r (vec bool)))
    (ensures (== (multiset r) (multiset a)) (== (occurrences r true) (occurrences a true))
             (== (concat (seq-lit) r) r) (== (seq-lit) (take r 0)) (== (take (seq-lit) 0) (take r 0))
             (none (take (seq-lit) 0)) (== (empty) (drop r (len r))) (== (if (none r) r a) r) (== (seq-lit (not false)) (seq-lit true))
             (chosen) (== (occurrences (seq-lit) true) 0) (not (contains (seq-lit) false))) (effects))
  (def same (body (return a)))
  (spec count (params (a (ref (slice bool)))) (returns (n i64)) (ensures (== n (len a))) (effects))
  (def count (body (return (len a))))
  (spec wrap (params) (returns (v (vec bool))) (ensures (== v (seq-lit))) (effects))
  (def wrap (body (let w (vec bool) (vec-new)) (let ((n i64)) (call count (borrow w))) (return w))))"""
assert all(r["verdict"] == "proved" for r in run(SORTS))
# A module that fails tier 0 has no goals; the error lists its diagnostics.
try:
    run(SORTS.replace("(return a)", "(return b)"))
    raise AssertionError("an undefined name was verified")
except ValueError as e:
    assert "E-TYPE-002: 'b' is undefined" in str(e), e

# Only verdicts reached within the budget are cached: a timeout is solved again (D23).
real = v.G.solve_stats
v.G.solve_stats = lambda q, seed=0: ("unknown: timeout", 0)
try:
    fresh = "(module t (header (purpose \"p\") (invariants \"i\") (failures \"f\")) (spec g (params) (returns (r i64)) (ensures (== r 7)) (effects)) (def g (body (return 7))))"
    assert not any(r["cached"] for r in run(fresh)) and not any(r["cached"] for r in run(fresh))
finally:
    v.G.solve_stats = real
# A partial entry from a crashed run is a miss, not an error.
entry = next(CACHE.rglob("*.json"))
entry.write_text('{"verdict": "pro')
assert v._read(entry) is None

print("verifier self-check passed")
