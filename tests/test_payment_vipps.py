from odoo.tests import tagged
from odoo.tests.common import HttpCase

@tagged('post_install', '-at_install')
class TestVippsPayment(HttpCase):

    def test_payment_flow(self):
        provider = self.env['payment.provider'].create({
            'name': 'Vipps Test',
            'code': 'vipps',
            'state': 'test',
            'vipps_api_key': 'test_key',
            'vipps_merchant_serial': 'test_serial'
        })
        
        tx = self.env['payment.transaction'].create({
            'provider_id': provider.id,
            'amount': 100,
            'currency_id': self.env.ref('base.EUR').id,
            'reference': 'test_ref_1'
        })
        
        # Test payment request
        tx._send_payment_request()
        self.assertNotEqual(tx.vipps_payment_id, False)
        
        # Test webhook handling
        self.url_open('/vipps/webhook', data=json.dumps({
            'paymentId': tx.vipps_payment_id,
            'status': 'AUTHORIZED'
        }))
        self.assertEqual(tx.state, 'authorized')