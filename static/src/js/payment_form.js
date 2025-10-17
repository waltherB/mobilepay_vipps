/** @odoo-module **/

import { registry } from "@web/core/registry";

// Vipps/MobilePay Payment Form Handler
// Custom implementation to handle redirect form properly

class VippsPaymentForm {
    setup() {
        this._setupVippsPaymentHandling();
    }
    
    _setupVippsPaymentHandling() {
        document.addEventListener('DOMContentLoaded', () => {
            // Find Vipps payment radio button
            const vippsRadio = document.querySelector('input[name="o_payment_radio"][data-provider-code="vipps"]');
            if (!vippsRadio) return;
            
            // Find the payment form
            const paymentForm = vippsRadio.closest('form');
            if (!paymentForm) return;
            
            // Override form submission for Vipps
            paymentForm.addEventListener('submit', (e) => {
                if (vippsRadio.checked) {
                    e.preventDefault();
                    console.log('Vipps payment: intercepting form submission');
                    this._handleVippsPayment(paymentForm);
                }
            });
        });
    }
    
    async _handleVippsPayment(form) {
        try {
            // Show loading state
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.textContent = 'Processing...';
            submitButton.disabled = true;
            
            // Get form data
            const formData = new FormData(form);
            const data = {
                provider_id: formData.get('provider_id'),
                reference: formData.get('reference') || 'temp-ref-' + Date.now(),
                amount: formData.get('amount'),
                currency_id: formData.get('currency_id'),
                partner_id: formData.get('partner_id')
            };
            
            console.log('Vipps payment data:', data);
            
            // Call our controller to get redirect form
            const response = await fetch('/payment/vipps/get_payment_url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: data
                })
            });
            
            const result = await response.json();
            
            if (result.error) {
                throw new Error(result.error.message || result.error);
            }
            
            if (result.result && result.result.redirect_form_html) {
                // Insert the redirect form and submit it
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = result.result.redirect_form_html;
                document.body.appendChild(tempDiv);
                
                const redirectForm = tempDiv.querySelector('form');
                if (redirectForm) {
                    console.log('Vipps: Submitting redirect form');
                    redirectForm.submit();
                } else {
                    throw new Error('No redirect form found in response');
                }
            } else {
                throw new Error('No redirect form in response');
            }
            
        } catch (error) {
            console.error('Vipps payment error:', error);
            alert('Payment initialization failed: ' + error.message);
            
            // Restore button state
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.textContent = originalText;
            submitButton.disabled = false;
        }
    }
}

// Register the component
registry.category("public_components").add("VippsPaymentForm", VippsPaymentForm);

console.log('Vipps/MobilePay payment module loaded - Custom redirect handling enabled');