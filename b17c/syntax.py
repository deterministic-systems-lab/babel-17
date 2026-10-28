"""The parser and canonical printer: B17-0's (docs/b17-0.md §2, D47-D54) and B17-1's (docs/b17-1.md §2).

    uv run --no-project b17c/syntax.py [--subset 1] FILE

prints FILE's canonical bytes, or `FILE:LINE:COL: E-PARSE-001: reason` on stderr
and exits 1.

parse() checks only §2's grammar and its lexical rules: names, integers, strings.
Name resolution, uniqueness, types and the rest of §3-§9 belong to WP3. parse_expr()
reads a single expression, such as the interpreter's command-line arguments. Both take
the subset (D101): 0 by default, for B17-0 exactly as frozen, or 1 for B17-1's grammar.
"""
import bisect
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CODE = "E-PARSE-001"
WHITESPACE = " \t\n\r"  # D48: nothing else separates tokens; there are no comments
NAME = re.compile(r"[a-z][a-z0-9_]*\Z")
DIGITS = re.compile(r"[+-]?[0-9]+\Z")
OPS = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "and", "or", "=>"}
# §2: every word of the grammar is reserved. The core library's names (sorted,
# in_i64) are reserved too, but they're called like ghost-fns, so they lex as
# names and redefining one is WP3's E-TYPE-002 (D51).
KEYWORDS = {
    "module", "header", "purpose", "invariants", "failures",
    "ghost-fn", "lemma", "spec", "def", "params", "returns", "requires", "ensures",
    "effects", "decreases", "body",
    "bool", "i64", "int", "seq", "multiset", "vec", "ref", "slice", "alloc", "panic", "io",
    "let", "let-mut", "set", "set-idx", "push", "if", "block", "while", "call", "assert",
    "ghost-let", "ghost-let-mut", "ghost-set", "return", "print", "invariant",
    "true", "false", "not", "neg", "len", "idx", "borrow", "vec-new", "seq-build", "fn",
    "forall", "exists", "seq-lit", "take", "drop", "concat", "last", "contains", "msum",
    "occurrences", "and", "or",
}
# docs/b17-1.md §2: B17-1's reserved words, which B17-0 programs may still use as names.
KEYWORDS_1 = KEYWORDS | {
    "data", "case", "match", "is", "field", "tuple", "get", "replace", "rank", "iset", "iset-lit",
    "iset-of", "map", "map-lit", "union", "diff", "inter", "update", "lookup", "obtain",
}
EFFECTS = ["alloc", "panic", "io"]  # D52: listed in this order, each at most once
MAX_DEPTH = 128  # D55: the same on every machine, and well inside Python's recursion limit
sys.set_int_max_str_digits(0)  # D53: integer literals have no size limit
_sub, _kw = 0, KEYWORDS  # the subset being read, set by parse() and parse_expr() (D101)


@dataclass(frozen=True)
class Sym:
    text: str
    pos: tuple = field(default=(0, 0), compare=False, repr=False)


@dataclass(frozen=True)
class Int:
    value: int
    pos: tuple = field(default=(0, 0), compare=False, repr=False)


@dataclass(frozen=True)
class Str:
    value: str
    pos: tuple = field(default=(0, 0), compare=False, repr=False)


@dataclass(frozen=True)
class Form:
    """A parenthesized list. `end` is the position of its closing paren."""
    items: tuple
    pos: tuple = field(default=(0, 0), compare=False, repr=False)
    end: tuple = field(default=(0, 0), compare=False, repr=False)


class ParseError(Exception):
    def __init__(self, pos, reason):
        self.code = CODE
        self.line, self.col = pos
        self.reason = reason
        super().__init__(f"{self.line}:{self.col}: {CODE}: {reason}")


def parse(text, subset=0):
    """Parse a module of the subset from str or UTF-8 bytes into a tree of Form, Sym, Int and Str."""
    _use(subset)
    tree = _read(_decode(text))
    _module(tree)
    return tree


def parse_expr(text, subset=0):
    """Parse one expression, such as `5` or `(seq-lit 1 2 3)`, from str or UTF-8 bytes."""
    _use(subset)
    tree = _read(_decode(text), expr=True)
    _expr(tree)
    return tree


def _use(subset):
    global _sub, _kw
    if subset not in (0, 1):
        raise ValueError(f"no subset B17-{subset}: 0 or 1 (D101)")
    _sub, _kw = subset, KEYWORDS_1 if subset else KEYWORDS


def _decode(text):
    if isinstance(text, bytes):
        try:
            return text.decode("utf-8")
        except UnicodeDecodeError as e:
            good = text[:e.start].decode("utf-8")
            raise ParseError(_Lines(good).at(len(good)), "input is not valid UTF-8") from None
    return text


def canonical(tree):
    """Canonical bytes (D47): the module, its name and header on line 1, then one item per line.

    Separators are single spaces, the module's closing paren ends the last line, and
    no newline follows it.
    """
    _, name, header, *items = tree.items
    lines = [f"(module {name.text} {_print(header)}"] + [_print(i) for i in items]
    return ("\n".join(lines) + ")").encode("utf-8")


def _print(x):
    if isinstance(x, Form):
        return "(" + " ".join(_print(i) for i in x.items) + ")"
    if isinstance(x, Sym):
        return x.text
    if isinstance(x, Int):
        return str(x.value)
    return '"' + x.value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# Reading: text to S-expression.

class _Lines:
    def __init__(self, text):
        self.starts = [0] + [i + 1 for i, c in enumerate(text) if c == "\n"]

    def at(self, i):
        line = bisect.bisect_right(self.starts, i)
        return line, i - self.starts[line - 1] + 1


def _read(text, expr=False):
    """The one term in text: a module, or with expr=True, any expression, including an atom."""
    what = "expression" if expr else "module"
    lines = _Lines(text)
    at = lines.at
    stack = []        # (position, items) of each open paren
    result = None
    i, n = 0, len(text)
    separated = True  # D49: adjacent elements of a list need whitespace between them
    while i < n:
        c = text[i]
        if c in WHITESPACE:
            i += 1
            separated = True
            continue
        if c == ")":
            if not stack:
                raise ParseError(at(i), "unmatched ')'")
            start, items = stack.pop()
            node = Form(tuple(items), start, at(i))
            i += 1
        elif result is not None:
            raise ParseError(at(i), f"text after the {what}")
        elif not separated:
            raise ParseError(at(i), "missing whitespace between list elements")
        elif c == "(":
            if len(stack) == MAX_DEPTH:
                raise ParseError(at(i), f"lists nest more than {MAX_DEPTH} deep")
            stack.append((at(i), []))
            i += 1
            separated = True
            continue
        elif not stack and not expr:
            raise ParseError(at(i), "expected '(' to open the module")
        elif c == '"':
            node, i = _string(text, i, at)
        else:
            j = i
            while j < n and text[j] not in WHITESPACE and text[j] not in '()"':
                j += 1
            node = _atom(text[i:j], at(i))
            i = j
        separated = False
        if stack:
            stack[-1][1].append(node)
        else:
            result = node
    if stack:
        raise ParseError(stack[-1][0], "unclosed '('")
    if result is None:
        raise ParseError(at(n), f"empty input: expected {'an' if expr else 'a'} {what}")
    return result


def _string(text, i, at):
    start = i
    out = []
    i += 1
    while True:
        if i >= len(text):
            raise ParseError(at(start), "unterminated string")
        c = text[i]
        if c == '"':
            return Str("".join(out), at(start)), i + 1
        if c == "\\":
            e = text[i + 1:i + 2]
            if e not in ('"', "\\"):
                shown = repr(e)[1:-1] if e else "end of input"
                raise ParseError(at(i), f"unknown string escape '\\{shown}': only \\\" and \\\\ are allowed")
            out.append(e)
            i += 2
            continue
        if ord(c) < 0x20 or ord(c) == 0x7F:
            raise ParseError(at(i), f"control character U+{ord(c):04X} in a string")  # D50
        if 0xD800 <= ord(c) <= 0xDFFF:
            raise ParseError(at(i), "unpaired surrogate in a string")
        out.append(c)
        i += 1


def _atom(tok, pos):
    if DIGITS.match(tok):
        if tok[0] == "+":
            raise ParseError(pos, f"integer '{tok}' has a '+' sign: write {tok[1:]}")
        digits = tok.lstrip("-")
        if len(digits) > 1 and digits[0] == "0":
            raise ParseError(pos, f"integer '{tok}' has a leading zero")
        if tok == "-0":
            raise ParseError(pos, "integer '-0' is not canonical: write 0")
        return Int(int(tok), pos)
    if NAME.match(tok) or tok in OPS or tok in _kw:
        return Sym(tok, pos)
    if re.match(r"[A-Za-z_]", tok):
        raise ParseError(pos, f"'{tok}' is not a valid name: names match [a-z][a-z0-9_]*")
    raise ParseError(pos, f"'{tok}' is not a name, keyword, operator or integer")


# Checking: S-expression against §2's grammar.

def _fail(x, reason):
    raise ParseError(x.pos, reason)


def _head(x):
    if isinstance(x, Form) and x.items and isinstance(x.items[0], Sym):
        return x.items[0].text
    return None


def _show(x):
    if isinstance(x, Form):
        h = _head(x)
        return f"({h} ...)" if h else "a list"
    if isinstance(x, Str):
        return "a string"
    if isinstance(x, Int):
        return f"integer {x.value}"
    return f"'{x.text}'"


def _name(x, what="a name"):
    if not isinstance(x, Sym):
        _fail(x, f"expected {what}, found {_show(x)}")
    if x.text in _kw:
        _fail(x, f"'{x.text}' is reserved and can't be used as a name")
    if not NAME.match(x.text):
        _fail(x, f"expected {what}, found '{x.text}'")


def _form(x, head, shape):
    """x must be (head ...); returns its arguments."""
    if _head(x) != head:
        _fail(x, f"expected ({head} {shape}), found {_show(x)}")
    return x.items[1:]


def _arity(x, shape):
    args = x.items[1:]
    if len(args) != len(shape):
        _fail(x, f"({' '.join((x.items[0].text,) + shape)}) takes {len(shape)} argument"
                 f"{'' if len(shape) == 1 else 's'}, got {len(args)}")
    return args


class _Clauses:
    """The clauses of an item, read in grammar order."""

    def __init__(self, form, start):
        self.form, self.i = form, start

    def peek(self):
        return self.form.items[self.i] if self.i < len(self.form.items) else None

    def take(self, head):
        x = self.peek()
        if x is not None and _head(x) == head:
            self.i += 1
            return x.items[1:]
        return None

    def need(self, head, shape, after=""):
        args = self.take(head)
        if args is None:
            x = self.peek()
            where = f" after {after}" if after else ""
            if x is None:
                raise ParseError(self.form.end, f"missing ({head} {shape}){where}")
            _fail(x, f"expected ({head} {shape}){where}, found {_show(x)}")
        return args

    def done(self):
        x = self.peek()
        if x is not None:
            _fail(x, f"unexpected {_show(x)} in ({self.form.items[0].text} ...)")


def _one(args, x, head):
    if len(args) != 1:
        _fail(x, f"({head} e) takes 1 expression, got {len(args)}")
    _expr(args[0])


def _module(x):
    if not isinstance(x, Form) or _head(x) != "module":
        _fail(x, f"expected (module NAME header item*), found {_show(x)}")
    if len(x.items) < 3:
        raise ParseError(x.end, "missing module name or header")
    _name(x.items[1], "a module name")
    h = x.items[2]
    _form(h, "header", "(purpose STR) (invariants STR) (failures STR)")
    if len(h.items) != 4:
        _fail(h, "(header ...) takes exactly (purpose STR) (invariants STR) (failures STR)")
    for part, head in zip(h.items[1:], ("purpose", "invariants", "failures")):
        args = _form(part, head, "STR")
        if len(args) != 1 or not isinstance(args[0], Str):
            _fail(part, f"({head} STR) takes one string")
    for item in x.items[3:]:
        _item(item)


def _item(x):
    h = _head(x)
    kinds = ("ghost-fn", "lemma", "spec", "def") + (("data",) if _sub else ())
    if h not in kinds:
        _fail(x, f"expected an item ({', '.join(kinds[:-1])} or {kinds[-1]}), found {_show(x)}")
    if len(x.items) < 2:
        raise ParseError(x.end, f"({h} ...) needs a name")
    _name(x.items[1], f"a {h} name")
    if h == "data":  # (data TNAME (TNAME*) ctor+), ctor = (NAME param*)
        if len(x.items) < 4:
            raise ParseError(x.end, "(data TNAME (TNAME*) ctor+) needs type parameters and a constructor")
        ps = x.items[2]
        if not isinstance(ps, Form) or _head(ps) is not None:
            _fail(ps, f"expected the data type's (TNAME*) parameters, written () when there are none, found {_show(ps)}")
        for t in ps.items:
            _name(t, "a type parameter")
        for ctor in x.items[3:]:
            if not isinstance(ctor, Form) or not ctor.items:
                _fail(ctor, f"expected a constructor (NAME param*), found {_show(ctor)}")
            _name(ctor.items[0], "a constructor name")
            for p in ctor.items[1:]:
                _param(p)
        return
    if h == "ghost-fn":
        if len(x.items) < 4:
            raise ParseError(x.end, "(ghost-fn NAME (param*) type ...) needs parameters and a type")
        ps = x.items[2]
        if not isinstance(ps, Form) or _head(ps) is not None:
            _fail(ps, f"expected the ghost-fn's (param*) list, found {_show(ps)}")
        for p in ps.items:
            _param(p)
        _type(x.items[3])
        c = _Clauses(x, 4)
        while (args := c.take("requires")) is not None:
            _one(args, x.items[c.i - 1], "requires")
        if (args := c.take("decreases")) is not None:
            _one(args, x.items[c.i - 1], "decreases")
        args = c.need("body", "e")
        _one(args, x.items[c.i - 1], "body")
        c.done()
        return
    c = _Clauses(x, 2)
    if h == "def":
        if (args := c.take("decreases")) is not None:
            _one(args, x.items[c.i - 1], "decreases")
        for s in c.need("body", "stmt*"):
            _stmt(s)
        c.done()
        return
    for p in c.need("params", "param*"):
        _param(p)
    if h == "spec":
        for p in c.need("returns", "param*", "(params ...)"):
            _param(p)
    for clause in ("requires", "ensures"):
        args = c.take(clause)
        if args == ():
            _fail(x.items[c.i - 1], f"an empty ({clause}) is not canonical: omit it")  # D54
        for e in args or ():
            _expr(e)
    if h == "spec":
        last = -1
        for eff in c.need("effects", "EFF*"):
            if not isinstance(eff, Sym) or eff.text not in EFFECTS:
                _fail(eff, f"expected an effect (alloc, panic or io), found {_show(eff)}")
            k = EFFECTS.index(eff.text)
            if k <= last:
                _fail(eff, "effects are listed once each, in the order alloc, panic, io")
            last = k
    else:
        if (args := c.take("decreases")) is not None:
            _one(args, x.items[c.i - 1], "decreases")
        for s in c.need("body", "stmt*"):
            _stmt(s)
    c.done()


def _param(x):
    if not isinstance(x, Form) or len(x.items) != 2:
        _fail(x, f"expected a parameter (NAME type), found {_show(x)}")
    _name(x.items[0], "a parameter name")
    _type(x.items[1])


def _type(x):
    if isinstance(x, Sym) and x.text in ("bool", "i64", "int"):
        return
    h = _head(x)
    if h in ("seq", "multiset", "vec") and len(x.items) == 2:
        return _type(x.items[1])
    if h == "ref" and len(x.items) == 2 and _head(x.items[1]) == "slice" and len(x.items[1].items) == 2:
        return _type(x.items[1].items[1])
    if _sub:  # B17-1: TNAME | (TNAME type+) | (tuple type type+) | (iset type) | (map type type)
        if isinstance(x, Sym) and x.text not in _kw and NAME.match(x.text):
            return
        n = len(x.items) - 1 if isinstance(x, Form) else -1
        if (h == "tuple" and n >= 2) or (h == "iset" and n == 1) or (h == "map" and n == 2) \
                or (h is not None and h not in _kw and n >= 1):
            for t in x.items[1:]:
                _type(t)
            return
    _fail(x, f"expected a type, found {_show(x)}")


# Fixed shapes: argument kinds of each head with a fixed arity.
STMTS = {
    "set": ("NAME", "e"), "set-idx": ("NAME", "e", "e"), "push": ("NAME", "e"),  # B17-1: a place (§2)
    "if": ("e", "stmt", "stmt"), "assert": ("e",),
    "ghost-let": ("NAME", "type", "e"), "ghost-let-mut": ("NAME", "type", "e"),
    "ghost-set": ("NAME", "e"), "panic": ("STR",), "print": ("e",),
}
EXPRS = {
    "not": ("e",), "neg": ("e",), "if": ("e", "e", "e"), "len": ("e",), "idx": ("e", "e"),
    "borrow": ("NAME",), "vec-new": (), "seq-build": ("e", "(fn (NAME) e)"),
    "take": ("e", "e"), "drop": ("e", "e"), "concat": ("e", "e"), "last": ("e",),
    "contains": ("e", "e"), "multiset": ("e",), "msum": ("e", "e"), "occurrences": ("e", "e"),
    **{op: ("e", "e") for op in OPS},
}
EXPRS_1 = {  # docs/b17-1.md §2's fixed shapes
    "is": ("NAME", "e"), "field": ("e", "NAME"), "get": ("e", "INT"), "rank": ("e",),
    "union": ("e", "e"), "diff": ("e", "e"), "inter": ("e", "e"), "update": ("e", "e", "e"),
    "lookup": ("e", "e"),
}


def _check(kind, x):
    if kind == "e":
        _expr(x)
    elif kind == "place":
        _place(x)
    elif kind == "stmt":
        _stmt(x)
    elif kind == "NAME":
        _name(x)
    elif kind == "type":
        _type(x)
    elif kind == "STR":
        if not isinstance(x, Str):
            _fail(x, f"expected a string, found {_show(x)}")
    elif kind == "INT":
        if not isinstance(x, Int):
            _fail(x, f"expected an integer literal, found {_show(x)}")
    else:  # (fn (NAME) e)
        if (_head(x) != "fn" or len(x.items) != 3 or not isinstance(x.items[1], Form)
                or len(x.items[1].items) != 1):
            _fail(x, f"expected (fn (NAME) e), found {_show(x)}")
        _name(x.items[1].items[0], "a binder name")
        _expr(x.items[2])


def _place(x):
    """B17-1's place = NAME | (idx place e) | (get place INT) | (field place NAME)."""
    h = _head(x)
    if h == "idx":
        p, e = _arity(x, ("place", "e"))
        _place(p)
        _expr(e)
    elif h in ("get", "field"):
        p, k = _arity(x, ("place", "INT" if h == "get" else "NAME"))
        _place(p)
        _check("INT" if h == "get" else "NAME", k)
    else:
        _name(x, "a place: a variable, or (idx place e), (get place INT) or (field place NAME)")


def _binders(x, h, one=False):
    """((NAME type)+), the binders of forall, exists, iset-of and obtain."""
    bs = x.items[1] if len(x.items) > 1 else None
    if not isinstance(bs, Form) or not bs.items or (one and len(bs.items) != 1):
        _fail(x, f"expected ({h} ((NAME type){'' if one else '+'}) ...)")
    for b in bs.items:
        if not isinstance(b, Form) or len(b.items) != 2:
            _fail(b, f"expected a binder (NAME type), found {_show(b)}")
        _name(b.items[0], "a binder name")
        _type(b.items[1])


def _cases(x, arm):
    """(match e case+), case = (case pat arm); pat = (NAME NAME*) | (tuple NAME NAME+)."""
    if len(x.items) < 3:
        raise ParseError(x.end, "(match e case+) needs a scrutinee and at least one case")
    _expr(x.items[1])
    for c in x.items[2:]:
        if _head(c) != "case":
            _fail(c, f"expected (case pat {arm}), found {_show(c)}")
        pat, body = _arity(c, ("pat", arm))
        if not isinstance(pat, Form) or not pat.items:
            _fail(pat, f"expected a pattern (NAME NAME*) or (tuple NAME NAME+), found {_show(pat)}")
        if _head(pat) == "tuple":
            if len(pat.items) < 3:
                _fail(pat, "a tuple pattern binds at least two names")
        else:
            _name(pat.items[0], "a constructor name")
        for b in pat.items[1:]:
            _name(b, "a pattern binder")
        _check(arm, body)


def _call(x, args):
    if not args:
        raise ParseError(x.end, "(call NAME e*) needs the callee's name")
    _name(args[0], "a callee name")
    for e in args[1:]:
        _expr(e)


def _stmt(x):
    h = _head(x)
    if h in STMTS:
        shape = STMTS[h]
        if _sub and h in ("set-idx", "push"):
            shape = ("place",) + shape[1:]
        for kind, arg in zip(shape, _arity(x, shape)):
            _check(kind, arg)
    elif h in ("let", "let-mut"):
        args = x.items[1:]
        if args and isinstance(args[0], Form):  # (let (param+) (call NAME e*))
            if len(args) != 2:
                _fail(x, f"({h} (param+) (call NAME e*)) takes 2 arguments, got {len(args)}")
            if not args[0].items:
                _fail(args[0], f"({h} (param+) ...) binds at least one result")
            for p in args[0].items:
                _param(p)
            _call(args[1], _form(args[1], "call", "NAME e*"))
        else:
            name, typ, e = _arity(x, ("NAME", "type", "e"))
            _name(name)
            _type(typ)
            if _sub and _head(e) == "replace":  # (let NAME type (replace place e))
                p, v = _arity(e, ("place", "e"))
                _place(p)
                _expr(v)
            else:
                _expr(e)
    elif h == "block":
        for s in x.items[1:]:
            _stmt(s)
    elif h == "return":
        for e in x.items[1:]:
            _expr(e)
    elif h == "call":
        _call(x, x.items[1:])
    elif _sub and h == "match":
        _cases(x, "stmt")
    elif _sub and h == "forall":  # (forall ((NAME type)+) (call NAME e*)), D99
        if len(x.items) != 3:
            _fail(x, "expected (forall ((NAME type)+) (call NAME e*))")
        _binders(x, h)
        _call(x.items[2], _form(x.items[2], "call", "NAME e*"))
    elif _sub and h == "obtain":  # (obtain ((NAME type)+) e), D100
        if len(x.items) != 3:
            _fail(x, "expected (obtain ((NAME type)+) e)")
        _binders(x, h)
        _expr(x.items[2])
    elif h == "while":
        if len(x.items) < 2:
            raise ParseError(x.end, "(while e inv* dec stmt*) needs a condition")
        _expr(x.items[1])
        c = _Clauses(x, 2)
        while (args := c.take("invariant")) is not None:
            _one(args, x.items[c.i - 1], "invariant")
        _one(c.need("decreases", "e", "the loop's invariants"), x.items[c.i - 1], "decreases")
        for s in x.items[c.i:]:
            _stmt(s)
    else:
        _fail(x, f"expected a statement, found {_show(x)}")


def _expr(x):
    if isinstance(x, Int):
        return
    if isinstance(x, Sym):
        if x.text in ("true", "false"):
            return
        return _name(x, "an expression")
    if isinstance(x, Str):
        _fail(x, "a string is not an expression")
    h = _head(x)
    if h is None:
        _fail(x, "expected an expression, found a list with no head word")
    if _sub and h in EXPRS_1:
        for kind, arg in zip(EXPRS_1[h], _arity(x, EXPRS_1[h])):
            _check(kind, arg)
    elif _sub and h == "match":
        _cases(x, "e")
    elif _sub and h == "tuple":
        if len(x.items) < 3:
            _fail(x, "(tuple e e+) takes at least two expressions")
        for e in x.items[1:]:
            _expr(e)
    elif _sub and h == "iset-lit":
        for e in x.items[1:]:
            _expr(e)
    elif _sub and h == "iset-of":  # (iset-of ((NAME type)) e)
        if len(x.items) != 3:
            _fail(x, "expected (iset-of ((NAME type)) e)")
        _binders(x, h, one=True)
        _expr(x.items[2])
    elif _sub and h == "map-lit":  # (map-lit (e e)*)
        for entry in x.items[1:]:
            if not isinstance(entry, Form) or len(entry.items) != 2:
                _fail(entry, f"expected a map entry (e e), found {_show(entry)}")
            _expr(entry.items[0])
            _expr(entry.items[1])
    elif h in EXPRS:
        args = _arity(x, EXPRS[h])
        for kind, arg in zip(EXPRS[h], args):
            _check(kind, arg)
        if h == "neg" and isinstance(args[0], Int):
            _fail(x, f"(neg INT) is not canonical: write {-args[0].value}")  # D53
    elif h == "seq-lit":
        for e in x.items[1:]:
            _expr(e)
    elif h in ("forall", "exists"):
        if len(x.items) != 3 or not isinstance(x.items[1], Form) or not x.items[1].items:
            _fail(x, f"expected ({h} ((NAME type)+) e)")
        _binders(x, h)
        _expr(x.items[2])
    elif h in _kw:
        _fail(x, f"({h} ...) is not an expression")
    else:  # (NAME e*): a ghost-fn call
        _name(x.items[0], "a ghost-fn name")
        for e in x.items[1:]:
            _expr(e)


if __name__ == "__main__":
    args = sys.argv[1:]
    subset = 0
    if args[:1] == ["--subset"] and len(args) == 3 and args[1] in ("0", "1"):
        subset, args = int(args[1]), args[2:]
    if len(args) != 1:
        sys.exit("usage: uv run --no-project b17c/syntax.py [--subset 1] FILE")
    path = args[0]
    try:
        out = canonical(parse(Path(path).read_bytes(), subset))
    except ParseError as e:
        print(f"{path}:{e.line}:{e.col}: {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    sys.stdout.buffer.write(out)
