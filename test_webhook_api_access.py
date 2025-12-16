#!/usr/bin/env python3
"""
Test if we can access the Vipps Webhooks API
Run this from Odoo shell to test webhook API connectivity
"""

# To run: docker exec -it <odoo_container> odoo shell -d <database> --no-http
# Then paste this code

import logging
_logger = logging.getLogger(__name__)

# Get Vipps provider
provider = env['payment.provider'].search([('code', '=', 'vipps')], limit=1)

if not provider:
    print("❌ No Vipps provider found")
else:
    print(f"✅ Found provider: {provider.name}")
    print(f"   Environment: {provider.vipps_environment}")
    print(f"   MSN: {provider.vipps_merchant_serial_number}")
    
    # Test webhook API URL
    webhook_api_url = provider._get_vipps_webhook_api_url()
    print(f"   Webhook API URL: {webhook_api_url}")
    
    # Test webhook URL
    webhook_url = provider._get_vipps_webhook_url()
    print(f"   Webhook callback URL: {webhook_url}")
    
    # Try to list existing webhooks
    print("\n🔧 Testing Webhooks API access...")
    try:
        response = provider._make_webhook_api_request('GET', 'webhooks/v1/webhooks')
        print(f"✅ Webhooks API accessible!")
        print(f"   Response: {response}")
        
        if isinstance(response, list):
            print(f"   Found {len(response)} registered webhooks")
            for webhook in response:
                print(f"     - ID: {webhook.get('id')}")
                print(f"       URL: {webhook.get('url')}")
                print(f"       Events: {len(webhook.get('events', []))} events")
        
    except Exception as e:
        print(f"❌ Webhooks API error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Try to register a test webhook
    print("\n🔧 Testing webhook registration...")
    try:
        test_payload = {
            "url": webhook_url,
            "events": ["epayments.payment.created.v1"]
        }
        response = provider._make_webhook_api_request('POST', 'webhooks/v1/webhooks', payload=test_payload)
        print(f"✅ Webhook registration successful!")
        print(f"   Webhook ID: {response.get('id')}")
        print(f"   Secret length: {len(response.get('secret', ''))}")
        
        # Clean up - delete the test webhook
        if response.get('id'):
            print(f"\n🔧 Cleaning up test webhook...")
            provider._make_webhook_api_request('DELETE', f"webhooks/v1/webhooks/{response['id']}")
            print(f"✅ Test webhook deleted")
        
    except Exception as e:
        print(f"❌ Webhook registration error: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("Test complete. Check the output above for any errors.")
print("="*80)
