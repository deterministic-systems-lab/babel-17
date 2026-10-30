"""Self-check for WP6's agent protocol (D93, D94): uv run --no-project b17c/test_agent.py

The queries that solve goals need z3 on PATH, so CI runs only the others.
"""
import contextlib
import io
import shutil
import tempfile
from pathlib import Path

import agent as A
import syntax


def parse(text, subset=0):  # B17-0's tests name their subset (D101)
    return syntax.parse(text, subset)


SUITE = Path(__file__).resolve().parent.parent / "suite"
CACHE = Path(tempfile.mkdtemp())
read = lambda name: parse((SUITE / name).read_bytes())
HEAD = '(module m (header (purpose "p") (invariants "i") (failures "f"))'

# explain: the rule from docs/b17-0.md §9, the text that states it, and the suite's labelled example.
e = A.explain("E-OWN-005")
assert "ownership" in e["rule"] and any("at most one" in d for d in e["details"]), e
assert e["examples"][0]["file"] == "suite/reject/E-OWN-005-vector-twice-in-call.b17"
assert A.explain("E-PROOF-POST")["rule"].startswith("`ensures` holds")

# A tier 0 error carries its D56 node ID.
[d] = A.diagnostics(read("reject/E-OWN-001-use-after-move.b17"))
assert d["code"] == "E-OWN-001" and d["node"] == "def moved/2.2.1.1@14:20" and d["severity"] == "error", d

# simulate: a checked run, in interface 10's terms.
s = A.simulate(read("accept/abs.b17"), "abs", ["-5"])
assert s["outcome"] == "ok" and s["results"] == [5] and s["text"] == "ok 5", s

if shutil.which("z3"):
    # A failed goal: the goal over the program's names, a counterexample the interpreter
    # reproduces, its context, and how many later goals assume it.
    [d] = A.diagnostics(read("reject/E-PROOF-OVERFLOW-unbounded-increment.b17"), 1, CACHE)
    assert d["code"] == "E-PROOF-OVERFLOW" and d["goal"] == "(in_i64 (+ x 1))", d
    assert d["counterexample"] == {"x": 9223372036854775807} and d["reproduced"] is True, d
    assert d["context"][0].startswith("spec ") and d["repairs"] == [] and d["dependents"] >= 1, d
    [d] = A.diagnostics(read("reject/E-PROOF-DIV-min-rem-minus-one.b17"), 1, CACHE)
    assert d["counterexample"] == {"x": -9223372036854775808, "y": -1} and d["reproduced"], d
    assert A.diagnostics(read("accept/merge_sorted.b17"), 1, CACHE) == []

    # obligations: every goal of one item, with its verdict.
    rows = A.obligations(read("accept/abs.b17"), "abs", 1, CACHE)
    assert {r["family"] for r in rows} == {"OVERFLOW", "POST"} and all(r["verdict"] == "proved" for r in rows), rows

    # A recursive call's goal states the callee's measure at the call's arguments.
    rec = parse(f"""{HEAD} (spec down (params (n i64)) (returns (r i64)) (requires (>= n 0)) (ensures (== r 0)) (effects))
      (def down (decreases n) (body (if (== n 0) (return 0) (block (let ((m i64)) (call down (+ n 1))) (return m))))))""".encode())
    term = [d for d in A.diagnostics(rec, 1, CACHE) if d["code"] == "E-PROOF-TERM"]
    assert [d["goal"] for d in term] == ["(and (<= 0 (+ n 1)) (< (+ n 1) n))"], term

    # impact: weakening a callee's ensures breaks its caller.
    calls = parse(f"""{HEAD} (spec one (params) (returns (r i64)) (ensures (== r 1)) (effects)) (def one (body (return 1)))
      (spec two (params) (returns (r i64)) (ensures (== r 2)) (effects)) (def two (body (let ((x i64)) (call one)) (return (+ x 1)))))""".encode())
    weak = parse(f"{HEAD} (spec one (params) (returns (r i64)) (ensures (>= r 1)) (effects)))".encode())
    i = A.impact(calls, weak, 1, CACHE)
    assert i["changed"] == ["one"] and i["callers"] == ["two"] and "POST" in {b["family"] for b in i["broken"]}, i

    # search: specs found by what they guarantee, with why the others don't.
    many = parse(f"""{HEAD}
      (spec abs (params (x i64)) (returns (y i64)) (requires (> x -9223372036854775808)) (ensures (>= y 0) (or (== y x) (== y (neg x)))) (effects))
      (def abs (body (if (< x 0) (return (neg x)) (return x))))
      (spec ident (params (x i64)) (returns (y i64)) (ensures (== y x)) (effects)) (def ident (body (return x)))
      (spec flag (params (x bool)) (returns (y bool)) (ensures (== y x)) (effects)) (def flag (body (return x))))""".encode())
    q = parse(f"{HEAD} (spec q (params (v i64)) (returns (w i64)) (requires (> v -9223372036854775808)) (ensures (>= w 0)) (effects)))".encode())
    found = A.search(many, q, 1, CACHE)["candidates"]
    assert found == [{"name": "abs", "guarantees": True}, {"name": "ident", "guarantees": False, "why": ["POST"]}], found

    # Review regressions. A ghost-fn's PRE is its requires at the call's arguments; DIV's bound
    # is a B17-0 literal.
    pre = parse(f"""{HEAD} (ghost-fn positive ((n int)) int (requires (> n 0)) (body n))
      (spec f (params (x i64)) (returns (r i64)) (ensures (>= (positive x) 0)) (effects)) (def f (body (return 1))))""".encode())
    assert [d["goal"] for d in A.diagnostics(pre, 1, CACHE) if d["code"] == "E-PROOF-PRE"] == ["(> x 0)"]
    [d] = A.diagnostics(read("reject/E-PROOF-DIV-min-rem-minus-one.b17"), 1, CACHE)
    assert "-9223372036854775808" in d["goal"] and "(- " not in d["goal"], d
    # Every parameter is in a counterexample, an unmentioned one at a default, so it replays.
    unused = parse(f"{HEAD} (spec f (params (x i64) (y bool)) (returns (r i64)) (ensures (== r (+ x 1))) (effects)) (def f (body (return (+ x 1)))))".encode())
    [d] = A.diagnostics(unused, 1, CACHE)
    assert d["counterexample"] == {"x": 9223372036854775807, "y": False} and d["reproduced"], d
    none = parse(f"{HEAD} (spec a (params) (returns) (effects)) (def a (body (assert false) (return))))".encode())
    [d] = A.diagnostics(none, 1, CACHE)
    assert d["counterexample"] == {} and d["reproduced"], d
    # Dependents are goals of the same item that assume this one, not equal text elsewhere.
    two = parse(f"""{HEAD} (spec a (params) (returns) (effects)) (def a (body (assert false) (return)))
      (spec b (params) (returns (r i64)) (requires false) (ensures (== r 0)) (effects)) (def b (body (return 1))))""".encode())
    assert [d["dependents"] for d in A.diagnostics(two, 1, CACHE)] == [0], A.diagnostics(two, 1, CACHE)
    # Search counts the probe spec's own goals, and names the probe apart from FILE's items.
    slices = parse(f"""{HEAD} (spec q (params (s (ref (slice i64)))) (returns) (effects)) (def q (body (return)))
      (spec found_0 (params) (returns) (effects)) (def found_0 (body (return))))""".encode())
    bad = parse(f"{HEAD} (spec q (params (s (ref (slice i64)))) (returns) (requires (> (idx s 0) 0)) (effects)))".encode())
    assert A.search(slices, bad, 1, CACHE)["candidates"] == [{"name": "q", "guarantees": False, "why": ["BOUNDS"]}]
    same = parse(f"{HEAD} (spec q (params (s (ref (slice i64)))) (returns) (effects)))".encode())
    assert A.search(slices, same, 1, CACHE)["candidates"] == [{"name": "q", "guarantees": True, "why": "identical spec"}]
    # Impact matches goals by path, so moving an already-failing spec breaks nothing.
    moved = parse(f"{HEAD}\n\n  (spec f\n    (params (s (ref (slice i64))))\n    (returns)\n    (requires (> (idx s 0) 0))\n    (effects)))".encode())
    orig = parse(f"{HEAD} (spec f (params (s (ref (slice i64)))) (returns) (requires (> (idx s 0) 0)) (effects)))".encode())
    assert A.impact(orig, moved, 1, CACHE)["broken"] == []

# A query on a module that doesn't parse is refused, with exit 2 (D94).
bad_file = SUITE / "reject" / "E-PARSE-001-while-without-decreases.b17"
with contextlib.redirect_stdout(io.StringIO()) as printed:
    assert A.main(["obligations", str(bad_file), "f"]) == 2
assert '"error": "E-PARSE-001' in printed.getvalue()

print("agent protocol self-check passed" + ("" if shutil.which("z3") else " (without z3: explain, tier 0 and simulate only)"))
