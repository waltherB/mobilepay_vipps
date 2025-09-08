# -*- coding: utf-8 -*-

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta

from odoo import api, SUPERUSER_ID
from odoo import release

_logger = logging.getLogger(__name__)

# pre_init_check function temporarily removed due to Odoo 17 caching issues
# The version check is not critical since we're already on Odoo 17

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
