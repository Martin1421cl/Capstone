"""Uso: python -m ksecure <archivo o carpeta> [...]  (como `ferret-scan --file`)."""

import os
import sys

from ksecure.preprocessors import process_file
from ksecure.validators import default_validators


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                yield from (os.path.join(root, f) for f in sorted(files))
        else:
            yield p


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows no muestra tildes por defecto
    validators = default_validators()
    total = 0
    for path in iter_files(argv):
        content = process_file(path)
        if not content.success:
            print(f"[omitido] {path}: {content.error}")
            continue
        matches = [m for v in validators for m in v.validate_content(content.text, content.filename)]
        total += len(matches)
        print(f"\n== {path} ({content.processor_type}, {len(matches)} hallazgos)")
        for m in sorted(matches, key=lambda m: m.line_number):
            print(f"  línea {m.line_number:>4}  {m.type:<16} {m.confidence_level.value:<6} "
                  f"{m.risk_level.value:<12} {m.text}")
    print(f"\nTotal: {total} hallazgos")
    return 1 if total else 0  # código 1 si hay datos sensibles, útil para CI como ferret-scan


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
