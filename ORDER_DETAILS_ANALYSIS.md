# MobilePay Order Details Implementation Analysis

## ❌ **Current Status: INCOMPLETE IMPLEMENTATION**

Your code **partially implements** order details but is **missing critical fields** required by the MobilePay API.

---

## 📋 What You're Currently Sending

### **Current Implementation** (Lines 490-504 in `payment_transaction.py`)

```python
# Add order details if available
if self.sale_order_ids:
    order_lines = []
    for line in self.sale_order_ids.order_line:
        order_lines.append({
            "name": line.name,
            "quantity": line.product_uom_qty,
            "unitPrice": {
                "currency": self.currency_id.name,
                "value": int(line.price_unit * 100)
            }
        })
    payload["orderDetails"] = {
        "orderLines": order_lines
    }
```

### **What This Sends**:
```json
{
  "orderDetails": {
    "orderLines": [
      {
        "name": "Product Name",
        "quantity": 2,
        "unitPrice": {
          "currency": "NOK",
          "value": 10000
        }
      }
    ]
  }
}
```

---

## ❌ **Problems with Current Implementation**

### **1. Wrong API Structure**

According to MobilePay documentation, order details should be in a **`receipt`** object, not `orderDetails`:

**Correct Structure**:
```json
{
  "receipt": {
    "orderLines": [...]
  }
}
```

**Your Current Structure** (WRONG):
```json
{
  "orderDetails": {
    "orderLines": [...]
  }
}
```

### **2. Missing Required Fields**

Each `orderLine` requires **additional mandatory fields**:

| Field | Status | Description |
|-------|--------|-------------|
| `name` | ✅ Included | Product name |
| `quantity` | ✅ Included | Quantity |
| `unitPrice` | ✅ Included | Unit price |
| `totalAmount` | ❌ **MISSING** | Total for this line (quantity × unitPrice) |
| `totalAmountExcludingTax` | ❌ **MISSING** | Amount excluding tax |
| `totalTaxAmount` | ❌ **MISSING** | Total tax amount |
| `taxRate` | ❌ **MISSING** | Tax rate percentage |
| `id` | ⚠️ Optional | Unique line identifier |
| `discount` | ⚠️ Optional | Discount amount |
| `productUrl` | ⚠️ Optional | Link to product |
| `isReturn` | ⚠️ Optional | Return indicator |
| `isShipping` | ⚠️ Optional | Shipping line indicator |

### **3. Missing Receipt-Level Fields**

The `receipt` object also requires:

| Field | Status | Description |
|-------|--------|-------------|
| `orderLines` | ✅ Included | Array of order lines |
| `bottomLine` | ❌ **MISSING** | Order totals summary |

---

## ✅ **Correct Implementation According to MobilePay API**

### **Complete Schema**

```json
{
  "receipt": {
    "orderLines": [
      {
        "id": "line-1",
        "name": "Premium Widget",
        "quantity": 2,
        "unitPrice": {
          "currency": "NOK",
          "value": 10000
        },
        "totalAmount": {
          "currency": "NOK",
          "value": 20000
        },
        "totalAmountExcludingTax": {
          "currency": "NOK",
          "value": 16000
        },
        "totalTaxAmount": {
          "currency": "NOK",
          "value": 4000
        },
        "taxRate": 25.0,
        "discount": {
          "currency": "NOK",
          "value": 0
        },
        "productUrl": "https://shop.example.com/products/premium-widget",
        "isReturn": false,
        "isShipping": false
      }
    ],
    "bottomLine": {
      "currency": "NOK",
      "tipAmount": 0,
      "receiptNumber": "ORDER-12345",
      "paymentSources": {
        "giftCard": 0,
        "card": 20000,
        "voucher": 0,
        "cash": 0
      },
      "barcode": {
        "format": "EAN-13",
        "data": "1234567890123"
      },
      "terminalId": "TERMINAL-001"
    }
  }
}
```

---

## 🔧 **Required Code Changes**

### **Updated Implementation**

Replace lines 490-504 in `payment_transaction.py` with:

```python
# Add order details (receipt) if available
if self.sale_order_ids:
    order = self.sale_order_ids[0]  # Get the first order
    order_lines = []
    
    for line in order.order_line:
        # Calculate amounts
        unit_price = int(line.price_unit * 100)  # In minor units (øre/cents)
        quantity = line.product_uom_qty
        
        # Calculate tax rate from Odoo tax configuration
        tax_rate = 0.0
        if line.tax_id:
            # Get the first tax rate (assuming single tax per line)
            tax_rate = line.tax_id[0].amount if line.tax_id else 0.0
        
        # Calculate amounts
        total_amount = int(line.price_subtotal * 100)  # Subtotal with tax
        total_tax_amount = int(line.price_tax * 100)  # Tax amount
        total_amount_excluding_tax = total_amount - total_tax_amount
        
        # Calculate discount if any
        discount_amount = 0
        if line.discount > 0:
            discount_amount = int((line.price_unit * quantity * line.discount / 100) * 100)
        
        order_line_data = {
            "id": str(line.id),
            "name": line.name[:100],  # Limit to 100 chars
            "quantity": quantity,
            "unitPrice": {
                "currency": self.currency_id.name,
                "value": unit_price
            },
            "totalAmount": {
                "currency": self.currency_id.name,
                "value": total_amount
            },
            "totalAmountExcludingTax": {
                "currency": self.currency_id.name,
                "value": total_amount_excluding_tax
            },
            "totalTaxAmount": {
                "currency": self.currency_id.name,
                "value": total_tax_amount
            },
            "taxRate": tax_rate,
            "isReturn": False,
            "isShipping": line.product_id.type == 'service' and 'shipping' in line.name.lower()
        }
        
        # Add discount if present
        if discount_amount > 0:
            order_line_data["discount"] = {
                "currency": self.currency_id.name,
                "value": discount_amount
            }
        
        # Add product URL if available
        if hasattr(line.product_id, 'website_url') and line.product_id.website_url:
            base_url = self.provider_id.get_base_url()
            order_line_data["productUrl"] = f"{base_url}{line.product_id.website_url}"
        
        order_lines.append(order_line_data)
    
    # Build bottom line (order totals)
    bottom_line = {
        "currency": self.currency_id.name,
        "tipAmount": 0,  # Odoo doesn't typically have tips
        "receiptNumber": order.name,  # Order reference
    }
    
    # Add payment sources (all from card/wallet in this case)
    bottom_line["paymentSources"] = {
        "giftCard": 0,
        "card": int(self.amount * 100),
        "voucher": 0,
        "cash": 0
    }
    
    # Add terminal ID if in POS context
    if self.pos_session_id:
        bottom_line["terminalId"] = f"POS-{self.pos_session_id}"
    
    # Build receipt object (correct API structure)
    payload["receipt"] = {
        "orderLines": order_lines,
        "bottomLine": bottom_line
    }
```

---

## 📊 **Validation Requirements**

According to MobilePay documentation, for order details to display correctly:

### **1. Amount Validation**
```python
# The payment amount MUST equal the sum of all order lines
payment_amount = payload["amount"]["value"]
order_lines_total = sum(line["totalAmount"]["value"] for line in order_lines)

assert payment_amount == order_lines_total, "Payment amount must equal order lines total"
```

### **2. Tax Validation**
```python
# All tax fields must be consistent
for line in order_lines:
    total = line["totalAmount"]["value"]
    excluding_tax = line["totalAmountExcludingTax"]["value"]
    tax = line["totalTaxAmount"]["value"]
    
    assert total == excluding_tax + tax, "Tax calculation must be correct"
```

### **3. Enable Order Summary**

To ensure order details are shown in the MobilePay app, you may need to set:

```python
payload["orderSummary"] = True  # Enable order summary display
```

---

## 🎯 **Benefits of Proper Implementation**

When correctly implemented, customers will see:

1. **In MobilePay App**:
   - Complete list of purchased items
   - Individual prices and quantities
   - Tax breakdown
   - Total amount verification

2. **In Receipt/History**:
   - Detailed purchase history
   - Proof of purchase
   - Tax documentation

3. **Better Customer Experience**:
   - Transparency about what they're paying for
   - Ability to verify order before confirming
   - Digital receipt in app

---

## ⚠️ **Important Notes**

### **1. API Endpoint**

Order details can be sent in two ways:

**Option A: At Payment Creation** (Current approach - RECOMMENDED)
```python
# Include receipt in POST /epayment/v1/payments
payload["receipt"] = {...}
```

**Option B: After Payment Creation** (Alternative)
```python
# Use Order Management API
POST /order-management/v2/ePayment/receipts/{orderId}
```

Your current implementation uses **Option A**, which is correct.

### **2. Immutability**

Once sent, order details **cannot be changed**. Ensure accuracy before sending.

### **3. Optional vs Required**

**Minimum Required Fields** (to display order details):
- `receipt.orderLines[].name`
- `receipt.orderLines[].quantity`
- `receipt.orderLines[].unitPrice`
- `receipt.orderLines[].totalAmount`
- `receipt.orderLines[].totalAmountExcludingTax`
- `receipt.orderLines[].totalTaxAmount`
- `receipt.orderLines[].taxRate`

**Recommended Additional Fields**:
- `receipt.bottomLine` (order summary)
- `receipt.orderLines[].id` (for tracking)
- `receipt.orderLines[].productUrl` (for customer reference)

---

## 🔍 **Testing Checklist**

After implementing the changes:

- [ ] Verify `receipt` object is in payload (not `orderDetails`)
- [ ] Check all required fields are present in each order line
- [ ] Validate payment amount equals sum of order lines
- [ ] Verify tax calculations are correct
- [ ] Test with multiple products
- [ ] Test with discounted products
- [ ] Test with different tax rates
- [ ] Verify order details display in MobilePay test app

---

## 📝 **Summary**

| Aspect | Current Status | Required Action |
|--------|---------------|-----------------|
| **API Structure** | ❌ Using `orderDetails` | ✅ Change to `receipt` |
| **Basic Fields** | ✅ name, quantity, unitPrice | ✅ Keep these |
| **Amount Fields** | ❌ Missing totalAmount, etc. | ✅ Add all amount fields |
| **Tax Fields** | ❌ Missing all tax fields | ✅ Add tax calculations |
| **Bottom Line** | ❌ Not implemented | ✅ Add order summary |
| **Validation** | ❌ No validation | ✅ Add amount validation |

**Conclusion**: Your code **attempts** to send order details but uses an **incorrect structure** and is **missing critical fields**. The order details will likely **not display** in the MobilePay app with the current implementation.

Implement the changes above to properly show purchased products to customers in their MobilePay app.
