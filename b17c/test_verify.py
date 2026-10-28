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

# A failing goal is reported by node ID and family, and the report lists it.
bad = (SUITE / "reject/E-PROOF-POST-wrong-result.b17").read_text()
rows, cfg = v.verify(parse(bad), 1, CACHE)
assert [(r["family"], r["node"]) for r in rows if r["verdict"] != "proved"] == [("POST", "def bad_abs/2.1@14:7")], rows
rep = v.report(parse(bad), rows, cfg)
assert rep["failed"] == [{"node": "def bad_abs/2.1@14:7", "family": "POST", "verdict": rows[-1]["verdict"]}]
assert rep["solver_trusted"] == [r["node"] for r in rows if r["verdict"] == "proved"] and rep["admitted"] == []
assert "law_take_step" in rep["axioms"]["core"]

print("verifier self-check passed")
