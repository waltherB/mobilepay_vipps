import logging
import uuid
import requests
from odoo import models, fields, api, _
from tenacity import retry, stop_after_attempt, wait_exponential

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    vipps_payment_id = fields.Char("Vipps Payment ID", copy=False)
    vipps_idempotency_key = fields.Char("Idempotency Key", copy=False)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _vipps_api_request(self, endpoint, payload=None, method='POST'):
        """Handle API requests with retry logic"""
        self.ensure_one()
        url = self.provider_id._get_vipps_api_url() + endpoint
        headers = {
            'Authorization': f'Bearer {self.provider_id.vipps_api_key}',
            'Idempotency-Key': str(uuid.uuid4()),
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.request(
                method, 
                url, 
                json=payload, 
                headers=headers, 
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("Vipps API Error: %s", str(e))
            self._set_error(_("Payment processing failed: %s") % str(e))
            raise

    def _send_payment_request(self):
        if self.provider_code != 'vipps':
            return super()._send_payment_request()
        
        payload = {
            "amount": int(self.amount * 100),
            "currency": self.currency_id.name,
            "reference": self.reference,
            "callbackUrl": self.provider_id._get_vipps_callback_url(),
            "returnUrl": self._get_return_url()
        }
        response = self._vipps_api_request('payments', payload)
        self.write({
            'vipps_payment_id': response['paymentId'],
            'vipps_idempotency_key': headers['Idempotency-Key']
        })
        return {
            'type': 'ir.actions.act_url',
            'url': response['redirectUrl'],
            'target': 'self'
        }

    def _vipps_capture_payment(self):
        self.ensure_one()
        self._vipps_api_request(f'payments/{self.vipps_payment_id}/capture')

    def action_vipps_refund(self):
        self.ensure_one()
        payload = {
            "amount": int(self.amount * 100),
            "description": "Refund from Odoo"
        }
        self._vipps_api_request(f'payments/{self.vipps_payment_id}/refund', payload)
        self._set_refunded()