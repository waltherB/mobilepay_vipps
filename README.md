# MobilePay by Vipps Payment Provider for Odoo 17 CE

[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

Official integration between Odoo 17 Community Edition and MobilePay/Vipps ePayment system.

![MobilePay Vipps Payment Flow](https://via.placeholder.com/800x400.png?text=Payment+Flow+Diagram)

## Key Features
✅ Full payment processing integration with Vipps ePayment API  
✅ MobilePay app redirection during checkout  
✅ Automatic payment status synchronization  
✅ Webhook authentication (HMAC-SHA256)  
✅ Refund management from Odoo interface  
✅ Capture-on-delivery automation  
✅ API request retry mechanism (3 attempts)  
✅ Idempotency key implementation  
✅ Multi-language status messages  
✅ Transaction monitoring dashboard  
✅ Comprehensive error logging  

## Installation
1. Clone module to your Odoo custom-addons directory:
```bash
git clone https://github.com/yourrepo/mobilepay_vipps.git ./custom-addons/mobilepay_vipps

    Install via Odoo Apps:

        Go to Apps → Update Apps List

        Search for "MobilePay Vipps"

        Click Install

Requirements:

    Odoo 17 Community Edition

    payment, website_sale, and sale_stock modules enabled

Configuration

    Obtain API Credentials:

        Register at Vipps Developer Portal

        Create API key and merchant serial number

    Odoo Configuration:

        Go to Accounting → Payment Providers

        Create new "MobilePay by Vipps" provider:

            Enter API Key

            Merchant Serial Number

            Webhook Secret

            Enable "Capture on Delivery" (recommended)

    Webhook Setup:

        In Vipps Dashboard → Webhooks:

            URL: https://yourdomain.com/vipps/webhook

            Secret: Same as configured in Odoo

Usage
For Merchants

    Online Payments: Customers will see MobilePay/Vipps option during checkout

    Refunds: Initiate refunds directly from sale orders/payments

    Capture Automation: Payments are automatically captured when deliveries are validated

For Developers

API Endpoints:

    Payment Initiation: /epayment/v1/payments

    Capture: /epayment/v1/payments/{paymentId}/capture

    Refund: /epayment/v1/payments/{paymentId}/refund

Extending the Module:
python
Copy

from odoo.addons.mobilepay_vipps.models.payment_provider import PaymentProvider

class CustomPaymentProvider(PaymentProvider):
    _inherit = 'payment.provider'
    
    def _custom_vipps_operation(self):
        # Your custom logic here

Running Tests:
bash
Copy

odoo-bin --test-enable --stop-after-init -d test_db -i mobilepay_vipps

Localization

Supported languages:

    English (US)

    Norwegian (Bokmål) [contrib]

    Danish [contrib]

To add translations:

    Create .po file in i18n/ directory

    Update __manifest__.py with new language code

    Submit pull request

Changelog
1.0.0 (2024-03-15)

    Initial release

    Full integration with Vipps ePayment API v1

    Capture-on-delivery workflow

    Comprehensive error handling

Support

Commercial Support: contact@yourcompany.com
Community Support: GitHub Issues

License: LGPL-3
Official Partner: Your Company Name