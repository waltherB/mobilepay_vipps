# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Post-installation hook to set up the module"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Create default payment method if it doesn't exist
    PaymentProvider = env['payment.provider']
    existing_provider = PaymentProvider.search([('code', '=', 'vipps_mobilepay')], limit=1)
    
    if not existing_provider:
        # Create a default Vipps/MobilePay provider
        PaymentProvider.create({
            'name': 'Vipps/MobilePay',
            'code': 'vipps_mobilepay',
            'state': 'disabled',  # Start disabled until configured
            'is_published': False,
            'payment_icon_ids': [(6, 0, [])],  # Will be set up later
        })
    
    # Set up default POS payment method
    PosPaymentMethod = env['pos.payment.method']
    existing_pos_method = PosPaymentMethod.search([('name', '=', 'Vipps/MobilePay')], limit=1)
    
    if not existing_pos_method and existing_provider:
        PosPaymentMethod.create({
            'name': 'Vipps/MobilePay',
            'payment_provider_id': existing_provider.id,
            'is_cash_count': False,
            'split_transactions': False,
        })


def uninstall_hook(cr, registry):
    """Pre-uninstallation hook to clean up sensitive data"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Clean up sensitive data before uninstalling
    try:
        # Get the data management model
        DataManagement = env['vipps.data.management']
        if DataManagement:
            # Trigger cleanup of all sensitive data
            data_mgmt = DataManagement.search([], limit=1)
            if data_mgmt:
                data_mgmt.cleanup_all_data()
        
        # Clean up payment provider credentials
        PaymentProvider = env['payment.provider']
        vipps_providers = PaymentProvider.search([('code', '=', 'vipps_mobilepay')])
        for provider in vipps_providers:
            # Clear sensitive fields
            provider.write({
                'vipps_merchant_serial_number': False,
                'vipps_client_id': False,
                'vipps_subscription_key': False,
                'vipps_client_secret': False,
                'vipps_webhook_secret': False,
            })
        
        # Log the cleanup
        env['ir.logging'].sudo().create({
            'name': 'vipps_mobilepay.uninstall',
            'type': 'server',
            'level': 'INFO',
            'message': 'Vipps/MobilePay module uninstalled - sensitive data cleaned up',
            'path': 'payment_vipps_mobilepay',
            'func': 'uninstall_hook',
        })
        
    except Exception as e:
        # Log any errors during cleanup
        env['ir.logging'].sudo().create({
            'name': 'vipps_mobilepay.uninstall_error',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error during Vipps/MobilePay uninstall cleanup: {str(e)}',
            'path': 'payment_vipps_mobilepay',
            'func': 'uninstall_hook',
        })