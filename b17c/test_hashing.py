"""Self-check for B17-0 hashes (D45, D46): uv run --no-project b17c/test_hashing.py"""
import hashlib
import re
from pathlib import Path

import hashing as h
from syntax import parse

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent / "suite"


def of(text):
    return h.hashes(parse(text))


def src(name):
    return (SUITE / "accept" / f"{name}.b17").read_text()


def rename(text, pairs):
    for old, new in pairs:
        text = re.sub(rf"\b{old}\b", new, text)
    return text


def error(text, code):
    try:
        of(text)
    except h.HashError as e:
        assert e.code == code, e
        return
    raise AssertionError(f"hashed but should not have: {text!r}")


# The golden file: any machine must reproduce every accept program's hashes (D46).
golden = [line for f in sorted((SUITE / "accept").glob("*.b17")) for line in h.report(parse(f.read_bytes()))]
assert golden == (HERE / "hashes.txt").read_text().splitlines()

# D45's worked examples, through D46's preimages.
spec = ("(spec _ (params ($0 i64)) (returns ($1 i64)) (requires (> $0 -9223372036854775808)) "
        "(ensures (>= $1 0) (or (== $1 $0) (== $1 (neg $0)))) (effects))")
s = "spec0:" + hashlib.sha256(("spec0:" + spec).encode()).hexdigest()
i = "impl0:" + hashlib.sha256(f"impl0:{s} (def _ (body (if (< $0 0) (return (neg $0)) (return $0))))".encode()).hexdigest()
assert of(src("abs"))["abs"] == ("spec", s, i)
fib = "(ghost-fn _ (($0 int)) int (requires (>= $0 0)) (decreases $0) (body (if (< $0 2) $0 (+ (_ (- $0 1)) (_ (- $0 2))))))"
assert of(src("fib"))["fib"] == ("ghost-fn", "spec0:" + hashlib.sha256(("spec0:" + fib).encode()).hexdigest(), None)

# Renaming locals, results, quantifier binders and items changes no hash.
for name, pairs in [("merge_sorted", [("out", "res"), ("merge_sorted", "merge"), ("i", "k")]),
                    ("fib", [("fib", "fibonacci"), ("n", "m"), ("prev", "p"), ("i", "j")]),
                    ("isqrt", [("square_bound", "sq"), ("x", "y"), ("r", "root")])]:
    assert list(of(rename(src(name), pairs)).values()) == list(of(src(name)).values()), name

# A body edit changes only that definition's implementation hash; callers refer to its spec.
CALLS = """(module calls (header (purpose "p") (invariants "i") (failures "f"))
  (spec one (params) (returns (r i64)) (ensures (== r 1)) (effects))
  (def one (body (return 1)))
  (spec two (params) (returns (r i64)) (ensures (== r 2)) (effects))
  (def two (body (let ((x i64)) (call one)) (return (+ x 1)))))"""
a, b = of(CALLS), of(CALLS.replace("(return 1)", "(let y i64 1) (return y)"))
assert a["one"][:2] == b["one"][:2] and a["one"][2] != b["one"][2] and a["two"] == b["two"]
# So does a lemma's proof.
a, b = of(src("isqrt")), of(src("isqrt").replace("(body))", "(body (assert (<= 0 x))))"))
assert a["square_bound"][:2] == b["square_bound"][:2] and a["square_bound"][2] != b["square_bound"][2]
assert a["isqrt"] == b["isqrt"]
# Editing a ghost-fn changes the spec hash of every spec that mentions it.
a, b = of(src("fib")), of(src("fib").replace("(+ (fib (- n 1)) (fib (- n 2)))", "(+ (fib (- n 2)) (fib (- n 1)))"))
assert a["fib"] != b["fib"] and a["fib_iter"][1] != b["fib_iter"][1] and a["fib_iter"][2] != b["fib_iter"][2]

# Identical ghost-fns hash alike across modules.
assert of(src("sum"))["sum_of"] == of(src("prefix_sums"))["sum_of"]

# The tier 0 failures hashing meets.
error((SUITE / "reject/E-TYPE-002-duplicate-spec.b17").read_text(), "E-TYPE-002")
HEAD = '(module m (header (purpose "p") (invariants "i") (failures "f"))'
error(HEAD + " (ghost-fn f ((x int)) int (body (g x))))", "E-TYPE-002")
error(HEAD + " (ghost-fn f ((x int)) int (body (g x))) (ghost-fn g ((x int)) int (body (f x))))", "E-TERM-002")
# A duplicate names the later spec first, for the checker to report there.
try:
    of((SUITE / "reject/E-TYPE-002-duplicate-spec.b17").read_text())
except h.HashError as e:
    assert len(e.names) == 2 and all(f"'{n}'" in e.reason for n in e.names), e

# A long chain of references, each item before the one it calls, hashes without
# overflowing Python's stack, and gives the hashes it gives in calling order.
CHAIN = ["(ghost-fn g0 ((x int)) int (body x))"] + [
    f"(ghost-fn g{k} ((x int)) int (body (g{k - 1} x)))" for k in range(1, 3000)]
assert of(HEAD + " " + " ".join(CHAIN[::-1]) + ")") == dict(reversed(of(HEAD + " " + " ".join(CHAIN) + ")").items()))

print("hashing self-check passed")
