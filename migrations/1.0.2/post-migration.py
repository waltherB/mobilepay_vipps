# -*- coding: utf-8 -*-
"""
Migration script for Vipps/MobilePay module version 1.0.2
Ensures new webhook fields are properly added to the database
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration script to add new webhook fields to payment_provider table
    """
    _logger.info("Starting migration to version 1.0.2")
    
    # Check if webhook fields exist, if not add them
    webhook_fields = [
        ('vipps_webhook_id', 'varchar'),
        ('vipps_system_name', 'varchar'),
        ('vipps_system_version', 'varchar'),
        ('vipps_plugin_name', 'varchar'),
        ('vipps_plugin_version', 'varchar'),
        ('vipps_last_credential_update', 'timestamp'),
        ('vipps_webhook_security_logging', 'boolean'),
    ]
    
    for field_name, field_type in webhook_fields:
        try:
            # Check if column exists
            cr.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'payment_provider' 
                AND column_name = %s
            """, (field_name,))
            
            if not cr.fetchone():
                # Column doesn't exist, add it
                _logger.info(f"Adding column {field_name} to payment_provider table")
                cr.execute(f"""
                    ALTER TABLE payment_provider 
                    ADD COLUMN {field_name} {field_type}
                """)
                _logger.info(f"Successfully added column {field_name}")
            else:
                _logger.info(f"Column {field_name} already exists, skipping")
                
        except Exception as e:
            _logger.error(f"Error adding column {field_name}: {str(e)}")
            # Continue with other fields even if one fails
            continue
    
    # Set default values for new fields
    try:
        cr.execute("""
            UPDATE payment_provider 
            SET vipps_system_name = 'Odoo ERP',
                vipps_plugin_name = 'vipps-mobilepay-odoo',
                vipps_plugin_version = '1.0.2'
            WHERE code = 'vipps' 
            AND (vipps_system_name IS NULL OR vipps_plugin_name IS NULL OR vipps_plugin_version IS NULL)
        """)
        _logger.info("Set default values for new webhook fields")
    except Exception as e:
        _logger.error(f"Error setting default values: {str(e)}")
    
    _logger.info("Migration to version 1.0.2 completed")