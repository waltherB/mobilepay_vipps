import hmac
import hashlib
import json
from odoo import http
from odoo.http import request

class VippsController(http.Controller):

    @http.route('/vipps/webhook', type='json', auth='public', csrf=False)
    def vipps_webhook(self):
        data = json.loads(request.httprequest.data)
        signature = request.httprequest.headers.get('Vipps-Signature')
        provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'vipps')], limit=1)

        # HMAC Verification
        computed_signature = hmac.new(
            provider.vipps_webhook_secret.encode(),
            request.httprequest.data,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, computed_signature):
            raise http.Forbidden()
        
        tx = request.env['payment.transaction'].sudo().search([
            ('vipps_payment_id', '=', data['paymentId'])
        ])
        
        status_handlers = {
            'AUTHORIZED': tx._set_authorized,
            'CAPTURED': tx._set_done,
            'CANCELLED': tx._set_canceled,
            'FAILED': tx._set_error
        }
        
        if data['status'] in status_handlers:
            status_handlers[data['status']](data.get('message', ''))
        
        return {'status': 'OK'}

    @http.route('/vipps/return', type='http', auth='public')
    def vipps_return(self, **kwargs):
        tx = request.env['payment.transaction'].sudo()._get_tx_from_transaction(kwargs.get('reference'))
        return request.redirect('/payment/status')