#!/usr/bin/env python3
"""
Delete orphaned webhooks automatically (no confirmation needed)
Run this in Odoo shell
"""

# Get Vipps provider
provider = env['payment.provider'].search([('code', '=', 'vipps')], limit=1)

if not provider:
    print("❌ No Vipps provider found")
else:
    print(f"✅ Found provider: {provider.name}")
    
    # Get all registered webhooks
    print("\n🔧 Fetching registered webhooks...")
    try:
        response = provider._make_webhook_api_request('GET', 'webhooks/v1/webhooks')
        webhooks = response.get('webhooks', [])
        print(f"✅ Found {len(webhooks)} registered webhooks")
        
        # Get all transactions with webhook IDs
        transactions = env['payment.transaction'].search([
            ('provider_code', '=', 'vipps'),
            ('vipps_webhook_id', '!=', False)
        ])
        
        stored_webhook_ids = set(tx.vipps_webhook_id for tx in transactions if tx.vipps_webhook_id)
        print(f"✅ Found {len(stored_webhook_ids)} webhooks with stored secrets in transactions")
        
        # Find orphaned webhooks (registered but no secret stored)
        orphaned = []
        for webhook in webhooks:
            webhook_id = webhook.get('id')
            if webhook_id not in stored_webhook_ids:
                orphaned.append(webhook)
        
        print(f"\n⚠️  Found {len(orphaned)} orphaned webhooks (no stored secret)")
        
        if orphaned:
            print("\nDeleting orphaned webhooks...")
            deleted_count = 0
            failed_count = 0
            
            for webhook in orphaned:
                webhook_id = webhook.get('id')
                try:
                    provider._make_webhook_api_request('DELETE', f"webhooks/v1/webhooks/{webhook_id}")
                    print(f"✅ Deleted webhook {webhook_id}")
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete webhook {webhook_id}: {str(e)}")
                    failed_count += 1
            
            print(f"\n{'='*80}")
            print(f"✅ Successfully deleted {deleted_count} orphaned webhooks")
            if failed_count > 0:
                print(f"❌ Failed to delete {failed_count} webhooks")
            print(f"{'='*80}")
            
            # Verify cleanup
            print("\n🔧 Verifying cleanup...")
            response = provider._make_webhook_api_request('GET', 'webhooks/v1/webhooks')
            remaining_webhooks = response.get('webhooks', [])
            print(f"✅ {len(remaining_webhooks)} webhooks remaining in Vipps")
            
            if len(remaining_webhooks) == len(stored_webhook_ids):
                print("✅ Perfect! Only webhooks with stored secrets remain")
            else:
                print(f"⚠️  Expected {len(stored_webhook_ids)}, found {len(remaining_webhooks)}")
        else:
            print("\n✅ No orphaned webhooks found - all registered webhooks have stored secrets")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("Cleanup complete!")
print("="*80)
print("\nNext steps:")
print("1. Create a new test payment")
print("2. Check that webhook arrives with correct ID")
print("3. Verify signature validation succeeds")
