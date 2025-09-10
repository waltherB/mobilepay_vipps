/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class PaymentVipps extends Component {
    static template = "payment_vipps_mobilepay.PaymentForm";
    
    setup() {
        super.setup();
        if (window.location.pathname === '/shop/payment') {
            this._convertVippsButtonToLink();
        }
    }

    _convertVippsButtonToLink() {
        const vippsButton = document.querySelector('button[name="pay_vipps"]');
        if (!vippsButton) return;

        const link = document.createElement('a');
        link.href = '/payment/vipps/redirect';
        link.textContent = vippsButton.textContent || 'Pay with Vipps/MobilePay';
        link.className = vippsButton.className;
        link.setAttribute('role', 'button');
        link.setAttribute('rel', 'external');

        // Preserve any surrounding layout/attributes
        if (vippsButton.id) link.id = vippsButton.id;
        for (const attr of vippsButton.attributes) {
            if (attr.name.startsWith('data-')) link.setAttribute(attr.name, attr.value);
        }

        vippsButton.replaceWith(link);
    }
}

registry.category("public_components").add("PaymentVipps", PaymentVipps);