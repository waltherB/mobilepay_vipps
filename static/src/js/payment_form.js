/** @odoo-module **/

// Vipps/MobilePay Payment Module
// Custom implementation to bypass Odoo's problematic redirect processing

console.log('Vipps/MobilePay payment module loaded - Custom redirect handling enabled');

// Override Vipps payment button to use direct redirect
document.addEventListener('DOMContentLoaded', function() {
    // Find Vipps payment radio button
    const vippsRadio = document.querySelector('input[name="o_payment_radio"][data-provider-code="vipps"]');
    if (!vippsRadio) return;
    
    // Find the payment form
    const paymentForm = vippsRadio.closest('form');
    if (!paymentForm) return;
    
    // Override form submission for Vipps
    paymentForm.addEventListener('submit', function(e) {
        if (vippsRadio.checked) {
            e.preventDefault();
            console.log('Vipps payment: intercepting form submission');
            
            // Get transaction ID from form data or URL
            const formData = new FormData(paymentForm);
            const reference = formData.get('reference');
            
            // Extract transaction ID from current URL or use reference
            const urlMatch = window.location.pathname.match(/\/payment\/transaction\/(\d+)/);
            const transactionId = urlMatch ? urlMatch[1] : reference;
            
            if (transactionId) {
                console.log('Redirecting to Vipps with transaction ID:', transactionId);
                // Direct redirect to our controller
                window.location.href = `/payment/vipps/redirect/${transactionId}`;
            } else {
                console.error('No transaction ID found');
                alert('Payment initialization failed: No transaction ID');
            }
        }
    });
});