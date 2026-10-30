"""Content hashes: B17-0's (D45, D46), and B17-1's data types and binders (D92).

    uv run --no-project b17c/hashing.py [--subset 1] FILE...

prints one line per item of each FILE: MODULE KIND NAME SPEC-HASH IMPL-HASH, with
`-` where there's no implementation hash (a ghost-fn, a data type, or a spec with no def).

Hashes are defined only for programs that pass tier 0 (WP3). hashes() raises
HashError for the tier 0 failures it meets on the way: an undefined name, mutual
recursion among ghost-fns, and two specs with the same spec hash.
"""
import hashlib
import sys
from pathlib import Path

from syntax import KEYWORDS, KEYWORDS_1, OPS, SUBSET, Form, ParseError, Sym, _head, _print, parse

CORE = parse((Path(__file__).parent / "core.b17").read_bytes(), 0)
CORE1 = parse((Path(__file__).parent / "core1.b17").read_bytes(), 1)  # B17-1's option (docs/b17-1.md §9)
PROOF = {"decreases", "body"}  # a lemma's implementation part (D45)


class HashError(Exception):
    """A tier 0 failure; names holds the items it's about, the one to report at first."""

    def __init__(self, code, reason, names=()):
        self.code, self.reason, self.names = code, reason, names
        super().__init__(f"{code}: {reason}")


def _symbols(x):
    out, stack = set(), [x]
    while stack:
        y = stack.pop()
        if isinstance(y, Form):
            stack.extend(y.items)
        elif isinstance(y, Sym):
            out.add(y.text)
    return out


class _Walk:
    """One definition's name replacements (D45): binders become $k in preorder, the
    definition's own name becomes _, and other items become their spec hashes.

    B17-1's (D92), given a _Data for the module's data types: a data type becomes its spec hash,
    or _ in its own item, and its type parameters $k; a constructor becomes H#i and a field .k."""

    def __init__(self, own, spec_hash, data=None):
        self.own, self.spec_hash, self.env, self.next = own, spec_hash, {}, 0
        self.data, self.tenv, self.own_type = data, {}, None
        self.keywords = KEYWORDS_1 if data else KEYWORDS

    def bind(self, name):
        self.env[name.text] = k = Sym(f"${self.next}")
        self.next += 1
        return k

    def params(self, ps):  # (NAME type)*
        return tuple(Form((self.bind(p.items[0]), self.type(p.items[1]))) for p in ps)

    def type(self, x):
        """A type, whose names are in the type namespace (D82); B17-0's hold none."""
        if self.data is None:
            return x
        if isinstance(x, Sym):
            t = x.text
            if t in self.keywords:
                return x
            if t in self.tenv:
                return self.tenv[t]
            return Sym("_") if t == self.own_type else Sym(self.data.hash(t))
        return Form(tuple(self.type(c) for c in x.items))

    def name(self, x):
        t = x.text
        if t in self.keywords or t in OPS:
            return x
        if t in self.env:
            return self.env[t]
        if self.data is not None and t in self.data.ctors:
            d, i = self.data.ctors[t]
            return Sym(f"{self.data.hash(d)}#{i}")
        return Sym("_") if t == self.own else Sym(self.spec_hash(t))

    def walk(self, x):
        if isinstance(x, Sym):
            return self.name(x)
        if not isinstance(x, Form):
            return x
        h, it = _head(x), x.items
        if h in ("params", "returns"):
            return Form((it[0],) + self.params(it[1:]))
        if h == "ghost-fn":
            return Form((it[0], self.name(it[1]), Form(self.params(it[2].items)), self.type(it[3]))
                        + tuple(self.walk(c) for c in it[4:]))
        if h in ("let", "let-mut", "ghost-let", "ghost-let-mut"):
            if isinstance(it[1], Form):  # (let (param+) (call NAME e*))
                return Form((it[0], Form(self.params(it[1].items)), self.walk(it[2])))
            return Form((it[0], self.bind(it[1]), self.type(it[2]), self.walk(it[3])))
        if h in ("forall", "exists", "fn", "iset-of"):  # binders scoped to the body
            saved = dict(self.env)
            bs = (tuple(self.bind(b) for b in it[1].items) if h == "fn"
                  else self.params(it[1].items))
            body = self.walk(it[2])
            self.env = saved
            return Form((it[0], Form(bs), body))
        if self.data is not None:
            if h == "data":
                return self.data_item(x)
            if h == "obtain":  # its binders are locals, visible after it (D100)
                return Form((it[0], Form(self.params(it[1].items)), self.walk(it[2])))
            if h == "case":  # a pattern's binders are scoped to its arm
                saved = dict(self.env)
                pat = it[1].items
                head = pat[0] if pat[0].text == "tuple" else self.name(pat[0])
                pat = Form((head,) + tuple(self.bind(b) for b in pat[1:]))
                body = self.walk(it[2])
                self.env = saved
                return Form((it[0], pat, body))
            if h == "field":  # (field e F) or a place: F's index in the operand's type
                return Form((it[0], self.walk(it[1]), Sym(f".{self.data.field(it[1], it[2].text)}")))
        return Form(tuple(self.walk(c) for c in it))

    def data_item(self, x):
        """(data D (A*) ctor+): D is _, its parameters $k, constructors #i and fields .k (D92)."""
        _, name, params, *ctors = x.items
        self.own_type = name.text
        for a in params.items:
            self.tenv[a.text] = Sym(f"${len(self.tenv)}")
        fields, out = 0, []
        for i, c in enumerate(ctors):
            fs = []
            for f in c.items[1:]:
                fs.append(Form((Sym(f".{fields}"), self.type(f.items[1]))))
                fields += 1
            out.append(Form((Sym(f"#{i}"),) + tuple(fs)))
        return Form((x.items[0], Sym("_"), Form(tuple(self.tenv.values()))) + tuple(out))


class _Data:
    """A module's data types, for B17-1's hashes: their hashes, constructors and field indexes."""

    def __init__(self, items, data_hash, types):
        self.items, self.hash, self.types = items, data_hash, types
        self.ctors, self.fields = {}, {}
        for name, it in items.items():
            self.fields[name] = {}
            for i, c in enumerate(it.items[3:]):
                self.ctors[c.items[0].text] = (name, i)
                for f in c.items[1:]:
                    self.fields[name][f.items[0].text] = len(self.fields[name])

    def field(self, operand, f):
        """F's index in operand's data type, from the checker's types (D92)."""
        return self.fields[self.types()[id(operand)][1]][f]


def _digest(prefix, data):
    """D46's text form: prefix, then SHA-256 over prefix and data in hex."""
    return prefix + hashlib.sha256(prefix.encode() + data).hexdigest()


def _bytes(tree):
    return _print(tree).encode("utf-8")


def hashes(module, subset=SUBSET, types=None):
    """{name: (kind, spec hash, implementation hash or None)} for the module's items, in order.

    In subset 1 a data type's key is ("data", NAME), since type and value names are apart (D82).
    A field's index comes from its operand's type: types is the checker's, computed if not given."""
    defs = {}  # name -> {item kind: item}; a spec and its def share a name
    datas = {}  # B17-1: type name -> data item
    for m in (CORE, CORE1, module) if subset else (CORE, module):
        for it in m.items[3:]:
            if it.items[0].text == "data":
                datas[it.items[1].text] = it
            else:
                defs.setdefault(it.items[1].text, {})[it.items[0].text] = it
    memo, busy = {}, set()
    known = {}

    def checked():
        if "types" not in known:
            if types is None:
                import check  # check imports this module, so only once it's loaded
                known["types"] = check.types(module, 1)
            else:
                known["types"] = types
        return known["types"]

    def data_hash(name):
        key = ("data", name)
        if key not in memo:
            if name not in datas:
                raise HashError("E-TYPE-002", f"type '{name}' is undefined")
            if key in busy:
                raise HashError("E-TERM-002", f"data type '{name}' is mutually recursive")
            busy.add(key)
            memo[key] = _digest("spec0:", _bytes(walker(name).walk(datas[name])))
            busy.discard(key)
        return memo[key]

    data = _Data(datas, data_hash, checked) if subset else None
    walker = lambda own: _Walk(own, spec_hash, data)

    def spec_part(name):
        d = defs.get(name)
        if d is None:
            raise HashError("E-TYPE-002", f"'{name}' is undefined")
        if "spec" in d:
            return d["spec"]
        if "lemma" in d:
            return Form(tuple(c for c in d["lemma"].items if _head(c) not in PROOF))
        if "ghost-fn" in d:
            return d["ghost-fn"]
        raise HashError("E-TYPE-002", f"def '{name}' has no spec")

    def spec_hash(name):
        if name not in memo:
            if name in busy:  # only ghost-fn bodies can loop; self-calls are _ already
                raise HashError("E-TERM-002", f"'{name}' is mutually recursive")
            busy.add(name)
            memo[name] = _digest("spec0:", _bytes(walker(name).walk(spec_part(name))))
            busy.discard(name)
        return memo[name]

    def impl_hash(name):
        d, w = defs[name], walker(name)
        if "def" in d:
            w.walk(d["spec"])  # numbers the spec's binders first
            part = w.walk(d["def"])
        elif "lemma" in d:
            whole = w.walk(d["lemma"])
            part = Form(whole.items[:2] + tuple(c for c in whole.items[2:] if _head(c) in PROOF))
        else:
            return None
        return _digest("impl0:", spec_hash(name).encode() + b" " + _bytes(part))

    # Hash every spec after the items it mentions, depth first with an explicit stack, so no
    # walk recurses into another item's hash: a long chain of references can't overflow
    # Python's stack, and recursion follows one item's nesting at a time (D55). In subset 1 a
    # name may be a type, a value or both, so its key says which; a constructor leads to its type.
    ctor_of = {c.items[0].text: n for n, it in datas.items() for c in it.items[3:]}

    def deps(key):
        part = datas[key[1]] if key[0] == "data" else spec_part(key)
        syms = _symbols(part)
        return iter(sorted([n for n in syms & defs.keys()]
                           + [("data", n) for n in syms & datas.keys()]
                           + [("data", ctor_of[n]) for n in syms & ctor_of.keys()], key=str))

    def finish(key):
        return data_hash(key[1]) if key[0] == "data" else spec_hash(key)

    roots = [("data", it.items[1].text) if it.items[0].text == "data" else it.items[1].text
             for it in module.items[3:]]
    done = set()
    for root in roots:
        if root in done:
            continue
        done.add(root)
        stack = [(root, deps(root))]
        while stack:
            key, rest = stack[-1]
            nxt = next((n for n in rest if n not in done), None)
            if nxt is None:
                stack.pop()
                finish(key)
            else:
                done.add(nxt)
                stack.append((nxt, deps(nxt)))
    out = {}
    for key in roots:
        if key not in out:
            if isinstance(key, tuple):
                out[key] = ("data", data_hash(key[1]), None)
            else:
                kind = next(k for k in ("spec", "lemma", "ghost-fn", "def") if k in defs[key])
                out[key] = (kind, spec_hash(key), impl_hash(key))
    # D45 and D92: once the rest of tier 0 passes, no two specs, and no two data types, share a spec hash.
    # The core library's option counts, since a reference by hash couldn't tell a copy of it apart.
    seen = {("data", data_hash(it.items[1].text)): ("data", it.items[1].text) for it in CORE1.items[3:]} if subset else {}
    for name, (kind, spec, _) in out.items():
        if kind in ("spec", "data") and seen.setdefault((kind, spec), name) != name:
            first = seen[(kind, spec)]
            show = (lambda n: n[1]) if kind == "data" else (lambda n: n)
            raise HashError("E-TYPE-002", f"{kind} '{show(name)}' is identical to '{show(first)}' up to names",
                            (name, first))
    return out


def report(module, subset=SUBSET):
    return [f"{module.items[1].text} {kind} {name[1] if kind == 'data' else name} {spec} {impl or '-'}"
            for name, (kind, spec, impl) in hashes(module, subset).items()]


if __name__ == "__main__":
    args, subset = sys.argv[1:], SUBSET
    if args[:1] == ["--subset"] and args[1:2] in (["0"], ["1"]):
        args, subset = args[2:], int(args[1])
    if not args:
        sys.exit("usage: uv run --no-project b17c/hashing.py [--subset 1] FILE...")
    for path in args:
        try:
            print("\n".join(report(parse(Path(path).read_bytes(), subset), subset)))
        except (ParseError, HashError, ValueError) as e:
            sys.exit(f"{path}: {e}")
