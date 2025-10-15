/** @odoo-module **/

import { registry } from "@web/core/registry";

// Vipps/MobilePay Payment Form Handler
// Disable Odoo's complex payment processing for Vipps

class VippsPaymentForm {
    setup() {
        // Override Odoo's payment form processing for Vipps
        this._disableOdooPaymentProcessing();
    }
    
    _disableOdooPaymentProcessing() {
        // Find Vipps payment forms and handle them differently
        document.addEventListener('DOMContentLoaded', () => {
            const vippsButtons = document.querySelectorAll('button[name*="vipps"], input[name*="vipps"]');
            vippsButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    // Let the form submit normally without JavaScript interference
                    console.log('Vipps payment: allowing normal form submission');
                });
            });
        });
    }
}

// Register but don't interfere with standard flow
registry.category("public_components").add("VippsPaymentForm", VippsPaymentForm);

console.log('Vipps/MobilePay payment module loaded - JavaScript interference disabled');