# Current Currency Implementation Analysis

## 📊 How Currency is Currently Implemented

### **1. Currency Field Source**

Your `PaymentTransaction` class **inherits** from Odoo's base `payment.transaction` model:

```python
class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
```

**What this means**:
- The `currency_id` field is **NOT defined** in your custom code
- It comes from Odoo's core `payment.transaction` model
- Located in: `odoo/addons/payment/models/payment_transaction.py`

---

### **2. Where Currency Comes From (Odoo Core)**

In Odoo's base payment transaction model, `currency_id` is defined as:

```python
# In odoo/addons/payment/models/payment_transaction.py
currency_id = fields.Many2one(
    'res.currency',
    string='Currency',
    required=True,
    readonly=True,
    states={'draft': [('readonly', False)]},
)
```

**Currency is set when the transaction is created**, typically from:

1. **Sale Order Currency** (most common):
   ```python
   # When creating transaction from sale order
   transaction = env['payment.transaction'].create({
       'currency_id': sale_order.currency_id.id,  # From order
       'amount': sale_order.amount_total,
       # ...
   })
   ```

2. **Invoice Currency**:
   ```python
   # When creating transaction from invoice
   transaction = env['payment.transaction'].create({
       'currency_id': invoice.currency_id.id,  # From invoice
       'amount': invoice.amount_total,
       # ...
   })
   ```

3. **Company Default Currency** (fallback):
   ```python
   # If no order/invoice
   transaction = env['payment.transaction'].create({
       'currency_id': env.company.currency_id.id,  # Company default
       'amount': 100.00,
       # ...
   })
   ```

---

### **3. How Your Code Uses Currency**

Your code **reads** the currency but **never sets** it. Here are all the places where currency is used:

#### **A. Payment Request Creation** (Line 449, 462)
```python
# models/payment_transaction.py, line 445-469
payload = {
    "reference": payment_reference,
    "returnUrl": return_url,
    "amount": {
        "currency": self.currency_id.name,  # ← READS currency
        "value": int(self.amount * 100)
    },
    # ...
    "transaction": {
        "amount": {
            "currency": self.currency_id.name,  # ← READS currency
            "value": int(self.amount * 100)
        },
        # ...
    }
}
```

#### **B. Order Details** (Line 498)
```python
# models/payment_transaction.py, line 490-504
if self.sale_order_ids:
    order_lines = []
    for line in self.sale_order_ids.order_line:
        order_lines.append({
            "name": line.name,
            "quantity": line.product_uom_qty,
            "unitPrice": {
                "currency": self.currency_id.name,  # ← READS currency
                "value": int(line.price_unit * 100)
            }
        })
```

#### **C. POS Payments** (Line 739, 755)
```python
# models/payment_transaction.py, line 736-763
payload = {
    "amount": {
        "currency": self.currency_id.name,  # ← READS currency
        "value": int(self.amount * 100)
    },
    # ...
    "transaction": {
        "amount": {
            "currency": self.currency_id.name,  # ← READS currency
            "value": int(self.amount * 100)
        },
        # ...
    }
}
```

#### **D. Capture/Refund Operations** (Lines 1255, 1356)
```python
# Capture payload
payload = {
    "modificationAmount": {
        "currency": self.currency_id.name,  # ← READS currency
        "value": int(capture_amount * 100)
    }
}

# Refund payload
payload = {
    "modificationAmount": {
        "currency": self.currency_id.name,  # ← READS currency
        "value": int(refund_amount * 100)
    }
}
```

#### **E. Logging and Display** (Multiple locations)
```python
# Debug logging
_logger.info("🔧 Amount: %s %s", self.amount, self.currency_id.name)

# Receipt data
'currency': self.currency_id.name,

# State messages
f"Partial capture: {capture_amount} {self.currency_id.name}"
```

---

### **4. Currency Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. TRANSACTION CREATION                                     │
│    (Odoo Core or E-commerce Module)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CURRENCY SOURCE (Priority Order)                         │
│    ┌──────────────────────────────────────────────┐         │
│    │ a) Sale Order Currency (if from order)       │         │
│    │    currency_id = sale_order.currency_id      │         │
│    └──────────────────────────────────────────────┘         │
│    ┌──────────────────────────────────────────────┐         │
│    │ b) Invoice Currency (if from invoice)        │         │
│    │    currency_id = invoice.currency_id         │         │
│    └──────────────────────────────────────────────┘         │
│    ┌──────────────────────────────────────────────┐         │
│    │ c) Company Default Currency (fallback)       │         │
│    │    currency_id = company.currency_id         │         │
│    └──────────────────────────────────────────────┘         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. YOUR CODE READS CURRENCY                                 │
│    - Payment request: self.currency_id.name                 │
│    - Order details: self.currency_id.name                   │
│    - Capture/Refund: self.currency_id.name                  │
│    - Logging: self.currency_id.name                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. SENT TO MOBILEPAY API                                    │
│    {                                                         │
│      "amount": {                                             │
│        "currency": "NOK",  ← From self.currency_id.name     │
│        "value": 10000                                        │
│      }                                                       │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
```

---

### **5. Example Scenarios**

#### **Scenario A: E-commerce Order (Most Common)**

```python
# 1. Customer creates order in webshop
sale_order = env['sale.order'].create({
    'partner_id': customer.id,
    'currency_id': env.ref('base.NOK').id,  # Norwegian Krone
    # ... order lines ...
})

# 2. Customer proceeds to payment
# Odoo creates transaction with order's currency
transaction = env['payment.transaction'].create({
    'sale_order_ids': [(6, 0, [sale_order.id])],
    'currency_id': sale_order.currency_id.id,  # ← NOK from order
    'amount': sale_order.amount_total,
    'provider_code': 'vipps',
})

# 3. Your code sends payment request
# Uses: self.currency_id.name → "NOK"
```

**Result**: Currency = **NOK** (from sale order)

---

#### **Scenario B: Direct Payment (No Order)**

```python
# 1. Create transaction directly
transaction = env['payment.transaction'].create({
    'partner_id': customer.id,
    'amount': 100.00,
    'provider_code': 'vipps',
    # currency_id NOT specified
})

# 2. Odoo sets default company currency
# If company currency is EUR:
transaction.currency_id → EUR

# 3. Your code sends payment request
# Uses: self.currency_id.name → "EUR"
```

**Result**: Currency = **EUR** (company default)

---

#### **Scenario C: POS Payment**

```python
# 1. POS creates transaction
transaction = env['payment.transaction'].create({
    'pos_session_id': session.id,
    'currency_id': session.config_id.currency_id.id,  # POS config currency
    'amount': 50.00,
    'provider_code': 'vipps',
})

# 2. Your code sends payment request
# Uses: self.currency_id.name → session currency
```

**Result**: Currency = **POS session currency**

---

### **6. Where Currency is NOT Set**

Your code **NEVER** sets `currency_id`. There is:

- ❌ No `create()` override to set currency
- ❌ No `write()` override to modify currency
- ❌ No `@api.onchange` to change currency
- ❌ No language-based currency detection
- ❌ No country-based currency detection
- ❌ No default currency configuration

**The currency is ALWAYS inherited from**:
1. The sale order
2. The invoice
3. The company default

---

### **7. Currency Usage Summary**

| Location | Line(s) | Purpose | Currency Source |
|----------|---------|---------|-----------------|
| Payment request amount | 449 | API payload | `self.currency_id.name` |
| Payment request transaction | 462 | API payload | `self.currency_id.name` |
| Order line unitPrice | 498 | Order details | `self.currency_id.name` |
| POS payment amount | 739 | API payload | `self.currency_id.name` |
| POS transaction amount | 755 | API payload | `self.currency_id.name` |
| Capture amount | 1255 | Capture API | `self.currency_id.name` |
| Refund amount | 1356 | Refund API | `self.currency_id.name` |
| Logging | Multiple | Debug output | `self.currency_id.name` |
| Receipt display | 2629 | POS receipt | `self.currency_id.name` |

**Total occurrences**: 35 times in the file
**All are READ operations** - no writes/modifications

---

### **8. The Problem**

```python
# Current flow:
Sale Order (NOK) → Transaction (NOK) → MobilePay API (NOK) ✅

# But if you want:
Danish User → Transaction (DKK) → MobilePay API (DKK) ❌
# This doesn't happen automatically!
```

**Why?**
- No code to detect user language
- No code to set currency based on language
- No code to default to DKK for Danish users

---

### **9. What Needs to Change**

To implement language-based currency with DKK default, you need to **ADD** code to:

1. **Detect language/country** when transaction is created
2. **Set currency_id** based on detection
3. **Default to DKK** if language is unknown

**Current**: Currency passively inherited from order/company
**Needed**: Currency actively set based on user context

---

## 🎯 Summary

### **Current Implementation**:
```python
# Your code ONLY reads currency, never sets it
"currency": self.currency_id.name  # ← Reads from Odoo core field
```

### **Currency Source Chain**:
```
Sale Order → currency_id → Your Code → MobilePay API
   OR
Company Default → currency_id → Your Code → MobilePay API
```

### **Missing**:
```
User Language → Currency Detection → currency_id → Your Code → MobilePay API
                    ↑
              NOT IMPLEMENTED
```

### **To Implement DKK Default**:

You need to **add** a `create()` method override:

```python
@api.model
def create(self, vals):
    """Set currency based on language with DKK default"""
    if vals.get('provider_code') == 'vipps' and not vals.get('currency_id'):
        # Add currency detection logic here
        vals['currency_id'] = dkk_currency.id
    
    return super().create(vals)
```

**This code does NOT exist in your current implementation.**

---

## 📋 Files Involved

1. **Your Code** (reads currency):
   - `/models/payment_transaction.py` - Uses `self.currency_id.name` 35 times

2. **Odoo Core** (defines currency):
   - `odoo/addons/payment/models/payment_transaction.py` - Defines `currency_id` field

3. **Currency Data**:
   - `odoo/addons/base/data/res_currency_data.xml` - Currency definitions (DKK, NOK, SEK, EUR)

---

## ✅ Conclusion

**Your code is a PASSIVE consumer of currency**:
- ✅ Reads currency correctly
- ✅ Sends to API correctly
- ❌ Never sets currency
- ❌ No language detection
- ❌ No DKK default

To implement language-based currency with DKK default, you need to **add new code** - it's not currently implemented.
