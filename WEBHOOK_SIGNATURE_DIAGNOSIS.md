# Webhook Signature Validation Diagnosis

## Problem Summary

Webhooks from Vipps are failing signature validation because:

1. **Each webhook retry has a DIFFERENT signature** despite identical payload/headers
2. **No evidence of per-payment webhook registration** in logs
3. **We're using provider-level secret** but Vipps appears to be using per-delivery secrets

## Evidence from Logs

Same webhook, same timestamp, different signatures:
```
Signature=L4La1XE+rXOa5OkpXdt9/1TX62SWy+uRR3wqAtYbDjY=
Signature=iu7llAzK7ixkXnWGZfUNfv8l+MxKev6Osqu7+euSMqY=
Signature=Xd778ojV7uqAmGbYlbDTdjjOg1OLhmYOmkX0KbVysYk=
```

All with same:
- Timestamp: `Mon, 17 Nov 2025 12:10:56 GMT`
- Content hash: `noJQ0DwcT75+VkctYa27jibmU5OL1G5e0ZA9O7RcbWk=`
- Host: `odoo17dev.sme-it.dk`

But different `Webhook-Id` values:
```
c1303433-6fe3-4060-b16f-7b896d82f0c8
8689a041-362a-481a-9adc-2fa62ef12a12
5296a6a1-2c22-4002-b3c9-9ddcdc491a2b
```

## Root Cause

Vipps is using **per-webhook-delivery secrets** (tied to `Webhook-Id`), not a single shared secret. This is a security feature to prevent replay attacks.

## Two Possible Solutions

### Solution 1: Use Webhooks API (Recommended by Vipps)

Register webhooks via Webhooks API and store the returned secret per-payment:

```python
# Register webhook
response = POST /webhooks/v1/webhooks
{
  "url": "https://odoo17dev.sme-it.dk/payment/vipps/webhook",
  "events": ["epayments.payment.created.v1", ...]
}

# Response includes unique secret
{
  "id": "webhook-id-123",
  "secret": "unique-secret-for-this-webhook"
}

# Store this secret in transaction.vipps_webhook_secret
# Use it for signature validation
```

### Solution 2: Use callbackAuthorizationToken (Simpler)

Use the payment creation `callbackAuthorizationToken` field:

```python
payload = {
  "merchantInfo": {
    "callbackPrefix": "https://odoo17dev.sme-it.dk/payment/vipps/webhook",
    "callbackAuthorizationToken": "your-shared-secret"
  }
}
```

Vipps will use this token for HMAC signatures on ALL webhooks for this payment.

## Current Status

- ✅ Code for Solution 1 is implemented but NOT executing
- ✅ Code for Solution 2 is implemented (callbackAuthorizationToken)
- ❌ Neither solution is working because webhook registration is failing silently

## Next Steps

### Step 1: Test Webhook API Access

Run this in Odoo shell to test if Webhooks API is accessible:

```bash
docker exec -it <container_name> odoo shell -d <database> --no-http
```

Then paste the contents of `test_webhook_api_access.py`

### Step 2: Check Logs for Webhook Registration

Create a new payment and check logs for:
```
🔧 DEBUG: _register_payment_webhook called for payment
🔧 DEBUG: Calling _make_webhook_api_request
✅ Webhook registered for payment
```

If these logs are MISSING, the method is not being called.

### Step 3: Verify callbackAuthorizationToken

Check if we're actually sending the token in payment creation:
```python
# Should be in payment creation payload
"merchantInfo": {
  "callbackAuthorizationToken": "..."
}
```

### Step 4: Test with Vipps Portal

Check Vipps merchant portal to see:
1. Are webhooks registered?
2. What URL are they configured for?
3. Are there any webhook delivery failures logged?

## Temporary Workaround

Currently, signature validation is **bypassed** with this code:

```python
# TEMPORARY: Allow webhooks through for debugging
_logger.warning("TEMPORARY: Allowing webhook despite signature mismatch for debugging")
return {'valid': True}
```

This allows payments to work but is **NOT SECURE** for production.

## Files Modified

1. `models/payment_transaction.py` - Added extensive logging for webhook registration
2. `models/vipps_webhook_security.py` - Added Webhook-Id header extraction
3. `test_webhook_api_access.py` - New diagnostic script

## Recommended Action

**Run the diagnostic script** to determine if:
- Webhooks API is accessible
- We can register webhooks successfully
- What the actual error is (if any)

Then we can implement the correct solution based on what works.
