# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import hooks as _hooks
from odoo import release


def pre_init_check(env):
    """Ensure module installs only on Odoo 17.0+ (expects env)."""
    version_str = getattr(release, 'version', '') or ''
    parts = version_str.split('.')
    major = int(parts[0]) if parts and parts[0].isdigit() else 0
    if major < 17:
        raise Exception(
            ("Requires Odoo 17.0+; " f"detected {version_str or 'unknown'}")
        )


def post_init_hook(cr, registry):
    """Post-installation hook. No-op reserved for future setup."""
    return None


def uninstall_hook(cr, registry):
    """Delegate to detailed uninstall hook in hooks.py."""
    return _hooks.uninstall_hook(cr, registry)