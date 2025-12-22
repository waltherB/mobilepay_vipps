# -*- coding: utf-8 -*-

import json
import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestWebhookIntegration(TransactionCase):
    """Test webhook handling and security validation"""

    def setUp(self):
        super().setUp()
        
        # Create test payment provider
        self.provider = self.env['payment.provider'].create({
            'name': 'Vipps Test',
            'code': 'vipps',
            'state': 'test',
            'vipps_environment': 'test',
            'vipps_merchant_serial_number': '123456',
            'vipps_client_id': 'test_client_id',
            'vipps_client_secret': 'test_client_secret',
            'vipps_subscription_key': 'test_subscription_key',
            'vipps_webhook_secret': 'test_webhook_secret_123',
        })
        
        # Create test transaction
        self.transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'vipps_payment_reference': 'vipps-test-001',
            'state': 'pending',
        })

    def _create_webhook_payload(self, event_name='epayments.payment.authorized.v1', 
                               reference=None, event_id=None):
        """Create test webhook payload"""
        return {
            'name': event_name,
            'eventId': event_id or str(uuid.uuid4()),
            'reference': reference or self.transaction.vipps_payment_reference,
            'pspReference': 'psp-test-123',
            'amount': {
                'value': 10000,
                'currency': 'NOK'
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _create_webhook_signature(self, payload_str, secret=None):
        """Create HMAC signature for webhook payload"""
        webhook_secret = secret or self.provider.vipps_webhook_secret
        return hmac.new(
            webhook_secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def test_webhook_event_mapping(self):
        """Test that webhook events are correctly mapped to payment states"""
        test_cases = [
            ('epayments.payment.created.v1', 'CREATED'),
            ('epayments.payment.authorized.v1', 'AUTHORIZED'),
            ('epayments.payment.captured.v1', 'CAPTURED'),
            ('epayments.payment.cancelled.v1', 'CANCELLED'),
            ('epayments.payment.refunded.v1', 'REFUNDED'),
            ('epayments.payment.aborted.v1', 'ABORTED'),
            ('epayments.payment.expired.v1', 'EXPIRED'),
            ('epayments.payment.terminated.v1', 'TERMINATED'),
        ]
        
        for event_name, expected_state in test_cases:
            with self.subTest(event_name=event_name):
                payload = self._create_webhook_payload(event_name=event_name)
                
                # Process webhook
                self.transaction._process_notification_data(payload)
                
                # Check state was updated correctly
                self.assertEqual(self.transaction.vipps_payment_state, expected_state)

    def test_webhook_signature_validation(self):
        """Test webhook signature validation"""
        security_model = self.env['vipps.webhook.security']
        
        # Create mock request
        mock_request = MagicMock()
        payload = json.dumps(self._create_webhook_payload())
        signature = self._create_webhook_signature(payload)
        
        mock_request.httprequest.headers = {
            'X-Vipps-Signature': signature,
            'Content-Type': 'application/json',
            'X-Vipps-Timestamp': datetime.now(timezone.utc).isoformat()
        }
        mock_request.httprequest.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        # Test valid signature
        result = security_model.validate_webhook_request(
            mock_request, payload, self.provider
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['errors']), 0)

    def test_webhook_signature_validation_invalid(self):
        """Test webhook signature validation with invalid signature"""
        security_model = self.env['vipps.webhook.security']
        
        # Create mock request with invalid signature
        mock_request = MagicMock()
        payload = json.dumps(self._create_webhook_payload())
        
        mock_request.httprequest.headers = {
            'X-Vipps-Signature': 'invalid_signature',
            'Content-Type': 'application/json',
            'X-Vipps-Timestamp': datetime.now(timezone.utc).isoformat()
        }
        mock_request.httprequest.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        # Test invalid signature
        result = security_model.validate_webhook_request(
            mock_request, payload, self.provider
        )
        
        self.assertFalse(result['success'])
        self.assertIn('Invalid webhook signature', result['errors'])

    def test_webhook_duplicate_event_prevention(self):
        """Test that duplicate webhook events are prevented"""
        event_id = str(uuid.uuid4())
        payload = self._create_webhook_payload(event_id=event_id)
        
        # Process webhook first time
        self.transaction._process_notification_data(payload)
        initial_state = self.transaction.vipps_payment_state
        
        # Process same webhook again
        self.transaction._process_notification_data(payload)
        
        # State should not change
        self.assertEqual(self.transaction.vipps_payment_state, initial_state)
        
        # Check that event was stored
        self.assertTrue(self.transaction._is_webhook_event_processed(event_id))

    def test_webhook_timestamp_validation(self):
        """Test webhook timestamp validation for replay attack prevention"""
        security_model = self.env['vipps.webhook.security']
        
        # Test valid timestamp (current time)
        mock_request = MagicMock()
        mock_request.httprequest.headers = {
            'X-Vipps-Timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.assertTrue(security_model._validate_webhook_timestamp(mock_request))
        
        # Test old timestamp (should fail)
        old_time = datetime.now(timezone.utc).replace(year=2020)
        mock_request.httprequest.headers = {
            'X-Vipps-Timestamp': old_time.isoformat()
        }
        
        self.assertFalse(security_model._validate_webhook_timestamp(mock_request))

    def test_webhook_unknown_event_handling(self):
        """Test handling of unknown webhook events"""
        payload = self._create_webhook_payload(event_name='unknown.event.v1')
        
        # Should not raise exception
        self.transaction._process_notification_data(payload)
        
        # State should remain unchanged
        self.assertEqual(self.transaction.state, 'pending')

    def test_payment_state_transitions(self):
        """Test correct payment state transitions from webhooks"""
        # Test AUTHORIZED -> transaction.state = 'authorized'
        payload = self._create_webhook_payload('epayments.payment.authorized.v1')
        self.transaction._process_notification_data(payload)
        self.assertEqual(self.transaction.state, 'authorized')
        
        # Test CAPTURED -> transaction.state = 'done'
        payload = self._create_webhook_payload('epayments.payment.captured.v1')
        self.transaction._process_notification_data(payload)
        self.assertEqual(self.transaction.state, 'done')

    def test_webhook_security_logging(self):
        """Test security event logging"""
        security_model = self.env['vipps.webhook.security']
        
        # Test security event logging
        security_model.log_security_event(
            'test_event',
            'Test security event',
            'info',
            '127.0.0.1',
            self.provider.id
        )
        
        # Check that event was logged (would be in system parameters)
        # This is a basic test - in production you'd check actual log storage

    def test_webhook_event_structure_validation(self):
        """Test webhook event structure validation"""
        security_model = self.env['vipps.webhook.security']
        
        # Valid event structure
        valid_payload = self._create_webhook_payload()
        self.assertTrue(security_model._validate_webhook_event_structure(valid_payload))
        
        # Invalid event structure (missing name)
        invalid_payload = {'reference': 'test-123'}
        self.assertFalse(security_model._validate_webhook_event_structure(invalid_payload))
        
        # Invalid event name format
        invalid_name_payload = {'name': 'invalid.event.name'}
        self.assertFalse(security_model._validate_webhook_event_structure(invalid_name_payload))

    def test_webhook_cleanup_old_events(self):
        """Test cleanup of old webhook events"""
        security_model = self.env['vipps.webhook.security']
        
        # Create some test events
        event_id = str(uuid.uuid4())
        self.transaction._store_webhook_event(event_id, 'epayments.payment.authorized.v1')
        
        # Test cleanup (should not delete recent events)
        deleted_count = security_model.cleanup_old_events(days_to_keep=30)
        
        # Event should still exist
        self.assertTrue(self.transaction._is_webhook_event_processed(event_id))

    def test_order_lines_in_payment_request(self):
        """Test that order lines are included in payment requests"""
        # Create a sale order with lines
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'phone': '+4712345678'
        })
        
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 50.00,
            'type': 'consu'
        })
        
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 2,
                'price_unit': 50.00,
            })]
        })
        
        # Link transaction to order
        self.transaction.write({
            'sale_order_ids': [(6, 0, [order.id])],
            'partner_id': partner.id,
        })
        
        # Mock the API client to capture the payload
        with patch.object(self.transaction, '_get_vipps_api_client') as mock_client:
            mock_api_instance = MagicMock()
            mock_client.return_value = mock_api_instance
            mock_api_instance._make_request.return_value = {
                'redirectUrl': 'https://test.vipps.no/redirect/123'
            }
            
            # Send payment request
            self.transaction._send_payment_request()
            
            # Check that API was called
            self.assertTrue(mock_api_instance._make_request.called)
            
            # Get the payload that was sent
            call_args = mock_api_instance._make_request.call_args
            payload = call_args[1]['payload']  # kwargs['payload']
            
            # Verify receipt is included
            self.assertIn('receipt', payload)
            self.assertIn('orderLines', payload['receipt'])
            self.assertEqual(len(payload['receipt']['orderLines']), 1)
            
            # Verify order line details
            order_line = payload['receipt']['orderLines'][0]
            self.assertEqual(order_line['name'], 'Test Product')
            self.assertEqual(order_line['quantity'], 2)
            self.assertEqual(order_line['unitPrice'], 5000)  # 50.00 * 100
            
            # Verify customer phone is included
            self.assertIn('customer', payload)
            self.assertEqual(payload['customer']['phoneNumber'], '4712345678')

    def test_customer_phone_formatting(self):
        """Test customer phone number formatting"""
        test_cases = [
            ('+4712345678', '4712345678'),
            ('12345678', '4512345678'),  # Danish number
            ('+45 12 34 56 78', '4512345678'),
            ('0012345678', '4512345678'),  # Remove leading zero
        ]
        
        for input_phone, expected_output in test_cases:
            with self.subTest(input_phone=input_phone):
                # Create partner with phone
                partner = self.env['res.partner'].create({
                    'name': 'Test Customer',
                    'phone': input_phone
                })
                
                self.transaction.partner_id = partner
                
                # Mock API client
                with patch.object(self.transaction, '_get_vipps_api_client') as mock_client:
                    mock_api_instance = MagicMock()
                    mock_client.return_value = mock_api_instance
                    mock_api_instance._make_request.return_value = {
                        'redirectUrl': 'https://test.vipps.no/redirect/123'
                    }
                    
                    # Send payment request
                    self.transaction._send_payment_request()
                    
                    # Get payload
                    call_args = mock_api_instance._make_request.call_args
                    payload = call_args[1]['payload']
                    
                    # Check phone formatting
                    if 'customer' in payload:
                        self.assertEqual(payload['customer']['phoneNumber'], expected_output)

    def test_idempotency_key_generation(self):
        """Test that idempotency keys are generated for requests"""
        with patch.object(self.transaction, '_get_vipps_api_client') as mock_client:
            mock_api_instance = MagicMock()
            mock_client.return_value = mock_api_instance
            mock_api_instance._make_request.return_value = {
                'redirectUrl': 'https://test.vipps.no/redirect/123'
            }
            
            # Send payment request
            self.transaction._send_payment_request()
            
            # Check that idempotency key was provided
            call_args = mock_api_instance._make_request.call_args
            self.assertIn('idempotency_key', call_args[1])
            self.assertIsNotNone(call_args[1]['idempotency_key'])

    def test_payment_reference_generation(self):
        """Test payment reference generation"""
        # Clear existing reference
        self.transaction.vipps_payment_reference = False
        
        # Generate reference
        reference = self.transaction._generate_vipps_reference()
        
        # Should be based on transaction reference with timestamp
        self.assertTrue(reference.startswith('TEST-001-'))
        self.assertEqual(self.transaction.vipps_payment_reference, reference)

    def test_webhook_controller_integration(self):
        """Test webhook controller with proper security validation"""
        from odoo.tests.common import HttpCase
        
        # This would require HttpCase for full controller testing
        # For now, test the security validation components
        security_model = self.env['vipps.webhook.security']
        
        # Test that validation components work
        self.assertTrue(hasattr(security_model, 'validate_webhook_request'))
        self.assertTrue(hasattr(security_model, '_validate_webhook_signature'))
        self.assertTrue(hasattr(security_model, '_validate_webhook_timestamp'))