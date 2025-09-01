# -*- coding: utf-8 -*-

# Expose hook functions for Odoo (referenced by name in __manifest__.py)
from .hooks import pre_init_check, post_init_hook, uninstall_hook

# Regular module imports
from . import models
from . import controllers

__all__ = [
    "pre_init_check",
    "post_init_hook",
    "uninstall_hook",
]