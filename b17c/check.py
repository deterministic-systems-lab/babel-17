"""The tier 0 checker: B17-0's (docs/b17-0.md §2-§7 and §9's tier 0 table; D33-D45, D51, D53,
D66-D78), and with subset 1, B17-1's (docs/b17-1.md §2-§7 and §9; D79-D92, D99, D100, D101).

    uv run --no-project b17c/check.py [--subset 1] FILE

parses and checks FILE and prints `FILE:LINE:COL: CODE: message` for each diagnostic,
exiting 1 if there are any. A parse error prints the same way, as E-PARSE-001.

check(module) returns the diagnostics in position order; an empty list means the module
passes tier 0. Proof goals are WP5's: this checker generates none, but types(module) gives
WP5 the type it computes for each expression.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

from hashing import CORE, CORE1, HashError, hashes
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
# B17-1 (docs/b17-1.md §4): ghost-only forms, and the core library's type and constructors (§9).
GHOST_ONLY_1 = {"rank", "iset-lit", "iset-of", "map-lit", "union", "diff", "inter", "update", "lookup"}
CORE1_TYPES = {it.items[1].text for it in CORE1.items[3:]}
CORE1_CTORS = {c.items[0].text for it in CORE1.items[3:] for c in it.items[3:]}
UNORDERED = ("iset", "map", "multiset")  # arrays in the encoding: no subtyping, and no type contains itself in one (§3)


@dataclass(frozen=True, order=True)
class Diagnostic:
    line: int
    col: int
    code: str
    message: str
    node: object = field(default=None, compare=False, repr=False)  # the form it's about, for WP6's node IDs

    def __str__(self):
        return f"{self.line}:{self.col}: {self.code}: {self.message}"


def check(module, subset=0):
    """module's tier 0 diagnostics, in position order; none means it passes tier 0."""
    return sorted(_Checker(module, subset).run())


def types(module, subset=0):
    """The type tier 0 gives each expression of module and of the core library, by node id,
    for WP5's goals and WP7's backend. Raises ValueError, listing the diagnostics, if module
    fails tier 0. The core library is typed on its own, as check() leaves it, since its
    binders, such as sorted's i and j, may share a name with an item of module (§2)."""
    c, core = _Checker(module, subset), _Checker(CORE)
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
    if t[0] == "data":
        return t[1] if len(t) == 2 else f"({' '.join([t[1]] + [show(a) for a in t[2:]])})"
    if t[0] == "param":
        return t[1]
    return f"({' '.join([t[0]] + [show(a) for a in t[1:]])})"


def subst(t, env):
    """t with each type parameter ("param", A) replaced by env[A]; ANY where env has none."""
    if t[0] == "param":
        return env.get(t[1], ANY)
    if t in (BOOL, I64, INT, ERR, ANY):
        return t
    return (t[0],) + tuple(a if isinstance(a, str) else subst(a, env) for a in t[1:])


def parts(t):
    """The component types of t: elements, components, or a data type's arguments."""
    return [a for a in t[1:] if not isinstance(a, str)]


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
class _Data:
    """A B17-1 data type (docs/b17-1.md §3): its parameters and constructors, whose field types
    are written over ("param", A); and what §3, §5 and §6 derive from them."""
    name: str
    form: Form
    params: list = field(default_factory=list)  # [str]
    ctors: list = field(default_factory=list)   # [(name Sym, [(field Sym, type)])]
    fields: dict = field(default_factory=dict)  # field name -> (ctor index, type)
    covariant: list = field(default_factory=list)  # per parameter (§3's variances)
    recursive: bool = False                        # its fields mention it (§5 rule 1)
    boxed: list = field(default_factory=list)      # per constructor: a boxed field, so building one allocates (§6)


@dataclass
class _Bind:
    type: tuple
    kind: str             # parameter, result, local, ghost local or binder
    mutable: bool = False
    ghost: bool = False


class _Checker:
    def __init__(self, module, subset=0):
        self.module, self.sub = module, subset
        self.datas, self.ctors = {}, {}  # B17-1: type name -> _Data; constructor name -> (type name, index)
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
        """D45: no two specs share a spec hash; D92: no two data types either."""
        try:
            hashes(self.module, self.sub, self.types)
        except HashError as e:
            if e.names and isinstance(e.names[0], tuple):  # two data types, placed at the module's later one
                mine = [self.datas[n].form.items[1] for _, n in e.names if self.datas[n].form not in CORE1.items]
                later = max(mine, key=lambda x: x.pos)
                first = next(n for _, n in e.names if self.datas[n].form.items[1] is not later)
                self.report(e.code, later, f"data type '{later.text}' is identical to '{first}' up to names (D92)")
                return
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
        if self.sub:
            for it in CORE1.items[3:]:
                self.data_item(it)
        defs = {}
        for it in self.module.items[3:] if self.module is not CORE else ():  # the core library itself
            kind, name = it.items[0].text, it.items[1]
            if kind == "data":
                if name.text in CORE1_TYPES:
                    self.report("E-TYPE-002", name, f"'{name.text}' is the core library's type (docs/b17-1.md §2)")
                elif name.text in self.datas:
                    self.report("E-TYPE-002", name, f"type '{name.text}' is already declared in this module")
                else:
                    self.data_item(it)
                continue
            if name.text in self.ctors and name.text not in self.clashes:
                self.report("E-TYPE-002", name, f"'{name.text}' is already a constructor, and constructors are value "
                                                f"names (D82)")
                self.clashes.add(name.text)
                continue
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
        if self.sub:
            self.data_types()
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
        elif sym.text in self.items or sym.text in self.defs or sym.text in self.ctors:
            self.report("E-TYPE-002", sym, f"'{sym.text}' is an item's name, so no parameter or local may take it (D41)")
        seen.add(sym.text)

    def type_of(self, node, runtime, slices):
        """The type node denotes, once it's checked to be allowed here (§3, D68); ERR if it isn't."""
        if self.sub:
            t = self.well_formed(node, slices, ())
            if runtime and t != ERR and t[0] != "slice" and not self.runtime(t):  # docs/b17-1.md §7, as D68
                if t == INT:
                    self.report("E-GHOST-002", node, "int is a ghost type; runtime code uses i64 (§3)")
                else:
                    self.report("E-GHOST-002", node, f"{show(t)} is a ghost type, so runtime code can't hold it (§3)")
                return ERR
            return t
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

    # B17-1's data types and their types (docs/b17-1.md §2, §3, §5, §6).

    def data_item(self, it):
        """Register a data item's names (D82). Its field types are read in data_types()."""
        name, ps, ctors = it.items[1].text, it.items[2].items, it.items[3:]
        d = self.datas[name] = _Data(name, it)
        for a in ps:
            if a.text in d.params or a.text == name:
                self.report("E-TYPE-002", a, f"type parameter '{a.text}' reuses a type name of its item (D82)")
            elif a.text in self.datas or a.text in CORE1_TYPES:
                self.report("E-TYPE-002", a, f"type parameter '{a.text}' shadows the data type '{a.text}' (D82)")
            d.params.append(a.text)
        for i, c in enumerate(ctors):
            cname = c.items[0]
            if cname.text in CORE1_CTORS and it not in CORE1.items:
                self.report("E-TYPE-002", cname, f"'{cname.text}' is a core library constructor (docs/b17-1.md §9)")
            elif cname.text in self.ctors or cname.text in self.items or cname.text in CORE_NAMES:
                self.report("E-TYPE-002", cname, f"'{cname.text}' is already a value name, and constructors are "
                                                 f"value names (D82)")
            else:
                self.ctors[cname.text] = (name, i)
            d.ctors.append((cname, []))
            for f in c.items[1:]:
                if f.items[0].text in d.fields:
                    self.report("E-TYPE-002", f.items[0], f"field '{f.items[0].text}' is already a field of "
                                                          f"{name} (D82)")
                else:
                    d.fields[f.items[0].text] = (i, None)

    def data_types(self):
        """Read every data type's field types, then §3's module-wide rules: finite values, no type
        inside its own set, no two types containing each other, and the derived properties."""
        for d in self.datas.values():
            for i, c in enumerate(d.form.items[3:]):
                for f in c.items[1:]:
                    t = self.well_formed(f.items[1], False, tuple(d.params))
                    d.ctors[i][1].append((f.items[0], t))
                    if d.fields.get(f.items[0].text) == (i, None):
                        d.fields[f.items[0].text] = (i, t)
        graph = {}
        for d in self.datas.values():
            named = [e for _, fs in d.ctors for _, t in fs for e in self.mentions(t)]
            graph[d.name] = [(e, None) for e in named if e != d.name]
            d.recursive = d.name in named
            d.boxed = [any(d.name in self.mentions(t, through_vec=False) for _, t in fs) for _, fs in d.ctors]
            d.covariant = [True] * len(d.params)
        for scc in _components(graph):  # reported at the later declaration, as the module reads
            later = max((self.datas[n].form.items[1] for n in scc), key=lambda x: x.pos)
            self.report("E-TERM-002", later, f"data types {' and '.join(sorted(scc))} contain each other "
                                             f"(docs/b17-1.md §3)")
        for d in self.datas.values():  # §3: never inside an iset, map or multiset of itself
            for c in d.form.items[3:]:
                for f in c.items[1:]:
                    self.unordered_self(f.items[1], d.name, False)
        finite, changed = set(), True  # §3: a least fixed point
        while changed:
            changed = False
            for d in self.datas.values():
                if d.name not in finite and any(all(self.inhabited(t, finite) for _, t in fs) for _, fs in d.ctors):
                    finite.add(d.name)
                    changed = True
        for d in self.datas.values():
            if d.name not in finite:
                self.report("E-TYPE-001", d.form.items[1], f"data type {d.name} has no finite value: every constructor "
                                                           f"needs one already (docs/b17-1.md §3)")
        changed = True  # §3: the largest assignment of variances, starting covariant
        while changed:
            changed = False
            for d in self.datas.values():
                for _, fs in d.ctors:
                    for _, t in fs:
                        for a in self.invariant_params(t, False):
                            k = d.params.index(a)
                            if d.covariant[k]:
                                d.covariant[k], changed = False, True

    def mentions(self, t, through_vec=True):
        """The data types mentioned anywhere in t; through_vec False skips what's inside a
        vector, for §6's boxed fields."""
        if t[0] == "vec" and not through_vec:
            return []
        return ([t[1]] if t[0] == "data" else []) + [e for a in parts(t) for e in self.mentions(a, through_vec)]

    def unordered_self(self, node, name, inside):
        """Report a data type written inside an iset, map or multiset of itself (§3)."""
        if isinstance(node, Sym):
            if inside and node.text == name:
                self.report("E-TYPE-001", node, f"{name} can't contain itself inside an iset, map or multiset, which "
                                                f"the encoding represents as arrays (docs/b17-1.md §3)")
            return
        h = node.items[0].text
        if inside and h == name:
            self.report("E-TYPE-001", node, f"{name} can't contain itself inside an iset, map or multiset (docs/b17-1.md §3)")
            return
        for c in node.items[1:]:
            self.unordered_self(c, name, inside or h in UNORDERED)

    def inhabited(self, t, finite):
        if t[0] == "data":
            return t[1] in finite or t[1] in CORE1_TYPES
        if t[0] == "tuple":
            return all(self.inhabited(a, finite) for a in parts(t))
        return True  # bool, i64, int, a parameter, and every collection, which may be empty

    def invariant_params(self, t, inside):
        """The type parameters occurring in t in an invariant position (§3)."""
        if t[0] == "param":
            return [t[1]] if inside else []
        out = []
        if t[0] == "data":
            cov = self.datas[t[1]].covariant if t[1] in self.datas else []
            for k, a in enumerate(parts(t)):
                out += self.invariant_params(a, inside or not (cov[k] if k < len(cov) else True))
            return out
        for a in parts(t):
            out += self.invariant_params(a, inside or t[0] in UNORDERED)
        return out

    def well_formed(self, node, slices, params):
        """A B17-1 type (§3), with params the data item's type parameters; ERR once reported."""
        if isinstance(node, Sym):
            t = node.text
            if t in ("bool", "i64", "int"):
                return {"bool": BOOL, "i64": I64, "int": INT}[t]
            if t in params:
                return ("param", t)
            if t in self.datas:
                if self.datas[t].params:
                    self.report("E-TYPE-001", node, f"{t} takes {len(self.datas[t].params)} type arguments (§3)")
                    return ERR
                return ("data", t)
            self.report("E-TYPE-002", node, f"type '{t}' is undefined")
            return ERR
        head, args = node.items[0].text, node.items[1:]
        if head == "ref":
            inner = self.well_formed(args[0].items[1], False, params)
            if inner == ERR:
                return ERR
            if not self.runtime(inner):
                self.report("E-TYPE-001", args[0].items[1], f"a slice holds a runtime type, not {show(inner)} (§3)")
                return ERR
            if not slices:
                self.report("E-OWN-002", node, "only a spec's parameter can be a slice, and no type contains one "
                                               "(docs/b17-1.md §3, D69)")
                return ERR
            return ("slice", inner)
        inner = [self.well_formed(a, False, params) for a in args]
        if ERR in inner:
            return ERR
        if head == "vec":
            if not self.runtime(inner[0]):
                self.report("E-TYPE-001", args[0], f"a vector holds a runtime type, and {show(inner[0])} is a ghost "
                                                   f"type (docs/b17-1.md §3)")
                return ERR
            return ("vec", inner[0])
        if head in ("seq", "multiset", "iset", "map", "tuple"):
            return (head,) + tuple(inner)
        d = self.datas.get(head)
        if d is None:
            self.report("E-TYPE-002", node.items[0], f"type '{head}' is undefined")
            return ERR
        if len(inner) != len(d.params):
            self.report("E-TYPE-001", node, f"{head} takes {len(d.params)} type arguments, not {len(inner)} (§3)")
            return ERR
        t = ("data", head) + tuple(inner)
        for _, fs in d.ctors:  # a vector field of a parameter needs a runtime argument (§3)
            for _, ft in fs:
                for v in self.vectors_in(ft):
                    if not self.runtime(subst(v, dict(zip(d.params, inner)))):
                        self.report("E-TYPE-001", node, f"{show(t)} would put a ghost type in a vector (§3)")
                        return ERR
        return t

    def vectors_in(self, t):
        out = [t[1]] if t[0] == "vec" else []
        for a in parts(t):
            out += self.vectors_in(a)
        return out

    def fields_of(self, t):
        """The constructors of data type t, with their field types substituted."""
        d = self.datas[t[1]]
        env = dict(zip(d.params, t[2:]))
        return [(c, [(f, subst(ft, env)) for f, ft in fs]) for c, fs in d.ctors]

    def runtime(self, t, seen=frozenset()):
        """§3: bool, i64, and vectors, tuples and data types of runtime types."""
        if t in (BOOL, I64, ANY, ERR) or t[0] == "param":
            return True
        if t[0] in ("vec", "tuple"):
            return all(self.runtime(a, seen) for a in parts(t))
        if t[0] == "data":
            if t in seen or t[1] not in self.datas:
                return True
            return all(self.runtime(ft, seen | {t}) for _, fs in self.fields_of(t) for _, ft in fs)
        return False  # int, a slice, and the ghost collections

    def moving(self, t, seen=frozenset()):
        """§5 rule 1: vectors, recursive data types, and anything holding either, move."""
        if t[0] == "vec":
            return True
        if t[0] == "tuple":
            return any(self.moving(a, seen) for a in parts(t))
        if t[0] == "data" and t[1] in self.datas and t not in seen:
            return self.datas[t[1]].recursive or any(
                self.moving(ft, seen | {t}) for _, fs in self.fields_of(t) for _, ft in fs)
        return False

    def exact(self, t, seen=frozenset(), via_seq=frozenset()):
        """D90: a quantifier binds only a type whose values the encoding represents exactly."""
        if t in (BOOL, INT, ERR, ANY):
            return True
        if t[0] in ("seq", "iset"):
            return self.exact(t[1], seen, seen | via_seq)
        if t[0] == "tuple":
            return all(self.exact(a, seen, via_seq) for a in parts(t))
        if t[0] == "data" and t[1] in self.datas:
            if t[1] in seen:
                return t[1] not in via_seq
            return all(self.exact(ft, seen | {t[1]}, via_seq) for _, fs in self.fields_of(t) for _, ft in fs)
        return False  # i64, vectors, slices, multisets and maps

    def sub1(self, t, u):
        """t <: u in B17-1's ghost code (docs/b17-1.md §3)."""
        if ERR in (t, u) or ANY in (t, u) or t == u or (t == I64 and u == INT):
            return True
        if t[0] in SEQUENCES and u[0] == "seq":
            return self.sub1(t[1], u[1])
        if t[0] == u[0] == "tuple" and len(t) == len(u):
            return all(self.sub1(a, b) for a, b in zip(parts(t), parts(u)))
        if t[0] == u[0] == "data" and t[1] == u[1] and len(t) == len(u):
            cov = self.datas[t[1]].covariant
            return all(self.sub1(a, b) if c else self.equal(a, b) for a, b, c in zip(parts(t), parts(u), cov))
        if t[0] == u[0] and t[0] in ("vec", "slice") + UNORDERED and len(t) == len(u):
            return all(self.equal(a, b) for a, b in zip(parts(t), parts(u)))
        return False

    def equal(self, t, u):
        """t and u are the same type, an open part (ANY) matching anything."""
        if ERR in (t, u) or ANY in (t, u) or t == u:
            return True
        return (t[0] == u[0] and len(t) == len(u) and (t[0] != "data" or t[1] == u[1])
                and all(self.equal(a, b) for a, b in zip(parts(t), parts(u))))

    def join1(self, a, b):
        """The least type both a and b convert to in B17-1's ghost code, or None: B17-0's join,
        with any element type, and tuples and data types by their parameters' variance."""
        if a == ERR or b == ERR:
            return ERR
        if a == b or b == ANY:
            return a
        if a == ANY:
            return b
        if a in (I64, INT) and b in (I64, INT):
            return INT
        if a[0] in SEQUENCES and b[0] in SEQUENCES:
            e = self.join1(a[1], b[1])
            return None if e is None else ("seq", e)
        if a[0] == b[0] == "tuple" and len(a) == len(b):
            es = [self.join1(x, y) for x, y in zip(parts(a), parts(b))]
            return None if None in es else ("tuple",) + tuple(es)
        if a[0] == b[0] == "data" and a[1] == b[1] and len(a) == len(b):
            out = []
            for x, y, c in zip(parts(a), parts(b), self.datas[a[1]].covariant):
                j = self.join1(x, y) if c else (x if not self.has_any(x) else y) if self.equal(x, y) else None
                if j is None:
                    return None
                out.append(j)
            return ("data", a[1]) + tuple(out)
        if self.equal(a, b):
            return b if self.has_any(a) else a
        return None

    def has_any(self, t):
        return t == ANY or (t != ERR and any(self.has_any(a) for a in parts(t)))

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
        if self.lookup(sym.text) is not None or sym.text in self.items or sym.text in self.defs or sym.text in self.ctors:
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
        if self.sub:
            if h in ("set-idx", "push"):
                return self.update(s)
            if h == "match":
                return self.match_stmt(s, g)
            if h == "forall":
                return self.forall_stmt(s)
            if h == "obtain":
                return self.obtain(s)
            if h in ("let", "let-mut") and not isinstance(it[1], Form) and _head(it[3]) == "replace":
                return self.replace(s, h == "let-mut")
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

    # B17-1's statements (docs/b17-1.md §5, §7).

    def place(self, p, h):
        """A place's type, its root checked changeable and live (§5 rule 3); ERR once reported."""
        if isinstance(p, Sym):
            b = self.target(p, h)
            t = ERR if b is None else b.type
            if b is not None and p.text in self.moves:
                self.var(p, False)  # reports the use after move
        else:
            hd, t0 = p.items[0].text, self.place(p.items[1], h)
            if hd == "idx":
                self.integer(p.items[2], False, "an index")
                if t0 != ERR and t0[0] != "vec":
                    self.report("E-TYPE-001", p.items[1], f"idx in a place takes a vector, not {show(t0)} (§7)")
                t = t0[1] if t0 != ERR and t0[0] == "vec" else ERR
            elif hd == "get":
                t = self.component(p, t0)
            else:
                if t0 != ERR and t0[0] != "data":
                    self.report("E-TYPE-001", p.items[1], f"field takes a data value, not {show(t0)} (§7)")
                    t0 = ERR
                t = self.field_type(p, t0)
        self.types[id(p)] = t
        return t

    @staticmethod
    def root(p):
        while isinstance(p, Form):
            p = p.items[1]
        return p

    def outlives(self, p, s):
        """§5 rule 3: a place's root is still live once the statement's value is evaluated."""
        r = self.root(p)
        if r.text in self.moves and self.moves[r.text] is not r:
            self.report("E-OWN-001", self.moves[r.text], f"this moves '{r.text}', the root of the place it updates, "
                                                         f"so the place would outlive it (docs/b17-1.md §5 rule 3)")
            self.moves.pop(r.text)

    def update(self, s):
        """(set-idx place i e) and (push place e): change a vector reached through a place."""
        it, h = s.items, s.items[0].text
        moved = set(self.moves)
        t = self.place(it[1], h)
        if t != ERR and t[0] != "vec":
            self.report("E-TYPE-001", it[1], f"{h} needs a vector, and this place is {show(t)}")
            t = ERR
        if h == "set-idx":
            self.integer(it[2], False, "an index")
        self.owned(it[-1], ERR if t == ERR else t[1])
        r = self.root(it[1])
        if r.text not in moved:
            self.outlives(it[1], s)
        if h == "push":
            self.effects.append(("alloc", s))
        return True

    def replace(self, s, mutable):
        """(let x T (replace place e)): x takes the place's value, and e takes its place (§7)."""
        it = s.items
        t = self.type_of(it[2], True, False)
        p, v = it[3].items[1], it[3].items[2]
        moved = set(self.moves)
        pt = self.place(p, "replace")
        if ERR not in (t, pt) and not self.equal(pt, t):
            self.report("E-TYPE-001", p, f"this place holds {show(pt)}, and the let declares {show(t)}")
        self.owned(v, t)
        if self.root(p).text not in moved:
            self.outlives(p, s)
        self.declare(it[1], _Bind(t, "local", mutable=mutable))
        return True

    def match_stmt(self, s, g):
        """A match statement: its arms join as an if's branches do (§5 rule 5). In runtime code its
        scrutinee is a variable, which moves when its type does, or a copied value (§5 rule 4)."""
        e = s.items[1]
        if g:
            t = self.expr(e, True)
        elif isinstance(e, Sym):
            t = self.var(e, False)
            if t != ERR and self.moving(t) and self.lookup(e.text) is not None:
                self.moves[e.text] = e
        else:
            t = self.expr(e, False)
            if t != ERR and self.moving(t):
                if self.place_read(e):
                    self.report("E-OWN-007", e, f"this moves {show(t)} out of a place to match it: take it out with "
                                                f"replace first (docs/b17-1.md §5 rule 4)")
                else:
                    self.report("E-OWN-006", e, f"a match statement's scrutinee is a variable or a copied value, not "
                                                f"{show(t)} (docs/b17-1.md §5 rule 4)")
        before, joined, any_live = dict(self.moves), {}, False
        for body in self.arms(s, t, g):
            self.moves = dict(before)
            live = self.stmt(body, g)
            self.leave()
            if live:
                joined.update(self.moves)
                any_live = True
        self.moves = joined if any_live else before
        return any_live

    def forall_stmt(self, s):
        """(forall ((x T) ...) (call L e*)): L applied at every value of the binders (D99)."""
        self.scopes.append({})
        self.binders(s.items[1].items)
        c = s.items[2]
        item = self.callee(c.items[1], "a lemma")
        if item is not None:
            if item.kind != "lemma":
                self.report("E-TYPE-001", c.items[1], f"a forall statement applies a lemma, and '{item.name}' is a "
                                                      f"{item.kind} (D99)")
            else:
                self.edges.append((self.item.name, item.name, c))
                self.arguments(c, item, True)
        self.scopes.pop()
        return True

    def obtain(self, s):
        """(obtain ((x T) ...) e): binds a witness of ∃x. e as ghost locals (D100)."""
        for b in s.items[1].items:
            t = self.type_of(b.items[1], False, False)
            if not self.exact(t):
                self.report("E-TYPE-001", b.items[1], f"a binder's type must be exact, and {show(t)} isn't "
                                                      f"(docs/b17-1.md §7, D90)")
                t = ERR
            self.declare(b.items[0], _Bind(t, "ghost local", ghost=True))
        self.boolean(s.items[2], True)
        return True

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
                    what = "vector" if self.lookup(name).type[0] == "vec" else "moving value"
                    self.report("E-OWN-005", sym, f"{what} '{name}' appears in more than one argument here (§5)")
                    self.quiet.add(name)
                seen.add(name)

    def vectors(self, e):
        """The runtime vector variables in e, in order; in B17-1, every moving variable (§5 rule 6)."""
        if isinstance(e, Sym):
            b = self.lookup(e.text)
            return [e] if b is not None and not b.ghost and self.moving(b.type) else []
        if isinstance(e, Form):
            h = _head(e)
            operands = e.items[1:2] if h == "field" else e.items[2:3] if h == "is" else e.items[1:]  # not field names
            return [v for c in operands for v in self.vectors(c)]
        return []

    def owned(self, e, t):
        """e in an owned position: a let initializer, set's right side, a return value or an owned
        argument (§5 rule 2). It must have type t, and a vector variable moves; in B17-1 any moving
        variable does, and a moving value can't come whole out of a place (E-OWN-007)."""
        got = self.expr(e, False, want=t, own=True)
        if not self.fits(got, t, False):
            self.report("E-TYPE-001", e, f"expected {show(t)}, found {show(got)}")
        elif t != ERR and isinstance(e, Sym) and self.moving(got) and e.text not in self.quiet:
            self.moves[e.text] = e
        elif self.sub and got != ERR and self.moving(got) and self.place_read(e):
            self.report("E-OWN-007", e, f"this moves {show(got)} out of a place: take it out with "
                                        f"(let x T (replace place e)) (docs/b17-1.md §5 rule 3)")
        return got

    def place_read(self, e):
        """e reads a part of a variable: (idx p i), (get p K) or (field p F), down to a NAME."""
        if _head(e) not in ("idx", "get", "field"):
            return False
        while _head(e) in ("idx", "get", "field"):
            e = e.items[1]
        return isinstance(e, Sym) and self.lookup(e.text) is not None

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
            elif self.moving(t) and not isinstance(a, Sym):
                if self.expr(a, False, want=t) != ERR and _head(a) != "if":  # an if already reported it
                    if self.sub and self.place_read(a):
                        self.report("E-OWN-007", a, f"this moves {show(t)} out of a place: take it out with replace "
                                                    f"first (docs/b17-1.md §5 rule 3)")
                    else:
                        what = "vector" if t[0] == "vec" else "moving"
                        self.report("E-OWN-006", a, f"an owned {what} argument must be a variable, which then moves "
                                                    f"(§7, D73)")
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

    def fits(self, got, t, g):
        """got converts to t: by subtyping in ghost code, exactly in runtime code (§3, D34)."""
        if self.sub:
            return self.sub1(got, t) if g else self.equal(got, t)
        return sub(got, t) if g else same(got, t)

    def join(self, a, b):
        return self.join1(a, b) if self.sub else join(a, b)

    def expect(self, e, t, g):
        got = self.expr(e, g, want=t)
        if not self.fits(got, t, g):
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

    def expr(self, x, g, want=None, own=False):
        """x's type; own is true when x is an owned position's whole value (docs/b17-1.md §5 rule 2)."""
        t = self.types[id(x)] = self._expr(x, g, want, own)
        return t

    def _expr(self, x, g, want, own=False):
        if isinstance(x, Int):
            if not g or want == I64:
                if not MIN <= x.value <= MAX:
                    self.report("E-TYPE-001", x, f"{x.value} doesn't fit in i64 (§4, D53)")
                return I64
            return INT
        if isinstance(x, Sym):
            return BOOL if x.text in ("true", "false") else self.var(x, g)
        h = x.items[0].text
        if h in GHOST_ONLY and not g or self.sub and h in GHOST_ONLY_1 and not g:
            self.report("E-GHOST-002", x, f"{h} is ghost-only, so runtime code can't use it (§4)")
            return {"forall": BOOL, "exists": BOOL, "contains": BOOL, "occurrences": I64}.get(h, ERR)
        if h in _OPERATORS:
            return self.operator(x, g, want)
        if self.sub and h in _FORMS_1:
            return getattr(self, _FORMS_1[h])(x, g, want, own)
        if self.sub and h in self.ctors:
            return self.construct(x, g, want, own)
        return getattr(self, _FORMS[h])(x, g, want) if h in _FORMS else self.apply(x, g)

    def var(self, x, g):
        b = self.lookup(x.text)
        if b is None:
            if x.text in self.clashes:
                pass  # reported where it was declared (D78)
            elif x.text in self.ctors:
                self.report("E-TYPE-001", x, f"'{x.text}' is a constructor: build a value with ({x.text} ...) (D81)")
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
            tb = self.expr(b, g, want=ta if ta[0] in COLLECTIONS or self.sub and ta not in (BOOL, I64, INT) else None)
            if ERR in (ta, tb):
                return BOOL
            if self.sub:  # docs/b17-1.md §7: ghost code compares joinable values; runtime code bool and i64
                if not g and (ta not in (BOOL, I64) or tb not in (BOOL, I64)):
                    self.report("E-GHOST-002", x, f"{h} on {show(ta if ta not in (BOOL, I64) else tb)} is ghost-only: "
                                                  f"runtime code compares bool and i64 (docs/b17-1.md §7, D71)")
                elif (self.join(ta, tb) is None) if g else ta != tb:
                    self.report("E-TYPE-001", x, f"{h} compares {show(ta)} with {show(tb)}")
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
        t = self.join(a, b) if g else (b if a == ERR or ANY in a else a) if self.fits(a, b, False) else None
        if t is None:
            self.report("E-TYPE-001", x, f"the branches of if are {show(a)} and {show(b)}")
            return ERR
        if not g and (self.moving(t) if self.sub else t[0] == "vec"):
            self.report("E-OWN-006", x, f"a {'vector' if t[0] == 'vec' else 'moving value'} can't come out of an if "
                                        f"expression (§7)")
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
        if self.sub:
            return self.seq_build1(x, g, want)
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
        self.binders(x.items[1].items)
        self.boolean(x.items[2], True)
        self.scopes.pop()
        return BOOL

    def binders(self, bs):
        """Bind a quantifier's variables: int or bool in B17-0 (D68), an exact type in B17-1 (D90)."""
        out = []
        for b in bs:
            t = self.type_of(b.items[1], False, False)
            if self.sub and not self.exact(t):
                self.report("E-TYPE-001", b.items[1], f"a binder's type must be exact, and {show(t)} isn't: the "
                                                      f"encoding admits values outside it (docs/b17-1.md §7, D90)")
                t = ERR
            elif not self.sub and t not in (INT, BOOL, ERR):
                self.report("E-TYPE-001", b.items[1], f"a quantifier binds int or bool, not {show(t)} (§7, D68)")
            self.binder(b.items[0], _Bind(t, "binder", ghost=True))
            out.append(t)
        return out

    e_exists = e_forall

    def e_seq_lit(self, x, g, want):
        elem = want[1] if want is not None and want[0] == "seq" else None  # a literal's destination (D70)
        t = elem if elem is not None and len(x.items) == 1 else ANY
        for e in x.items[1:]:
            u = self.expr(e, True, want=elem)
            if u != ERR and u[0] in COLLECTIONS and not self.sub:
                self.report("E-TYPE-001", e, "B17-0 has no nested collections (§11)")
                return ERR
            j = self.join(t, u)
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
        e = self.join(a, b)
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
        if self.sub:  # docs/b17-1.md §4: an element read from an open literal may be any type
            return want if want is not None else INT if g else I64
        if want is not None and want != ERR and want[0] in COLLECTIONS:
            self.report("E-TYPE-001", x, f"an element of a sequence is never {show(want)} (§11, D68)")
            return ERR
        return want if want in (BOOL, I64, INT, ERR) else INT if g else I64

    def e_contains(self, x, g, want):
        if self.sub:
            return self.contains1(x)
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
        j = self.join(a, b)
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

    # B17-1's expressions (docs/b17-1.md §4, §5, §7).

    def construct(self, x, g, want, own):
        """(C e*): a value of C's data type, its type parameters inferred from the arguments and
        then from the destination (§4, §7). In runtime code a moving one is an owned position's
        whole value (§5 rule 7), and a constructor with a boxed field allocates (§6)."""
        name, args = x.items[0], x.items[1:]
        dname, i = self.ctors[name.text]
        d = self.datas[dname]
        fs = d.ctors[i][1]
        if len(args) != len(fs):
            self.report("E-TYPE-001", x, f"constructor {name.text} takes {len(fs)} fields, got {len(args)}")
        env = {}
        if want is not None and want[0] == "data" and want[1] == dname:
            env = {a: t for a, t in zip(d.params, want[2:]) if t != ANY}
        quiet = self.quiet
        self.once(args)
        for a, (_, ft) in zip(args, fs):
            got = self.part(a, subst(ft, env), g, own)
            self.unify(ft, got, env)
        for a in args[len(fs):]:
            self.expr(a, g)
        self.quiet = quiet
        t = ("data", dname) + tuple(env.get(a, ANY) for a in d.params)
        if not g:
            if self.moving(t) and not own:
                self.report("E-OWN-006", x, f"a moving value is built only as an owned position's whole value: a let, "
                                            f"set, return or argument (docs/b17-1.md §5 rule 7)")
            if d.boxed[i]:
                self.effects.append(("alloc", x))
        return t

    def part(self, a, t, g, own):
        """An argument of a constructor call or tuple: an owned position when the call is (§5 rule 2)."""
        if own and not g:
            return self.owned(a, t)
        got = self.expr(a, g, want=t)
        if not self.fits(got, t, g):
            self.report("E-TYPE-001", a, f"expected {show(t)}, found {show(got)}")
        return got

    def unify(self, ft, got, env):
        """Bind the type parameters in field type ft to the parts of got."""
        if ft[0] == "param":
            if got not in (ERR, ANY):
                env[ft[1]] = self.join(env[ft[1]], got) or env[ft[1]] if ft[1] in env else got
        elif got not in (ERR, ANY) and got[0] == ft[0] and len(got) == len(ft):
            for a, b in zip(parts(ft), parts(got)):
                self.unify(a, b, env)

    def e_tuple(self, x, g, want, own):
        want = want if want is not None and want[0] == "tuple" and len(want) == len(x.items) else None
        quiet = self.quiet
        self.once(x.items[1:])
        t = ("tuple",) + tuple(self.part(a, want[k + 1] if want else ANY, g, own) for k, a in enumerate(x.items[1:]))
        self.quiet = quiet
        if not g and self.moving(t) and not own:
            self.report("E-OWN-006", x, "a moving tuple is built only as an owned position's whole value (§5 rule 7)")
        return t

    def e_match(self, x, g, want, own):
        t = self.expr(x.items[1], g)
        if not g and t != ERR and self.moving(t):
            self.report("E-OWN-006", x.items[1], f"a match expression's scrutinee has a copied type, and {show(t)} "
                                                 f"moves: use a match statement (docs/b17-1.md §5 rule 4)")
        out = None
        for body in self.arms(x, t, g):
            u = self.expr(body, g, want)
            self.leave()
            if out is None or u == ERR:
                out = u if out is None else out
            else:
                j = self.join(out, u) if g else out if self.fits(u, out, False) else None
                if j is None:
                    self.report("E-TYPE-001", body, f"this arm is {show(u)}, and an earlier one {show(out)}")
                    return ERR
                out = j
        out = ERR if out is None else out
        if not g and out != ERR and self.moving(out):
            self.report("E-OWN-006", x, "a moving value can't come out of a match expression (docs/b17-1.md §5 rule 7)")
        return out

    def arms(self, x, t, g, ghost_binders=None):
        """Check (match e case+)'s patterns against t (§7) and yield each arm's body, with its
        binders declared in a scope of its own, which the caller leaves."""
        cases = x.items[2:]
        shapes = self.patterns(x, t)
        ghost = g if ghost_binders is None else ghost_binders
        for case, types in zip(cases, shapes):
            self.scopes.append({})
            for b, bt in zip(case.items[1].items[1:], types):
                self.declare(b, _Bind(bt, "local", ghost=ghost))  # case binders are locals (D41, D82)
            yield case.items[2]

    def patterns(self, x, t):
        """Each case's binder types, checking that the arms name t's constructors once each, in
        order, with one binder per field; ERR for a binder once something is reported."""
        cases = x.items[2:]
        pats = [c.items[1].items for c in cases]
        errs = [[ERR] * (len(p) - 1) for p in pats]
        if t == ERR:
            return errs
        if t[0] == "tuple":
            n = len(parts(t))
            if len(cases) != 1 or pats[0][0].text != "tuple" or len(pats[0]) - 1 != n:
                self.report("E-TYPE-001", x, f"a match on {show(t)} has one arm, (case (tuple x1 ... x{n}) ...) (§7)")
                return errs
            return [parts(t)]
        if t[0] != "data":
            self.report("E-TYPE-001", x.items[1], f"match takes a data value or a tuple, not {show(t)} (§7)")
            return errs
        ctors = self.fields_of(t)
        for k, (cname, fs) in enumerate(ctors):
            if k >= len(cases):
                self.report("E-TYPE-001", x, f"this match has no arm for {cname.text}: arms name every constructor "
                                             f"of {t[1]} once, in order (§7)")
                return errs
            head = pats[k][0]
            if head.text != cname.text:
                self.report("E-TYPE-001", head, f"expected the arm for {cname.text} here: arms name every constructor "
                                                f"of {t[1]} once, in order (§7)")
                return errs
            if len(pats[k]) - 1 != len(fs):
                self.report("E-TYPE-001", cases[k].items[1], f"({cname.text} ...) binds {len(fs)} fields, got "
                                                              f"{len(pats[k]) - 1} (§7)")
                return errs
        if len(cases) > len(ctors):
            self.report("E-TYPE-001", cases[len(ctors)], f"{t[1]} has {len(ctors)} constructors, and this match more "
                                                         f"arms (§7)")
            return errs
        return [[ft for _, ft in fs] for _, fs in ctors]

    def data_operand(self, x, what):
        """The type of x, which must be a data value; ERR, reported, if it isn't."""
        t = self.types[id(x)]
        if t != ERR and t[0] != "data":
            self.report("E-TYPE-001", x, f"{what} takes a data value, not {show(t)} (§7)")
            return ERR
        return t

    def e_is(self, x, g, want, own):
        self.expr(x.items[2], g)
        t = self.data_operand(x.items[2], "is")
        c = x.items[1].text
        if t != ERR and self.ctors.get(c, (None,))[0] != t[1]:
            self.report("E-TYPE-001", x.items[1], f"'{c}' is not a constructor of {t[1]} (docs/b17-1.md §7)")
        return BOOL

    def e_field(self, x, g, want, own):
        self.expr(x.items[1], g)
        return self.field_type(x, self.data_operand(x.items[1], "field"))

    def field_type(self, x, t):
        """(field e F)'s type, for e of type t (§7)."""
        f = x.items[2].text
        if t == ERR:
            return ERR
        for _, fs in self.fields_of(t):
            for name, ft in fs:
                if name.text == f:
                    return ft
        self.report("E-TYPE-001", x.items[2], f"'{f}' is not a field of {t[1]} (docs/b17-1.md §7)")
        return ERR

    def e_get(self, x, g, want, own):
        return self.component(x, self.expr(x.items[1], g))

    def component(self, x, t):
        """(get e K)'s type, for e of type t (§7)."""
        k = x.items[2].value
        if t == ERR:
            return ERR
        if t[0] != "tuple":
            self.report("E-TYPE-001", x.items[1], f"get takes a tuple, not {show(t)} (§7)")
            return ERR
        if not 0 <= k < len(parts(t)):
            self.report("E-TYPE-001", x.items[2], f"{show(t)} has components 0 to {len(parts(t)) - 1} (§7)")
            return ERR
        return parts(t)[k]

    def e_rank(self, x, g, want, own):
        self.expr(x.items[1], True)
        self.data_operand(x.items[1], "rank")
        return INT

    def e_iset_lit(self, x, g, want, own):
        elem = want[1] if want is not None and want[0] == "iset" else ANY  # destination first (§4)
        t = elem
        for e in x.items[1:]:
            u = self.expr(e, True, want=None if elem == ANY else elem)
            j = (elem if self.sub1(u, elem) else None) if elem != ANY else self.join(t, u)
            if j is None:
                self.report("E-TYPE-001", e, f"an element of {show(('iset', elem if elem != ANY else t))} can't be "
                                             f"{show(u)}")
                return ERR
            t = j
        return ("iset", t)

    def e_iset_of(self, x, g, want, own):
        self.scopes.append({})
        (t,) = self.binders(x.items[1].items)
        self.boolean(x.items[2], True)
        self.scopes.pop()
        return ("iset", t)

    def e_map_lit(self, x, g, want, own):
        k0, v0 = (want[1], want[2]) if want is not None and want[0] == "map" else (ANY, ANY)
        k, v = k0, v0
        for entry in x.items[1:]:
            for e, which in ((entry.items[0], 0), (entry.items[1], 1)):
                fixed = (k0, v0)[which]
                u = self.expr(e, True, want=None if fixed == ANY else fixed)
                cur = (k, v)[which]
                j = (fixed if self.sub1(u, fixed) else None) if fixed != ANY else self.join(cur, u)
                if j is None:
                    self.report("E-TYPE-001", e, f"a map entry's {'key' if which == 0 else 'value'} can't be {show(u)}")
                    return ERR
                k, v = (j, v) if which == 0 else (k, j)
        return ("map", k, v)

    def pair(self, x, kinds):
        """The two operands of union, diff or inter, one of the kinds, of the same type; a literal
        operand takes the other's type (§4)."""
        a, b = x.items[1], x.items[2]
        ta = self.expr(a, True)
        tb = self.expr(b, True, want=ta)
        if self.has_any(ta) and not self.has_any(tb):
            ta = self.expr(a, True, want=tb)
        for e, t in ((a, ta), (b, tb)):
            if t != ERR and t[0] not in kinds:
                self.report("E-TYPE-001", e, f"{x.items[0].text} takes {' or '.join(kinds)}s, not {show(t)} (§7)")
                return ERR
        if ERR in (ta, tb):
            return ERR
        if not self.equal(ta, tb) or ta[0] != tb[0]:
            self.report("E-TYPE-001", x, f"{x.items[0].text} of {show(ta)} and {show(tb)}: sets and maps have no "
                                         f"subtyping (§3)")
            return ERR
        return tb if self.has_any(ta) else ta

    def e_union(self, x, g, want, own):
        return self.pair(x, ("iset", "map"))

    def e_diff(self, x, g, want, own):
        return self.pair(x, ("iset",))

    e_inter = e_diff

    def e_update(self, x, g, want, own):
        m = self.expr(x.items[1], True, want=want)
        if m != ERR and m[0] != "map":
            self.report("E-TYPE-001", x.items[1], f"update takes a map, not {show(m)} (§7)")
            return ERR
        k, v = (ANY, ANY) if m == ERR else (m[1], m[2])
        self.expect(x.items[2], k, True)
        self.expect(x.items[3], v, True)
        return m

    def e_lookup(self, x, g, want, own):
        m = self.expr(x.items[1], True)
        if m != ERR and m[0] != "map":
            self.report("E-TYPE-001", x.items[1], f"lookup takes a map, not {show(m)} (§7)")
            return ERR
        self.expect(x.items[2], ANY if m == ERR else m[1], True)
        return ERR if m == ERR else want if m[2] == ANY and want is not None else m[2]

    def contains1(self, x):
        """(contains s x) on a sequence, a set or a map's keys; occurrences on a sequence (§7)."""
        h, s, e = x.items[0].text, x.items[1], x.items[2]
        t = self.expr(s, True)
        if t != ERR and (t[0] in SEQUENCES or h == "contains" and t[0] in ("iset", "map")):
            elem = t[1]
        else:
            if t != ERR:
                self.report("E-TYPE-001", s, f"{h} takes a sequence{', set or map' if h == 'contains' else ''}, "
                                             f"not {show(t)}")
            elem = ERR
        u = self.expr(e, True, want=None if elem in (ERR, ANY) else elem)
        if (self.join(elem, u) is None) if t == ERR or t[0] in SEQUENCES else not self.sub1(u, elem):
            self.report("E-TYPE-001", e, f"{h} looks for {show(u)} in {show(t)}")
        return BOOL if h == "contains" else INT

    def seq_build1(self, x, g, want):
        """docs/b17-1.md §7: a vector or sequence of any element type. Its runtime body is an owned
        position that runs once per element, so it moves no outer variable (§5 rules 2 and 5)."""
        self.integer(x.items[1], g, "seq-build's length")
        fn = x.items[2]
        elem = want[1] if want is not None and want[0] in (("seq",) if g else ("vec",)) else None
        self.scopes.append({})
        self.binder(fn.items[1].items[0], _Bind(INT if g else I64, "binder", ghost=g))
        if g:
            t = self.expr(fn.items[2], True, want=elem)
        else:
            before = dict(self.moves)
            t = self.owned(fn.items[2], elem or ANY)
            for name in sorted(set(self.moves) - set(before)):
                self.report("E-OWN-004", self.moves[name], f"seq-build's body runs once per element, so it can't move "
                                                           f"'{name}' (docs/b17-1.md §5 rule 5)")
            self.moves = before
            self.effects.append(("alloc", x))
        self.scopes.pop()
        if t == ERR:
            return ERR
        if not g and not self.runtime(t):
            self.report("E-TYPE-001", fn.items[2], f"a vector holds a runtime type, not {show(t)} (docs/b17-1.md §3)")
            return ERR
        return ("seq", t) if g else ("vec", t)

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
_FORMS_1 = {h: "e_" + h.replace("-", "_") for h in ("tuple", "match", "is", "field", "get", "rank", "iset-lit",
                                                  "iset-of", "map-lit", "union", "diff", "inter", "update", "lookup")}
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
    subset = 0
    if argv[:2] == ["--subset", "1"]:
        subset, argv = 1, argv[2:]
    if len(argv) != 1:
        print("usage: uv run --no-project b17c/check.py [--subset 1] FILE", file=sys.stderr)
        return 2
    path = argv[0]
    try:
        diags = check(parse(Path(path).read_bytes(), subset), subset)
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
