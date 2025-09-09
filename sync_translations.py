#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synchronize .po files with source strings using TranslationValidator's extractor:
- Ensure required headers exist (UTF-8, Language, etc.)
- Add any missing msgids with msgstr identical to msgid
"""

from pathlib import Path
from typing import Set
import re


def extract_source_strings_with_validator(module_root: Path) -> Set[str]:
    import importlib.util
    vt_path = module_root / 'validate_translations.py'
    spec = importlib.util.spec_from_file_location('vt', str(vt_path))
    vt = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(vt)  # type: ignore
    validator = vt.TranslationValidator()  # type: ignore
    validator._extract_source_strings()
    return set(validator.source_strings)


def ensure_header(po_path: Path):
    content = po_path.read_text(encoding='utf-8')
    if content.startswith('msgid ""') and 'Content-Type: text/plain; charset=UTF-8' in content:
        return  # header present
    # Build minimal header
    lang = po_path.stem
    header = [
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: MobilePay Vipps Payment\\n"',
        '"Report-Msgid-Bugs-To: \\n"',
        '"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"',
        f'"Last-Translator: \\n"',
        f'"Language-Team: {lang}\\n"',
        f'"Language: {lang}\\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        ''
    ]
    # Remove any existing header-like block at top
    lines = content.splitlines()
    start_idx = 0
    if lines and lines[0].startswith('msgid ""'):
        # skip until first blank line after header
        i = 1
        while i < len(lines) and lines[i].strip() != '':
            i += 1
        start_idx = i + 1 if i < len(lines) else i
        tail = '\n'.join(lines[start_idx:])
    else:
        tail = content
    po_path.write_text('\n'.join(header) + tail, encoding='utf-8')


def parse_po_msgids(po_path: Path) -> Set[str]:
    msgids: Set[str] = set()
    with po_path.open('r', encoding='utf-8') as f:
        current = None
        in_msgid = False
        for raw in f:
            line = raw.rstrip('\n')
            if line.startswith('msgid '):
                text = line[6:]
                current = text.strip().strip('"')
                in_msgid = True
            elif in_msgid and line.startswith('"') and not line.startswith('""'):
                # multiline msgid continuation
                current = (current or '') + line.strip().strip('"')
            elif line.startswith('msgstr '):
                if current is not None and current != '':
                    msgids.add(current)
                current = None
                in_msgid = False
            elif line.strip() == '':
                in_msgid = False
    return msgids


def append_entries(po_path: Path, missing: Set[str]):
    if not missing:
        return
    with po_path.open('a', encoding='utf-8') as f:
        f.write('\n')
        for msgid in sorted(missing):
            f.write(f'msgid "{msgid}"\n')
            f.write(f'msgstr "{msgid}"\n\n')


def main() -> int:
    module_root = Path('.')
    i18n_dir = module_root / 'i18n'
    sources = extract_source_strings_with_validator(module_root)
    print(f"Found {len(sources)} source strings via validator")
    for po in sorted(i18n_dir.glob('*.po')):
        ensure_header(po)
        existing = parse_po_msgids(po)
        missing = sources - existing
        append_entries(po, missing)
        print(f"{po.name}: added {len(missing)} entries and ensured header")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


