"""Self-check for WP4b's spec workbench (D121): uv run --no-project b17c/test_spec.py

Needs z3 on PATH, so it runs locally rather than in CI. Back-translation runs against a fake
CLI, so no subscription is spent.
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

import spec as S
import syntax
import verify as V

SUITE = Path(__file__).resolve().parent.parent / "suite"
TMP = Path(tempfile.mkdtemp())
H = '(module t (header (purpose "p") (invariants "i") (failures "f"))\n'
MERGE = syntax.parse((SUITE / "accept/merge_sorted.b17").read_bytes(), 0)


def module(body):
    return syntax.parse(H + "  " + body + ")", 0)


# Vacuity: the worked example's requires can hold, and neither ensures clause follows from them alone.
(m,) = S.vacuity(MERGE, 0)
assert m["item"] == "spec merge_sorted" and m["requires"]["verdict"] == "satisfiable", m
assert [c["trivial"] for c in m["ensures"]] == [False, False], m
# A requires no input meets is vacuous, with a spec challenge; a clause the types alone prove is trivial.
(m,) = S.vacuity(module("""(spec f (params (x i64)) (returns (r i64)) (requires (> x 5) (< x 3)) (ensures (== r x)) (effects))"""), 0)
c = m["requires"]["challenge"]
assert m["requires"]["verdict"] == "vacuous" and c["kind"] == "requires-unsatisfiable" and c["verdict"] == "proved", m
assert c["spec_hash"].startswith("spec0:") and len(c["query_sha256"]) == 64 and m["ensures"][0]["trivial"] is None, m
(m,) = S.vacuity(module("""(spec f (params (a (ref (slice i64)))) (returns (r (vec i64))) (requires (> (len a) 0))
    (ensures (>= (len r) 0) (== (len r) (len a))) (effects))"""), 0)
assert m["requires"]["verdict"] == "satisfiable" and [c["trivial"] for c in m["ensures"]] == [True, False], m

# A lemma's claim always follows from its requires, so only its requires are judged.
lemma = next(e for e in S.vacuity(syntax.parse((SUITE / "accept/isqrt.b17").read_bytes(), 0), 0) if e["item"] == "lemma square_bound")
assert lemma["requires"]["verdict"] != "vacuous" and lemma["ensures"] == [], lemma

# Witnesses: readable inputs from the tests' own, the def's output, and nearby outputs the spec
# forbids, each with the clause it breaks: here an element lost or gained, and an order broken.
ws = S.witness(MERGE, "merge_sorted", 0)
assert len(ws) == 3 and all(max(abs(int(x)) for t in w["input"] for x in t[8:-1].split() or [0]) <= 10 for w in ws), ws
for w in ws:
    a, b = ([int(x) for x in t[8:-1].split()] for t in w["input"])
    assert w["allowed"] == [f"(seq-lit {' '.join(map(str, sorted(a + b)))})".replace("seq-lit )", "seq-lit)")], w
    assert {f["breaks"] for f in w["forbidden"]} >= {"(sorted out)", "(== (multiset out) (msum (multiset a) (multiset b)))"}, w
    assert w["also_allowed"] == [], w
# A weak spec allows nearby outputs too.
(w, *_) = S.witness(module("""(spec f (params (x i64)) (returns (r i64)) (requires (>= x 0) (< x 100)) (ensures (> r x)) (effects))
  (def f (body (return (+ x 1))))"""), "f", 0)
assert w["also_allowed"] == [[f"{int(w['input'][0]) + 2}"]], w
# With no def, the solver says whether any output meets the ensures; where none does, that's a challenge.
for w in S.witness(module("""(spec f (params (x i64)) (returns (r i64)) (requires (>= x 0) (<= x 3)) (ensures (> r x) (< r x)) (effects))"""), "f", 0):
    assert w["output"] == "none" and w["challenge"]["kind"] == "no-output" and w["challenge"]["input"] == w["input"], w
for w in S.witness(module("""(spec f (params (x i64)) (returns (r i64)) (requires (>= x 0) (<= x 3)) (ensures (> r x)) (effects))"""), "f", 0):
    assert w["output"] == "exists" and int(w["allowed"][0]) > int(w["input"][0]), w  # found by drawing outputs

# Mutants: the worked example kills every mutant but one, which computes the same results, so
# its spec isn't shown to be weak; a test can kill one through the def's own invariants.
ms = S.mutants(MERGE, "merge_sorted", 0, seeds=1, cache=TMP / "cache")
assert len(ms) > 15 and [m for m in ms if m["killed"] is None] == [
    {"change": "(<= (idx a i) (idx b j)) -> (< (idx a i) (idx b j))", "path": "2.4.9.1.2.2", "killed": None, "differs_at": None}], ms
assert {m["goal"] for m in ms if m["killed"] == "test"} >= {"POST", "INV-KEEP"}, ms
# A weak spec lets a mutant through that computes something else: x + 2 is also above x.
WEAK = module("""(spec f (params (x i64)) (returns (r i64)) (requires (>= x 0) (< x 100)) (ensures (> r x)) (effects))
  (def f (body (return (+ x 1))))""")
ms = S.mutants(WEAK, "f", 0, seeds=1, cache=TMP / "cache")
assert {m["change"]: (m["killed"], m.get("differs_at") is not None) for m in ms} == {
    "(+ x 1) -> (- x 1)": ("test", False), "1 -> 2": (None, True), "1 -> 0": ("test", False)}, ms

# Back-translation: the CLI's reply is parsed and recorded with the prompt's hash; a reply that
# isn't the JSON asked for is an error.
fake = TMP / "fake.py"
fake.write_text("""import sys
prompt, out = sys.stdin.read(), sys.argv[sys.argv.index("-o") + 1]
reply = {"specs": {"merge_sorted": "merges"}, "disagreements": []} if "merge_sorted" in prompt and "(def " not in prompt else "no"
open(out, "w").write(__import__("json").dumps(reply) if reply != "no" else "I can't.")
""")
r = S.english(MERGE, [sys.executable, str(fake), "-o", "{reply}", "-"])
assert r["specs"] == {"merge_sorted": "merges"} and r["disagreements"] == [] and r["error"] is None, r
assert len(r["prompt_sha256"]) == 64 and r["version"].startswith("Python"), r  # the def isn't shown
r = S.english(module("(spec f (params) (returns (r i64)) (effects))"), [sys.executable, str(fake), "-o", "{reply}", "-"])
assert r["specs"] is None and r["error"] == "the reply isn't the JSON asked for", r

# Signing: a signature records the spec's hash, so editing the spec makes it unsigned again, and
# the trusted base report lists the specs no one has signed.
f = TMP / "merge_sorted.b17"
shutil.copy(SUITE / "accept/merge_sorted.b17", f)
assert V.unsigned(f, MERGE, 0) == ["merge_sorted"]
entry = S.sign(f, MERGE, "merge_sorted", "a reviewer", 0)
assert entry["spec"] == V.H.hashes(MERGE, 0)["merge_sorted"][1] and V.unsigned(f, MERGE, 0) == []
edited = syntax.parse(f.read_text().replace("(ensures (sorted out)", "(ensures (sorted out) (>= (len out) 0)"), 0)
assert V.unsigned(f, edited, 0) == ["merge_sorted"]
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    assert V.main(["--subset", "0", "--seeds", "1", "--cache", str(TMP / "cache"), "--report", str(TMP / "r.json"), str(f)]) == 0
    assert S.main(["--subset", "0", "nonsense", str(f)]) == 2 and S.main(["--subset", "0", "witness", str(f), "nope"]) == 2
    assert S.main(["--subset", "0", "unsigned", str(f)]) == 0 and S.main(["--subset", "0", "--seeds", "1", "mutants", str(f), "merge_sorted"]) == 0
assert json.loads((TMP / "r.json").read_text())["unsigned_specs"] == []

print("spec workbench self-check passed")
