{
    'name': 'MobilePay by Vipps Payment Provider',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'MobilePay/Vipps integration for Odoo eCommerce',
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['payment', 'website_sale', 'sale_stock'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_templates.xml',
        'views/transaction_views.xml',
        'data/payment_provider_data.xml',
        'security/ir.model.access.csv',
        'i18n/en_US.po',
        'i18n/nb_NO.po',
        'i18n/da_DK.po',
        'i18n/en_GB.po',
    ],
    'assets': {
        'web.assets_frontend': [
            'mobilepay_vipps/static/src/js/payment_form.js',
        ],
    },
    'application': True,
    'installable': True,
}