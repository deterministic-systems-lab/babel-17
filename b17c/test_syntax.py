"""Self-check for the parser and canonical printer: uv run --no-project b17c/test_syntax.py"""
import re
from pathlib import Path

import syntax as s

SUITE = Path(__file__).resolve().parent.parent / "suite"
PARSE_REJECT = SUITE / "reject/E-PARSE-001-while-without-decreases.b17"


def error(text):
    try:
        s.parse(text)
    except s.ParseError as e:
        assert e.code == "E-PARSE-001", e
        return e
    raise AssertionError(f"parsed but should not have: {text!r}")


def at(text, snippet):
    """The (line, column) where snippet first occurs in text."""
    i = text.index(snippet)
    return text.count("\n", 0, i) + 1, i - (text.rfind("\n", 0, i) + 1) + 1


# Every suite file parses and round-trips, except the one parse reject.
files = sorted(SUITE.glob("*/*.b17"))  # B17-0's accept/ and reject/; suite/b17-1/ waits for B17-1's parser
assert len([f for f in files if f.parent.name == "accept"]) == 20, files
assert PARSE_REJECT in files
for f in files:
    text = f.read_text()
    if f == PARSE_REJECT:
        e = error(text)
        assert (e.line, e.col) == at(text, "(set i (+ i 1))") and "decreases" in e.reason, e
        continue
    tree = s.parse(text)
    c = s.canonical(tree)
    assert s.parse(c) == tree, f
    assert s.canonical(s.parse(c)) == c, f
    lines = c.decode().split("\n")
    assert len(lines) == len(tree.items) - 2, f      # module line, then one line per item
    assert not c.endswith(b"\n") and b"  " not in c and b" \n" not in c and b" )" not in c, f
    assert lines[0].startswith("(module ") and " (header (purpose " in lines[0], f

# Canonical bytes of a small module, exactly.
OK = ('(module m (header (purpose "p") (invariants "i") (failures "f"))\n'
      '(spec f (params (x i64)) (returns (r i64)) (requires (> x -9223372036854775808)) (ensures (== r x)) (effects))\n'
      '(def f (body (return x))))')
assert s.canonical(s.parse(OK)) == OK.encode()
# Any whitespace layout parses to the same tree.
loose = OK.replace(" ", " \t\r\n  ").replace("(module", "\n\n(module") + "\n \n"
assert s.parse(loose) == s.parse(OK) and s.canonical(s.parse(loose)) == OK.encode()
# Strings keep UTF-8 and the two escapes; a lone module has a one-line canonical form.
esc = '(module m (header (purpose "a \\"q\\" \\\\ é") (invariants "") (failures "→")))'
assert s.parse(esc).items[2].items[1].items[1].value == 'a "q" \\ é'
assert s.canonical(s.parse(esc)) == esc.encode()
assert s.parse(esc.encode()) == s.parse(esc)


def bad(old, new, snippet, phrase, base=OK):
    """Replace old with new in base; parsing must fail where snippet starts, citing phrase."""
    assert old in base, old
    text = base.replace(old, new, 1)
    e = error(text)
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
assert s.canonical(s.parse(prelude)) == prelude.encode()
assert s.parse(prelude).items[4].items[4].items[1].items[2].items[2] == s.Int(2**63)
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
e = error(OK[:-1])
assert (e.line, e.col) == (1, 1) and e.reason == "unclosed '('", e
bad("(module", "(x) (module", "(module", "text after the module")
assert error("").reason.startswith("empty input")
assert error(b"(module m \xff)").reason == "input is not valid UTF-8"

# D55: lists nest at most 128 deep, counting the module, and the deepest legal term still prints.
HEAD = '(module m (header (purpose "p") (invariants "i") (failures "f")) (ghost-fn f () bool (body '
deep = lambda n: HEAD + "(not " * n + "true" + ")" * n + ")))"
assert s.parse(s.canonical(s.parse(deep(125)))) == s.parse(deep(125))
assert error(deep(126)).reason == "lists nest more than 128 deep"
# D53: integer literals of any size.
big = int("1" * 5000)
assert s.canonical(s.parse(HEAD.replace("bool", "int") + f"{big})))")).endswith(f"{big})))".encode())

# parse_expr reads exactly one expression, an atom included, under the same rules.
assert s.parse_expr(" -5\n") == s.Int(-5) and s.parse_expr(b"true") == s.Sym("true")
assert s.parse_expr("(seq-lit 1 (neg x))") == s.Form((s.Sym("seq-lit"), s.Int(1), s.Form((s.Sym("neg"), s.Sym("x")))))
for text, reason in [("", "empty input: expected an expression"), ("1 2", "text after the expression"),
                     ("(neg 5)", "not canonical"), ('"s"', "a string is not an expression"),
                     ("(seq-lit 1", "unclosed '('"), ("len", "'len' is reserved"), ("007", "leading zero")]:
    try:
        s.parse_expr(text)
    except s.ParseError as e:
        assert reason in e.reason, (text, e)
    else:
        raise AssertionError(f"parsed but should not have: {text!r}")

print("syntax self-check passed")
