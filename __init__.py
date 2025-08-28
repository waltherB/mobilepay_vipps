# -*- coding: utf-8 -*-

from . import models
from . import controllers
# Hook functions are imported from hooks.py to be exposed at module level


def pre_init_check(cr, registry):
    """Pre-initialization check to ensure all required modules are installed"""
    # This function is now handled by the pre_init_check hook in hooks.py
    pass


def post_init_hook(cr, registry):
    """Post-installation hook to set up the module"""
    # This function is now handled by the post_init_hook hook in hooks.py
    pass


def uninstall_hook(cr, registry):
    """Pre-uninstallation hook to clean up sensitive data"""
    # This function is now handled by the uninstall_hook hook in hooks.py
    pass