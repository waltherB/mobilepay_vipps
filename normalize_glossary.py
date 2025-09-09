#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize English translations (en_US, en_GB) to a consistent glossary.

For specific msgid variants (case/ALLCAPS/camelCase), set msgstr to the
preferred human-facing form. Does not modify msgid.
"""

from pathlib import Path
from typing import Dict


GLOSSARY: Dict[str, str] = {
    # Fields
    'phoneNumber': 'Phone Number',
    'birthDate': 'Birth Date',
    'address': 'Address',
    'security': 'Security',
    # Actions / buttons
    'cancel': 'Cancel',
    'success': 'Success',
    # Statuses - normalize to Title Case
    'created': 'Created',
    'CREATED': 'Created',
    'authorized': 'Authorized',
    'AUTHORIZED': 'Authorized',
    'captured': 'Captured',
    'CAPTURED': 'Captured',
    'cancelled': 'Cancelled',
    'CANCELLED': 'Cancelled',
    'refunded': 'Refunded',
    'REFUNDED': 'Refunded',
    'failed': 'Failed',
    'FAILED': 'Failed',
    'expired': 'Expired',
    'EXPIRED': 'Expired',
    'aborted': 'Aborted',
    'ABORTED': 'Aborted',
    'terminated': 'Terminated',
    'TERMINATED': 'Terminated',
    'active': 'Active',
    'annual': 'Annual',
    'completed': 'Completed',
    'consent': 'Consent',
    'critical': 'Critical',
    'disabled': 'Disabled',
    'high': 'High',
    'info': 'Info',
    'medium': 'Medium',
    'monthly': 'Monthly',
    'overdue': 'Overdue',
    'quarterly': 'Quarterly',
    'true': 'True',
    'unknown': 'Unknown',
    'welcome': 'Welcome',
}


def normalize_file(po_path: Path) -> int:
    lines = po_path.read_text(encoding='utf-8').splitlines()
    i = 0
    changes = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('msgid '):
            msgid = line[6:].strip().strip('"')
            # find msgstr line
            j = i + 1
            while j < len(lines) and not lines[j].startswith('msgstr '):
                j += 1
            if j < len(lines) and lines[j].startswith('msgstr '):
                desired = None
                # Exact msgid mapping
                if msgid in GLOSSARY:
                    desired = GLOSSARY[msgid]
                # Also map pure case variants if listed
                elif msgid.lower() in GLOSSARY:
                    desired = GLOSSARY[msgid.lower()]
                if desired is not None:
                    current_msgstr = lines[j][7:].strip().strip('"')
                    new_line = f'msgstr "{desired}"'
                    if current_msgstr != desired:
                        lines[j] = new_line
                        changes += 1
                i = j
        i += 1
    if changes:
        po_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return changes


def main() -> int:
    i18n_dir = Path('i18n')
    total = 0
    for lang in ('en_US', 'en_GB'):
        po = i18n_dir / f'{lang}.po'
        if po.exists():
            c = normalize_file(po)
            print(f"{po.name}: {c} entries normalized")
            total += c
    print(f"Done. Total normalized entries: {total}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


