#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fill missing translations in all .po files using the POT template.

For each msgid present in i18n/payment_vipps_mobilepay.pot but missing in a .po file,
append a translation block with msgstr identical to msgid (fallback to source text).
"""

from pathlib import Path
import sys


def parse_pot_strings(pot_path: Path) -> list[str]:
    strings: list[str] = []
    if not pot_path.exists():
        raise FileNotFoundError(f"POT file not found: {pot_path}")
    current_msgid: str | None = None
    with pot_path.open('r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith('msgid '):
                current_msgid = line[6:].strip().strip('"')
            elif line.startswith('msgstr '):
                if current_msgid is not None:
                    strings.append(current_msgid)
                    current_msgid = None
            else:
                # ignore
                pass
    return [s for s in strings if s]


def parse_po_translations(po_path: Path) -> set[str]:
    translations: set[str] = set()
    current_msgid: str | None = None
    current_msgstr_started = False
    with po_path.open('r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith('msgid '):
                # store previous if any
                current_msgid = line[6:].strip().strip('"')
                current_msgstr_started = False
            elif line.startswith('msgstr '):
                current_msgstr_started = True
                if current_msgid is not None:
                    translations.add(current_msgid)
                    current_msgid = None
            else:
                # ignore
                pass
    return translations


def append_missing(po_path: Path, missing: list[str]) -> None:
    if not missing:
        return
    with po_path.open('a', encoding='utf-8') as f:
        f.write("\n")
        for msgid in missing:
            f.write(f'msgid "{msgid}"\n')
            f.write(f'msgstr "{msgid}"\n\n')


def main() -> int:
    module_root = Path('.')
    i18n_dir = module_root / 'i18n'
    pot_path = i18n_dir / 'payment_vipps_mobilepay.pot'

    # Ensure POT exists (ask user to run validator/update first if missing)
    if not pot_path.exists():
        print(f"POT template not found at {pot_path}. Run validate_translations.py first.")
        return 1

    pot_strings = parse_pot_strings(pot_path)
    pot_set = set(pot_strings)
    print(f"Loaded {len(pot_strings)} msgids from POT")

    po_files = sorted(i18n_dir.glob('*.po'))
    if not po_files:
        print("No .po files found under i18n/")
        return 0

    total_added = 0
    for po in po_files:
        have = parse_po_translations(po)
        missing = sorted(pot_set - have)
        append_missing(po, missing)
        print(f"{po.name}: added {len(missing)} entries")
        total_added += len(missing)

    print(f"Done. Added {total_added} missing translations across {len(po_files)} files.")
    return 0


if __name__ == '__main__':
    sys.exit(main())


