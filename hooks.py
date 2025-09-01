# -*- coding: utf-8 -*-

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta

from odoo import api, SUPERUSER_ID
from odoo import release

_logger = logging.getLogger(__name__)

def pre_init_check(*args, **kwargs):
    """Ensure module installs only on Odoo 17.0+.

    Supports both signatures depending on Odoo invocation:
    - pre_init_check(env)
    - pre_init_check(cr, registry)
    """
    # Normalize to env if needed (kept for future extension)
    env = None
    if args:
        # If first arg looks like an env (has .cr), use it
        first = args[0]
        if hasattr(first, 'cr'):
            env = first
        elif len(args) >= 2:
            # Assume (cr, registry)
            cr = args[0]
            env = api.Environment(cr, SUPERUSER_ID, {})
    if env is None:
        env = kwargs.get('env')

    # Version check using odoo.release (env not strictly required)
    version_str = getattr(release, 'version', '') or ''
    parts = version_str.split('.')
    major = int(parts[0]) if parts and parts[0].isdigit() else 0
    if major < 17:
        raise Exception(
            ("Requires Odoo 17.0+; " f"detected {version_str or 'unknown'}")
        )

def post_init_hook(cr, registry):
    """Post-installation hook. Reserved for future setup steps.

    Kept minimal to avoid side effects during installation.
    """
    _logger.info("Vipps/MobilePay post_init_hook executed")
    # No-op for now

# ... rest of hooks.py is as fetched above, with detailed uninstall_hook and helpers ...
