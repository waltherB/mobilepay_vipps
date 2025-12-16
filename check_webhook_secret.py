#!/usr/bin/env python3
"""
Check webhook secret configuration
Run this in Odoo shell to diagnose webhook secret issues
"""

# To run in Odoo shell:
# python3 odoo-bin shell -d your_database -c your_config.conf

# Then paste this code:

provider = env['payment.provider'].search([('code', '=', 'vipps')], limit=1)

if provider:
    print("=" * 60)
    print("WEBHOOK SECRET DIAGNOSTIC")
    print("=" * 60)
    print(f"Provider: {provider.name}")
    print(f"Environment: {provider.vipps_environment}")
    print(f"State: {provider.state}")
    print()
    
    print("WEBHOOK CONFIGURATION:")
    print(f"  Webhook ID: {provider.vipps_webhook_id or 'NOT SET'}")
    print(f"  Webhook URL: {provider._get_vipps_webhook_url()}")
    print()
    
    print("SECRET STATUS:")
    webhook_secret = provider.vipps_webhook_secret
    webhook_secret_encrypted = provider.vipps_webhook_secret_encrypted
    webhook_secret_decrypted = provider.vipps_webhook_secret_decrypted
    
    print(f"  Plaintext secret exists: {'Yes' if webhook_secret else 'No'}")
    print(f"  Encrypted secret exists: {'Yes' if webhook_secret_encrypted else 'No'}")
    print(f"  Decrypted secret exists: {'Yes' if webhook_secret_decrypted else 'No'}")
    
    if webhook_secret_decrypted:
        print(f"  Secret length: {len(webhook_secret_decrypted)} characters")
        print(f"  Secret (first 10 chars): {webhook_secret_decrypted[:10]}...")
        print(f"  Secret (last 10 chars): ...{webhook_secret_decrypted[-10:]}")
    else:
        print("  ⚠️  NO SECRET FOUND!")
    
    print()
    print("DIAGNOSIS:")
    
    if not webhook_secret_decrypted:
        print("  ❌ No webhook secret configured")
        print("  → ACTION: Register webhook to get secret from Vipps")
    elif len(webhook_secret_decrypted) == 88:
        print("  ⚠️  Secret length is 88 (base64 encoded 64-byte secret)")
        print("  → This matches your logs")
        print("  → But Vipps signature doesn't match")
        print("  → ACTION: Re-register webhook to get fresh secret")
    else:
        print(f"  ℹ️  Secret length: {len(webhook_secret_decrypted)}")
        print("  → Check if this matches Vipps expectations")
    
    print()
    print("RECOMMENDED ACTIONS:")
    print("1. Click 'Re-register Webhook (New Secret)' button")
    print("2. Check logs for webhook registration response")
    print("3. Verify secret is stored: provider.vipps_webhook_secret")
    print("4. Test a new payment")
    print("5. Check if signature validation passes")
    
else:
    print("❌ No Vipps provider found!")
