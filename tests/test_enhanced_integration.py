# -*- coding: utf-8 -*-

import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestEnhancedIntegration(TransactionCase):
    """Enhanced integration tests for production readiness"""

    def setUp(self):
        super().setUp()
        
        # Create test payment provider
        self.provider = self.env['payment.provider'].create({
            'name': 'Vipps Test Enhanced',
            'code': 'vipps',
            'state': 'test',
            'vipps_environment': 'test',
            'vipps_merchant_serial_number': '123456',
            'vipps_client_id': 'test_client_id',
            'vipps_client_secret': 'test_client_secret',
            'vipps_subscription_key': 'test_subscription_key',
            'vipps_webhook_secret': 'test_webhook_secret_123',
        })
        
        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
            'phone': '+4712345678'
        })

    def test_user_friendly_error_messages(self):
        """Test user-friendly error message handling"""
        transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-ERROR-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
        })
        
        # Test different error codes
        error_test_cases = [
            ('INSUFFICIENT_FUNDS', 'Insufficient funds. Please check your account balance.'),
            ('CARD_DECLINED', 'Payment declined. Please try a different payment method.'),
            ('TIMEOUT', 'Payment timed out. Please try again.'),
            ('NETWORK_ERROR', 'Connection issue. Please check your internet and try again.'),
            ('UNKNOWN_ERROR', 'Payment failed. Please try again.'),
        ]
        
        for error_code, expected_message in error_test_cases:
            with self.subTest(error_code=error_code):
                transaction._set_user_friendly_error(error_code, "Technical error details")
                
                # Check that user-friendly message is set
                self.assertEqual(transaction.state, 'error')
                self.assertIn(expected_message, transaction.state_message or '')

    def test_error_code_extraction(self):
        """Test error code extraction from API responses"""
        transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-EXTRACT-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
        })
        
        # Test different error response formats
        test_cases = [
            ({'detail': 'Insufficient funds in account'}, 'INSUFFICIENT_FUNDS'),
            ({'detail': 'Payment was declined by issuer'}, 'CARD_DECLINED'),
            ({'detail': 'Request timeout occurred'}, 'TIMEOUT'),
            ({'detail': 'Invalid phone number format'}, 'INVALID_PHONE_NUMBER'),
            ({'detail': 'Unknown error occurred'}, 'UNKNOWN_ERROR'),
        ]
        
        for error_response, expected_code in test_cases:
            with self.subTest(error_response=error_response):
                actual_code = transaction._extract_error_code_from_response(error_response)
                self.assertEqual(actual_code, expected_code)

    def test_payment_expiry_handling(self):
        """Test payment expiry time setting and cleanup"""
        transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-EXPIRY-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
            'state': 'pending',
        })
        
        # Test setting expiry time
        transaction._set_payment_expiry(minutes=30)
        
        # Check that expiry time is set correctly
        self.assertIsNotNone(transaction.vipps_payment_expires_at)
        expected_expiry = datetime.now() + timedelta(minutes=30)
        actual_expiry = transaction.vipps_payment_expires_at
        
        # Allow 1 minute tolerance for test execution time
        time_diff = abs((actual_expiry - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)

    def test_expired_payment_cleanup(self):
        """Test automatic cleanup of expired payments"""
        # Create expired payment
        expired_transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-EXPIRED-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
            'state': 'pending',
            'vipps_payment_expires_at': datetime.now() - timedelta(hours=1),  # Expired 1 hour ago
        })
        
        # Create non-expired payment
        active_transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-ACTIVE-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
            'state': 'pending',
            'vipps_payment_expires_at': datetime.now() + timedelta(hours=1),  # Expires in 1 hour
        })
        
        # Run cleanup
        cancelled_count = self.env['payment.transaction']._cancel_expired_payments()
        
        # Check results
        self.assertEqual(cancelled_count, 1)
        
        # Refresh records
        expired_transaction.invalidate_cache()
        active_transaction.invalidate_cache()
        
        # Check states
        self.assertEqual(expired_transaction.state, 'error')
        self.assertEqual(active_transaction.state, 'pending')

    def test_enhanced_retry_logic(self):
        """Test enhanced retry logic with exponential backoff"""
        from ..models.vipps_api_client import VippsAPIClient
        
        api_client = VippsAPIClient(self.provider)
        
        # Mock requests to simulate retryable errors
        with patch('requests.get') as mock_get:
            # First two calls return 503 (retryable), third succeeds
            mock_get.side_effect = [
                MagicMock(status_code=503),  # Service Unavailable
                MagicMock(status_code=503),  # Service Unavailable
                MagicMock(status_code=200, json=lambda: {'result': 'success'})  # Success
            ]
            
            with patch.object(api_client, '_get_access_token', return_value='test_token'):
                with patch('time.sleep'):  # Mock sleep to speed up test
                    result = api_client._make_request('GET', 'test-endpoint')
                    
                    # Should succeed after retries
                    self.assertEqual(result['result'], 'success')
                    self.assertEqual(mock_get.call_count, 3)

    def test_retryable_error_detection(self):
        """Test detection of retryable vs non-retryable errors"""
        from ..models.vipps_api_client import VippsAPIClient
        
        api_client = VippsAPIClient(self.provider)
        
        # Test retryable status codes
        retryable_codes = [408, 429, 500, 502, 503, 504]
        for code in retryable_codes:
            with self.subTest(status_code=code):
                self.assertTrue(api_client._is_retryable_error(code))
        
        # Test non-retryable status codes
        non_retryable_codes = [400, 401, 403, 404, 409]
        for code in non_retryable_codes:
            with self.subTest(status_code=code):
                self.assertFalse(api_client._is_retryable_error(code))

    def test_complete_ecommerce_flow_with_errors(self):
        """Test complete eCommerce flow with error handling"""
        transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-FLOW-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
        })
        
        # Test payment creation with API error
        with patch.object(transaction, '_get_vipps_api_client') as mock_client:
            mock_api_instance = MagicMock()
            mock_client.return_value = mock_api_instance
            
            # Simulate API error
            from ..models.vipps_api_client import VippsAPIException
            mock_api_instance._make_request.side_effect = VippsAPIException(
                "Insufficient funds", 
                error_code="INSUFFICIENT_FUNDS"
            )
            
            # Should raise user-friendly error
            with self.assertRaises(UserError) as context:
                transaction._send_payment_request()
            
            # Check user-friendly message
            self.assertIn("Insufficient funds", str(context.exception))
            self.assertEqual(transaction.state, 'error')

    def test_webhook_processing_with_enhanced_security(self):
        """Test webhook processing with enhanced security features"""
        transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-WEBHOOK-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
            'vipps_payment_reference': 'vipps-test-001',
        })
        
        # Test webhook with proper event structure
        webhook_data = {
            'name': 'epayments.payment.authorized.v1',
            'eventId': str(uuid.uuid4()),
            'reference': transaction.vipps_payment_reference,
            'pspReference': 'psp-123',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Process webhook
        transaction._process_notification_data(webhook_data)
        
        # Check state transition
        self.assertEqual(transaction.vipps_payment_state, 'AUTHORIZED')
        self.assertEqual(transaction.state, 'authorized')
        
        # Test duplicate prevention
        initial_state = transaction.vipps_payment_state
        transaction._process_notification_data(webhook_data)  # Same webhook again
        
        # State should not change (duplicate prevented)
        self.assertEqual(transaction.vipps_payment_state, initial_state)

    def test_cron_job_functionality(self):
        """Test cron job methods work correctly"""
        # Test expired payment cleanup
        cancelled_count = self.env['payment.transaction']._cancel_expired_payments()
        self.assertIsInstance(cancelled_count, int)
        self.assertGreaterEqual(cancelled_count, 0)

    def test_production_readiness_indicators(self):
        """Test production readiness indicators"""
        transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'reference': 'TEST-PROD-001',
            'amount': 100.00,
            'currency_id': self.env.ref('base.NOK').id,
            'partner_id': self.partner.id,
        })
        
        # Test that all enhanced methods exist
        required_methods = [
            '_set_user_friendly_error',
            '_extract_error_code_from_response',
            '_set_payment_expiry',
            '_cancel_expired_payments',
        ]
        
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(hasattr(transaction, method_name))
                method = getattr(transaction, method_name)
                self.assertTrue(callable(method))

    def test_error_message_constants(self):
        """Test that error message constants are properly defined"""
        from ..models.payment_transaction import VIPPS_ERROR_MESSAGES
        
        # Check that all expected error codes have messages
        expected_codes = [
            'INSUFFICIENT_FUNDS',
            'CARD_DECLINED',
            'TIMEOUT',
            'NETWORK_ERROR',
            'CANCELLED_BY_USER',
            'INVALID_AMOUNT',
            'PAYMENT_LIMIT_EXCEEDED',
        ]
        
        for code in expected_codes:
            with self.subTest(error_code=code):
                self.assertIn(code, VIPPS_ERROR_MESSAGES)
                self.assertIsInstance(VIPPS_ERROR_MESSAGES[code], str)
                self.assertGreater(len(VIPPS_ERROR_MESSAGES[code]), 10)  # Reasonable message length