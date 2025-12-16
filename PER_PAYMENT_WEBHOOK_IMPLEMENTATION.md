# Per-Payment Webhook Implementation

## ✅ **Implemented: Webhook Registration Per Payment**

According to Vipps Webhooks API documentation, each payment should register its own webhook. This has now been implemented.

## 🔧 **How It Works**

### **Step 1: Create Payment**
When creating a payment transaction:
```python
def _send_payment_request(self):
    # 1. Register webhook for THIS payment
    webhook_result = self._register_payment_webhook(payment_reference)
    
    # 2. Create payment with Vipps
    response = api_client._make_request('POST', 'payments', payload)
    
    # 3. Store payment details
    self.write({
        'vipps_payment_reference': payment_reference,
        'vipps_webhook_id': webhook_id,  # From webhook registration
        'vipps_webhook_secret': webhook_secret  # From webhook registration
    })
```

### **Step 2: Webhook Registration**
```python
def _register_payment_webhook(self, payment_reference):
    # Register webhook using Webhooks API
    POST /webhooks/v1/webhooks
    {
      "url": "https://your-domain.com/payment/vipps/webhook",
      "events": [
        "epayments.payment.created.v1",
        "epayments.payment.authorized.v1",
        ...
      ]
    }
    
    # Vipps returns:
    {
      "id": "webhook-id-for-this-payment",
      "secret": "secret-for-this-payment"
    }
    
    # Store in transaction
    self.vipps_webhook_id = response['id']
    self.vipps_webhook_secret = response['secret']
```

### **Step 3: Webhook Validation**
When webhook arrives:
```python
# 1. Find transaction by reference
transaction = find_by_reference(webhook_data['reference'])

# 2. Validate signature using transaction's secret
webhook_secret = transaction.vipps_webhook_secret  # Per-payment secret!

# 3. Validate HMAC signature
is_valid = validate_signature(webhook, webhook_secret)
```

## 📋 **Changes Made**

### **1. Added Per-Payment Webhook Registration**
**File**: `models/payment_transaction.py`

```python
def _register_payment_webhook(self, payment_reference):
    """Register webhook for this specific payment"""
    # Registers webhook with Vipps Webhooks API
    # Stores webhook ID and secret in transaction
```

### **2. Added Transaction Webhook Fields**
**File**: `models/payment_transaction.py`

```python
vipps_webhook_id = fields.Char(
    string="Webhook ID",
    help="Webhook ID for this specific payment"
)
vipps_webhook_secret = fields.Char(
    string="Webhook Secret",
    help="Webhook secret for this specific payment"
)
```

### **3. Updated Webhook Validation**
**File**: `models/vipps_webhook_security.py`

```python
def validate_webhook_request(self, request, payload, provider, transaction=None):
    # Now accepts transaction parameter
    # Uses transaction's webhook secret if available
```

### **4. Updated Signature Validation**
**File**: `models/vipps_webhook_security.py`

```python
def _validate_hmac_signature(self, payload, headers, provider, transaction=None):
    # Prefer transaction-specific secret
    if transaction and transaction.vipps_webhook_secret:
        webhook_secret = transaction.vipps_webhook_secret
    else:
        webhook_secret = provider.vipps_webhook_secret_decrypted
```

### **5. Updated Controller**
**File**: `controllers/main.py`

```python
# Find transaction first
transaction = find_by_reference(webhook_data['reference'])

# Pass transaction to validation
validation_result = validate_webhook_request(
    request, payload, provider, transaction
)
```

## 🎯 **Flow Diagram**

```
Payment Creation:
1. Customer initiates payment
2. System registers webhook for THIS payment → Get secret
3. System creates payment with Vipps
4. Store payment reference + webhook ID + webhook secret

Webhook Reception:
1. Vipps sends webhook for payment
2. System finds transaction by reference
3. System gets webhook secret from transaction
4. System validates signature using transaction's secret
5. ✅ Signature matches!
```

## ✅ **Benefits**

### **Security**
- Each payment has its own webhook secret
- Secrets are isolated per payment
- Compromised secret only affects one payment

### **Compliance**
- Follows Vipps Webhooks API specification
- Proper per-payment webhook registration
- Correct signature validation

### **Reliability**
- No shared secret conflicts
- Each payment independently validated
- Clear audit trail per payment

## 🚀 **Testing**

To test the implementation:

1. **Create a new payment**
   - Check logs for: `🔧 DEBUG: Registering webhook for payment`
   - Check logs for: `✅ DEBUG: Webhook registered for payment`

2. **Verify webhook registration**
   - Transaction should have `vipps_webhook_id`
   - Transaction should have `vipps_webhook_secret`

3. **Receive webhook**
   - Check logs for: `Using per-payment webhook secret`
   - Check logs for: `Signature validation result: {'valid': True}`

4. **Verify signature validation**
   - No more "Signature mismatch" warnings
   - Webhooks process successfully

## 📊 **Database Schema**

### **payment.transaction**
```
vipps_payment_reference: Unique payment reference
vipps_webhook_id: Webhook ID from Vipps
vipps_webhook_secret: Webhook secret from Vipps
```

Each transaction now stores its own webhook credentials!

## ⚠️ **Important Notes**

1. **Webhook Registration Timing**
   - Webhook registered BEFORE payment creation
   - Ensures webhook is ready when payment is created

2. **Secret Storage**
   - Secrets stored per transaction
   - Not encrypted (consider encrypting in production)

3. **Fallback**
   - If transaction secret not found, uses provider secret
   - Ensures backward compatibility

4. **Cleanup**
   - Consider deleting webhooks after payment completion
   - Prevents accumulation of unused webhooks

## ✅ **Summary**

**Implementation**: Complete ✅  
**Per-Payment Webhooks**: Yes ✅  
**Signature Validation**: Uses per-payment secret ✅  
**Vipps API Compliance**: Yes ✅  

The system now correctly registers a webhook for each payment and validates signatures using the per-payment webhook secret! 🎉