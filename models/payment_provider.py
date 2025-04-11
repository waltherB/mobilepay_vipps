from odoo import models, fields, api

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('vipps', 'MobilePay by Vipps')],
        ondelete={'vipps': 'set default'}
    )
    vipps_api_key = fields.Char("API Key", required_if_provider='vipps', groups='base.group_system')
    vipps_merchant_serial = fields.Char("Merchant Serial", required_if_provider='vipps')
    vipps_webhook_secret = fields.Char("Webhook Secret", groups='base.group_system')
    vipps_capture_automatically = fields.Boolean(
        "Capture on Delivery",
        help="Automatically capture payments when delivery is confirmed"
    )

    def _get_vipps_api_url(self):
        return "https://api.vipps.no/epayment/v1/"
    
    def _get_vipps_callback_url(self):
        return self.get_base_url() + "/vipps/webhook"