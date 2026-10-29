"""WP7's backend: B17-0 to safe Rust (D18, D95-D97), and B17-1 with --subset 1 (D101, D110).

    uv run --no-project b17c/rust.py [--subset 1] FILE                              # the emitted Rust
    uv run --no-project b17c/rust.py [--subset 1] -o BINARY [--report JSON] FILE    # built with rustc
    uv run --no-project b17c/rust.py [--subset 1] --run FILE NAME ARG...            # built, then run like interp.py

emit() turns a module that passes tier 0 (WP3) into the source of one Rust crate. The
crate forbids unsafe code and erases ghost code. Every runtime goal of §9 is checked
explicitly: arithmetic, division and indexing that would leave §8 stop the run with the
interpreter's err outcome, at the same node (D56). The crate's main runs one def on its
arguments and prints the run's trace and outcome in interface 10's text form, as
interp.py does, so the two can be compared line for line. That comparison is WP7's
differential test (test_rust.py).

In B17-1 (docs/b17-1.md), data types become enums, a field read on the wrong constructor
is err FIELD, places are updated where they are, and match becomes match (D110). B17-0's
output is the same, byte for byte, as before B17-1 (D101).

--run builds into .b17c/rust/, keyed by the emitted source and the toolchain. Each ARG is
a closed expression, evaluated as interp.py evaluates it, and the run exits as
interp.py's does: 0 on ok, 1 on any other outcome, and 2 when the run can't start.
--report adds the backend's fields to a trusted base report (D25), creating it if needed.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import interp
from check import _Checker
from check import types as tier0_types
from syntax import Form, Int, ParseError, Sym, _head, _print, canonical, parse

BOOL, I64 = ("bool",), ("i64",)
FLAGS = ("--edition", "2021", "-O", "-C", "overflow-checks=on")  # D97
CACHE = Path(".b17c/rust")
# Rust's strict and reserved keywords, in every edition. A B17-0 name that is one becomes
# a raw identifier, except the three Rust can't write raw (D95).
KEYWORDS = {
    "abstract", "as", "async", "await", "become", "box", "break", "const", "continue", "crate", "do",
    "dyn", "else", "enum", "extern", "false", "final", "fn", "for", "gen", "if", "impl", "in", "let",
    "loop", "macro", "match", "mod", "move", "mut", "override", "priv", "pub", "ref", "return", "self",
    "static", "struct", "super", "trait", "true", "try", "type", "typeof", "unsafe", "unsized", "use",
    "virtual", "where", "while", "yield",
}
UNRAW = {"crate", "self", "super"}
ARITH = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "rem"}
COMPARE = {"<", "<=", ">", ">=", "==", "!="}
GHOST = {"assert", "ghost-let", "ghost-let-mut", "ghost-set", "forall", "obtain"}  # the last two are B17-1's
# Lints that valid B17-0 programs trigger: a helper the module doesn't use, a local it never
# reads or a let-mut it never sets, (while true ...), recursion a proof bounds, a comparison
# with an i64 limit, and a name with two underscores in a row (D95).
ALLOW = ("dead_code, unused_variables, unused_mut, unused_assignments, while_true, unconditional_recursion, "
         "unused_comparisons, non_snake_case")
ALLOW_1 = ALLOW + ", non_camel_case_types"  # B17-1's types and constructors are lowercase (D110)


class BuildError(Exception):
    """rustc rejected emitted code. The module passed tier 0, so this is a backend bug (D18)."""


def emit(module, subset=0):
    """module, which must pass tier 0, as the source of one Rust crate (D95, D110). Text that
    doesn't parse raises ParseError. A module that fails tier 0 raises ValueError, and so
    does a call to a spec with no def, in code that can run, since a binary can't make
    that call (D96)."""
    if not isinstance(module, Form):
        module = parse(module, subset)
    try:
        typed = tier0_types(module, subset)  # every expression's type, as WP3 gives it
    except ValueError as e:
        found = str(e).splitlines()
        more = f" (and {len(found) - 1} more)" if len(found) > 1 else ""
        raise ValueError(f"the module doesn't pass tier 0: {found[0]}{more}") from None
    return _Emitter(module, typed, subset, data_types(module) if subset else {}).crate()


def data_types(module):
    """B17-1 module's data types, with what §3, §5 and §6 derive from them, as tier 0 reads them."""
    checker = _Checker(module, 1)
    checker.collect()
    return checker.datas


def rid(name):
    """A B17-0 name as a Rust identifier (D95): itself, unless Rust reserves it. B17-0
    names never start with _, so _crate, _self and _super can't clash with one."""
    if name in UNRAW:
        return "_" + name
    return "r#" + name if name in KEYWORDS else name


def string(text):
    """text as a Rust string literal. Only printable ASCII appears as itself, so no
    bidirectional or other invisible character reaches the source."""
    out = []
    for c in text:
        if c in '\\"':
            out.append("\\" + c)
        elif " " <= c <= "~":
            out.append(c)
        else:
            out.append(f"\\u{{{ord(c):x}}}")
    return '"' + "".join(out) + '"'


def _type(t):
    """A type form as check.py writes types: ("bool",), ("i64",), ("vec", T) or ("slice", T),
    and in B17-1 ("tuple", T...) and ("data", NAME, T...)."""
    if isinstance(t, Sym):
        return (t.text,) if t.text in ("bool", "i64", "int") else ("data", t.text)
    h = t.items[0].text
    if h == "ref":
        return ("slice", _type(t.items[1].items[1]))
    head = (h,) if h in ("vec", "seq", "multiset", "iset", "map", "tuple") else ("data", h)
    return head + tuple(_type(a) for a in t.items[1:])


def _args(item, head):
    """The arguments of item's clauses with this head, in order."""
    return [a for c in item.items[2:] if _head(c) == head for a in c.items[1:]]


def _ends(s):
    """No path through statement s continues normally: §7's ⊥, where every while may end (D77).
    A B17-1 match statement is ⊥ when every arm is."""
    h = _head(s)
    if h in ("return", "panic"):
        return True
    if h == "block":
        return any(_ends(c) for c in s.items[1:])
    if h == "match":
        return all(_ends(c.items[2]) for c in s.items[2:])
    return h == "if" and _ends(s.items[2]) and _ends(s.items[3])


def _untyped(x):
    """Rust would give x no type of its own: a literal, or an if whose branches are literals."""
    return isinstance(x, Int) or (_head(x) == "if" and _untyped(x.items[2]) and _untyped(x.items[3]))


def _parens(parts):
    """A variant's fields or a call's arguments, (a, b), or nothing when there are none."""
    parts = list(parts)
    return f"({', '.join(parts)})" if parts else ""


def _mentions(t, name):
    """Field type t mentions data type name other than inside a vector: a boxed field (D86)."""
    if t[0] == "vec":
        return False
    return t[:2] == ("data", name) or any(_mentions(a, name) for a in t[1:] if isinstance(a, tuple))


class _Emitter:
    def __init__(self, module, typed, subset, datas):
        self.module, self.typed, self.sub, self.datas = module, typed, subset, datas
        self.specs, self.defs, self.lemmas, self.ids = {}, {}, set(), {}
        for m in (interp.CORE, module):
            for it in m.items[3:]:
                kind, name = it.items[0].text, it.items[1].text
                if kind == "spec":
                    self.specs[name] = it
                elif kind == "def":
                    self.defs[name] = it
                elif kind == "lemma":
                    self.lemmas.add(name)
        for it in module.items[3:]:
            if it.items[0].text == "def":
                self.index(it, f"def {it.items[1].text}", ())
        self.uses = set()
        # B17-1 (D110): constructors, and what the crate's data module and runtime need.
        self.ctors = {c.text: (name, k) for name, d in self.datas.items() for k, (c, _) in enumerate(d.ctors)}
        self.wanted = []     # data type names, in first-use order
        self.accessors = {}  # (data type, field, mutable) -> None
        self.arities = set()  # of the tuple types the crate reads and prints

    def index(self, x, item, path):
        self.ids[id(x)] = (item, path)
        if isinstance(x, Form):
            for k, c in enumerate(x.items):
                self.index(c, item, path + (k,))

    def node(self, x):
        """x's node ID as interp.py writes it (D56), as a string literal."""
        return string(str(interp.Node(*self.ids[id(x)], x.pos)))

    def crate(self):
        name = self.module.items[1].text
        digest = hashlib.sha256(canonical(self.module)).hexdigest()
        defs = [it for it in self.module.items[3:] if it.items[0].text == "def"]
        fns = [line for d in defs for line in self.fn(d)]
        arms = [line for d in defs for line in self.arm(d)]
        uses = [f"    use crate::{p};" for p in ("rt", "rt::SetIdx", "data") if p in self.uses]
        data = self.data_module()
        return "\n".join([
            f"// Emitted by b17c's Rust backend (WP7, D95{', D110' if self.sub else ''}) from "
            f"{'B17-1 ' if self.sub else ''}module {name}. Emit it again rather",
            f"// than editing it. The module's canonical bytes have SHA-256 {digest}.",
            "#![forbid(unsafe_code)]",
            f"#![allow({ALLOW_1 if self.sub else ALLOW})]",
            "",
            *data,
            "mod program {",
            *uses,
            *fns,
            "}",
            "",
            "fn dispatch(name: &str, args: &[String]) -> Result<rt::Run, String> {",
            "    match name {",
            *arms,
            "        _ => Err(format!(\"no def named '{}'\", name)),",
            "    }",
            "}",
            "",
            "fn main() {",
            "    std::process::exit(rt::main(dispatch));",
            "}",
            "",
            self.runtime() if self.sub else RUNTIME,
        ])

    # Items.

    def fn(self, d):
        name = d.items[1].text
        spec = self.specs[name]
        params, results = _args(spec, "params"), [_type(p.items[1]) for p in _args(spec, "returns")]
        sig = ", ".join(f"{rid(p.items[0].text)}: {self.rtype(_type(p.items[1]))}" for p in params)
        ret = "" if not results else f" -> {self.tuple(map(self.rtype, results))}"
        return ["", f"    /// def {name}, line {d.pos[0]}", f"    pub fn {rid(name)}({sig}){ret} {{",
                *self.stmts(_args(d, "body"), 2), "    }"]

    def arm(self, d):
        """The driver's case for def d: its arguments read and type-checked, then its run."""
        name = d.items[1].text
        params = _args(self.specs[name], "params")
        results = len(_args(self.specs[name], "returns"))
        lines = [f"        {string(name)} => {{", f"            rt::arity(name, args, {len(params)})?;"]
        call = []
        for k, p in enumerate(params):
            t = _type(p.items[1])
            owned = ("vec", t[1]) if t[0] == "slice" else t
            lines.append(f"            let a{k}: {self.rtype(owned)} = rt::arg(args, {k}, "
                         f"{string(p.items[0].text)}, {string(_print(p.items[1]))})?;")
            call.append(f"&a{k}" if t[0] == "slice" else f"a{k}")
        names = [f"r{k}" for k in range(results)]
        run = f"program::{rid(name)}({', '.join(call)})"
        terms = f"vec![{', '.join(f'rt::term(&{n})' for n in names)}]" if names else "Vec::new()"
        lines += ["            Ok(Box::new(move || -> Vec<String> {",
                  f"                {f'let {self.tuple(names)} = ' if names else ''}{run};",
                  f"                {terms}",
                  "            }))", "        }"]
        return lines

    @staticmethod
    def tuple(parts):
        parts = list(parts)
        return parts[0] if len(parts) == 1 else f"({', '.join(parts)})"

    # Types. B17-0's are bool, i64, Vec<T> and &[T]. B17-1 adds tuples, and data types,
    # which live in the crate's data module (D110).

    def rtype(self, t, inside=None):
        """Type t in Rust, as the program and driver name it, or inside the declaration of
        data type inside, whose type parameters are T0, T1, ... there."""
        h = t[0]
        if h == "vec":
            return f"Vec<{self.rtype(t[1], inside)}>"
        if h == "slice":
            return f"&[{self.rtype(t[1], inside)}]"
        if h == "tuple":
            self.arities.add(len(t) - 1)
            return f"({', '.join(self.rtype(a, inside) for a in t[1:])})"
        if h == "data":
            path, args = self.data_type(t, inside)
            return path + args
        if h == "param":
            return f"T{self.kept(inside).index(t[1])}"
        return "_" if h == "any" else h  # an open element type, which the destination fixes (§4)

    def data_type(self, t, inside=None):
        """Data type t's path and type arguments, such as ("data::option", "<i64>"). Only the
        parameters a value can hold are Rust's, since Rust rejects a parameter it never uses."""
        self.need(t[1])
        args = [self.rtype(a, inside) for a in self.rust_args(t)]
        return ("" if inside else "data::") + rid(t[1]), f"<{', '.join(args)}>" if args else ""

    def kept(self, name):
        d = self.datas[name]
        return [a for a in d.params if a in d.stored]

    def need(self, name):
        """The crate declares data type name. D104 makes a data type's recursion regular, so a
        module's instances, and the Rust types for them, are finite."""
        if name not in self.wanted:
            self.wanted.append(name)
            self.uses.add("data")

    def rust_args(self, t):
        """The type arguments of data type t that Rust keeps: those for the parameters a value holds."""
        d = self.datas[t[1]]
        return [a for a, p in zip(t[2:], d.params) if p in d.stored]

    def boxed(self, name):
        """Per constructor of data type name, which of its fields are boxed (D86)."""
        return [[_mentions(ft, name) for _, ft in fs] for _, fs in self.datas[name].ctors]

    def ctor(self, name):
        """Constructor name's path, such as data::option::some, and which of its fields are boxed."""
        dname, k = self.ctors[name]
        self.need(dname)
        return f"data::{rid(dname)}::{rid(name)}", self.boxed(dname)[k]

    # Statements. Ghost statements and lemma calls are erased (§4, §8), and statements after
    # one that never continues normally are left out, since none of them can run (D77).

    def stmts(self, ss, depth):
        out = []
        for s in ss:
            out += self.stmt(s, depth)
            if _ends(s):
                break
        return out

    def stmt(self, s, depth):
        pad, it, h = "    " * depth, s.items, _head(s)
        if self.sub:
            if h in ("let", "let-mut") and not isinstance(it[1], Form) and _head(it[3]) == "replace":
                return self.replace(s, depth)
            if h in ("set-idx", "push") and isinstance(it[1], Form):
                return self.update(s, depth)
            if h == "match":
                return self.match_stmt(s, depth)
        if h in ("let", "let-mut"):
            mut = "mut " if h == "let-mut" else ""
            if isinstance(it[1], Form):  # a call's results, one name each (D43, D74)
                names = [mut + rid(p.items[0].text) for p in it[1].items]
                types = [self.rtype(_type(p.items[1])) for p in it[1].items]
                return [f"{pad}let {self.tuple(names)}: {self.tuple(types)} = {self.call(it[2])};"]
            return [f"{pad}let {mut}{rid(it[1].text)}: {self.rtype(_type(it[2]))} = {self.top(it[3])};"]
        if h == "set":
            return [f"{pad}{rid(it[1].text)} = {self.top(it[2])};"]
        if h == "set-idx":  # the index, then the value, then the check (D56)
            self.uses.add("rt::SetIdx")
            v = it[1].text
            return [f"{pad}{rid(v)}.set_idx({self.top(it[2])}, {self.top(it[3])}, {string(v)}, {self.node(s)});"]
        if h == "push":
            return [f"{pad}{rid(it[1].text)}.push({self.top(it[2])});"]
        if h == "if":
            return self.branches(s, depth)
        if h == "block":
            return [pad + "{", *self.stmts(it[1:], depth + 1), pad + "}"]
        if h == "while":
            body = [c for c in it[2:] if _head(c) not in ("invariant", "decreases")]
            return [f"{pad}while {self.top(it[1])} {{", *self.stmts(body, depth + 1), pad + "}"]
        if h == "call":
            if it[1].text in self.lemmas:
                return []  # its arguments are ghost, so nothing runs (D57)
            return [f"{pad}{self.call(s)};"]
        if h == "return":
            values = [self.top(e) for e in it[1:]]
            return [f"{pad}return{' ' + self.tuple(values) if values else ''};"]
        if h == "panic":
            self.uses.add("rt")
            return [f"{pad}rt::panic({string(it[1].value)});"]
        if h == "print":
            self.uses.add("rt")
            return [f"{pad}rt::print({self.top(it[1])});"]
        assert h in GHOST, f"not a statement: {h}"
        return []

    def branches(self, s, depth):
        """An if statement, with an if in else position as else if."""
        pad = "    " * depth
        out = [f"{pad}if {self.top(s.items[1])} {{"]
        while True:
            out += self.branch(s.items[2], depth + 1)
            s = s.items[3]
            if _head(s) != "if":
                alt = self.branch(s, depth + 1)
                return out + ([pad + "} else {", *alt] if alt else []) + [pad + "}"]
            out.append(f"{pad}}} else if {self.top(s.items[1])} {{")

    def branch(self, s, depth):
        return self.stmts(s.items[1:], depth) if _head(s) == "block" else self.stmts([s], depth)

    def call(self, c):
        """A def call. An argument for a slice parameter is a borrow or a slice passed on (§5)."""
        name = c.items[1].text
        if name not in self.defs:
            raise ValueError(f"{c.pos[0]}:{c.pos[1]}: {name} is a spec with no def, so a binary can't call it (D96)")
        args = ["&" + rid(a.items[1].text) if _head(a) == "borrow" else self.top(a) for a in c.items[2:]]
        return f"{rid(name)}({', '.join(args)})"

    # B17-1's statements (docs/b17-1.md §5, §7; D110). An update through a place evaluates
    # the place's indices in source order, then the statement's index and value, into
    # temporaries, as interp.py does. Then it walks down from the root, checking each idx
    # and field on the way, and changes the part where it is (§8).

    def match_stmt(self, s, depth):
        """A match statement. Its scrutinee is a variable, which moves when its type does, or a
        copied value (§5 rule 4). A boxed field's binder takes the value out of its box."""
        pad = "    " * depth
        out = [f"{pad}match {self.top(s.items[1])} {{"]
        for case in s.items[2:]:
            pattern, boxed = self.pattern(case.items[1])
            out.append(f"{pad}    {pattern} => {{")
            out += [f"{pad}        let {b} = *{b};" for b in boxed]
            out += self.branch(case.items[2], depth + 2)
            out.append(f"{pad}    }}")
        return out + [pad + "}"]

    def pattern(self, pat):
        """A case's pattern, and its binders that hold a boxed field. The constructor names
        the data type, and (tuple x...) a tuple."""
        names = [rid(b.text) for b in pat.items[1:]]
        if pat.items[0].text == "tuple":
            return f"({', '.join(names)})", []
        path, boxes = self.ctor(pat.items[0].text)
        return path + _parens(names), [n for n, b in zip(names, boxes) if b]

    def indices(self, p, pad):
        """The lets that evaluate place p's idx indices into temporaries, from its root out,
        which is source order, and the temporary each idx reads."""
        steps = []
        while isinstance(p, Form):
            if p.items[0].text == "idx":
                steps.insert(0, p)
            p = p.items[1]
        lets = [f"{pad}    let _i{k}: i64 = {self.top(f.items[2])};" for k, f in enumerate(steps)]
        return lets, {id(f): f"_i{k}" for k, f in enumerate(steps)}

    def update(self, s, depth):
        """(set-idx place i e) or (push place e), for a place that isn't a variable."""
        pad, it, h = "    " * depth, s.items, s.items[0].text
        lets, temps = self.indices(it[1], pad)
        elem, call = self.rtype(self.typed[id(it[1])][1]), "push(_v)"
        if h == "set-idx":
            self.uses.add("rt::SetIdx")
            lets.append(f"{pad}    let _i: i64 = {self.top(it[2])};")
            call = f"set_idx(_i, _v, {string(_print(it[1]))}, {self.node(s)})"
        lets.append(f"{pad}    let _v: {elem} = {self.top(it[-1])};")
        return [pad + "{", *lets, f"{pad}    {self.place(it[1], temps)[1]}.{call};", pad + "}"]

    def replace(self, s, depth):
        """(let x T (replace place e)): the place's old value, with e left where it was (§5 rule 3)."""
        pad, it = "    " * depth, s.items
        p, e = it[3].items[1], it[3].items[2]
        mut = "mut " if it[0].text == "let-mut" else ""
        t = self.rtype(_type(it[2]))
        lets, temps = self.indices(p, pad)
        out = [f"{pad}let {mut}{rid(it[1].text)}: {t} = {{", *lets, f"{pad}    let _v: {t} = {self.top(e)};",
               f"{pad}    std::mem::replace({self.pointer(p, temps)}, _v)"]
        return out + [pad + "};"]

    def place(self, x, temps=None):
        """x where it is: read, or with temps, which hold a place's indices, changed. Gives
        ("ref", code) for code of type &T or &mut T, or ("place", code) for a Rust place or
        value. Each idx and field on the way down is checked where interp.py checks it (§8),
        and a moving value is only ever read through a reference (§5 rule 3)."""
        h, mutable = _head(x), temps is not None
        if h == "idx":
            self.uses.add("rt")
            seq = self.pointer(x.items[1], temps)
            if mutable:
                return "ref", f"rt::at_mut({seq}, {temps[id(x)]}, {string(_print(x.items[1]))}, {self.node(x)})"
            return "ref", f"rt::at({seq}, {self.top(x.items[2])}, {self.node(x)})"
        if h == "field":
            return "ref", f"{self.place(x.items[1], temps)[1]}.{self.accessor(x, mutable)}"
        if h == "get":
            return "place", f"{self.place(x.items[1], temps)[1]}.{x.items[2].value}"
        return "place", self.expr(x)[0]  # a variable, or a value such as a constructor call

    def pointer(self, x, temps=None):
        """x where it is, as a reference: &T to read, or &mut T to change."""
        kind, code = self.place(x, temps)
        return code if kind == "ref" else ("&mut " if temps is not None else "&") + code

    def accessor(self, x, mutable):
        """The call that reaches field F of (field e F), and checks e's constructor has it (§8)."""
        t, f = self.typed[id(x.items[1])], x.items[2].text
        self.accessors[(t[1], f, mutable)] = None
        return f"_{'m' if mutable else 'r'}_{f}({self.node(x)})"

    # Expressions. Each has the type WP3 gives it, which fixes the element type a (vec-new)
    # leaves open (D70): its destination's, or i64 when nothing gives one.

    def top(self, x):
        """x's code where nothing around it needs parentheses: an operand of a statement, or an argument."""
        code, wrapped = self.expr(x)
        return code[1:-1] if wrapped else code

    def expr(self, x, force=False):
        """(Rust code, whether it's an operator this added parentheses around). force gives a
        literal the type i64, where Rust would give it none of its own. In B17-1 every literal
        has it, since a tuple or a type argument may give a literal no type either."""
        if isinstance(x, Int):  # rustc reads -9223372036854775808 as i64::MIN, as B17-0 does
            return f"{x.value}{'i64' if force or self.sub else ''}", False
        if isinstance(x, Sym):
            return (x.text if x.text in ("true", "false") else rid(x.text)), False
        h, it = _head(x), x.items
        if self.sub and (h in ("len", "idx", "field", "get", "is", "tuple", "match") or h in self.ctors):
            return self.expr1(x)
        if h in ARITH:
            self.uses.add("rt")
            return f"rt::{ARITH[h]}({self.top(it[1])}, {self.top(it[2])}, {self.node(x)})", False
        if h in COMPARE:
            a = self.expr(it[1], _untyped(it[1]) and _untyped(it[2]))[0]
            return f"({a} {h} {self.expr(it[2])[0]})", True
        if h in ("and", "or", "=>"):
            a, b = self.expr(it[1])[0], self.expr(it[2])[0]
            return {"and": f"({a} && {b})", "or": f"({a} || {b})", "=>": f"(!{a} || {b})"}[h], True
        if h == "not":
            return f"!{self.expr(it[1])[0]}", False
        if h == "neg":
            self.uses.add("rt")
            return f"rt::neg({self.top(it[1])}, {self.node(x)})", False
        if h == "if":
            a, wrapped = self.expr(it[2], force)
            a = a[1:-1] if wrapped else a
            return f"(if {self.top(it[1])} {{ {a} }} else {{ {self.top(it[3])} }})", True
        if h == "len":
            return f"({self.sequence(it[1], I64)}.len() as i64)", True
        if h == "idx":
            self.uses.add("rt")
            s = self.sequence(it[1], self.typed[id(x)])
            return f"rt::idx(&{s}, {self.top(it[2])}, {self.node(x)})", False
        if h == "vec-new":  # only where a declared type fixes T; see sequence() for the rest
            return "Vec::new()", False
        if h == "seq-build":
            self.uses.add("rt")
            i, t = it[2].items[1].items[0].text, self.rtype(self.typed[id(x)][1])
            return (f"rt::seq_build({self.top(it[1])}, {self.node(x)}, |{rid(i)}: i64| -> {t} "
                    f"{{ {self.top(it[2].items[2])} }})"), False
        raise AssertionError(f"not runtime code: {_print(x)}")

    def sequence(self, x, elem):
        """The sequence operand of len or idx. A (vec-new) there has no destination to give
        it a type, so it gets elem: the element type tier 0 gave idx, or i64 under len."""
        if _head(x) == "vec-new":
            return f"Vec::<{self.rtype(elem)}>::new()"
        return self.expr(x)[0]

    def expr1(self, x):
        """B17-1's expressions. A moving value inside a place is only ever read further, so
        idx, field and get read through references (§5 rule 3); a copied value is copied out."""
        h, it = _head(x), x.items
        if h == "len":
            return f"({self.place(it[1])[1]}.len() as i64)", True
        if h in ("idx", "field", "get"):
            kind, code = self.place(x)
            return (f"*{code}" if kind == "ref" else code), False
        if h == "is":
            path, fields = self.ctor(it[1].text)
            return f"matches!({self.pointer(it[2])}, {path}{'(..)' if fields else ''})", False
        if h == "tuple":
            return f"({', '.join(self.top(a) for a in it[1:])})", False
        if h == "match":  # its scrutinee has a copied type (§5 rule 4)
            arms = [f"{self.pattern(c.items[1])[0]} => {self.top(c.items[2])}" for c in it[2:]]
            return f"(match {self.top(it[1])} {{ {', '.join(arms)} }})", True
        path, args = self.data_type(self.typed[id(x)])  # a constructor call, whose type arguments Rust can't always infer
        boxes = self.ctor(h)[1]
        values = [f"Box::new({self.top(a)})" if b else self.top(a) for a, b in zip(it[1:], boxes)]
        return f"{path}{'::' + args if args else ''}::{rid(h)}{_parens(values)}", False

    # B17-1's data module: an enum per data type the crate uses, with what reads, prints and
    # parses its values (D110).

    def data_module(self):
        if not self.wanted:
            return []
        out = []
        for name in self.wanted:  # declaring a type may want more, which this loop reaches too
            out += self.declare(name)
        return ["mod data {", "    //! The data types the program uses, as enums (D110).", *out,
                "}", ""]

    def declare(self, name):
        d, ts = self.datas[name], [f"T{k}" for k in range(len(self.kept(name)))]
        generics = lambda bound="": f"<{', '.join(t + bound for t in ts)}>" if ts else ""
        me = rid(name) + generics()
        where = "the core library's" if name == "option" else f"line {d.form.pos[0]}"  # docs/b17-1.md §9
        out = ["", f"    /// data {name}, {where}"]
        if not d.mv_base:
            out.append("    #[derive(Clone, Copy)]")  # copied (§5 rule 1); Rust adds T: Copy for each parameter
        out.append(f"    pub enum {me} {{")
        for (c, fs), boxes in zip(d.ctors, self.boxed(name)):
            types = [self.rtype(ft, name) for _, ft in fs]
            types = [f"Box<{t}>" if b else t for t, b in zip(types, boxes)]
            names = f" // {', '.join(f.text for f, _ in fs)}" if fs else ""
            out.append(f"        {rid(c.text)}{_parens(types)},{names}")
        out.append("    }")
        shapes = [(c.text, len(fs)) for c, fs in d.ctors]
        terms = [f"                Self::{rid(c)}{_parens(f'a{k}' for k in range(n))} => crate::rt::form({string(c)}, &["
                 f"{', '.join(f'crate::rt::Term::term(a{k})' for k in range(n))}]),"
                 for c, n in shapes]
        reads = [f"                ({string(c)}, {n}) => Some(Self::{rid(c)}"
                 f"{_parens(f'crate::rt::Arg::from_sx(&a[{k}])?' for k in range(n))}),"
                 for c, n in shapes]
        out += [f"    impl{generics(': crate::rt::Term')} crate::rt::Term for {me} {{",
                "        fn term(&self) -> String {", "            match self {", *terms, "            }",
                "        }", "    }",
                f"    impl{generics(': crate::rt::Arg')} crate::rt::Arg for {me} {{",
                "        fn from_sx(sx: &crate::rt::Sx) -> Option<Self> {",
                "            let (c, a) = sx.form()?;", "            match (c, a.len()) {", *reads,
                "                _ => None,", "            }", "        }", "    }"]
        methods = [m for (t, f, mutable) in self.accessors if t == name for m in self.read_field(name, f, mutable)]
        if methods:
            out += [f"    impl{generics()} {me} {{", *methods, "    }"]
        return out

    def read_field(self, name, f, mutable):
        """The method that reaches field f of a name value, or stops the run with err FIELD."""
        d = self.datas[name]
        ref = "&mut " if mutable else "&"
        arms, t = [], None
        for (c, fs), boxes in zip(d.ctors, self.boxed(name)):
            names = [x.text for x, _ in fs]
            if f in names:
                k = names.index(f)
                t, box = fs[k][1], boxes[k]
                parts = ", ".join("x" if j == k else "_" for j in range(len(fs)))
                arms.append(f"                Self::{rid(c.text)}({parts}) => {f'{ref}**x' if box else 'x'},")
            else:
                parts = "(..)" if fs else ""
                arms.append(f"                Self::{rid(c.text)}{parts} => crate::rt::no_field(node, "
                            f"{string(f'a {c.text} value has no field {f}')}),")
        return [f"        pub fn _{'m' if mutable else 'r'}_{f}({ref}self, node: crate::rt::Node) "
                f"-> {ref}{self.rtype(t, name)} {{", "            match self {", *arms, "            }", "        }"]

    def runtime(self):
        """B17-1's runtime: B17-0's, with places, data values and tuples, and arguments read as
        terms (D110)."""
        tuples = []
        for n in sorted(self.arities):
            ts = [f"A{k}" for k in range(n)]
            tuples += [
                f"    impl<{', '.join(t + ': Term' for t in ts)}> Term for ({', '.join(ts)}) {{",
                "        fn term(&self) -> String {",
                f"            form(\"tuple\", &[{', '.join(f'self.{k}.term()' for k in range(n))}])",
                "        }", "    }", "",
                f"    impl<{', '.join(t + ': Arg' for t in ts)}> Arg for ({', '.join(ts)}) {{",
                "        fn from_sx(sx: &Sx) -> Option<Self> {",
                f"            match sx.args(\"tuple\")? {{",
                f"                [{', '.join(f'a{k}' for k in range(n))}] => "
                f"Some(({', '.join(f'A{k}::from_sx(a{k})?' for k in range(n))})),",
                "                _ => None,", "            }", "        }", "    }", ""]
        return _RT_HEAD + _RT_PLACES + _RT_DRIVER + _RT_ARG_1 + _RT_TERM + _RT_TERM_1 + "\n".join(tuples) + "}\n"


# The runtime every emitted crate carries (D95, D96).
_RT_HEAD = r"""mod rt {
    //! Checked operations, which stop a run where b17c/interp.py stops it, and the driver,
    //! which prints the run's trace and outcome in interface 10's text form (D56, D96).
    use std::io::BufRead;
    use std::panic;

    /// How a run stops before it returns: §8's err, at a node, or a B17-0 panic.
    pub enum Stop {
        Err(&'static str, &'static str, String),
        Panic(&'static str),
    }

    #[cold]
    #[inline(never)]
    fn fail(reason: &'static str, node: &'static str, detail: String) -> ! {
        panic::panic_any(Stop::Err(reason, node, detail))
    }

    pub fn panic(message: &'static str) -> ! {
        panic::panic_any(Stop::Panic(message))
    }

    fn overflow(op: &str, a: i64, b: i64, exact: i128, node: &'static str) -> ! {
        fail("OVERFLOW", node, format!("({} {} {}) = {} leaves i64", op, a, b, exact))
    }

    pub fn add(a: i64, b: i64, node: &'static str) -> i64 {
        a.checked_add(b).unwrap_or_else(|| overflow("+", a, b, a as i128 + b as i128, node))
    }

    pub fn sub(a: i64, b: i64, node: &'static str) -> i64 {
        a.checked_sub(b).unwrap_or_else(|| overflow("-", a, b, a as i128 - b as i128, node))
    }

    pub fn mul(a: i64, b: i64, node: &'static str) -> i64 {
        a.checked_mul(b).unwrap_or_else(|| overflow("*", a, b, a as i128 * b as i128, node))
    }

    /// / and % truncate toward zero (D37), and fail on a zero divisor and on MIN by -1.
    fn divide(op: &str, a: i64, b: i64, r: Option<i64>, node: &'static str) -> i64 {
        if b == 0 {
            fail("DIV", node, format!("({} {} 0) divides by zero", op, a))
        }
        r.unwrap_or_else(|| fail("DIV", node, format!("({} {} -1) leaves i64", op, a)))
    }

    pub fn div(a: i64, b: i64, node: &'static str) -> i64 {
        divide("/", a, b, a.checked_div(b), node)
    }

    pub fn rem(a: i64, b: i64, node: &'static str) -> i64 {
        divide("%", a, b, a.checked_rem(b), node)
    }

    pub fn neg(a: i64, node: &'static str) -> i64 {
        a.checked_neg().unwrap_or_else(|| fail("OVERFLOW", node, format!("(neg {}) leaves i64", a)))
    }

    pub fn idx<T: Copy>(s: &[T], i: i64, node: &'static str) -> T {
        if i < 0 || i >= s.len() as i64 {
            fail("BOUNDS", node, format!("(idx s {}) on a sequence of length {}", i, s.len()))
        }
        s[i as usize]
    }

    /// (set-idx v i e) as a method, so that i and e may read v. They're evaluated before
    /// the index is checked (D56).
    pub trait SetIdx<T> {
        fn set_idx(&mut self, i: i64, e: T, name: &'static str, node: &'static str);
    }

    impl<T> SetIdx<T> for Vec<T> {
        fn set_idx(&mut self, i: i64, e: T, name: &'static str, node: &'static str) {
            if i < 0 || i >= self.len() as i64 {
                fail("BOUNDS", node, format!("(set-idx {} {} ...) on a vector of length {}", name, i, self.len()))
            }
            self[i as usize] = e;
        }
    }

    /// Elements are computed in order, so the first to fail is the interpreter's, and the
    /// vector grows with them, so no allocation runs ahead of the elements computed.
    pub fn seq_build<T>(n: i64, node: &'static str, mut f: impl FnMut(i64) -> T) -> Vec<T> {
        if n < 0 {
            fail("BOUNDS", node, format!("(seq-build {} ...) has a negative length", n))
        }
        let mut out = Vec::new();
        for i in 0..n {
            out.push(f(i));
        }
        out
    }

    pub fn print(v: i64) {
        println!("print {}", v);
    }

"""
_RT_DRIVER = r"""    // The driver.

    /// A def with its arguments read, ready to run, giving its results as B17-0 terms.
    pub type Run = Box<dyn FnOnce() -> Vec<String>>;

    /// A run's stack: room for D59's 1,000 nested calls, at up to 1 MiB a frame (D96). It's
    /// reserved, not used, until the run needs it.
    const STACK: usize = 1 << 30;

    /// BINARY NAME ARG... runs NAME once and exits as interp.py does: 0 on ok, 1 on any
    /// other outcome, 2 when the run can't start. BINARY --batch reads one NAME ARG... per
    /// line of stdin and prints each run's lines, a refusal as a "refused: why" line.
    pub fn main(dispatch: fn(&str, &[String]) -> Result<Run, String>) -> i32 {
        panic::set_hook(Box::new(|info| {
            if info.payload().downcast_ref::<Stop>().is_none() {
                eprintln!("internal error: {}", info);
            }
        }));
        let mut argv = Vec::new();
        for arg in std::env::args_os().skip(1) {
            match arg.into_string() {
                Ok(arg) => argv.push(arg),
                Err(arg) => {
                    eprintln!("argument {:?} isn't UTF-8", arg);
                    return 2;
                }
            }
        }
        let runs = std::thread::Builder::new().stack_size(STACK).spawn(move || drive(dispatch, argv));
        match runs.map(|t| t.join()) {
            Ok(Ok(code)) => code,
            Ok(Err(_)) => 3, // the panic hook has said why
            Err(e) => {
                eprintln!("internal error: no thread to run on: {}", e);
                3
            }
        }
    }

    fn drive(dispatch: fn(&str, &[String]) -> Result<Run, String>, argv: Vec<String>) -> i32 {
        if argv.len() == 1 && argv[0] == "--batch" {
            for line in std::io::stdin().lock().lines() {
                match line.map_err(|e| e.to_string()).and_then(|l| words(&l)).and_then(|w| start(dispatch, &w)) {
                    Ok(run) => {
                        finish(run);
                    }
                    Err(why) => println!("refused: {}", why),
                }
            }
            return 0;
        }
        match start(dispatch, &argv) {
            Ok(run) => finish(run),
            Err(why) => {
                eprintln!("{}", why);
                2
            }
        }
    }

    fn start(dispatch: fn(&str, &[String]) -> Result<Run, String>, words: &[String]) -> Result<Run, String> {
        match words.split_first() {
            Some((name, args)) => dispatch(name, args),
            None => Err("usage: BINARY NAME ARG... | BINARY --batch".to_string()),
        }
    }

    /// Run to the end, print the outcome line, and give the exit code.
    fn finish(run: Run) -> i32 {
        match panic::catch_unwind(panic::AssertUnwindSafe(run)) {
            Ok(results) => {
                let mut line = String::from("ok");
                for r in results {
                    line.push(' ');
                    line.push_str(&r);
                }
                println!("{}", line);
                0
            }
            Err(payload) => match payload.downcast::<Stop>() {
                Ok(stop) => {
                    match *stop {
                        Stop::Err(reason, node, detail) => println!("err {} at {}: {}", reason, node, detail),
                        Stop::Panic(message) => {
                            println!("panic \"{}\"", message.replace('\\', "\\\\").replace('"', "\\\""))
                        }
                    }
                    1
                }
                Err(_) => {
                    println!("internal error");
                    3
                }
            },
        }
    }

    /// A batch line's words: the def's name, then each argument, which may be in parentheses.
    fn words(line: &str) -> Result<Vec<String>, String> {
        let (mut out, mut word, mut depth) = (Vec::new(), String::new(), 0usize);
        for c in line.chars() {
            match c {
                ' ' | '\t' | '\r' if depth == 0 => {
                    if !word.is_empty() {
                        out.push(std::mem::take(&mut word));
                    }
                }
                '(' | ')' => {
                    if c == '(' {
                        depth += 1;
                    } else if depth == 0 {
                        return Err(format!("unbalanced ) in {}", line));
                    } else {
                        depth -= 1;
                    }
                    word.push(c);
                }
                _ => word.push(c),
            }
        }
        if depth != 0 {
            return Err(format!("unbalanced ( in {}", line));
        }
        if !word.is_empty() {
            out.push(word);
        }
        Ok(out)
    }

    pub fn arity(name: &str, args: &[String], n: usize) -> Result<(), String> {
        if args.len() == n {
            return Ok(());
        }
        Err(format!("{} takes {} argument{}, got {}", name, n, if n == 1 { "" } else { "s" }, args.len()))
    }

"""
_RT_ARG = r"""    /// Argument k, read as a value of its parameter's type: a canonical B17-0 integer,
    /// true or false, or a (seq-lit ...) of them (D96).
    pub fn arg<T: Arg>(args: &[String], k: usize, param: &str, ty: &str) -> Result<T, String> {
        let text = args[k].trim_matches([' ', '\t', '\n', '\r']); // B17-0's whitespace, and no other (D48)
        T::read(text).ok_or_else(|| format!("argument {}: {} is not a value of type {}", param, args[k], ty))
    }

    pub trait Arg: Sized {
        fn read(text: &str) -> Option<Self>;
    }

    impl Arg for i64 {
        fn read(text: &str) -> Option<i64> {
            let digits = text.strip_prefix('-').unwrap_or(text);
            let canonical = !digits.is_empty()
                && digits.bytes().all(|b| b.is_ascii_digit())
                && (digits == "0" || !digits.starts_with('0'))
                && text != "-0";
            if canonical {
                text.parse().ok()
            } else {
                None
            }
        }
    }

    impl Arg for bool {
        fn read(text: &str) -> Option<bool> {
            match text {
                "true" => Some(true),
                "false" => Some(false),
                _ => None,
            }
        }
    }

    impl<T: Arg> Arg for Vec<T> {
        fn read(text: &str) -> Option<Vec<T>> {
            let inner = text.strip_prefix('(')?.strip_suffix(')')?;
            let mut items = inner.split([' ', '\t', '\n', '\r']).filter(|w| !w.is_empty());
            if items.next()? != "seq-lit" {
                return None;
            }
            items.map(T::read).collect()
        }
    }

"""
_RT_TERM = r"""    pub trait Term {
        fn term(&self) -> String;
    }

    impl Term for i64 {
        fn term(&self) -> String {
            self.to_string()
        }
    }

    impl Term for bool {
        fn term(&self) -> String {
            self.to_string()
        }
    }

    impl<T: Term> Term for Vec<T> {
        fn term(&self) -> String {
            let mut s = String::from("(seq-lit");
            for x in self {
                s.push(' ');
                s.push_str(&x.term());
            }
            s + ")"
        }
    }

    pub fn term<T: Term>(v: &T) -> String {
        v.term()
    }
"""
RUNTIME = _RT_HEAD + _RT_DRIVER + _RT_ARG + _RT_TERM + "}\n"
# B17-1's additions to the runtime (D110). The crate's runtime is B17-0's with these spliced
# in, its argument reader replaced, and Term and Arg for each tuple arity the crate uses.
_RT_PLACES = r"""    // B17-1's places and fields (docs/b17-1.md §5, §8).

    /// A node's ID, as the data module's field readers take it. There, str may name a data type.
    pub type Node = &'static str;

    /// Element i of s, read where it is, as a moving value is (§5 rule 3).
    pub fn at<'a, T>(s: &'a [T], i: i64, node: &'static str) -> &'a T {
        if i < 0 || i >= s.len() as i64 {
            fail("BOUNDS", node, format!("(idx s {}) on a sequence of length {}", i, s.len()))
        }
        &s[i as usize]
    }

    /// Element i of the vector at a place, to change it where it is. BOUNDS names the place,
    /// as interp.py does.
    pub fn at_mut<'a, T>(v: &'a mut [T], i: i64, place: &'static str, node: &'static str) -> &'a mut T {
        if i < 0 || i >= v.len() as i64 {
            fail("BOUNDS", node, format!("(idx {} {}) on a vector of length {}", place, i, v.len()))
        }
        &mut v[i as usize]
    }

    /// A field read on a value whose constructor lacks the field.
    pub fn no_field(node: &'static str, detail: &'static str) -> ! {
        fail("FIELD", node, detail.to_string())
    }

"""
_RT_ARG_1 = r"""    /// Argument k, read as a value of its parameter's type, as interface 10 writes values: a
    /// canonical integer, true or false, or a form such as (seq-lit 1 2), (tuple 1 false)
    /// or (some 3) (D96, D110).
    pub fn arg<T: Arg>(args: &[String], k: usize, param: &str, ty: &str) -> Result<T, String> {
        Sx::read(&args[k])
            .and_then(|sx| T::from_sx(&sx))
            .ok_or_else(|| format!("argument {}: {} is not a value of type {}", param, args[k], ty))
    }

    /// A term: an atom, or a form in parentheses.
    pub enum Sx {
        Atom(String),
        Form(Vec<Sx>),
    }

    impl Sx {
        /// text as one term, read as the interpreter reads it: only B17's four whitespace
        /// characters around and between its parts (D48), whitespace between a list's
        /// elements (D49), and lists at most 128 deep (D55).
        fn read(text: &str) -> Option<Sx> {
            let mut open = vec![Vec::new()];
            let (mut atom, mut separated) = (String::new(), true);
            for c in text.chars().chain([' ']) {
                if matches!(c, ' ' | '\t' | '\n' | '\r' | '(' | ')') && !atom.is_empty() {
                    open.last_mut()?.push(Sx::Atom(std::mem::take(&mut atom)));
                    separated = false;
                }
                match c {
                    ' ' | '\t' | '\n' | '\r' => separated = true,
                    ')' => {
                        let form = Sx::Form(open.pop()?);
                        open.last_mut()?.push(form);
                        separated = false;
                    }
                    _ if atom.is_empty() && !separated => return None,
                    '(' if open.len() > 128 => return None,
                    '(' => {
                        open.push(Vec::new());
                        separated = true;
                    }
                    _ => atom.push(c),
                }
            }
            match (open.pop(), open.is_empty()) {
                (Some(mut top), true) if top.len() == 1 => top.pop(),
                _ => None,
            }
        }

        /// A form's head and arguments.
        pub fn form(&self) -> Option<(&str, &[Sx])> {
            match self {
                Sx::Form(items) => match items.split_first() {
                    Some((Sx::Atom(head), rest)) => Some((head.as_str(), rest)),
                    _ => None,
                },
                Sx::Atom(_) => None,
            }
        }

        /// The arguments of a form whose head is head.
        pub fn args(&self, head: &str) -> Option<&[Sx]> {
            self.form().filter(|(h, _)| *h == head).map(|(_, rest)| rest)
        }
    }

    pub trait Arg: Sized {
        fn from_sx(sx: &Sx) -> Option<Self>;
    }

    impl Arg for i64 {
        fn from_sx(sx: &Sx) -> Option<i64> {
            let text = match sx {
                Sx::Atom(text) => text.as_str(),
                Sx::Form(_) => return None,
            };
            let digits = text.strip_prefix('-').unwrap_or(text);
            let canonical = !digits.is_empty()
                && digits.bytes().all(|b| b.is_ascii_digit())
                && (digits == "0" || !digits.starts_with('0'))
                && text != "-0";
            if canonical {
                text.parse().ok()
            } else {
                None
            }
        }
    }

    impl Arg for bool {
        fn from_sx(sx: &Sx) -> Option<bool> {
            match sx {
                Sx::Atom(text) if text == "true" => Some(true),
                Sx::Atom(text) if text == "false" => Some(false),
                _ => None,
            }
        }
    }

    impl<T: Arg> Arg for Vec<T> {
        fn from_sx(sx: &Sx) -> Option<Vec<T>> {
            sx.args("seq-lit")?.iter().map(T::from_sx).collect()
        }
    }

    impl<T: Arg> Arg for Box<T> {
        fn from_sx(sx: &Sx) -> Option<Box<T>> {
            T::from_sx(sx).map(Box::new)
        }
    }

"""
_RT_TERM_1 = r"""
    impl<T: Term> Term for Box<T> {
        fn term(&self) -> String {
            (**self).term()
        }
    }

    /// (head part ...), as interface 10 writes tuples and data values.
    pub fn form(head: &str, parts: &[String]) -> String {
        let mut s = format!("({}", head);
        for p in parts {
            s.push(' ');
            s.push_str(p);
        }
        s + ")"
    }

"""


# Building and running.

def toolchain(rustc="rustc"):
    """The backend's fields for the trusted base report (D25, D97): rustc's release, commit
    and LLVM, the target triple, which is rustc's host since the build is native, and the
    flags every build uses."""
    lines = subprocess.run([rustc, "-vV"], capture_output=True, text=True, check=True).stdout.splitlines()
    info = dict(line.split(": ", 1) for line in lines[1:] if ": " in line)
    return {"rustc": lines[0], "commit": info.get("commit-hash"), "llvm": info.get("LLVM version"),
            "target": info["host"], "flags": list(FLAGS)}


def build(source, out, rustc="rustc", flags=()):
    """Compile emitted source into the executable out (D18). It's compiled and linked in a
    temporary directory, by relative paths and under fixed names, so no path in the binary
    depends on where it was built, and the same source and toolchain give the same bytes (D97)."""
    out = Path(out).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.rs").write_text(source, encoding="utf-8")
        r = subprocess.run([rustc, *FLAGS, *flags, "-o", "main", "main.rs"], capture_output=True, text=True, cwd=tmp)
        if r.returncode:
            raise BuildError(r.stderr)
        shutil.move(Path(tmp) / "main", out)
    return out


def cached(source, rustc="rustc", cache=None):
    """The binary for source, built once per source and toolchain under cache (CACHE by default)."""
    key = hashlib.sha256(json.dumps([source, toolchain(rustc)]).encode()).hexdigest()
    binary = Path(cache or CACHE) / key[:32] / "main"
    if not binary.exists():
        binary.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=binary.parent, prefix="main.", delete=False) as part:
            pass  # a name no other build uses
        build(source, part.name, rustc)
        os.replace(part.name, binary)  # whole, or not at all
    return binary


def batch(binary, runs, timeout=600):
    """Run each (name, [argument term, ...]) of runs in one process: the text interface 10
    gives each run, as text_of() writes it, or "refused: why"."""
    stdin = "".join(" ".join([name, *args]) + "\n" for name, args in runs)
    r = subprocess.run([str(binary), "--batch"], input=stdin, capture_output=True, encoding="utf-8",
                       timeout=timeout)
    outs, lines = [], []
    for line in r.stdout.split("\n")[:-1]:  # only \n ends a line: a panic's string may hold U+2028 (D50)
        lines.append(line)
        if not line.startswith("print "):
            outs.append("\n".join(lines))
            lines = []
    if r.returncode or lines or len(outs) != len(runs):
        raise RuntimeError(f"the batch stopped after {len(outs)} of {len(runs)} runs (exit {r.returncode}):\n"
                           f"{r.stderr[-2000:]}")
    return outs


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_report(path, module):
    """The trusted base report at path, which must be module's, or a new one. WP5's
    verify.py writes the rest of a report, so one it wrote is kept and extended."""
    path, digest = Path(path), sha256(canonical(module))
    data = json.loads(path.read_text()) if path.exists() else {"module": module.items[1].text, "input_sha256": digest}
    if data.get("input_sha256") != digest:
        raise ValueError(f"{path} is the report of a different input")
    return data


def add_report(path, module, source, binary, rustc="rustc"):
    """Write the backend's fields into the module's trusted base report at path (D25, D97)."""
    data = read_report(path, module)
    data["backend"] = {**toolchain(rustc), "rust_sha256": sha256(source.encode()),
                       "binary_sha256": sha256(Path(binary).read_bytes())}
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def main(argv):
    usage = ("usage: uv run --no-project b17c/rust.py [--subset 1] [-o BINARY [--report JSON]] FILE\n"
             "       uv run --no-project b17c/rust.py [--subset 1] --run FILE NAME ARG...")
    subset = 0
    if argv[:1] == ["--subset"] and argv[1:2] in (["0"], ["1"]):
        subset, argv = int(argv[1]), argv[2:]
    out = report = None
    running = bool(argv) and argv[0] == "--run"
    if running:
        argv = argv[1:]
    while not running and argv and argv[0] in ("-o", "--report") and len(argv) > 1:
        if argv[0] == "-o":
            out = argv[1]
        else:
            report = argv[1]
        argv = argv[2:]
    if not argv or (not running and len(argv) != 1) or (running and len(argv) < 2) or (report and not out):
        print(usage, file=sys.stderr)
        return 2
    path = argv[0]
    try:
        module = parse(Path(path).read_bytes(), subset)
        source = emit(module, subset)
    except OSError as e:
        print(f"{path}: {e.strerror}", file=sys.stderr)
        return 2
    except ParseError as e:
        print(f"{path}:{e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"{path}: {e}", file=sys.stderr)
        return 2
    try:
        if running:
            name, args = argv[1], []
            for k, expr in enumerate(argv[2:], 1):
                try:
                    args.append(interp._term(interp.value(module, expr, subset)))
                except ParseError as e:
                    raise ValueError(f"argument {k}:{e}") from None
            r = subprocess.run([str(cached(source)), name, *args], capture_output=True, encoding="utf-8",
                               errors="replace")
            sys.stdout.write(r.stdout)
            if r.returncode == 2:
                print(f"{path}: {r.stderr.strip()}", file=sys.stderr)
            else:
                sys.stderr.write(r.stderr)
            return r.returncode
        if out is None:
            print(source)
            return 0
        if report:
            read_report(report, module)  # before building, so a wrong report leaves out alone
        build(source, out)
        if report:
            add_report(report, module, source, out)
        return 0
    except ValueError as e:
        print(f"{path}: {e}", file=sys.stderr)
        return 2
    except (BuildError, OSError, subprocess.CalledProcessError) as e:
        print(f"{path}: the build failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
