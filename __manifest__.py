# -*- coding: utf-8 -*-
{
    'name': 'Vipps/MobilePay Payment Integration',
    'version': '1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'Complete Vipps/MobilePay payment integration for Odoo with eCommerce and POS support',
    'description': """
Vipps/MobilePay Payment Integration
===================================

This module provides comprehensive integration with Vipps (Norway) and MobilePay (Denmark/Finland/Sweden) 
payment services for Odoo 17.0+, supporting both eCommerce and Point of Sale (POS) transactions.

Key Features:
-------------
* **eCommerce Integration**: Seamless checkout experience for online stores
* **POS Integration**: Multiple payment flows for in-store transactions
  - QR code generation for customer scanning
  - Phone number push notifications
  - Manual shop number/QR code entry with verification
* **Real-time Payment Processing**: Instant payment status updates via webhooks
* **Customer Profile Management**: Optional customer data collection with privacy controls
* **Security & Compliance**: 
  - GDPR compliant data handling
  - PCI DSS security measures
  - Encrypted credential storage
  - Webhook signature validation
* **Multi-language Support**: Danish localization included
* **Comprehensive Testing**: Full test suite with security and performance validation
* **Production Ready**: Complete validation and deployment tools

Payment Flows Supported:
------------------------
1. **Online eCommerce**: Standard web checkout with redirect flow
2. **POS QR Code**: Customer scans QR code displayed on terminal
3. **POS Phone Push**: Payment request sent to customer's phone number
4. **POS Manual Entry**: Customer enters shop number/QR code in their app

Technical Features:
-------------------
* Automatic access token management
* Idempotent payment operations
* Comprehensive error handling and retry logic
* Real-time webhook processing
* Payment capture, refund, and cancellation support
* Audit logging and monitoring
* Backup and disaster recovery procedures

Requirements:
-------------
* Odoo 17.0+
* PostgreSQL database
* Valid Vipps/MobilePay merchant account
* SSL certificate for webhook endpoints
* Python 3.8+

Installation & Setup:
---------------------
1. Install the module through Odoo Apps
2. Run the onboarding wizard to configure credentials
3. Test the integration using the built-in validation tools
4. Go live with production credentials

For detailed setup instructions, see the included documentation.

Support:
--------
* Documentation: See docs/ directory
* Testing: Run included test suites
* Validation: Use production readiness validation tools
* Community: This is an open-source project - contributions welcome!

License: LGPL-3
Author: Vipps/MobilePay Integration Team
Website: https://github.com/waltherB/mobilepay_vipps
    """,
    'author': 'Vipps/MobilePay Integration Team',
    'website': 'https://github.com/waltherB/mobilepay_vipps',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'payment',
        'website_sale',
        'point_of_sale',
        'account',
        'sale',
        'website',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/security.xml',
        
        # Data
        'data/payment_method_data.xml',
        'data/vipps_profile_scopes.xml',
        
        # Views
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/pos_payment_method_views.xml',
        'views/vipps_profile_wizard_views.xml',
        'views/vipps_data_management_views.xml',
        'views/vipps_security_views.xml',
        'views/res_partner_views.xml',
        
        # Templates
        'views/payment_form_templates.xml',
        'views/checkout_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mobilepay_vipps/static/src/css/payment_form.css',
            'mobilepay_vipps/static/src/js/payment_form.js',
        ],
        'point_of_sale.assets': [
            'mobilepay_vipps/static/src/css/pos_payment.css',
            'mobilepay_vipps/static/src/js/pos_payment.js',
            'mobilepay_vipps/static/src/js/pos_payment_screen.js',
            'mobilepay_vipps/static/src/xml/pos_payment_screen.xml',
        ],
        'web.assets_backend': [
            'mobilepay_vipps/static/src/css/backend.css',
            'mobilepay_vipps/static/src/js/backend.js',
        ],
    },
    'demo': [
        'demo/payment_demo.xml',
    ],
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
        'static/description/screenshot_1.png',
        'static/description/screenshot_2.png',
        'static/description/screenshot_3.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    # 'pre_init_hook': 'pre_init_check',  # Temporarily disabled due to Odoo 17 caching issues
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'external_dependencies': {
        'python': ['requests', 'cryptography'],
    },
    'price': 0.00,
    'currency': 'EUR',
    'support': 'community',
    'maintainer': 'Vipps/MobilePay Integration Team',
    'contributors': [
        'Development Team',
        'Security Team',
        'QA Team',
    ],
    'development_status': 'Production/Stable',
    'technical_name': 'payment_vipps_mobilepay',
}