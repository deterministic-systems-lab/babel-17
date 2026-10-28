"""Port AlgoVeri's Dafny specs into gym/tasks/algoveri/ (task format: see harness.py).

    git clone https://github.com/haoyuzhao123/algoveri <dir>
    uv run gym/import_algoveri.py <dir>

AlgoVeri (Apache-2.0) has no reference solutions, so ported tasks have an empty solution
section; check-tasks then requires only that an empty body fails and that the frozen
contracts are well-formed. Preamble functions and predicates are made ghost, as in the
seed tasks, so an implementation can't run the spec itself. Tasks whose method lives
inside a class are skipped: the generated <Name>_Check wrapper calls a top-level method.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tasks" / "algoveri"
# Specs that are ill-formed under Dafny 4.11 as written, or unsatisfiable, so no agent could solve them.
BROKEN = {"polymul_karatsuba": "applies << to int; Dafny 4.11 requires a bitvector type",
          "matrix_multiplication": "dot_product's body fails its own well-formedness check (index out of range)",
          "rod_cutting": "n has no lower bound, and at n = -1 no strategy of positive cuts exists"}


def ghost(preamble):
    """Make the frozen functions and predicates ghost, so an implementation can't run the spec.
    A by-method declaration made ghost no longer parses, so check-tasks reports it."""
    return re.sub(r"^(\s*(?:(?:static|opaque)\s+)*)(function|predicate)\b", r"\1ghost \2",
                  preamble, flags=re.M)


def section(text, name):
    m = re.search(rf"// <{name}>\n(.*?)// </{name}>", text, re.S)
    return m.group(1).strip() if m else ""


def main(src):
    src = Path(src)
    commit = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "LICENSE", OUT / "LICENSE")
    ported, skipped = 0, []
    for spec_file in sorted(src.glob("algoveri_data/*/dafny_spec.dfy")):
        name, text = spec_file.parent.name, spec_file.read_text()
        preamble = section(text, "preamble")
        if name in BROKEN or re.search(r"^\s*class\b", preamble, re.M):
            skipped.append(name)
            continue
        spec = section(text, "spec")
        # Declarations before the method (e.g. a datatype) belong with the frozen preamble.
        head, sig = spec[:spec.index("method")], spec[spec.index("method"):]
        preamble = "\n\n".join(p for p in (preamble, section(text, "helpers"), head.strip()) if p)
        preamble = ghost(preamble)
        nl = (spec_file.parent / "dafny_nl.txt").read_text().strip()
        intent = re.split(r"(?<=\.)\s", nl, maxsplit=1)[0]
        (OUT / f"{name}.dfy").write_text(
            f"// intent: {intent}\n// difficulty: algoveri\n"
            f"// source: AlgoVeri {commit[:12]} algoveri_data/{name}/dafny_spec.dfy (Apache-2.0)\n"
            f"//== preamble\n{preamble}\n//== signature\n{sig}\n//== solution\n")
        ported += 1
    print(f"ported {ported}; skipped {len(skipped)} (class-based, or in BROKEN): {', '.join(skipped)}")


if __name__ == "__main__":
    main(sys.argv[1])
