"""B17-0's tier 0 checker (docs/b17-0.md §2-§7 and §9's tier 0 table; D33-D45, D51, D53, D66-D78).

    uv run --no-project b17c/check.py FILE

parses and checks FILE and prints `FILE:LINE:COL: CODE: message` for each diagnostic,
exiting 1 if there are any. A parse error prints the same way, as E-PARSE-001.

check(module) returns the diagnostics in position order; an empty list means the module
passes tier 0. Proof goals are WP5's: this checker generates none, but types(module) gives
WP5 the type it computes for each expression.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

from hashing import CORE, HashError, hashes
from syntax import Form, Int, ParseError, Sym, _head, parse

MIN, MAX = -2**63, 2**63 - 1
BOOL, I64, INT = ("bool",), ("i64",), ("int",)
ERR = ("error",)  # the type of something already reported: compatible with everything, so errors don't cascade
ANY = ("any",)    # the element type of an empty seq-lit or a vec-new that its context doesn't fix
COLLECTIONS = ("vec", "slice", "seq", "multiset")
SEQUENCES = ("vec", "slice", "seq")  # each is a (seq T) in ghost code (§3)
GHOST_ONLY = {"forall", "exists", "seq-lit", "take", "drop", "concat", "last", "contains", "multiset", "msum",
              "occurrences"}
RUNTIME_STATEMENTS = {"let", "let-mut", "set", "set-idx", "push", "panic", "print"}
CORE_NAMES = {it.items[1].text for it in CORE.items[3:]}


@dataclass(frozen=True, order=True)
class Diagnostic:
    line: int
    col: int
    code: str
    message: str
    node: object = field(default=None, compare=False, repr=False)  # the form it's about, for WP6's node IDs

    def __str__(self):
        return f"{self.line}:{self.col}: {self.code}: {self.message}"


def check(module):
    """module's tier 0 diagnostics, in position order; none means it passes tier 0."""
    return sorted(_Checker(module).run())


def types(module):
    """The type tier 0 gives each expression of module and of the core library, by node id,
    for WP5's goals and WP7's backend. Raises ValueError, listing the diagnostics, if module
    fails tier 0. The core library is typed on its own, as check() leaves it, since its
    binders, such as sorted's i and j, may share a name with an item of module (§2)."""
    c, core = _Checker(module), _Checker(CORE)
    if diags := sorted(c.run()) or sorted(core.run(core=True)):
        raise ValueError("\n".join(map(str, diags)))
    return core.types | c.types


def show(t):
    if t in (BOOL, I64, INT):
        return t[0]
    if t == ERR:
        return "an ill-typed value"
    if t == ANY:
        return "?"
    if t[0] == "slice":
        return f"(ref (slice {show(t[1])}))"
    return f"({t[0]} {show(t[1])})"


def _args(item, head):
    """The arguments of item's clauses with this head, in order."""
    return [a for c in item.items[2:] if _head(c) == head for a in c.items[1:]]


def _elem(t):
    return t[1] if t[0] in COLLECTIONS else None


def join(a, b):
    """The least type both a and b convert to in ghost code (§3's subtyping), or None."""
    if a == ERR or b == ERR:
        return ERR
    if a == b or b == ANY:
        return a
    if a == ANY:
        return b
    if a in (I64, INT) and b in (I64, INT):
        return INT
    if a[0] in SEQUENCES and b[0] in SEQUENCES:
        e = join(a[1], b[1])
        return None if e is None or e[0] in COLLECTIONS else ("seq", e)
    if a[0] == b[0] and a[0] in ("vec", "slice", "multiset") and ANY in (a[1], b[1]):
        return (a[0], a[1] if b[1] == ANY else b[1])
    return None  # D70: (multiset T) has no subtyping


def sub(t, u):
    """t <: u in ghost code (§3)."""
    if ERR in (t, u) or ANY in (t, u) or t == u or (t == I64 and u == INT):
        return True
    if t[0] in SEQUENCES and u[0] == "seq":
        return sub(t[1], u[1])
    if t[0] == u[0] and t[0] in ("vec", "slice", "multiset"):
        return ANY in (t[1], u[1]) or t[1] == u[1]
    return False


def same(t, u):
    """t and u are the same type, as runtime code needs: it has no subtyping (D34)."""
    if ERR in (t, u) or t == u:
        return True
    return t[0] == u[0] and t[0] in COLLECTIONS and (ANY in (t[1], u[1]) or t[1] == u[1])


@dataclass
class _Item:
    kind: str                     # spec, ghost-fn or lemma; a def is checked with its spec
    name: str
    form: Form
    params: list = field(default_factory=list)   # [(Sym, type)]
    results: list = field(default_factory=list)  # a spec's [(Sym, type)]
    result: tuple = None                         # a ghost-fn's type
    effects: set = field(default_factory=set)    # a spec's
    defn: Form = None                            # the def that implements a spec

    def decreases(self):
        source = self.defn if self.kind == "spec" else self.form
        return None if source is None else next(iter(_args(source, "decreases")), None)


@dataclass
class _Bind:
    type: tuple
    kind: str             # parameter, result, local, ghost local or binder
    mutable: bool = False
    ghost: bool = False


class _Checker:
    def __init__(self, module):
        self.module = module
        self.diags = set()
        self.items = {}      # name -> _Item, the core library's included
        self.edges = []      # (caller, callee, call node), for E-TERM
        self.item = None     # the item being checked, and its state:
        self.scopes = []     # [{name: _Bind}], innermost last
        self.names = set()   # parameter and local names declared in the item (D41)
        self.moves = {}      # runtime vector variable -> where it moved; absent while live (§5)
        self.effects = []    # (effect, node) of the def body (§6)
        self.quiet = set()   # vectors repeated in one call or return, already reported (E-OWN-005)
        self.reported = set()  # moved vectors already reported used (E-OWN-001), so each is reported once
        self.defs = set()      # the names of the module's defs
        self.clashes = set()   # names declared wrongly: reported once, then never checked where used (D78)
        self.types = {}        # id(expression) -> its type, for WP5

    def run(self, core=False):
        """The diagnostics; with core, the core library's items are checked too, for their types."""
        self.collect()
        for item in [i for n, i in self.items.items() if core or n not in CORE_NAMES]:
            self.item, self.names, self.moves, self.effects, self.reported = item, set(), {}, [], set()
            {"spec": self.check_spec, "ghost-fn": self.check_ghost_fn, "lemma": self.check_lemma}[item.kind](item)
        self.recursion()
        if not self.diags:  # D45's rule is defined once the rest of tier 0 passes
            self.duplicates()
        return self.diags

    def duplicates(self):
        """D45: no two specs share a spec hash."""
        try:
            hashes(self.module)
        except HashError as e:
            specs = sorted((self.items[n].form.items[1].pos, n) for n in e.names if n in self.items)
            if e.code == "E-TYPE-002" and len(specs) == 2:  # placed at the later spec, as the module reads
                (_, first), (_, later) = specs
                self.report(e.code, self.items[later].form.items[1],
                            f"spec '{later}' is identical to '{first}' up to names (D45)")
            else:
                self.report(e.code, self.module, e.reason)

    def report(self, code, node, message):
        self.diags.add(Diagnostic(node.pos[0], node.pos[1], code, message, node))

    # Items and names (§2).

    def collect(self):
        for it in CORE.items[3:]:
            self.items[it.items[1].text] = _Item(it.items[0].text, it.items[1].text, it)
        defs = {}
        for it in self.module.items[3:] if self.module is not CORE else ():  # the core library itself
            kind, name = it.items[0].text, it.items[1]
            if name.text in CORE_NAMES:
                if name.text not in self.clashes:  # once for a spec and its def
                    self.report("E-TYPE-002", name, f"'{name.text}' is a core library name (D51)")
                self.clashes.add(name.text)
            elif (defs if kind == "def" else self.items).get(name.text) is not None:
                self.report("E-TYPE-002", name, f"'{name.text}' is already declared in this module")
                self.clashes.add(name.text)
            elif kind == "def":
                defs[name.text] = it
            else:
                self.items[name.text] = _Item(kind, name.text, it)
        for name, d in defs.items():
            spec = self.items.get(name)
            if name in self.clashes:
                continue  # its spec was the declaration already reported
            if spec is None or spec.kind != "spec":
                why = "" if spec is None else f"; '{name}' is a {spec.kind}"
                self.report("E-TYPE-002", d.items[1], f"def '{name}' has no spec to implement (D39){why}")
                self.clashes.add(name)
            else:
                spec.defn = d
        self.defs = set(defs)
        for item in self.items.values():
            self.signature(item, item.name in CORE_NAMES)

    def signature(self, item, core):
        it, seen = item.form, set()

        def bind(p, runtime, slices):
            if not core:
                self.unique(p.items[0], seen)
            return p.items[0], self.type_of(p.items[1], runtime, slices)

        if item.kind == "spec":
            item.params = [bind(p, True, True) for p in _args(it, "params")]
            item.results = [bind(p, True, False) for p in _args(it, "returns")]
            item.effects = {e.text for e in _args(it, "effects")}
        elif item.kind == "ghost-fn":
            item.params = [bind(p, False, False) for p in it.items[2].items]
            item.result = self.type_of(it.items[3], False, False)
        else:
            item.params = [bind(p, False, False) for p in _args(it, "params")]

    def unique(self, sym, seen):
        """A parameter or local name: unique within its item, and not an item's name (D41)."""
        if sym.text in seen:
            self.report("E-TYPE-002", sym, f"'{sym.text}' is already declared in this item (D41)")
        elif sym.text in self.items or sym.text in self.defs:
            self.report("E-TYPE-002", sym, f"'{sym.text}' is an item's name, so no parameter or local may take it (D41)")
        seen.add(sym.text)

    def type_of(self, node, runtime, slices):
        """The type node denotes, once it's checked to be allowed here (§3, D68); ERR if it isn't."""
        if isinstance(node, Sym):
            if node.text == "int" and runtime:
                self.report("E-GHOST-002", node, "int is a ghost type; runtime code uses i64 (§3)")
                return ERR
            return {"bool": BOOL, "i64": I64, "int": INT}[node.text]
        head = node.items[0].text
        inner = node.items[1].items[1] if head == "ref" else node.items[1]
        allowed = ("bool", "i64") if head in ("vec", "ref") else ("bool", "i64", "int")
        if not isinstance(inner, Sym) or inner.text not in allowed:
            self.report("E-TYPE-001", inner, f"a {'vector or slice' if head in ('vec', 'ref') else head} holds "
                                             f"{' or '.join(allowed)}; B17-0 has no nested collections (§3, §11)")
            return ERR
        if head in ("seq", "multiset") and runtime:  # only a well-formed type is a ghost type (D68)
            self.report("E-GHOST-002", node, f"({head} T) is a ghost type (§3)")
            return ERR
        elem = {"bool": BOOL, "i64": I64, "int": INT}[inner.text]
        if head == "ref":
            if not slices:
                self.report("E-OWN-002", node, "only a spec's parameter can be a slice: slices can't be stored, "
                                               "returned or put in a let (§5, D69)")
                return ERR
            return ("slice", elem)
        return (head, elem)

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def declare(self, sym, bind):
        """Bind a local in the innermost scope; it's visible to the end of that scope (D66). A
        name already declared keeps the binding in scope, so its uses don't report again (D78)."""
        self.unique(sym, self.names)
        if self.lookup(sym.text) is None:
            self.scopes[-1][sym.text] = bind
            self.moves.pop(sym.text, None)

    def binder(self, sym, bind):
        """Bind a forall, exists or fn variable, which may not reuse a name in scope (§2)."""
        if self.lookup(sym.text) is not None or sym.text in self.items or sym.text in self.defs:
            self.report("E-TYPE-002", sym, f"binder '{sym.text}' reuses a name in scope (§2)")
        self.scopes[-1][sym.text] = bind

    def enter(self, params, ghost):
        self.scopes = [{}]
        for sym, t in params:
            self.names.add(sym.text)
            self.scopes[0][sym.text] = _Bind(t, "parameter", ghost=ghost)

    # Items (§7).

    def check_spec(self, item):
        self.enter(item.params, False)
        for e in _args(item.form, "requires"):
            self.boolean(e, True)
        self.scopes.append({sym.text: _Bind(t, "result") for sym, t in item.results})
        for e in _args(item.form, "ensures"):
            self.boolean(e, True)
        if item.defn is None:
            return
        self.scopes.pop()
        for e in _args(item.defn, "decreases"):
            self.integer(e, True, "a decreases clause")
        body = next(c for c in item.defn.items[2:] if _head(c) == "body")
        if self.block(body.items[1:], False):
            self.report("E-RET-001", body, f"a path through def {item.name} ends without return or panic (D40)")
        missing = {}  # each undeclared effect, at its first statement (D78)
        for effect, node in self.effects:
            if effect not in item.effects and effect not in missing:
                missing[effect] = node
                self.report("E-EFF-001", node, f"this has effect {effect}, which spec {item.name} doesn't declare (§6)")

    def check_ghost_fn(self, item):
        self.enter(item.params, True)
        for e in _args(item.form, "requires"):
            self.boolean(e, True)
        for e in _args(item.form, "decreases"):
            self.integer(e, True, "a decreases clause")
        self.expect(_args(item.form, "body")[0], item.result, True)

    def check_lemma(self, item):
        self.enter(item.params, True)
        for e in _args(item.form, "requires") + _args(item.form, "ensures"):
            self.boolean(e, True)
        for e in _args(item.form, "decreases"):
            self.integer(e, True, "a decreases clause")
        self.block(_args(item.form, "body"), True)

    # Statements. g is true in ghost context: a lemma body. Each returns whether the statement
    # can continue normally, the opposite of §7's ⊥; moves accumulate in self.moves.

    def block(self, stmts, g):
        self.scopes.append({})
        live = True
        for s in stmts:
            before = dict(self.moves)
            if not live:  # unreachable: checked all the same, with the moves of the path that reached it
                self.stmt(s, g)
                self.moves = before
                continue
            live = self.stmt(s, g)
            if not live:
                self.moves = before
        self.leave()
        return live

    def branch(self, s, g):
        self.scopes.append({})  # a statement in a branch is a scope of its own (D66)
        live = self.stmt(s, g)
        self.leave()
        return live

    def leave(self):
        """End a block's scope. Its locals go out of scope with their move records, so a later
        binder may reuse a name (§2, D66)."""
        for name in self.scopes.pop():
            self.moves.pop(name, None)

    def stmt(self, s, g):
        it = s.items
        h = it[0].text
        if g and (h in RUNTIME_STATEMENTS or (h == "return" and len(it) > 1)):
            self.report("E-GHOST-003", s, f"{h} is a runtime statement, and a lemma body is ghost code (§7)")
            return True
        if h in ("let", "let-mut"):
            if isinstance(it[1], Form):
                self.bind_results(s, h == "let-mut")
            else:
                t = self.type_of(it[2], True, False)
                if t == ERR and _head(it[3]) == "borrow":  # a slice let is reported once, at its type
                    self.var(it[3].items[1], False)
                else:
                    self.owned(it[3], t)
                self.declare(it[1], _Bind(t, "local", mutable=h == "let-mut"))
        elif h in ("ghost-let", "ghost-let-mut"):
            t = self.type_of(it[2], False, False)
            self.expect(it[3], t, True)
            self.declare(it[1], _Bind(t, "ghost local", mutable=h == "ghost-let-mut", ghost=True))
        elif h in ("set", "ghost-set"):
            b = self.target(it[1], h)
            if h == "set" and b is None:
                self.expr(it[2], False)  # no move: the set itself is wrong
            elif h == "set":
                self.owned(it[2], b.type)
                self.moves.pop(it[1].text, None)  # live again
            else:
                self.expect(it[2], b.type if b else ERR, True)
        elif h in ("set-idx", "push"):
            b = self.target(it[1], h)
            t = ERR if b is None else b.type
            if t not in (ERR,) and t[0] != "vec":
                self.report("E-TYPE-001", it[1], f"{h} needs a vector, and '{it[1].text}' is {show(t)}")
                t = ERR
            elif b is not None and it[1].text in self.moves:
                self.var(it[1], False)  # reports the use after move
            if h == "set-idx":
                self.integer(it[2], False, "an index")
            self.expect(it[-1], _elem(t) or ERR, False)
            if h == "push":
                self.effects.append(("alloc", s))
        elif h == "if":
            self.boolean(it[1], g)
            before = dict(self.moves)
            live1 = self.branch(it[2], g)
            after1, self.moves = self.moves, dict(before)
            live2 = self.branch(it[3], g)
            if live1 and live2:
                self.moves = {**after1, **self.moves}  # moved on either branch: moved (§5)
            elif live1:
                self.moves = after1
            elif not live2:
                self.moves = before
                return False
        elif h == "block":
            return self.block(it[1:], g)
        elif h == "while":
            self.loop(s, g)
        elif h == "call":
            self.call(s, g, statement=True)
        elif h == "assert":
            self.boolean(it[1], True)
        elif h == "return":
            self.ret(s)
            return False
        elif h == "panic":
            self.effects.append(("panic", s))
            return False
        elif h == "print":
            self.expect(it[1], I64, False)
            self.effects.append(("io", s))
        return True

    def target(self, sym, h):
        """The binding that set, set-idx, push or ghost-set changes, checked to be changeable (§5, D75)."""
        b = self.lookup(sym.text)
        if b is None:
            self.var(sym, True)  # reports it undefined, or not a value
            return None
        if (h == "ghost-set") != b.ghost:
            want = "a ghost local" if h == "ghost-set" else "a runtime local"
            self.report("E-GHOST-001", sym, f"{h} changes {want}, and '{sym.text}' is a {b.kind} (§7)")
            return None
        if not b.mutable:
            self.report("E-OWN-003", sym, f"'{sym.text}' is a {b.kind} and can't change: only let-mut and "
                                          f"ghost-let-mut locals can (§5)")
            return None
        return b

    def loop(self, s, g):
        it = s.items
        self.boolean(it[1], g)
        for c in it[2:]:
            if _head(c) == "invariant":
                self.boolean(c.items[1], True)
            elif _head(c) == "decreases":
                self.integer(c.items[1], True, "a decreases clause")
        outer = {n for scope in self.scopes for n in scope}
        before = dict(self.moves)
        live = self.block([c for c in it[2:] if _head(c) not in ("invariant", "decreases")], g)
        if live and not g:  # §5 rule 6: the body's normal end leaves outer variables as it found them
            for name in sorted(outer & (set(before) ^ set(self.moves))):
                if name in self.moves:
                    self.report("E-OWN-004", self.moves[name], f"'{name}' moves in the loop body and isn't set "
                                                               f"again before the next iteration (§5)")
                else:
                    self.report("E-OWN-004", s, f"the loop body gives '{name}' a new value, but it had moved "
                                                f"before the loop (§5)")
        self.moves = before

    def ret(self, s):
        results = self.item.results
        exprs = s.items[1:]
        if len(exprs) != len(results):
            self.report("E-TYPE-001", s, f"return gives {len(exprs)} values; spec {self.item.name} declares "
                                         f"{len(results)} (D40, D43)")
        self.once(exprs)
        for e, (_, t) in zip(exprs, results):
            self.owned(e, t)
        for e in exprs[len(results):]:
            self.expr(e, False)
        self.quiet = set()

    def once(self, exprs):
        """§5 rule 7: a vector variable appears in at most one of a call's arguments or a return's
        expressions, owned, borrowed or read (D72)."""
        seen = set()
        for e in exprs:
            mine = {}
            for sym in self.vectors(e):
                mine.setdefault(sym.text, sym)
            for name, sym in mine.items():
                if name in seen and name not in self.quiet:
                    self.report("E-OWN-005", sym, f"vector '{name}' appears in more than one argument here (§5)")
                    self.quiet.add(name)
                seen.add(name)

    def vectors(self, e):
        """The runtime vector variables in e, in order."""
        if isinstance(e, Sym):
            b = self.lookup(e.text)
            return [e] if b is not None and not b.ghost and b.type[0] == "vec" else []
        if isinstance(e, Form):
            return [v for c in e.items[1:] for v in self.vectors(c)]
        return []

    def owned(self, e, t):
        """e in an owned position: a let initializer, set's right side, a return value or an owned
        argument (§5 rule 2). It must have type t, and a vector variable moves."""
        got = self.expr(e, False, want=t)
        if not same(got, t):
            self.report("E-TYPE-001", e, f"expected {show(t)}, found {show(got)}")
        elif t != ERR and isinstance(e, Sym) and got[0] == "vec" and e.text not in self.quiet:
            self.moves[e.text] = e

    def callee(self, name, wanted):
        """The item that name calls, or None once any error is reported: a binding isn't
        callable (D67), and a clashing name was reported where it was declared (D78)."""
        if name.text in self.clashes:
            return None
        item = self.items.get(name.text)
        if item is None:
            b = self.lookup(name.text)
            if b is not None:
                self.report("E-TYPE-001", name, f"'{name.text}' is a {b.kind}, not {wanted} (D67)")
            else:
                self.report("E-TYPE-002", name, f"'{name.text}' is undefined")
        return item

    def call(self, c, g, statement):
        """(call f e*): a def's result types, or [] for a lemma or a call that can't be checked."""
        name = c.items[1]
        item = self.callee(name, "a def or lemma")
        if item is None:
            return None
        if item.kind == "lemma":
            self.edges.append((self.item.name, item.name, c))
            self.arguments(c, item, True)
            return []
        if item.kind == "ghost-fn":
            if g:
                self.report("E-TYPE-001", name, f"'{name.text}' is a ghost-fn: call it in an expression (§2)")
            else:
                self.report("E-GHOST-002", name, f"ghost-fn '{name.text}' can't be called from runtime code (§4)")
            return None
        if g:
            self.report("E-GHOST-003", c, f"a lemma body is ghost code and can't call def '{name.text}' (§7)")
            return None
        self.edges.append((self.item.name, item.name, c))
        if statement and item.results:
            self.report("E-TYPE-001", c, f"'{name.text}' returns {len(item.results)} values: bind them with "
                                         f"(let ((x T) ...) (call {name.text} ...)) (D74)")
        self.arguments(c, item, False)
        self.effects += [(e, c) for e in sorted(item.effects)]
        return [t for _, t in item.results]

    def arguments(self, c, item, g):
        args = c.items[2:]
        if len(args) != len(item.params):
            self.report("E-TYPE-001", c, f"'{item.name}' takes {len(item.params)} arguments, got {len(args)}")
        if g:  # a lemma call's arguments are ghost (§7)
            for a, (_, t) in zip(args, item.params):
                self.expect(a, t, True)
            return
        self.once(args)
        for a, (_, t) in zip(args, item.params):
            if t[0] == "slice":
                self.slice_argument(a, t)
            elif _head(a) == "borrow":
                self.var(a.items[1], False)
                self.report("E-OWN-002", a, f"(borrow {a.items[1].text}) can only be an argument for a slice parameter, "
                                            f"and this one is {show(t)} (§5, D69)")
            elif t[0] == "vec" and not isinstance(a, Sym):
                if self.expr(a, False, want=t) != ERR and _head(a) != "if":  # an if already reported it
                    self.report("E-OWN-006", a, "an owned vector argument must be a variable, which then moves (§7, D73)")
            else:
                self.owned(a, t)
        for a in args[len(item.params):]:
            self.expr(a, False)
        self.quiet = set()

    def slice_argument(self, a, t):
        """A slice parameter takes (borrow v) of a live vector, or a slice parameter (§7)."""
        if _head(a) == "borrow":
            v, self.types[id(a)] = a.items[1], t
            got = self.var(v, False)
            if got not in (ERR,) and (got[0] != "vec" or not same(("slice", got[1]), t)):
                self.report("E-TYPE-001", v, f"(borrow {v.text}) needs a vector of {show(t[1])}, and '{v.text}' "
                                             f"is {show(got)}")
            return
        got = self.expr(a, False)
        if got != ERR and not (isinstance(a, Sym) and same(got, t)):
            self.report("E-TYPE-001", a, f"a {show(t)} parameter takes (borrow v) or a slice parameter, "
                                         f"not {show(got)}")

    def bind_results(self, s, mutable):
        params, c = s.items[1].items, s.items[2]
        results = self.call(c, False, statement=False)
        if results is not None and len(params) != len(results):
            self.report("E-TYPE-001", s, f"'{c.items[1].text}' returns {len(results)} values, and {len(params)} "
                                         f"names bind them (D43)")
        for i, p in enumerate(params):
            t = self.type_of(p.items[1], True, False)
            if results is not None and i < len(results) and not same(t, results[i]):
                self.report("E-TYPE-001", p.items[1], f"'{c.items[1].text}' result {i + 1} is {show(results[i])}, "
                                                      f"not {show(t)}")
            self.declare(p.items[0], _Bind(t, "local", mutable=mutable))

    # Expressions. g is true in ghost context (§4); want is the type the context needs, which
    # fixes what a literal, (vec-new) or an empty seq-lit is.

    def expect(self, e, t, g):
        got = self.expr(e, g, want=t)
        if not (sub(got, t) if g else same(got, t)):
            self.report("E-TYPE-001", e, f"expected {show(t)}, found {show(got)}")

    def boolean(self, e, g):
        self.expect(e, BOOL, g)

    def integer(self, e, g, what):
        t = self.expr(e, g)
        if t != ERR and t != I64 and not (g and t == INT):
            self.report("E-TYPE-001", e, f"{what} takes an integer, not {show(t)}")

    def sequence(self, e, what):
        """A ghost operand viewed as a (seq T): its element type, or ERR."""
        t = self.expr(e, True)
        if t != ERR and t[0] not in SEQUENCES:
            self.report("E-TYPE-001", e, f"{what} takes a sequence, not {show(t)}")
            return ERR
        return ERR if t == ERR else t[1]

    def expr(self, x, g, want=None):
        t = self.types[id(x)] = self._expr(x, g, want)
        return t

    def _expr(self, x, g, want):
        if isinstance(x, Int):
            if not g or want == I64:
                if not MIN <= x.value <= MAX:
                    self.report("E-TYPE-001", x, f"{x.value} doesn't fit in i64 (§4, D53)")
                return I64
            return INT
        if isinstance(x, Sym):
            return BOOL if x.text in ("true", "false") else self.var(x, g)
        h = x.items[0].text
        if h in GHOST_ONLY and not g:
            self.report("E-GHOST-002", x, f"{h} is ghost-only, so runtime code can't use it (§4)")
            return {"forall": BOOL, "exists": BOOL, "contains": BOOL, "occurrences": I64}.get(h, ERR)
        if h in _OPERATORS:
            return self.operator(x, g, want)
        return getattr(self, _FORMS[h])(x, g, want) if h in _FORMS else self.apply(x, g)

    def var(self, x, g):
        b = self.lookup(x.text)
        if b is None:
            if x.text in self.clashes:
                pass  # reported where it was declared (D78)
            elif x.text in self.items:
                self.report("E-TYPE-001", x, f"'{x.text}' is a {self.items[x.text].kind}, not a value (D67)")
            else:
                self.report("E-TYPE-002", x, f"'{x.text}' is undefined")
            return ERR
        if not g and b.ghost:
            kind = b.kind if b.kind.startswith("ghost") else "ghost " + b.kind
            self.report("E-GHOST-001", x, f"runtime code can't use {kind} '{x.text}' (§4)")
            return ERR
        if not g and x.text in self.moves and x.text not in self.quiet | self.reported:
            moved = self.moves[x.text]
            self.reported.add(x.text)  # once per vector, so one move doesn't cascade
            self.report("E-OWN-001", x, f"'{x.text}' is used after it moved at {moved.pos[0]}:{moved.pos[1]} (§5)")
        return b.type

    def operator(self, x, g, want):
        h, a, b = x.items[0].text, x.items[1], x.items[2]
        if h in ("and", "or", "=>"):
            self.boolean(a, g)
            self.boolean(b, g)
            return BOOL
        if h in ("==", "!="):
            ta = self.expr(a, g)
            tb = self.expr(b, g, want=ta if ta[0] in COLLECTIONS else None)
            if ERR in (ta, tb):
                return BOOL
            if not g and (ta[0] in COLLECTIONS or tb[0] in COLLECTIONS):
                self.report("E-GHOST-002", x, f"{h} on collections is ghost-only (§7, D71)")
            elif not (join(ta, tb) is not None if g else ta == tb and ta in (BOOL, I64)):
                self.report("E-TYPE-001", x, f"{h} compares {show(ta)} with {show(tb)}")
            return BOOL
        self.integer(a, g, h)
        self.integer(b, g, h)
        return BOOL if h in ("<", "<=", ">", ">=") else INT if g else I64

    def e_not(self, x, g, want):
        self.boolean(x.items[1], g)
        return BOOL

    def e_neg(self, x, g, want):
        self.integer(x.items[1], g, "neg")
        return INT if g else I64

    def e_if(self, x, g, want):
        self.boolean(x.items[1], g)
        a = self.expr(x.items[2], g, want)
        b = self.expr(x.items[3], g, want if want is not None else a if a[0] in COLLECTIONS else None)
        t = join(a, b) if g else (b if a == ERR or ANY in a else a) if same(a, b) else None
        if t is None:
            self.report("E-TYPE-001", x, f"the branches of if are {show(a)} and {show(b)}")
            return ERR
        if not g and t[0] == "vec":
            self.report("E-OWN-006", x, "a vector can't come out of an if expression (§7)")
        return t

    def e_len(self, x, g, want):
        t = self.expr(x.items[1], g)
        if t != ERR and t[0] not in SEQUENCES:
            self.report("E-TYPE-001", x.items[1], f"len takes a sequence, not {show(t)}")
        return INT if g else I64

    def e_idx(self, x, g, want):
        t = self.expr(x.items[1], g)
        self.integer(x.items[2], g, "an index")
        if t != ERR and t[0] not in SEQUENCES:
            self.report("E-TYPE-001", x.items[1], f"idx takes a sequence, not {show(t)}")
            return ERR
        return ERR if t == ERR else self.element(x, t[1], g, want)

    def e_borrow(self, x, g, want):
        self.report("E-OWN-002", x, "(borrow v) can only be an argument of a def call (§5, D69)")
        return ERR

    def e_vec_new(self, x, g, want):
        return want if want is not None and want[0] == "vec" else ("vec", ANY)

    def e_seq_build(self, x, g, want):
        self.integer(x.items[1], g, "seq-build's length")
        fn = x.items[2]
        self.scopes.append({})
        self.binder(fn.items[1].items[0], _Bind(INT if g else I64, "binder", ghost=g))
        t = self.expr(fn.items[2], g)
        self.scopes.pop()
        if not g:
            self.effects.append(("alloc", x))
        if t == ERR:
            return ERR
        if t not in ((BOOL, I64, INT) if g else (BOOL, I64)):
            self.report("E-TYPE-001", fn.items[2], f"a seq-build element must be bool or an integer, not {show(t)}")
            return ERR
        return ("seq", t) if g else ("vec", t)

    def e_forall(self, x, g, want):
        self.scopes.append({})
        for b in x.items[1].items:
            t = self.type_of(b.items[1], False, False)
            if t not in (INT, BOOL, ERR):
                self.report("E-TYPE-001", b.items[1], f"a quantifier binds int or bool, not {show(t)} (§7, D68)")
            self.binder(b.items[0], _Bind(t, "binder", ghost=True))
        self.boolean(x.items[2], True)
        self.scopes.pop()
        return BOOL

    e_exists = e_forall

    def e_seq_lit(self, x, g, want):
        elem = want[1] if want is not None and want[0] == "seq" else None  # a literal's destination (D70)
        t = elem if elem is not None and len(x.items) == 1 else ANY
        for e in x.items[1:]:
            u = self.expr(e, True, want=elem)
            if u != ERR and u[0] in COLLECTIONS:
                self.report("E-TYPE-001", e, "B17-0 has no nested collections (§11)")
                return ERR
            j = join(t, u)
            if j is None:
                self.report("E-TYPE-001", e, f"seq-lit elements of types {show(t)} and {show(u)}")
                return ERR
            t = j
        return ERR if t == ERR else ("seq", t)

    def e_take(self, x, g, want):
        e = self.sequence(x.items[1], x.items[0].text)
        self.integer(x.items[2], True, x.items[0].text)
        return ERR if e == ERR else ("seq", e)

    e_drop = e_take

    def e_concat(self, x, g, want):
        a, b = self.sequence(x.items[1], "concat"), self.sequence(x.items[2], "concat")
        e = join(a, b)
        if e is None:
            self.report("E-TYPE-001", x, f"concat of sequences of {show(a)} and {show(b)}")
            return ERR
        return ERR if e == ERR else ("seq", e)

    def e_last(self, x, g, want):
        e = self.sequence(x.items[1], "last")
        return e if e == ERR else self.element(x, e, True, want)

    def element(self, x, e, g, want):
        """An element of a sequence of e. An element type an empty literal leaves open takes its
        destination's, which can't be a collection (D68), or is an integer if nothing fixes it (D70)."""
        if e != ANY:
            return e
        if want is not None and want != ERR and want[0] in COLLECTIONS:
            self.report("E-TYPE-001", x, f"an element of a sequence is never {show(want)} (§11, D68)")
            return ERR
        return want if want in (BOOL, I64, INT, ERR) else INT if g else I64

    def e_contains(self, x, g, want):
        e = self.sequence(x.items[1], x.items[0].text)
        t = self.expr(x.items[2], True)
        if t != ERR and t[0] in COLLECTIONS:
            self.report("E-TYPE-001", x.items[2], f"{x.items[0].text} looks for an element, and B17-0 has no "
                                                  f"nested collections (§11, D68)")
        elif join(e, t) is None:
            self.report("E-TYPE-001", x.items[2], f"{x.items[0].text} looks for {show(t)} among {show(e)}")
        return BOOL if x.items[0].text == "contains" else INT

    e_occurrences = e_contains

    def e_multiset(self, x, g, want):
        e = self.sequence(x.items[1], "multiset")
        return ERR if e == ERR else ("multiset", e)

    def e_msum(self, x, g, want):
        a, b = self.expr(x.items[1], True), self.expr(x.items[2], True)
        for e, t in ((x.items[1], a), (x.items[2], b)):
            if t != ERR and t[0] != "multiset":
                self.report("E-TYPE-001", e, f"msum takes multisets, not {show(t)}")
                return ERR
        if ERR in (a, b):
            return ERR
        j = join(a, b)
        if j is None:
            self.report("E-TYPE-001", x, f"msum of {show(a)} and {show(b)} (D70)")
            return ERR
        return j

    def apply(self, x, g):
        """(NAME e*): a ghost-fn call."""
        name = x.items[0]
        item = self.callee(name, "a ghost-fn")
        if item is None:
            return ERR
        if item.kind != "ghost-fn":
            self.report("E-TYPE-001", name, f"'{name.text}' is a {item.kind}, not a ghost-fn (D67)")
            return ERR
        if not g:
            self.report("E-GHOST-002", x, f"ghost-fn '{name.text}' can't be called from runtime code (§4)")
            return ERR
        self.edges.append((self.item.name, item.name, x))
        args = x.items[1:]
        if len(args) != len(item.params):
            self.report("E-TYPE-001", x, f"'{name.text}' takes {len(item.params)} arguments, got {len(args)}")
        for a, (_, t) in zip(args, item.params):
            self.expect(a, t, True)
        return item.result

    # Recursion (§7): a call to an item's own name needs its decreases (E-TERM-001), and a
    # cycle through two or more items is mutual recursion (E-TERM-002).

    def recursion(self):
        graph = {}
        for caller, callee, node in self.edges:
            if caller == callee:
                if self.items[caller].decreases() is None:
                    self.report("E-TERM-001", node, f"'{caller}' calls itself but has no decreases (§7)")
            else:
                graph.setdefault(caller, []).append((callee, node))
        for scc in _components(graph):
            calls = sorted((node.pos, a, b) for a in scc for b, node in graph.get(a, []) if b in scc)
            pos, a, b = calls[0]
            names = " and ".join(sorted(scc)) if len(scc) == 2 else ", ".join(sorted(scc))
            self.report("E-TERM-002", next(n for x, n in graph[a] if x == b and n.pos == pos),
                        f"{names} are mutually recursive (§7)")


_OPERATORS = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "and", "or", "=>"}
_FORMS = {h: "e_" + h.replace("-", "_") for h in ("not", "neg", "if", "len", "idx", "borrow", "vec-new", "seq-build", "forall",
                                                "exists", "seq-lit", "take", "drop", "concat", "last", "contains",
                                                "multiset", "msum", "occurrences")}


def _components(graph):
    """The strongly connected components of graph with more than one node: Tarjan's algorithm,
    iteratively, so that a long chain of calls can't overflow Python's stack."""
    index, low, stack, on, out = {}, {}, [], set(), []

    def enter(v):
        index[v] = low[v] = len(index)
        stack.append(v)
        on.add(v)
        return v, iter(graph.get(v, []))

    for root in sorted(graph):
        if root in index:
            continue
        work = [enter(root)]
        while work:
            v, edges = work[-1]
            for w, _ in edges:
                if w not in index:
                    work.append(enter(w))
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            else:
                work.pop()
                if work:
                    u = work[-1][0]
                    low[u] = min(low[u], low[v])
                if low[v] == index[v]:
                    scc = set()
                    while True:
                        w = stack.pop()
                        on.discard(w)
                        scc.add(w)
                        if w == v:
                            break
                    if len(scc) > 1:
                        out.append(scc)
    return out


def main(argv):
    if len(argv) != 1:
        print("usage: uv run --no-project b17c/check.py FILE", file=sys.stderr)
        return 2
    path = argv[0]
    try:
        diags = check(parse(Path(path).read_bytes()))
    except OSError as e:
        print(f"{path}: {e.strerror}", file=sys.stderr)
        return 2
    except ParseError as e:
        diags = [Diagnostic(e.line, e.col, e.code, e.reason)]
    for d in diags:
        print(f"{path}:{d}")
    return 1 if diags else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
