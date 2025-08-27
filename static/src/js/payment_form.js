/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class PaymentVipps extends Component {
    static template = "payment_vipps_mobilepay.PaymentForm";
    
    setup() {
        super.setup();
        if (window.location.pathname === '/shop/payment') {
            this._handleVippsRedirect();
        }
    }

    _handleVippsRedirect() {
        const vippsButton = document.querySelector('button[name="pay_vipps"]');
        if (vippsButton) {
            vippsButton.addEventListener('click', (ev) => {
                ev.preventDefault();
                window.location.href = '/payment/vipps/redirect';
            });
        }
    }
}

registry.category("public_components").add("PaymentVipps", PaymentVipps);