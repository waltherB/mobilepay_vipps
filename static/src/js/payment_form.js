odoo.define('mobilepay_vipps.payment_form', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    
    publicWidget.registry.PaymentVipps = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        
        start: function () {
            if (window.location.pathname === '/shop/payment') {
                this._handleVippsRedirect();
            }
            return this._super.apply(this, arguments);
        },

        _handleVippsRedirect: function () {
            const $vippsButton = $('button[name="pay_vipps"]');
            $vippsButton.click(function (ev) {
                ev.preventDefault();
                window.location.href = '/payment/vipps/redirect';
            });
        }
    });
});