# Currency Based on Language/Locale Implementation

## 📋 Current Situation

Your code currently uses `self.currency_id.name` which comes from the Odoo transaction's currency field. This is typically set from:
1. The sale order currency
2. The company's default currency
3. The pricelist currency

**Problem**: Currency is NOT automatically determined by the user's language/locale.

---

## ✅ Required Implementation

### **Language to Currency Mapping**

According to MobilePay/Vipps supported countries:

| Language Code | Country | Currency | Default |
|---------------|---------|----------|---------|
| `da_DK` | Denmark | **DKK** | ✅ **DEFAULT** |
| `nb_NO` | Norway | NOK | |
| `sv_SE` | Sweden | SEK | |
| `fi_FI` | Finland | EUR | |
| `en_US` | International | DKK | (fallback to default) |

---

## 🔧 Implementation Code

### **Step 1: Add Currency Detection Method**

Add this method to `models/payment_transaction.py`:

```python
def _get_currency_from_language(self):
    """
    Determine currency based on user's language/locale
    Default to DKK (Danish Krone) for MobilePay
    
    Returns:
        recordset: Currency record
    """
    self.ensure_one()
    
    # Get user's language from context or partner
    lang = self.env.context.get('lang') or \
           (self.partner_id.lang if self.partner_id else False) or \
           self.env.user.lang or \
           'da_DK'  # Default to Danish
    
    # Language to currency mapping for Nordic countries
    language_currency_map = {
        'da_DK': 'DKK',  # Danish - Denmark
        'da': 'DKK',     # Danish (short code)
        'nb_NO': 'NOK',  # Norwegian Bokmål - Norway
        'nn_NO': 'NOK',  # Norwegian Nynorsk - Norway
        'no': 'NOK',     # Norwegian (short code)
        'sv_SE': 'SEK',  # Swedish - Sweden
        'sv': 'SEK',     # Swedish (short code)
        'fi_FI': 'EUR',  # Finnish - Finland
        'fi': 'EUR',     # Finnish (short code)
    }
    
    # Get currency code from language, default to DKK
    currency_code = language_currency_map.get(lang, 'DKK')
    
    # Find currency in Odoo
    currency = self.env['res.currency'].search([
        ('name', '=', currency_code),
        ('active', '=', True)
    ], limit=1)
    
    if not currency:
        # Fallback to DKK if currency not found
        _logger.warning(
            "Currency %s not found for language %s, falling back to DKK",
            currency_code, lang
        )
        currency = self.env['res.currency'].search([
            ('name', '=', 'DKK'),
            ('active', '=', True)
        ], limit=1)
    
    if not currency:
        # Last resort: use company currency
        currency = self.env.company.currency_id
    
    _logger.info(
        "Determined currency %s for language %s (transaction %s)",
        currency.name, lang, self.reference
    )
    
    return currency
```

---

### **Step 2: Override Transaction Creation**

Add this method to automatically set currency on transaction creation:

```python
@api.model
def create(self, vals):
    """Override create to set currency based on language if not specified"""
    
    # If currency not explicitly set and this is a Vipps transaction
    if vals.get('provider_code') == 'vipps' and not vals.get('currency_id'):
        # Create temporary record to access helper methods
        temp_tx = self.new(vals)
        currency = temp_tx._get_currency_from_language()
        if currency:
            vals['currency_id'] = currency.id
            _logger.info(
                "Auto-set currency to %s based on language for transaction %s",
                currency.name, vals.get('reference', 'NEW')
            )
    
    return super().create(vals)
```

---

### **Step 3: Update Payment Request to Use Detected Currency**

Modify the `_send_payment_request` method (around line 448):

**BEFORE**:
```python
payload = {
    "reference": payment_reference,
    "returnUrl": return_url,
    "amount": {
        "currency": self.currency_id.name,  # Uses transaction currency
        "value": int(self.amount * 100)
    },
    # ...
}
```

**AFTER**:
```python
# Ensure currency is set based on language if not already set
if not self.currency_id:
    currency = self._get_currency_from_language()
    self.currency_id = currency
    _logger.info(
        "Set currency to %s based on language for transaction %s",
        currency.name, self.reference
    )

# Use the determined currency
currency_code = self.currency_id.name

payload = {
    "reference": payment_reference,
    "returnUrl": return_url,
    "amount": {
        "currency": currency_code,
        "value": int(self.amount * 100)
    },
    # ...
}
```

---

### **Step 4: Add Country-Based Detection (Alternative/Additional)**

For even better accuracy, you can also detect currency from the partner's country:

```python
def _get_currency_from_country(self):
    """
    Determine currency based on partner's country
    
    Returns:
        recordset: Currency record
    """
    self.ensure_one()
    
    if not self.partner_id or not self.partner_id.country_id:
        return None
    
    # Country to currency mapping
    country_currency_map = {
        'DK': 'DKK',  # Denmark
        'NO': 'NOK',  # Norway
        'SE': 'SEK',  # Sweden
        'FI': 'EUR',  # Finland
    }
    
    country_code = self.partner_id.country_id.code
    currency_code = country_currency_map.get(country_code)
    
    if currency_code:
        currency = self.env['res.currency'].search([
            ('name', '=', currency_code),
            ('active', '=', True)
        ], limit=1)
        
        if currency:
            _logger.info(
                "Determined currency %s from country %s for transaction %s",
                currency.name, country_code, self.reference
            )
            return currency
    
    return None
```

Then update `_get_currency_from_language` to use country as primary method:

```python
def _get_currency_from_language(self):
    """
    Determine currency based on country (primary) or language (fallback)
    Default to DKK (Danish Krone) for MobilePay
    """
    self.ensure_one()
    
    # Try country-based detection first (more accurate)
    currency = self._get_currency_from_country()
    if currency:
        return currency
    
    # Fallback to language-based detection
    lang = self.env.context.get('lang') or \
           (self.partner_id.lang if self.partner_id else False) or \
           self.env.user.lang or \
           'da_DK'  # Default to Danish
    
    # ... rest of language-based logic ...
```

---

## 🌐 Website/E-commerce Integration

For website orders, ensure the language is properly set in the context:

### **In Website Controller** (if you have custom controllers):

```python
# Get language from website visitor
lang = request.website.get_current_website().default_lang_id.code

# Set in context when creating transaction
transaction = request.env['payment.transaction'].with_context(lang=lang).create({
    'provider_code': 'vipps',
    'amount': amount,
    # currency_id will be auto-set based on lang
})
```

---

## 📊 Testing the Implementation

### **Test Case 1: Danish User (Default)**
```python
# User with Danish language
transaction = env['payment.transaction'].with_context(lang='da_DK').create({
    'provider_code': 'vipps',
    'amount': 100.00,
    'partner_id': partner.id,
})

assert transaction.currency_id.name == 'DKK'
```

### **Test Case 2: Norwegian User**
```python
# User with Norwegian language
transaction = env['payment.transaction'].with_context(lang='nb_NO').create({
    'provider_code': 'vipps',
    'amount': 100.00,
    'partner_id': partner.id,
})

assert transaction.currency_id.name == 'NOK'
```

### **Test Case 3: Swedish User**
```python
# User with Swedish language
transaction = env['payment.transaction'].with_context(lang='sv_SE').create({
    'provider_code': 'vipps',
    'amount': 100.00,
    'partner_id': partner.id,
})

assert transaction.currency_id.name == 'SEK'
```

### **Test Case 4: Unknown Language (Fallback to DKK)**
```python
# User with unsupported language
transaction = env['payment.transaction'].with_context(lang='en_US').create({
    'provider_code': 'vipps',
    'amount': 100.00,
    'partner_id': partner.id,
})

assert transaction.currency_id.name == 'DKK'  # Falls back to default
```

---

## ⚙️ Configuration Requirements

### **1. Ensure Currencies are Active**

In Odoo, activate all required currencies:

```sql
-- Check active currencies
SELECT name, active FROM res_currency WHERE name IN ('DKK', 'NOK', 'SEK', 'EUR');

-- Activate if needed
UPDATE res_currency SET active = true WHERE name IN ('DKK', 'NOK', 'SEK', 'EUR');
```

Or via Odoo UI:
1. Go to **Accounting → Configuration → Currencies**
2. Activate: DKK, NOK, SEK, EUR

### **2. Set Exchange Rates**

Configure automatic exchange rate updates:
1. Go to **Accounting → Configuration → Settings**
2. Enable **Automatic Currency Rates**
3. Choose a provider (e.g., European Central Bank)
4. Set update interval (e.g., daily)

---

## 🎯 Priority Order for Currency Detection

The implementation uses this priority order:

1. **Explicit currency_id** in transaction creation (highest priority)
2. **Partner's country** (if available)
3. **User's language** from context or partner
4. **Session language** from Odoo context
5. **Default to DKK** (Danish Krone - MobilePay default)

---

## 📝 Complete Implementation Summary

### **Files to Modify**:

1. **`models/payment_transaction.py`**:
   - Add `_get_currency_from_language()` method
   - Add `_get_currency_from_country()` method
   - Override `create()` method
   - Update `_send_payment_request()` to ensure currency is set

### **Code Additions**:

```python
# Add to PaymentTransaction class

def _get_currency_from_country(self):
    """Determine currency from partner's country"""
    # ... (code from Step 4)

def _get_currency_from_language(self):
    """Determine currency from language with DKK default"""
    # ... (code from Step 1)

@api.model
def create(self, vals):
    """Auto-set currency based on language"""
    # ... (code from Step 2)
```

### **Expected Behavior**:

- ✅ Danish users → DKK (default)
- ✅ Norwegian users → NOK
- ✅ Swedish users → SEK
- ✅ Finnish users → EUR
- ✅ Unknown/English users → DKK (fallback)
- ✅ Explicit currency setting → Respected (highest priority)

---

## ⚠️ Important Notes

### **1. MobilePay Supported Currencies**

Ensure you only use currencies supported by MobilePay:
- ✅ DKK (Denmark)
- ✅ NOK (Norway)
- ✅ SEK (Sweden)
- ✅ EUR (Finland)

### **2. Amount Conversion**

If the sale order is in a different currency, you may need to convert:

```python
# Convert amount if needed
if self.sale_order_ids and self.sale_order_ids[0].currency_id != self.currency_id:
    # Convert order amount to transaction currency
    order_currency = self.sale_order_ids[0].currency_id
    converted_amount = order_currency._convert(
        self.amount,
        self.currency_id,
        self.company_id,
        fields.Date.today()
    )
    self.amount = converted_amount
```

### **3. Pricelist Integration**

For e-commerce, consider using Odoo's pricelist feature:
- Create pricelists for each country/language
- Link pricelists to country groups
- Odoo will automatically apply correct prices and currency

---

## ✅ Validation Checklist

After implementation:

- [ ] DKK is set as default currency for new transactions
- [ ] Danish language (`da_DK`) → DKK
- [ ] Norwegian language (`nb_NO`) → NOK
- [ ] Swedish language (`sv_SE`) → SEK
- [ ] Finnish language (`fi_FI`) → EUR
- [ ] Unknown languages fall back to DKK
- [ ] All currencies are active in Odoo
- [ ] Exchange rates are configured
- [ ] Payment requests use correct currency code
- [ ] Order details use correct currency in receipt

---

## 🚀 Quick Implementation

**Minimum required changes** for Danish default:

```python
# In models/payment_transaction.py

@api.model
def create(self, vals):
    """Set DKK as default currency for Vipps transactions"""
    if vals.get('provider_code') == 'vipps' and not vals.get('currency_id'):
        # Get DKK currency
        dkk = self.env['res.currency'].search([('name', '=', 'DKK')], limit=1)
        if dkk:
            vals['currency_id'] = dkk.id
    
    return super().create(vals)
```

This ensures **DKK is always the default** for MobilePay transactions unless explicitly overridden.
