#!/usr/bin/env python3
"""
Diagnostic script to check webhook registration status
"""

import logging
import sys

# Add Odoo to path
sys.path.append('/opt/odoo17')

import odoo
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def diagnose_webhook_registration():
    """Check webhook registration status for recent transactions"""
    
    # Initialize Odoo
    odoo.tools.config.parse_config(['-c', '/etc/odoo17/odoo.conf'])
    
    with api.Environment.manage():
        registry = odoo.registry(odoo.tools.config['db_name'])
        
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            
            # Find recent Vipps transactions
            transactions = env['payment.transaction'].search([
                ('provider_code', '=', 'vipps'),
                ('create_date', '>=', '2025-11-17 00:00:00')
            ], order='create_date desc', limit=10)
            
            print("\n" + "="*80)
            print("WEBHOOK REGISTRATION DIAGNOSTIC REPORT")
            print("="*80 + "\n")
            
            for tx in transactions:
                print(f"Transaction: {tx.reference}")
                print(f"  Created: {tx.create_date}")
                print(f"  State: {tx.state}")
                print(f"  Vipps Payment Reference: {tx.vipps_payment_reference or 'Not set'}")
                print(f"  Vipps Payment State: {tx.vipps_payment_state or 'Not set'}")
                print(f"  Webhook ID: {tx.vipps_webhook_id or 'NOT REGISTERED'}")
                print(f"  Webhook Secret: {'SET' if tx.vipps_webhook_secret else 'NOT SET'}")
                if tx.vipps_webhook_secret:
                    print(f"  Webhook Secret Length: {len(tx.vipps_webhook_secret)}")
                print(f"  Webhook Received: {tx.vipps_webhook_received}")
                print()
            
            # Check provider configuration
            provider = env['payment.provider'].search([
                ('code', '=', 'vipps')
            ], limit=1)
            
            if provider:
                print("\nProvider Configuration:")
                print(f"  Name: {provider.name}")
                print(f"  Environment: {provider.vipps_environment}")
                print(f"  Webhook URL: {provider._get_vipps_webhook_url()}")
                print(f"  Webhook API URL: {provider._get_vipps_webhook_api_url()}")
                print(f"  Provider Webhook Secret: {'SET' if provider.vipps_webhook_secret else 'NOT SET'}")
                if provider.vipps_webhook_secret:
                    print(f"  Provider Secret Length: {len(provider.vipps_webhook_secret_decrypted)}")
            
            print("\n" + "="*80)
            print("DIAGNOSIS:")
            print("="*80)
            
            no_webhook_id = transactions.filtered(lambda t: not t.vipps_webhook_id)
            if no_webhook_id:
                print(f"\n⚠️  {len(no_webhook_id)} transactions have NO webhook ID")
                print("   This means per-payment webhook registration is NOT working!")
                print("\n   Possible causes:")
                print("   1. _register_payment_webhook() is not being called")
                print("   2. Webhook API request is failing silently")
                print("   3. Payment creation is using a different code path")
            
            no_secret = transactions.filtered(lambda t: not t.vipps_webhook_secret)
            if no_secret:
                print(f"\n⚠️  {len(no_secret)} transactions have NO per-payment webhook secret")
                print("   Signature validation will fail for these payments!")
            
            has_webhook = transactions.filtered(lambda t: t.vipps_webhook_id and t.vipps_webhook_secret)
            if has_webhook:
                print(f"\n✅ {len(has_webhook)} transactions have proper webhook registration")
            
            print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    diagnose_webhook_registration()
