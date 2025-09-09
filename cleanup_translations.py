#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prune .po files to only include msgids present in the POT and optionally
normalize a few English term capitalizations for consistency.
"""

from pathlib import Path
import sys


def read_pot_msgids(pot_path: Path) -> list[str]:
    msgids: list[str] = []
    with pot_path.open('r', encoding='utf-8') as f:
        current = None
        for raw in f:
            line = raw.strip()
            if line.startswith('msgid '):
                current = line[6:].strip().strip('"')
            elif line.startswith('msgstr '):
                if current is not None and current != "":
                    msgids.append(current)
                current = None
    return msgids


def iter_po_entries(lines: list[str]):
    i = 0
    n = len(lines)
    while i < n:
        # Find msgid start
        if lines[i].startswith('msgid '):
            start = i
            msgid = lines[i][6:].strip().strip('"')
            i += 1
            # advance to msgstr
            while i < n and not lines[i].startswith('msgstr '):
                i += 1
            if i < n and lines[i].startswith('msgstr '):
                # include msgstr line
                i += 1
                # include any continuation lines
                while i < n and (lines[i].strip() == '' or lines[i].startswith('"')):
                    i += 1
            end = i
            yield msgid, start, end
        else:
            i += 1


def prune_po_to_pot(po_path: Path, pot_msgids: set[str]) -> int:
    with po_path.open('r', encoding='utf-8') as f:
        lines = f.readlines()

    header_end = 0
    # keep initial header (until first blank line after the initial msgstr "")
    for idx, line in enumerate(lines):
        if line.strip() == '' and idx > 0:
            header_end = idx + 0
            break

    to_keep = [True] * len(lines)
    removed = 0
    for msgid, start, end in iter_po_entries(lines):
        if msgid not in pot_msgids:
            for j in range(start, end):
                to_keep[j] = False
            removed += 1

    new_lines = []
    for idx, keep in enumerate(to_keep):
        if keep:
            new_lines.append(lines[idx])

    with po_path.open('w', encoding='utf-8') as f:
        f.writelines(new_lines)

    return removed


def normalize_english_terms(po_path: Path) -> int:
    replacements = {
        'Finalising...': 'Finalizing...',
        'Initialising payment...': 'Initializing payment...',
        'Authorised': 'Authorized',
    }
    content = po_path.read_text(encoding='utf-8')
    updated = content
    for old, new in replacements.items():
        updated = updated.replace(f'msgstr "{old}"', f'msgstr "{new}"')
    if updated != content:
        po_path.write_text(updated, encoding='utf-8')
        return 1
    return 0


def main() -> int:
    module_root = Path('.')
    i18n_dir = module_root / 'i18n'
    pot_path = i18n_dir / 'payment_vipps_mobilepay.pot'
    if not pot_path.exists():
        print("POT template missing. Run validate_translations.py to generate it.")
        return 1
    pot_msgids = set(read_pot_msgids(pot_path))
    print(f"POT contains {len(pot_msgids)} msgids")

    total_removed = 0
    normalized = 0
    for po in sorted(i18n_dir.glob('*.po')):
        removed = prune_po_to_pot(po, pot_msgids)
        total_removed += removed
        if po.stem in { 'en_US', 'en_GB' }:
            normalized += normalize_english_terms(po)
        print(f"{po.name}: removed {removed} entries")

    print(f"Done. Removed {total_removed} entries. Normalized English files: {normalized}")
    return 0


if __name__ == '__main__':
    sys.exit(main())


