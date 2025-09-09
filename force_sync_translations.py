#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force-sync .po files with extracted source strings by scanning content to detect
truly missing msgid blocks and appending them with msgstr identical to msgid.
This avoids parser limitations (e.g., multiline msgids or special characters).
"""

from pathlib import Path
from typing import Set


def extract_source_strings(module_root: Path) -> Set[str]:
    import importlib.util
    vt_path = module_root / 'validate_translations.py'
    spec = importlib.util.spec_from_file_location('vt', str(vt_path))
    vt = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(vt)  # type: ignore
    validator = vt.TranslationValidator()  # type: ignore
    validator._extract_source_strings()
    return set(validator.source_strings)


def ensure_present(po_path: Path, sources: Set[str]) -> int:
    content = po_path.read_text(encoding='utf-8')
    added = 0
    with po_path.open('a', encoding='utf-8') as f:
        for s in sorted(sources):
            # Exact literal search for msgid line to avoid false positives
            needle = f'msgid "{s}"'
            if needle not in content:
                f.write('\n')
                f.write(needle + '\n')
                f.write(f'msgstr "{s}"\n')
                f.write('\n')
                added += 1
    return added


def main() -> int:
    root = Path('.')
    i18n = root / 'i18n'
    sources = extract_source_strings(root)
    print(f"Found {len(sources)} source strings")
    total_added = 0
    for po in sorted(i18n.glob('*.po')):
        added = ensure_present(po, sources)
        print(f"{po.name}: added {added}")
        total_added += added
    print(f"Done. Total added: {total_added}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


