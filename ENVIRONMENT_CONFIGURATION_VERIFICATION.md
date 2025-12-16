# Environment Configuration Verification

## ✅ **Confirmed: Server Selection Based on `vipps_environment` Only**

The implementation correctly uses **only the `vipps_environment` setting** to determine which servers to use, **regardless of the provider state** (disabled/test/enabled).

## 🎯 **Configuration Logic**

### **Provider State vs Environment**

| Provider State | vipps_environment | Servers Used |
|----------------|-------------------|--------------|
| **Disabled** | `test` | ✅ Test servers |
| **Disabled** | `production` | ✅ Production servers |
| **Test** | `test` | ✅ Test servers |
| **Test** | `production` | ✅ Production servers |
| **Enabled** | `test` | ✅ Test servers |
| **Enabled** | `production` | ✅ Production servers |

**Key Point**: The `state` field (disabled/test/enabled) controls **visibility and availability** of the payment method, but **NOT which servers are used**.

## 📋 **Verified Implementation**

### **1. API Server Selection**

**File**: `models/payment_provider.py`

```python
def _get_vipps_api_url(self):
    """Return the appropriate API base URL based on environment"""
    self.ensure_one()
    if self.vipps_environment == 'production':
        return "https://api.vipps.no/epayment/v1/"
    else:
        return "https://apitest.vipps.no/epayment/v1/"
```

✅ **Uses**: `self.vipps_environment`  
❌ **Does NOT use**: `self.state`

### **2. Access Token URL**

**File**: `models/payment_provider.py`

```python
def _get_vipps_access_token_url(self):
    """Return the access token endpoint URL based on environment"""
    self.ensure_one()
    if self.vipps_environment == 'production':
        return "https://api.vipps.no/accesstoken/get"
    else:
        return "https://apitest.vipps.no/accesstoken/get"
```

✅ **Uses**: `self.vipps_environment`  
❌ **Does NOT use**: `self.state`

### **3. Webhook API URL**

**File**: `models/payment_provider.py`

```python
def _get_vipps_webhook_api_url(self):
    """Return the webhook API base URL based on environment"""
    self.ensure_one()
    if self.vipps_environment == 'production':
        return "https://api.vipps.no/"
    else:
        return "https://apitest.vipps.no/"
```

✅ **Uses**: `self.vipps_environment`  
❌ **Does NOT use**: `self.state`

### **4. Webhook Callback Hostnames**

**File**: `models/vipps_webhook_security.py`

```python
def _get_allowed_hostnames(self, provider):
    """Get allowed hostnames for webhook validation based on environment"""
    if provider.vipps_environment == 'production':
        return [
            'callback-1.vipps.no',
            'callback-2.vipps.no',
            'callback-3.vipps.no',
            'callback-4.vipps.no',
        ]
    else:
        return [
            'callback-mt-1.vipps.no',
            'callback-mt-2.vipps.no',
        ]
```

✅ **Uses**: `provider.vipps_environment`  
❌ **Does NOT use**: `provider.state`

### **5. API Client Base URL**

**File**: `models/vipps_api_client.py`

```python
def _get_api_base_url(self):
    """Get API base URL based on environment"""
    if self.provider.vipps_environment == 'production':
        return "https://api.vipps.no/epayment/v1"
    else:
        return "https://apitest.vipps.no/epayment/v1"
```

✅ **Uses**: `self.provider.vipps_environment`  
❌ **Does NOT use**: `self.provider.state`

### **6. Controller Webhook Validation**

**File**: `controllers/main.py`

```python
def _validate_webhook_ip(self, request_ip, provider):
    """Validate webhook source IP against Vipps/MobilePay server hostnames"""
    if provider.vipps_environment == 'production':
        vipps_hostnames = ['callback-1.vipps.no', ...]
    else:
        vipps_hostnames = ['callback-mt-1.vipps.no', ...]
```

✅ **Uses**: `provider.vipps_environment`  
❌ **Does NOT use**: `provider.state`

## 🔍 **Complete Server Configuration**

### **Test Environment** (`vipps_environment = 'test'`)
- **API Server**: `https://apitest.vipps.no`
- **Access Token**: `https://apitest.vipps.no/accesstoken/get`
- **Webhook API**: `https://apitest.vipps.no/`
- **Callback Servers**: 
  - `callback-mt-1.vipps.no`
  - `callback-mt-2.vipps.no`

### **Production Environment** (`vipps_environment = 'production'`)
- **API Server**: `https://api.vipps.no`
- **Access Token**: `https://api.vipps.no/accesstoken/get`
- **Webhook API**: `https://api.vipps.no/`
- **Callback Servers**:
  - `callback-1.vipps.no`
  - `callback-2.vipps.no`
  - `callback-3.vipps.no`
  - `callback-4.vipps.no`

## ✅ **Verification Results**

### **All Server Selection Logic**
- ✅ Based on `vipps_environment` field
- ✅ Independent of `state` field
- ✅ Consistent across all modules
- ✅ Follows official Vipps documentation

### **Provider State Field Purpose**
The `state` field controls:
- ✅ Payment method visibility in checkout
- ✅ Payment method availability
- ✅ UI display and access control

The `state` field does **NOT** control:
- ❌ Which API servers are used
- ❌ Which webhook servers are validated
- ❌ Which credentials are used

## 🎯 **Usage Scenarios**

### **Scenario 1: Testing with Disabled Provider**
```
state: disabled
vipps_environment: test
Result: Uses test servers (apitest.vipps.no, callback-mt-*.vipps.no)
```

### **Scenario 2: Testing with Test Provider**
```
state: test
vipps_environment: test
Result: Uses test servers (apitest.vipps.no, callback-mt-*.vipps.no)
```

### **Scenario 3: Testing with Enabled Provider**
```
state: enabled
vipps_environment: test
Result: Uses test servers (apitest.vipps.no, callback-mt-*.vipps.no)
```

### **Scenario 4: Production with Enabled Provider**
```
state: enabled
vipps_environment: production
Result: Uses production servers (api.vipps.no, callback-*.vipps.no)
```

## 🚀 **Conclusion**

✅ **The implementation is correct!**

The system properly uses the `vipps_environment` setting to determine which servers to use, completely independent of the provider `state` setting. This ensures:

1. **Consistent behavior** across all provider states
2. **Proper environment isolation** between test and production
3. **Correct server selection** for API calls and webhook validation
4. **Compliance** with official Vipps/MobilePay documentation

You can safely set the provider to any state (disabled/test/enabled) and the system will always use the servers corresponding to the `vipps_environment` setting! 🎉