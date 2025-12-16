# Webhook Registration - How It Works

## ✅ **Correct Behavior**

Your implementation is **correct**! Webhooks are registered **once per provider**, not per payment.

## 📋 **When Webhooks Are Registered**

### **1. Automatic Registration**
Webhooks are automatically registered when:
- ✅ Provider is **enabled** for the first time
- ✅ Provider **credentials are updated**
- ✅ Provider state changes to **enabled**

**Code location**: `models/payment_provider.py` line 1563
```python
if (vals.get('state') == 'enabled' or credential_changed) and provider.state == 'enabled':
    provider._register_webhook()
```

### **2. Manual Registration**
You can manually register webhooks by clicking:
- ✅ **"Register Webhook"** button in provider configuration
- ✅ **"Re-register Webhook (New Secret)"** button for fresh secret

### **3. Never Per Payment**
- ❌ Webhooks are **NOT** registered for each payment
- ❌ Webhooks are **NOT** registered for each transaction
- ✅ One webhook handles **ALL** payments for that provider

## 🔄 **How Webhooks Work**

### **One-Time Setup**
```
1. Register webhook with Vipps → Get webhook URL and secret
2. Vipps stores: https://your-domain.com/payment/vipps/webhook
3. Vipps stores: webhook secret for signing
```

### **For Each Payment**
```
1. Customer makes payment
2. Vipps processes payment
3. Vipps sends webhook to YOUR URL (registered once)
4. Your system validates and processes webhook
5. Payment status updated
```

## 🎯 **Single Webhook, Multiple Payments**

```
Provider: Vipps Test
Webhook URL: https://odoo17dev.sme-it.dk/payment/vipps/webhook
Webhook Secret: [stored securely]

Payment 1 → Webhook notification → Your URL
Payment 2 → Webhook notification → Your URL  
Payment 3 → Webhook notification → Your URL
...
All use the SAME webhook URL and secret!
```

## 🔍 **Webhook Identification**

Each webhook contains:
- **reference**: Unique payment reference (e.g., `S00007-41-20251112111902`)
- **pspReference**: Vipps payment ID
- **idempotencyKey**: Unique webhook event ID

Your system uses the **reference** to find the correct transaction.

## ⚠️ **Common Misconceptions**

### ❌ **WRONG**: "I need to register a webhook for each payment"
- This would create hundreds/thousands of webhooks
- Vipps would reject duplicate URLs
- Completely unnecessary

### ✅ **CORRECT**: "I register ONE webhook that handles ALL payments"
- One webhook URL for the provider
- Vipps sends all payment notifications to this URL
- Your system routes to correct transaction using reference

## 📊 **Current Status**

Based on your logs:
```
✅ Webhook registered: https://odoo17dev.sme-it.dk/payment/vipps/webhook
✅ Receiving webhooks: Multiple payments using same webhook
✅ Processing correctly: Transactions identified by reference
✅ No re-registration needed: Unless changing environment/credentials
```

## 🚀 **When to Re-register Webhook**

Only re-register when:
1. **Changing environment** (test ↔ production)
2. **Updating credentials** (MSN, client ID, etc.)
3. **Signature mismatch** (secret out of sync)
4. **Webhook URL changes** (domain change)
5. **Troubleshooting** (testing webhook flow)

## 💡 **Best Practices**

### **Do**
- ✅ Register webhook once during setup
- ✅ Keep webhook secret secure
- ✅ Monitor webhook logs
- ✅ Re-register when changing environments

### **Don't**
- ❌ Register webhook for each payment
- ❌ Delete and re-register frequently
- ❌ Share webhook secrets
- ❌ Hardcode webhook URLs

## 🔧 **Troubleshooting**

### "Webhooks not arriving"
1. Check webhook is registered in Vipps portal
2. Verify webhook URL is accessible
3. Check firewall/proxy settings
4. Test with "List Webhooks" button

### "Signature validation failing"
1. Re-register webhook to sync secret
2. Verify environment matches (test/production)
3. Check webhook secret is stored correctly

### "Wrong transaction updated"
1. Check reference matching logic
2. Verify transaction references are unique
3. Review webhook payload parsing

## ✅ **Summary**

Your implementation is **correct**:
- Webhook registered **once** per provider ✅
- Handles **all payments** for that provider ✅
- No per-payment registration needed ✅
- Standard Vipps/MobilePay pattern ✅

The error you're seeing is **NOT** about needing to register webhooks per payment. It's about the **webhook secret** needing to be synchronized with Vipps (which you do by re-registering the webhook once).