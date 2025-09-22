# -*- coding: utf-8 -*-

def post_init_hook(env):
    """
    Post-installation hook to create payment method after provider is set up
    """
    # Create payment method for Vipps/MobilePay
    payment_method = env['payment.method'].search([('code', '=', 'vipps')])
    
    if not payment_method:
        # Create the payment method
        env['payment.method'].create({
            'name': 'Vipps/MobilePay',
            'code': 'vipps',
            'active': True,
            'brand_ids': [(6, 0, [])],
        })
        
    # Ensure the payment provider exists and has correct settings
    provider = env['payment.provider'].search([('code', '=', 'vipps')], limit=1)
    if provider:
        # Make sure the provider supports the payment method
        provider.write({
            'supported_payment_method_ids': [(4, env.ref('mobilepay_vipps.payment_method_vipps').id)]
        })