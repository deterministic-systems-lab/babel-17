"""B17-0 content hashes (D45, D46).

    uv run --no-project b17c/hashing.py FILE...

prints one line per item of each FILE: MODULE KIND NAME SPEC-HASH IMPL-HASH, with
`-` where there's no implementation hash (a ghost-fn, or a spec with no def).

Hashes are defined only for programs that pass tier 0 (WP3). hashes() raises
HashError for the tier 0 failures it meets on the way: an undefined name, mutual
recursion among ghost-fns, and two specs with the same spec hash.
"""
import hashlib
import sys
from pathlib import Path

from syntax import KEYWORDS, OPS, Form, ParseError, Sym, _head, _print, parse

CORE = parse((Path(__file__).parent / "core.b17").read_bytes())
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
    definition's own name becomes _, and other items become their spec hashes."""

    def __init__(self, own, spec_hash):
        self.own, self.spec_hash, self.env, self.next = own, spec_hash, {}, 0

    def bind(self, name):
        self.env[name.text] = k = Sym(f"${self.next}")
        self.next += 1
        return k

    def params(self, ps):  # (NAME type)*; types hold no names
        return tuple(Form((self.bind(p.items[0]), p.items[1])) for p in ps)

    def name(self, x):
        t = x.text
        if t in KEYWORDS or t in OPS:
            return x
        if t in self.env:
            return self.env[t]
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
            return Form((it[0], self.name(it[1]), Form(self.params(it[2].items)))
                        + tuple(self.walk(c) for c in it[3:]))
        if h in ("let", "let-mut", "ghost-let", "ghost-let-mut"):
            if isinstance(it[1], Form):  # (let (param+) (call NAME e*))
                return Form((it[0], Form(self.params(it[1].items)), self.walk(it[2])))
            return Form((it[0], self.bind(it[1])) + tuple(self.walk(c) for c in it[2:]))
        if h in ("forall", "exists", "fn"):  # binders scoped to the body
            saved = dict(self.env)
            bs = (tuple(self.bind(b) for b in it[1].items) if h == "fn"
                  else self.params(it[1].items))
            body = self.walk(it[2])
            self.env = saved
            return Form((it[0], Form(bs), body))
        return Form(tuple(self.walk(c) for c in it))


def _digest(prefix, data):
    """D46's text form: prefix, then SHA-256 over prefix and data in hex."""
    return prefix + hashlib.sha256(prefix.encode() + data).hexdigest()


def _bytes(tree):
    return _print(tree).encode("utf-8")


def hashes(module):
    """{name: (kind, spec hash, implementation hash or None)} for the module's items, in order."""
    defs = {}  # name -> {item kind: item}; a spec and its def share a name
    for m in (CORE, module):
        for it in m.items[3:]:
            defs.setdefault(it.items[1].text, {})[it.items[0].text] = it
    memo, busy = {}, set()

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
            memo[name] = _digest("spec0:", _bytes(_Walk(name, spec_hash).walk(spec_part(name))))
            busy.discard(name)
        return memo[name]

    def impl_hash(name):
        d, w = defs[name], _Walk(name, spec_hash)
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
    # Python's stack, and recursion follows one item's nesting at a time (D55).
    done = set()
    for root in [it.items[1].text for it in module.items[3:]]:
        if root in done:
            continue
        done.add(root)
        stack = [(root, iter(sorted(_symbols(spec_part(root)) & defs.keys())))]
        while stack:
            name, rest = stack[-1]
            nxt = next((n for n in rest if n not in done), None)
            if nxt is None:
                stack.pop()
                spec_hash(name)
            else:
                done.add(nxt)
                stack.append((nxt, iter(sorted(_symbols(spec_part(nxt)) & defs.keys()))))
    out = {}
    for it in module.items[3:]:
        name = it.items[1].text
        if name not in out:
            kind = next(k for k in ("spec", "lemma", "ghost-fn", "def") if k in defs[name])
            out[name] = (kind, spec_hash(name), impl_hash(name))
    # D45: once the rest of tier 0 passes, no two specs may share a spec hash.
    seen = {}
    for name, (kind, spec, _) in out.items():
        if kind == "spec" and seen.setdefault(spec, name) != name:
            raise HashError("E-TYPE-002", f"spec '{name}' is identical to '{seen[spec]}' up to names",
                            (name, seen[spec]))
    return out


def report(module):
    return [f"{module.items[1].text} {kind} {name} {spec} {impl or '-'}"
            for name, (kind, spec, impl) in hashes(module).items()]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: uv run --no-project b17c/hashing.py FILE...")
    for path in sys.argv[1:]:
        try:
            print("\n".join(report(parse(Path(path).read_bytes()))))
        except (ParseError, HashError) as e:
            sys.exit(f"{path}: {e}")
