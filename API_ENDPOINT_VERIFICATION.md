# API Endpoint Verification for Test Environment

## ✅ API Endpoints Analysis

### **1. Payment API Endpoints** ✅ CORRECT

**Location**: `models/payment_provider.py` lines 665-671

```python
def _get_vipps_api_url(self):
    """Return the appropriate API base URL based on environment"""
    self.ensure_one()
    if self.vipps_environment == 'production':
        return "https://api.vipps.no/epayment/v1/"
    else:
        return "https://apitest.vipps.no/epayment/v1/"
```

**Status**: ✅ **CORRECT**
- Test environment: `https://apitest.vipps.no/epayment/v1/`
- Production environment: `https://api.vipps.no/epayment/v1/`

---

### **2. Webhook API Endpoints** ✅ CORRECT

**Location**: `models/payment_provider.py` lines 681-687

```python
def _get_vipps_webhook_api_url(self):
    """Return the webhook API base URL based on environment"""
    self.ensure_one()
    if self.vipps_environment == 'production':
        return "https://api.vipps.no/"
    else:
        return "https://apitest.vipps.no/"
```

**Status**: ✅ **CORRECT**
- Test environment: `https://apitest.vipps.no/`
- Production environment: `https://api.vipps.no/`

**Full Webhook Registration URL**:
- Test: `https://apitest.vipps.no/webhooks/v1/webhooks`
- Production: `https://api.vipps.no/webhooks/v1/webhooks`

---

### **3. Webhook Callback URL** ✅ CORRECT

**Location**: `models/payment_provider.py` lines 268-275

```python
def _get_vipps_webhook_url(self):
    """Get webhook URL for Vipps configuration"""
    self.ensure_one()
    base_url = self.get_base_url().rstrip('/')
    # Vipps requires HTTPS for webhook URLs
    if base_url.startswith('http://'):
        base_url = base_url.replace('http://', 'https://', 1)
    return f"{base_url}/payment/vipps/webhook"
```

**Status**: ✅ **CORRECT**
- Automatically converts HTTP to HTTPS (required by MobilePay)
- Returns: `https://your-domain.com/payment/vipps/webhook`

---

## ✅ Controller Endpoints Analysis

### **1. Webhook Receiver Endpoint** ✅ CORRECT

**Location**: `controllers/main.py` line 292

```python
@http.route(['/payment/vipps/webhook', '/payment/mobilepay/webhook'], 
            type='http', auth='public', methods=['POST'], csrf=False)
def vipps_webhook(self, **kwargs):
    """Handle incoming webhooks from Vipps/MobilePay with enhanced security"""
```

**Status**: ✅ **CORRECT**
- Accepts both `/payment/vipps/webhook` and `/payment/mobilepay/webhook`
- Type: `http` (correct for webhooks)
- Auth: `public` (correct - webhooks don't use Odoo auth)
- Methods: `POST` (correct)
- CSRF: `False` (correct - external API calls)

**Features**:
- ✅ Finds transaction by reference
- ✅ Uses per-payment webhook secret for validation
- ✅ Comprehensive security validation
- ✅ Proper error handling with appropriate HTTP status codes
- ✅ Debug logging for test environment

---

### **2. Return URL Endpoint** ✅ CORRECT

**Location**: `controllers/main.py` line 499

```python
@http.route(['/payment/vipps/return', '/payment/mobilepay/return'], 
            type='http', auth='public', methods=['GET'], csrf=False)
def vipps_return(self, **kwargs):
    """Handle customer return from Vipps/MobilePay payment flow"""
```

**Status**: ✅ **CORRECT**
- Handles customer redirects after payment
- Processes payment status
- Redirects to appropriate confirmation/error pages

---

## 🔍 Per-Payment Webhook Implementation

### **Webhook Registration Flow** ✅ IMPLEMENTED

**Location**: `models/payment_transaction.py` lines 423-441

```python
# Register webhook for this specific payment using Webhooks API
# This gives us a unique secret per payment for proper signature validation
_logger.info("🔧 DEBUG: About to register webhook for payment %s", payment_reference)
try:
    webhook_result = self._register_payment_webhook(payment_reference)
    if webhook_result:
        _logger.info("✅ Successfully registered webhook for payment %s", payment_reference)
        # Verify the secret was stored
        if self.vipps_webhook_id and self.vipps_webhook_secret:
            _logger.info("✅ Webhook ID: %s", self.vipps_webhook_id)
            _logger.info("✅ Webhook secret stored: %d chars", len(self.vipps_webhook_secret))
```

**Status**: ✅ **CORRECTLY IMPLEMENTED**

The `_register_payment_webhook()` method (lines 150-226):
1. ✅ Calls `POST /webhooks/v1/webhooks` via `_make_webhook_api_request()`
2. ✅ Stores `webhook_id` and `webhook_secret` in transaction fields
3. ✅ Verifies data was stored correctly
4. ✅ Has comprehensive debug logging

---

### **Webhook Validation with Per-Payment Secret** ✅ IMPLEMENTED

**Location**: `controllers/main.py` lines 330-343

```python
# Find transaction first to get per-payment webhook secret
webhook_data_temp = json.loads(payload) if payload else {}
reference_temp = webhook_data_temp.get('reference')
transaction_for_validation = None

if reference_temp:
    transaction_for_validation = request.env['payment.transaction'].sudo().search([
        ('vipps_payment_reference', '=', reference_temp)
    ], limit=1)

# Run comprehensive security validation with transaction
try:
    validation_result = request.env['vipps.webhook.security'].validate_webhook_request(
        request, payload, provider, transaction_for_validation
    )
```

**Status**: ✅ **CORRECTLY IMPLEMENTED**
- Finds transaction by reference
- Passes transaction to validation (which uses per-payment secret)
- Proper error handling

---

## 🚨 Potential Issues

### **Issue 1: Webhook Registration May Be Failing Silently**

**Symptoms**:
- No webhooks registered in test environment
- Payments created but webhook fields empty

**Possible Causes**:

#### **A. API Authentication Failure**
```python
# Check if credentials are valid
if not provider.vipps_credentials_validated:
    # Credentials not validated - webhook registration will fail
```

**Solution**: Ensure credentials are validated before creating payments

#### **B. Webhook URL Not Accessible**
```python
# MobilePay test servers need to reach your webhook URL
webhook_url = "https://your-domain.com/payment/vipps/webhook"
# Must be:
# - HTTPS (required)
# - Publicly accessible (not localhost)
# - Return HTTP 200 on POST
```

**Solution**: Test webhook URL accessibility from external network

#### **C. API Error Not Properly Handled**
The webhook registration continues even if it fails (line 441):
```python
except Exception as webhook_error:
    _logger.error("❌ Exception during webhook registration: %s", str(webhook_error))
    _logger.exception("Full webhook registration exception:")
    # Continue anyway - webhook registration failure shouldn't block payment
```

**Impact**: Payment proceeds even if webhook registration fails

---

### **Issue 2: Validation Temporarily Bypassed**

**Location**: `controllers/main.py` line 360

```python
# TEMPORARY: Always proceed as if validation passed
if False:  # Changed from: if not validation_result['success']:
```

**Status**: ⚠️ **VALIDATION DISABLED**

This means webhook signature validation is currently **bypassed** for debugging purposes.

**Recommendation**: Re-enable validation once webhook registration is working:
```python
if not validation_result['success']:  # Remove the 'False' condition
```

---

## 📋 Diagnostic Checklist

### **For Test Environment Webhook Issues**:

- [ ] **Provider Configuration**
  - [ ] Provider state is `'enabled'` (not 'test' or 'disabled')
  - [ ] `vipps_environment` is set to `'test'`
  - [ ] `vipps_credentials_validated` is `True`
  - [ ] All credential fields are filled:
    - `vipps_client_id`
    - `vipps_client_secret`
    - `vipps_subscription_key`
    - `vipps_merchant_serial_number`

- [ ] **Webhook URL Accessibility**
  - [ ] URL is HTTPS (required by MobilePay)
  - [ ] URL is publicly accessible (test from external network)
  - [ ] SSL certificate is valid
  - [ ] No authentication required for webhook endpoint
  - [ ] Firewall allows inbound HTTPS on port 443

- [ ] **API Connectivity**
  - [ ] Server can reach `https://apitest.vipps.no`
  - [ ] No proxy blocking outbound HTTPS
  - [ ] DNS resolution works for `apitest.vipps.no`

- [ ] **Debug Logging**
  - [ ] Check Odoo logs for webhook registration attempts
  - [ ] Look for error messages with status codes (401, 400, 403, 500)
  - [ ] Verify debug logging is enabled for test environment

---

## 🔧 Testing Commands

### **1. Test Webhook URL Accessibility**
```bash
# From external server (not localhost)
curl -X POST https://your-domain.com/payment/vipps/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'

# Should return HTTP 200
```

### **2. Test API Connectivity**
```bash
# Test connection to MobilePay test API
curl -I https://apitest.vipps.no/

# Should return HTTP 200 or similar
```

### **3. Check Odoo Logs**
```bash
# Monitor logs in real-time
tail -f /var/log/odoo/odoo-server.log | grep -i webhook

# Or for systemd
sudo journalctl -u odoo -f | grep -i webhook
```

### **4. Manual Webhook Registration Test**
```python
# In Odoo shell: ./odoo-bin shell -d your_database

provider = env['payment.provider'].search([('code', '=', 'vipps')], limit=1)
print(f"Provider: {provider.name}")
print(f"Environment: {provider.vipps_environment}")
print(f"Credentials validated: {provider.vipps_credentials_validated}")
print(f"Webhook API URL: {provider._get_vipps_webhook_api_url()}")

# Try to register a test webhook
transaction = env['payment.transaction'].search([('provider_code', '=', 'vipps')], limit=1, order='id desc')
if transaction:
    result = transaction._register_payment_webhook('TEST-REF-123')
    print(f"Registration result: {result}")
    print(f"Webhook ID: {transaction.vipps_webhook_id}")
    print(f"Webhook Secret: {transaction.vipps_webhook_secret[:20]}..." if transaction.vipps_webhook_secret else "None")
```

---

## ✅ Summary

### **API Endpoints**: ✅ ALL CORRECT
- Payment API: `https://apitest.vipps.no/epayment/v1/`
- Webhook API: `https://apitest.vipps.no/webhooks/v1/webhooks`
- Webhook callback: `https://your-domain.com/payment/vipps/webhook`

### **Controllers**: ✅ ALL CORRECT
- Webhook receiver: `/payment/vipps/webhook` ✅
- Return handler: `/payment/vipps/return` ✅
- Proper HTTP methods, auth, and CSRF settings ✅

### **Per-Payment Webhook Implementation**: ✅ CORRECTLY IMPLEMENTED
- Webhook registration per payment ✅
- Per-payment secret storage ✅
- Transaction-specific validation ✅

### **Likely Issue**: 🔍 WEBHOOK REGISTRATION FAILING SILENTLY
- Check credentials validation
- Verify webhook URL accessibility
- Review server logs for API errors
- Test API connectivity to `apitest.vipps.no`

---

## 🎯 Next Steps

1. **Check provider credentials** - Ensure `vipps_credentials_validated = True`
2. **Test webhook URL** - Verify it's accessible from external network
3. **Review server logs** - Look for webhook registration error messages
4. **Manual test** - Use Odoo shell to test webhook registration
5. **Re-enable validation** - Once webhooks work, remove the bypass in line 360

The implementation is **correct** - the issue is likely with **credentials, network accessibility, or API connectivity**.
