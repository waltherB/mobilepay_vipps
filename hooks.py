# -*- coding: utf-8 -*-

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta

from odoo import api, SUPERUSER_ID
from odoo import release

_logger = logging.getLogger(__name__)

def pre_init_check(env_or_cr, registry=None):
    """Ensure module installs only on Odoo 17.0+.
    
    Handles both calling conventions:
    - pre_init_check(env) - when called with environment
    - pre_init_check(cr, registry) - when called with cursor and registry
    
    Args:
        env_or_cr: Either an Environment object or database cursor
        registry: Odoo registry (optional, when first arg is cursor)
    """
    # Version check using odoo.release (doesn't need database access)
    version_str = getattr(release, 'version', '') or ''
    parts = version_str.split('.')
    major = int(parts[0]) if parts and parts[0].isdigit() else 0
    if major < 17:
        raise Exception(
            f"Vipps/MobilePay module requires Odoo 17.0+; detected {version_str or 'unknown'}"
        )
    
    _logger.info("Pre-init check passed: Odoo %s detected", version_str)

def post_init_hook(cr, registry):
    """Post-installation hook. Reserved for future setup steps.

    Kept minimal to avoid side effects during installation.
    """
    _logger.info("Vipps/MobilePay post_init_hook executed")
    # No-op for now

def uninstall_hook(cr, registry):
    """
    Clean up after module uninstall.

    - Delete cron jobs created by this module (if any).
    - Remove ir.config_parameter keys.
    - Don't touch core tables or Odoo-managed xml_id records.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Vipps/MobilePay uninstall_hook executed")

    # Remove scheduled actions/crons set by module (example xml_id below)
    cron_xml_ids = [
        'mobilepay_vipps.ir_cron_vipps_sync',
        # Add other crons here as needed
    ]
    for xml_id in cron_xml_ids:
        cron = env.ref(xml_id, raise_if_not_found=False)
        if cron:
            try:
                cron.sudo().unlink()
                _logger.info(f"Unlinked cron job: {xml_id}")
            except Exception as e:
                _logger.warning(f"Could not unlink cron job {xml_id}: {e}")

    # Remove ir.config_parameter keys set by module
    config_keys = [
        'vipps.webhook_secret',
        'vipps.merchant_serial',
        'vipps.api_key',
        # Add additional keys as needed
    ]
    param_model = env['ir.config_parameter'].sudo()
    for key in config_keys:
        params = param_model.search([('key', '=', key)])
        if params:
            params.unlink()
            _logger.info(f"Removed ir.config_parameter: {key}")

    # Add other uninstall clean-ups here as needed (avoid touching core tables)

    _logger.info("Vipps/MobilePay uninstall_hook completed successfully.")
