"""Self-check for the harness's verdict logic: uv run gym/test_harness.py"""
from pathlib import Path

import harness as h

assert h.param_names("a: array<int>, m: map<int, int>, ghost g: nat") == ["a", "m", "g"]
assert h.violations("// we never assume\nmethod M() {}") == []
assert h.violations("method M() { assume false; }") == ["assume"]
assert h.violations("lemma {:axiom} L() ensures false") == ["{:axiom}"]
assert h.violations("@Axiom\nlemma L() ensures false") == ["@Axiom"]
assert h.violations("method {:verify false} M() {}") == ["{:verify}"]
assert h.violations("method M() decreases * {}") == ["decreases *"]
assert h.violations("lemma assume'() ensures true {}\nmethod expect?() {}") == []
# A "//" inside a string must not hide the code after it; nor may a verbatim string.
assert h.violations('method M() { var s := "//"; assume false; }') == ["assume"]
assert h.violations('method M() { var s := @"\\"; assume false; var t := ""; }') == ["assume"]
# Allowed attributes, comments and old@label are fine.
assert h.violations("lemma {:induction xs} L(xs: seq<int>) {} // {:axiom} @Axiom\n"
                    "method M() { label L: assert old@L(true); }") == []
assert h.extract_code("x\n```dafny\nA\n```\ny\n```dafny\nB\n```") == "B"
assert h.extract_code("no code here") is None

# A quota that resets after the whole retry budget (65 min > 61) fails at once instead of sleeping.
h.CLIS["fake"] = ["sh", "-c", "echo 'error: Individual quota reached. Resets in 1h5m' >&2; exit 3"]
r = h.call_cli("fake", "hi")
assert len(r["errors"]) == 1 and "1h5m" in r["error"], r

# Tuple types contain parentheses and commas; the wrapper must still find the parameters.
ac = h.load_task(h.TASKS / "algoveri/ac_automata.dfy")
assert ac["id"] == "algoveri/ac_automata"
assert ac["check"].rstrip().endswith("results := ac_automata_search(haystack, patterns);\n}")

abs_task = h.load_task(h.TASKS / "abs.dfy")
assert abs_task["check"].startswith("method Abs_Check(x: int) returns (y: int)")
assert abs_task["check"].rstrip().endswith("y := Abs(x);\n}")

cases = {
    "verified": abs_task["solution"],
    "proof_failed": "method Abs(x: int) returns (y: int) ensures y >= 0 ensures y == x || y == -x { y := x; }",
    # Weakened contract: Abs itself verifies, but Abs_Check can't prove the frozen ensures.
    "proof_failed ": "method Abs(x: int) returns (y: int) ensures y == x || y == -x { y := x; }",
    "axiom": "lemma Magic(x: int) ensures x >= 0\n"
             "method Abs(x: int) returns (y: int) ensures y >= 0 ensures y == x || y == -x { Magic(x); y := x; }",
    "rejected": "method Abs(x: int) returns (y: int) { y := ; }",
}
for want, code in cases.items():
    got, out = h.verify(abs_task, code)
    assert got == want.strip(), (want, got, out)

# Preamble definitions are ghost, so calling the spec function isn't an implementation.
fib = h.load_task(h.TASKS / "fib.dfy")
got, out = h.verify(fib, "method FibIter(n: nat) returns (f: nat) ensures f == Fib(n) { return Fib(n); }")
assert got == "rejected", (got, out)

# An exhausted resource budget must not count as verified.
merge = h.load_task(h.TASKS / "merge_sorted.dfy")
h.DAFNY[h.DAFNY.index("--resource-limit") + 1] = "1000000"
got, out = h.verify(merge, merge["solution"])
assert got == "out_of_resource", (got, out)

print("harness self-check passed")
