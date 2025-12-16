# Webhook API Implementation Fix

## ✅ **Issue Fixed**

The code was generating a **local webhook secret** before registering with Vipps, instead of using the secret that **Vipps generates and returns**.

## 🔧 **What Was Wrong**

### **Before (Incorrect)**
```python
# Generate webhook secret if not exists
if not self.vipps_webhook_secret:
    webhook_secret = secrets.token_urlsafe(32)  # ❌ Local secret
    self.sudo().write({'vipps_webhook_secret': webhook_secret})

payload = {
    "url": webhook_url,
    "events": ["epayments.payment.created.v1"]
}
```

**Problem**: 
- Generated a local secret
- Sent registration to Vipps
- Vipps generated THEIR OWN secret
- But code kept using the local secret
- **Signatures never matched!**

### **After (Correct)**
```python
# Vipps will generate and return the webhook secret
# Do NOT generate a local secret - use the one Vipps provides
payload = {
    "url": webhook_url,
    "events": [
        "epayments.payment.created.v1",
        "epayments.payment.authorized.v1",
        "epayments.payment.captured.v1",
        "epayments.payment.cancelled.v1",
        "epayments.payment.aborted.v1",
        "epayments.payment.expired.v1",
        "epayments.payment.refunded.v1",
        "epayments.payment.terminated.v1"
    ]
}

# Response handling (already correct):
if response.get('secret'):
    update_vals['vipps_webhook_secret'] = response['secret']  # ✅ Vipps secret
```

**Solution**:
- Don't generate local secret
- Register webhook with Vipps
- Vipps returns their secret in response
- Store that secret
- **Signatures will match!**

## 📋 **Changes Made**

### **1. Removed Local Secret Generation**
- ❌ Removed: `secrets.token_urlsafe(32)`
- ✅ Now: Wait for Vipps to provide secret

### **2. Added All Payment Events**
According to Vipps documentation, monitor these events:
- ✅ `epayments.payment.created.v1` - Payment created
- ✅ `epayments.payment.authorized.v1` - Payment authorized
- ✅ `epayments.payment.captured.v1` - Payment captured
- ✅ `epayments.payment.cancelled.v1` - Payment cancelled
- ✅ `epayments.payment.aborted.v1` - Payment aborted
- ✅ `epayments.payment.expired.v1` - Payment expired
- ✅ `epayments.payment.refunded.v1` - Payment refunded
- ✅ `epayments.payment.terminated.v1` - Payment terminated

### **3. Response Handling (Already Correct)**
The code already correctly:
- ✅ Extracts `id` from response
- ✅ Extracts `secret` from response
- ✅ Stores both in database
- ✅ Logs success/failure

## 🎯 **How It Works Now**

### **Step 1: Register Webhook**
```
POST https://api.vipps.no/webhooks/v1/webhooks
{
  "url": "https://your-domain.com/payment/vipps/webhook",
  "events": ["epayments.payment.created.v1", ...]
}
```

### **Step 2: Vipps Response**
```json
{
  "id": "01JCQM9VVVVVVVVVVVVVVVVVVV",
  "url": "https://your-domain.com/payment/vipps/webhook",
  "events": ["epayments.payment.created.v1", ...],
  "secret": "base64-encoded-secret-from-vipps"  ← THIS!
}
```

### **Step 3: Store Secret**
```python
vipps_webhook_id = "01JCQM9VVVVVVVVVVVVVVVVVVV"
vipps_webhook_secret = "base64-encoded-secret-from-vipps"
```

### **Step 4: Validate Webhooks**
```python
# Vipps signs webhook with their secret
# Odoo validates using same secret
# ✅ Signatures match!
```

## 🚀 **Next Steps**

1. **Re-register webhook** to get fresh secret from Vipps
   - Click "Re-register Webhook (New Secret)" button
   - This will use the fixed code

2. **Check logs** for webhook registration
   - Look for: `✅ DEBUG: Webhook registration successful`
   - Look for: `✅ DEBUG: Stored webhook secret: Yes`

3. **Test payment** to verify signatures match
   - Create a new payment
   - Check webhook logs
   - Should see: No signature mismatch warnings

4. **Verify all events** are being received
   - Payment created ✅
   - Payment authorized ✅
   - Payment captured ✅
   - etc.

## ✅ **Expected Results**

After re-registering with the fixed code:

```
✅ Webhook registered successfully
✅ Secret received from Vipps
✅ Secret stored in database
✅ Webhooks arrive with correct signatures
✅ Signature validation passes
✅ No more "Signature mismatch" warnings
✅ All payment events monitored
```

## 📊 **Verification**

To verify the fix worked:

1. **Check webhook registration logs**:
```
✅ DEBUG: Webhook registration successful
✅ DEBUG: Response: {'id': '...', 'secret': '...'}
✅ DEBUG: Stored webhook secret: Yes
```

2. **Check webhook validation logs**:
```
✅ Signature validation result: {'valid': True}
✅ No "Signature mismatch" warnings
```

3. **Check payment processing**:
```
✅ Webhook processed successfully
✅ Payment status updated correctly
```

## 🎯 **Summary**

**Root Cause**: Using locally-generated secret instead of Vipps-provided secret  
**Fix**: Removed local secret generation, use Vipps secret from response  
**Action Required**: Re-register webhook once with fixed code  
**Expected Result**: Signature validation will pass ✅