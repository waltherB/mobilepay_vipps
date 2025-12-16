# Webhook Signature Validation - Root Cause & Solution

## Root Cause Identified ✅

The diagnostic revealed the actual problem:

### What We Found

1. **14 webhooks are already registered** with Vipps Webhooks API
2. **Each webhook has a unique secret** (88 characters, base64 encoded)
3. **None of these secrets are stored** in the Odoo database
4. **Webhook IDs in logs match registered webhooks**:
   - `c1303433-6fe3-4060-b16f-7b896d82f0c8` ✅ Registered
   - `8689a041-362a-481a-9adc-2fa62ef12a12` ✅ Registered
   - `5296a6a1-2c22-4002-b3c9-9ddcdc491a2b` ✅ Registered

### Why Signatures Fail

When a webhook arrives:
1. Vipps signs it with the **unique secret for that webhook ID**
2. We try to validate with the **provider-level secret** (wrong!)
3. Signature mismatch → validation fails

### Why Secrets Weren't Stored

The webhook registration code was **temporarily disabled** in an earlier change. The 14 registered webhooks are from:
- Previous test runs before the code was disabled
- Manual registrations
- Test scripts

## Solution Implemented ✅

### 1. Re-enabled Webhook Registration

```python
# In _send_payment_request()
webhook_result = self._register_payment_webhook(payment_reference)
```

### 2. Fixed Storage Issues

- Removed problematic `self.env.cr.commit()` call
- Added `self.env.cr.flush()` to ensure write is applied
- Added verification after write to confirm storage

### 3. Enhanced Logging

Added detailed logging to track:
- Webhook registration attempts
- Secret storage verification
- Webhook ID matching
- Which secret is being used for validation

### 4. Improved Signature Validation

- Check if transaction has per-payment secret
- Verify webhook ID matches
- Log which secret is being used
- Warn if webhook ID mismatch detected

## Next Steps

### Step 1: Clean Up Orphaned Webhooks

Run this in Odoo shell to delete webhooks without stored secrets:

```bash
docker exec -it <container> odoo shell -d <database> --no-http
```

Then paste contents of `cleanup_orphaned_webhooks.py`

This will:
- List all registered webhooks
- Identify which ones don't have stored secrets
- Offer to delete them
- Clean up the orphaned registrations

### Step 2: Test New Payment

Create a new payment and verify in logs:

```
🔧 DEBUG: About to register webhook for payment S00014-X-...
🔧 DEBUG: _register_payment_webhook called for payment
🔧 DEBUG: Calling _make_webhook_api_request
✅ Webhook registered for payment S00014-X-...
✅ Webhook ID: <uuid>
✅ Webhook secret length: 88
✅ Verification: Webhook data successfully stored
```

### Step 3: Verify Webhook Delivery

When webhook arrives, check logs for:

```
✅ Using per-payment webhook secret for transaction S00014-X
✅ Per-payment secret length: 88
✅ Transaction webhook ID: <uuid>
✅ Incoming webhook ID: <uuid>
```

IDs should match!

### Step 4: Remove Temporary Bypass

Once signatures validate correctly, remove this code:

```python
# In _validate_hmac_signature()
# TEMPORARY: Allow webhooks through for debugging
_logger.warning("TEMPORARY: Allowing webhook despite signature mismatch for debugging")
return {'valid': True}
```

Replace with:

```python
return {
    'valid': False,
    'error': 'Invalid webhook signature'
}
```

## Expected Behavior After Fix

### Payment Creation
1. Generate payment reference
2. **Register webhook** → Get unique ID + secret
3. **Store in transaction** → `vipps_webhook_id`, `vipps_webhook_secret`
4. Create payment with Vipps
5. Vipps sends webhooks using that webhook ID

### Webhook Delivery
1. Webhook arrives with `Webhook-Id` header
2. Find transaction by reference
3. **Use transaction's stored secret** for validation
4. Verify webhook ID matches
5. Signature validates ✅
6. Process webhook

## Why This Approach

### Vipps Webhooks API Design

Vipps uses **per-webhook secrets** for security:
- Each webhook registration gets a unique secret
- Prevents secret reuse across payments
- Enables webhook-specific revocation
- Provides better audit trail

### Alternative Approach (Not Recommended)

Using `callbackAuthorizationToken` in payment creation:
- Single shared secret for all webhooks
- Less secure (secret reuse)
- No per-payment isolation
- Harder to debug issues

## Files Modified

1. `models/payment_transaction.py`
   - Re-enabled webhook registration
   - Fixed storage verification
   - Enhanced logging

2. `models/vipps_webhook_security.py`
   - Added webhook ID extraction
   - Enhanced secret selection logic
   - Added webhook ID matching verification

3. `cleanup_orphaned_webhooks.py` (new)
   - Diagnostic and cleanup script

4. `test_webhook_api_access.py` (new)
   - Webhooks API connectivity test

## Success Criteria

✅ Webhook registration logs appear for each payment
✅ Webhook ID and secret stored in transaction
✅ Signature validation uses per-payment secret
✅ Webhook ID in header matches transaction
✅ Signatures validate successfully
✅ No more "signature mismatch" warnings

## Current Status

- ✅ Root cause identified
- ✅ Solution implemented
- ⏳ Needs testing with new payment
- ⏳ Needs orphaned webhook cleanup
- ⏳ Needs temporary bypass removal

## Testing Checklist

- [ ] Run `cleanup_orphaned_webhooks.py` to clean up
- [ ] Create new test payment
- [ ] Verify webhook registration logs
- [ ] Verify secret storage in database
- [ ] Complete payment and trigger webhook
- [ ] Verify signature validation succeeds
- [ ] Remove temporary bypass code
- [ ] Test in production environment
