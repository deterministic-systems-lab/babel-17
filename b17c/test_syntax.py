"""Self-check for the parser and canonical printer: uv run --no-project b17c/test_syntax.py"""
import re
from pathlib import Path

import syntax as s


def parse(text, subset=0):  # B17-0's tests name their subset (D101)
    return s.parse(text, subset)


def parse_expr(text, subset=0):  # B17-0's tests name their subset (D101)
    return s.parse_expr(text, subset)


SUITE = Path(__file__).resolve().parent.parent / "suite"
PARSE_REJECT = SUITE / "reject/E-PARSE-001-while-without-decreases.b17"


def error(text, subset=0):
    try:
        parse(text, subset)
    except s.ParseError as e:
        assert e.code == "E-PARSE-001", e
        return e
    raise AssertionError(f"parsed but should not have: {text!r}")


def at(text, snippet):
    """The (line, column) where snippet first occurs in text."""
    i = text.index(snippet)
    return text.count("\n", 0, i) + 1, i - (text.rfind("\n", 0, i) + 1) + 1


# Every suite file parses and round-trips, except the one parse reject.
files = sorted(SUITE.glob("*/*.b17"))  # B17-0's accept/ and reject/; suite/b17-1/ is read below, with subset 1
assert len([f for f in files if f.parent.name == "accept"]) == 20, files
assert PARSE_REJECT in files
for f in files:
    text = f.read_text()
    if f == PARSE_REJECT:
        e = error(text)
        assert (e.line, e.col) == at(text, "(set i (+ i 1))") and "decreases" in e.reason, e
        continue
    tree = parse(text)
    c = s.canonical(tree)
    assert parse(c) == tree, f
    assert s.canonical(parse(c)) == c, f
    lines = c.decode().split("\n")
    assert len(lines) == len(tree.items) - 2, f      # module line, then one line per item
    assert not c.endswith(b"\n") and b"  " not in c and b" \n" not in c and b" )" not in c, f
    assert lines[0].startswith("(module ") and " (header (purpose " in lines[0], f

# Canonical bytes of a small module, exactly.
OK = ('(module m (header (purpose "p") (invariants "i") (failures "f"))\n'
      '(spec f (params (x i64)) (returns (r i64)) (requires (> x -9223372036854775808)) (ensures (== r x)) (effects))\n'
      '(def f (body (return x))))')
assert s.canonical(parse(OK)) == OK.encode()
# Any whitespace layout parses to the same tree.
loose = OK.replace(" ", " \t\r\n  ").replace("(module", "\n\n(module") + "\n \n"
assert parse(loose) == parse(OK) and s.canonical(parse(loose)) == OK.encode()
# Strings keep UTF-8 and the two escapes; a lone module has a one-line canonical form.
esc = '(module m (header (purpose "a \\"q\\" \\\\ é") (invariants "") (failures "→")))'
assert parse(esc).items[2].items[1].items[1].value == 'a "q" \\ é'
assert s.canonical(parse(esc)) == esc.encode()
assert parse(esc.encode()) == parse(esc)


def bad(old, new, snippet, phrase, base=OK, subset=0):
    """Replace old with new in base; parsing must fail where snippet starts, citing phrase."""
    assert old in base, old
    text = base.replace(old, new, 1)
    e = error(text, subset)
    assert (e.line, e.col) == at(text, snippet), (text, e)
    assert phrase in e.reason, (phrase, e)


# Integers.
bad("(return x)", "(return 007)", "007", "leading zero")
bad("(return x)", "(return +1)", "+1", "'+' sign")
bad("(return x)", "(return -0)", "-0", "-0")
bad("(return x)", "(return (neg 5))", "(neg 5)", "(neg INT) is not canonical")
bad("(return x)", "(return (neg -5))", "(neg -5)", "write 5")
# Names.
bad("(spec f", "(spec F", "F (params", "not a valid name")
bad("(x i64)", "(x-y i64)", "x-y", "not a valid name")
bad("(x i64)", "(len i64)", "len i64", "'len' is reserved")
bad("(x i64)", "(let-mut i64)", "let-mut i64", "'let-mut' is reserved")
bad("(module m", "(module seq", "seq (header", "reserved")
# The reserved words are exactly the grammar's words in docs/b17-0.md §2, and none is a name.
doc = (SUITE.parent / "docs/b17-0.md").read_text()
grammar = doc[doc.index("module    = "):doc.index("```", doc.index("module    = "))]
heads = set(re.findall(r"\(([a-z][a-z0-9-]*)", grammar)) - {"param"}  # (param*) is a nonterminal
atoms = {"bool", "i64", "int", "alloc", "panic", "io", "true", "false", "and", "or"}
assert heads | atoms == s.KEYWORDS, (heads | atoms) ^ s.KEYWORDS
for word in s.KEYWORDS:
    bad("(x i64)", f"({word} i64)", f"{word} i64", f"'{word}' is reserved")
bad("(return x)", "(return (foo-bar x))", "foo-bar", "not a valid name")
# The core library's ghost-fns, as §9 and D45 write them, parse; in_i64 needs a literal past i64 (D53).


def quoted(text, start):
    i = text.index("`" + start) + 1
    return text[i:text.index("`", i)]


prelude = "\n".join([OK.split("\n")[0], quoted(doc, "(ghost-fn sorted"),
                     quoted((SUITE.parent / "DECISIONS.md").read_text(), "(ghost-fn in_i64")]) + ")"
assert s.canonical(parse(prelude)) == prelude.encode()
assert parse(prelude).items[4].items[4].items[1].items[2].items[2] == s.Int(2**63)
# Strings.
bad('(purpose "p")', '(purpose "a\\nb")', "\\n", "unknown string escape")
bad('(purpose "p")', '(purpose "a\nb")', "\nb", "control character U+000A")
assert error('(module m (header (purpose "p').reason == "unterminated string"
# Clauses: required, in grammar order, and non-empty when optional.
bad(" (effects)", "", ")\n(def", "missing (effects EFF*)")
bad("(params (x i64)) (returns (r i64))", "(params (x i64))", "(requires", "expected (returns param*)")
bad("(requires (> x -9223372036854775808)) (ensures (== r x))",
    "(ensures (== r x)) (requires (> x -9223372036854775808))", "(requires (>", "expected (effects EFF*), found (requires")
bad("(requires (> x -9223372036854775808))", "(requires)", "(requires)", "empty (requires)")
bad("(effects)", "(effects io alloc)", "alloc)", "order alloc, panic, io")
bad("(effects)", "(effects alloc alloc)", "alloc))", "once each")
bad(' (failures "f")', "", "(header", "(header ...) takes exactly")
bad("(return x))", "(return x)) (decreases 0)", "(decreases 0)", "unexpected (decreases ...) in (def ...)")
bad("(return x)", "(while true (invariant true) (return x))", "(return x)", "expected (decreases e)")
bad("(return x)", "(if true (return x))", "(if true", "(if e stmt stmt) takes 3 arguments, got 2")
# Arity and form errors.
bad("(== r x)", "(- r)", "(- r)", "(- e e) takes 2 arguments")
bad("(return x)", "(sorted x)", "(sorted x)", "expected a statement")
bad("(return x)", "(return (block))", "(block)", "not an expression")
bad("(x i64)", "(x (slice i64))", "(slice", "expected a type")
# Layout: whitespace between siblings, nothing outside the module, no comments.
bad("(return x)", "(return(+ x 1))", "(+ x", "missing whitespace")
bad('(purpose "p")', '(purpose"p")', '"p"', "missing whitespace")
bad("(def f", "; c\n(def f", "; c", "not a name")
e = error(OK + ")")
assert (e.line, e.col) == (3, len(OK.split("\n")[2]) + 1) and e.reason == "unmatched ')'", e
# An unclosed '(' names the item that probably lacks the ')': the first one still open when a later
# line starts at or left of its column, or else the last one.
e = error(OK[:-1])
assert (e.line, e.col) == (3, 1) and e.reason.endswith("at its end, or in its last item, at lines 3-3"), e
e = error(OK.replace("(effects))\n", "(effects)\n"))
assert (e.line, e.col) == (2, 1) and "still open at line 3" in e.reason and e.reason.endswith("lines 2-2"), e
e = error("(module m\n  (x")
assert (e.line, e.col) == (2, 3) and e.reason == "unclosed '('", e
assert error("(module m").reason == "unclosed '('"
bad("(module", "(x) (module", "(module", "text after the module")
assert error("").reason.startswith("empty input")
assert error(b"(module m \xff)").reason == "input is not valid UTF-8"

# D55: lists nest at most 128 deep, counting the module, and the deepest legal term still prints.
HEAD = '(module m (header (purpose "p") (invariants "i") (failures "f")) (ghost-fn f () bool (body '
deep = lambda n: HEAD + "(not " * n + "true" + ")" * n + ")))"
assert parse(s.canonical(parse(deep(125)))) == parse(deep(125))
assert error(deep(126)).reason == "lists nest more than 128 deep"
# D53: integer literals of any size.
big = int("1" * 5000)
assert s.canonical(parse(HEAD.replace("bool", "int") + f"{big})))")).endswith(f"{big})))".encode())

# parse_expr reads exactly one expression, an atom included, under the same rules.
assert parse_expr(" -5\n") == s.Int(-5) and parse_expr(b"true") == s.Sym("true")
assert parse_expr("(seq-lit 1 (neg x))") == s.Form((s.Sym("seq-lit"), s.Int(1), s.Form((s.Sym("neg"), s.Sym("x")))))
for text, reason in [("", "empty input: expected an expression"), ("1 2", "text after the expression"),
                     ("(neg 5)", "not canonical"), ('"s"', "a string is not an expression"),
                     ("(seq-lit 1", "unclosed '('"), ("len", "'len' is reserved"), ("007", "leading zero")]:
    try:
        parse_expr(text)
    except s.ParseError as e:
        assert reason in e.reason, (text, e)
    else:
        raise AssertionError(f"parsed but should not have: {text!r}")

# B17-1, read with subset 1 (D101). Every suite/b17-1 file parses and round-trips but its two parse rejects.
for f in sorted((SUITE / "b17-1").rglob("*.b17")):
    text = f.read_text()
    if f.name.startswith("E-PARSE-001"):
        e = error(text, 1)
        assert e.reason in ("expected an integer literal, found 'k'", "(replace ...) is not an expression"), (f, e)
        continue
    tree = parse(text, 1)
    assert parse(s.canonical(tree), 1) == tree and s.canonical(parse(s.canonical(tree), 1)) == s.canonical(tree), f
assert len(list((SUITE / "b17-1").rglob("*.b17"))) == 66
# Every B17-0 suite program is a B17-1 program with the same tree (docs/b17-1.md, opening).
assert all(parse(f.read_text(), 1) == parse(f.read_text()) for f in files if f != PARSE_REJECT)
# B17-1's reserved words are exactly those docs/b17-1.md §2 adds; B17-0 still reads them as names.
doc1 = (SUITE.parent / "docs/b17-1.md").read_text()
added = doc1[doc1.index("**Reserved words:**"):doc1.index("(D51)", doc1.index("**Reserved words:**"))]
assert set(re.findall(r"`([a-z-]+)`", added)) == s.KEYWORDS_1 - s.KEYWORDS, set(re.findall(r"`([a-z-]+)`", added)) ^ (s.KEYWORDS_1 - s.KEYWORDS)
assert parse(OK.replace("(x i64)", "(map i64)")) and parse(OK.replace("(return x)", "(return (field x))"))
bad("(x i64)", "(map i64)", "map i64", "'map' is reserved", subset=1)
bad("(x i64)", "(obtain i64)", "obtain i64", "'obtain' is reserved", subset=1)
# B17-1's forms, each misused once.
B1 = OK.split("\n")[0] + """
(data t () (leaf) (node (v i64) (l t)))
(data box (a b) (box (first a) (second (option b))))
(ghost-fn g ((x t)) int (body (match x (case (leaf) 0) (case (node v l) (get (tuple v 1) 0)))))
(ghost-fn k ((p (tuple int int)) (s (iset int)) (m (map int int))) bool (body (match p (case (tuple a b) (== (diff s (iset-lit a)) (iset-of ((c int)) (contains (update m b a) c)))))))
(spec h (params (x t) (a (vec (vec i64)))) (returns (r i64)) (effects))
(def h (body (let-mut b (vec (vec i64)) a) (set-idx (idx b 0) 0 1) (set-idx (get b 0) 1 2) (let-mut c (vec i64) (replace (field b f) (vec-new))) (obtain ((k int)) (> k 0)) (return 0))))"""
assert s.canonical(parse(B1, 1)) == B1.encode()
error(B1)  # B17-0 has none of these forms
bad1 = lambda old, new, snippet, phrase: bad(old, new, snippet, phrase, B1, 1)
bad1("(data t () (leaf)", "(data t leaf (leaf)", "leaf (leaf)", "written () when there are none")
bad1("(data box (a b)", "(data box (a (b))", "(b)", "expected a type parameter")
bad1("(a (vec (vec i64)))", "(a (+ i64))", "(+ i64)", "expected a type")
bad1("(data t () (leaf) (node (v i64) (l t)))", "(data t ())", ")\n(data box", "needs type parameters and a constructor")
bad1("(data t () (leaf)", "(data t () leaf", "leaf (node", "expected a constructor")
bad1("(case (leaf) 0)", "(leaf 0)", "(leaf 0)", "expected (case pat e)")
bad1("(match x (case (leaf) 0) (case (node v l) (get (tuple v 1) 0)))", "(match x)", ")))\n(ghost-fn k", "at least one case")
bad1("(tuple v 1)", "(tuple v)", "(tuple v)", "at least two expressions")
bad1("(case (node v l)", "(case (tuple v)", "(tuple v)", "binds at least two names")
bad1("(get (tuple v 1) 0)", "(iset-of ((a int) (b int)) true)", "(iset-of", "expected (iset-of ((NAME type)) ...)")
bad1("(get (tuple v 1) 0)", "(map-lit (1))", "(1)", "expected a map entry")
bad1("(get (tuple v 1) 0)", "(replace v 1)", "(replace", "not an expression")
bad1("(obtain ((k int)) (> k 0))", "(obtain ((k int)))", "(obtain", "expected (obtain ((NAME type)+) e)")
bad1("(obtain ((k int)) (> k 0))", "(forall ((k int)) (assert true))", "(assert", "expected (call NAME e*)")
bad1("(set-idx (idx b 0) 0 1)", "(set-idx (len b) 0 1)", "(len b)", "expected a place")
bad1("(a (vec (vec i64)))", "(a (tuple i64))", "(tuple i64)", "expected a type")
bad("(def f (body (return x)))", "(def f (body (set-idx (idx x 0) 0 1) (return x)))", "(idx x 0)", "expected a name")  # B17-0: no places

print("syntax self-check passed")
