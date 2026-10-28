"""WP7's backend: B17-0 to safe Rust (D18, D95-D97).

    uv run --no-project b17c/rust.py FILE                              # the emitted Rust
    uv run --no-project b17c/rust.py -o BINARY [--report JSON] FILE    # built with rustc
    uv run --no-project b17c/rust.py --run FILE NAME ARG...            # built, then run like interp.py

emit() turns a module that passes tier 0 (WP3) into the source of one Rust crate. The
crate forbids unsafe code and erases ghost code. Every runtime goal of §9 is checked
explicitly: arithmetic, division and indexing that would leave §8 stop the run with the
interpreter's err outcome, at the same node (D56). The crate's main runs one def on its
arguments and prints the run's trace and outcome in interface 10's text form, as
interp.py does, so the two can be compared line for line. That comparison is WP7's
differential test (test_rust.py).

--run builds into .b17c/rust/, keyed by the emitted source and the toolchain. Each ARG is
a closed B17-0 expression, evaluated as interp.py evaluates it, and the run exits as
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
GHOST = {"assert", "ghost-let", "ghost-let-mut", "ghost-set"}
# Lints that valid B17-0 programs trigger: a helper the module doesn't use, a local it never
# reads or a let-mut it never sets, (while true ...), recursion a proof bounds, a comparison
# with an i64 limit, and a name with two underscores in a row (D95).
ALLOW = ("dead_code, unused_variables, unused_mut, unused_assignments, while_true, unconditional_recursion, "
         "unused_comparisons, non_snake_case")


class BuildError(Exception):
    """rustc rejected emitted code. The module passed tier 0, so this is a backend bug (D18)."""


def emit(module):
    """module, which must pass tier 0, as the source of one Rust crate (D95). Text that
    doesn't parse raises ParseError. A module that fails tier 0 raises ValueError, and so
    does a call to a spec with no def, in code that can run, since a binary can't make
    that call (D96)."""
    if not isinstance(module, Form):
        module = parse(module)
    try:
        typed = tier0_types(module)  # every expression's type, as WP3 gives it
    except ValueError as e:
        found = str(e).splitlines()
        more = f" (and {len(found) - 1} more)" if len(found) > 1 else ""
        raise ValueError(f"the module doesn't pass tier 0: {found[0]}{more}") from None
    return _Emitter(module, typed).crate()


def rid(name):
    """A B17-0 name as a Rust identifier (D95): itself, unless Rust reserves it. B17-0
    names never start with _, so _crate, _self and _super can't clash with one."""
    if name in UNRAW:
        return "_" + name
    return "r#" + name if name in KEYWORDS else name


def rust_type(t):
    if t[0] == "vec":
        return f"Vec<{rust_type(t[1])}>"
    if t[0] == "slice":
        return f"&[{rust_type(t[1])}]"
    return t[0]


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
    """A type form as check.py writes types: ("bool",), ("i64",), ("vec", T) or ("slice", T)."""
    if isinstance(t, Sym):
        return (t.text,)
    if t.items[0].text == "ref":
        return ("slice", _type(t.items[1].items[1]))
    return (t.items[0].text, _type(t.items[1]))


def _args(item, head):
    """The arguments of item's clauses with this head, in order."""
    return [a for c in item.items[2:] if _head(c) == head for a in c.items[1:]]


def _ends(s):
    """No path through statement s continues normally: §7's ⊥, where every while may end (D77)."""
    h = _head(s)
    if h in ("return", "panic"):
        return True
    if h == "block":
        return any(_ends(c) for c in s.items[1:])
    return h == "if" and _ends(s.items[2]) and _ends(s.items[3])


def _untyped(x):
    """Rust would give x no type of its own: a literal, or an if whose branches are literals."""
    return isinstance(x, Int) or (_head(x) == "if" and _untyped(x.items[2]) and _untyped(x.items[3]))


class _Emitter:
    def __init__(self, module, typed):
        self.module, self.typed = module, typed
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
        uses = [f"    use crate::rt{p};" for p, used in (("", "rt"), ("::SetIdx", "SetIdx")) if used in self.uses]
        arms = [line for d in defs for line in self.arm(d)]
        return "\n".join([
            f"// Emitted by b17c's Rust backend (WP7, D95) from module {name}. Emit it again rather",
            f"// than editing it. The module's canonical bytes have SHA-256 {digest}.",
            "#![forbid(unsafe_code)]",
            f"#![allow({ALLOW})]",
            "",
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
            RUNTIME,
        ])

    # Items.

    def fn(self, d):
        name = d.items[1].text
        spec = self.specs[name]
        params, results = _args(spec, "params"), [_type(p.items[1]) for p in _args(spec, "returns")]
        sig = ", ".join(f"{rid(p.items[0].text)}: {rust_type(_type(p.items[1]))}" for p in params)
        ret = "" if not results else f" -> {self.tuple(map(rust_type, results))}"
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
            lines.append(f"            let a{k}: {rust_type(owned)} = rt::arg(args, {k}, "
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
        if h in ("let", "let-mut"):
            mut = "mut " if h == "let-mut" else ""
            if isinstance(it[1], Form):  # a call's results, one name each (D43, D74)
                names = [mut + rid(p.items[0].text) for p in it[1].items]
                types = [rust_type(_type(p.items[1])) for p in it[1].items]
                return [f"{pad}let {self.tuple(names)}: {self.tuple(types)} = {self.call(it[2])};"]
            return [f"{pad}let {mut}{rid(it[1].text)}: {rust_type(_type(it[2]))} = {self.top(it[3])};"]
        if h == "set":
            return [f"{pad}{rid(it[1].text)} = {self.top(it[2])};"]
        if h == "set-idx":  # the index, then the value, then the check (D56)
            self.uses.add("SetIdx")
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

    # Expressions. Each has the type WP3 gives it, which fixes the element type a (vec-new)
    # leaves open (D70): its destination's, or i64 when nothing gives one.

    def top(self, x):
        """x's code where nothing around it needs parentheses: an operand of a statement, or an argument."""
        code, wrapped = self.expr(x)
        return code[1:-1] if wrapped else code

    def expr(self, x, force=False):
        """(Rust code, whether it's an operator this added parentheses around). force gives a
        literal the type i64, where Rust would give it none of its own."""
        if isinstance(x, Int):  # rustc reads -9223372036854775808 as i64::MIN, as B17-0 does
            return f"{x.value}{'i64' if force else ''}", False
        if isinstance(x, Sym):
            return (x.text if x.text in ("true", "false") else rid(x.text)), False
        h, it = _head(x), x.items
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
            i, t = it[2].items[1].items[0].text, rust_type(self.typed[id(x)][1])
            return (f"rt::seq_build({self.top(it[1])}, {self.node(x)}, |{rid(i)}: i64| -> {t} "
                    f"{{ {self.top(it[2].items[2])} }})"), False
        raise AssertionError(f"not runtime code: {_print(x)}")

    def sequence(self, x, elem):
        """The sequence operand of len or idx. A (vec-new) there has no destination to give
        it a type, so it gets elem: the element type tier 0 gave idx, or i64 under len."""
        if _head(x) == "vec-new":
            return f"Vec::<{rust_type(elem)}>::new()"
        return self.expr(x)[0]


# The runtime every emitted crate carries (D95, D96).
RUNTIME = r"""mod rt {
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

    // The driver.

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

    /// Argument k, read as a value of its parameter's type: a canonical B17-0 integer,
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

    pub trait Term {
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
    usage = ("usage: uv run --no-project b17c/rust.py [-o BINARY [--report JSON]] FILE\n"
             "       uv run --no-project b17c/rust.py --run FILE NAME ARG...")
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
        module = parse(Path(path).read_bytes())
        source = emit(module)
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
                    args.append(interp._term(interp.value(module, expr)))
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
