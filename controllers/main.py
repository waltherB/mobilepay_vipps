# -*- coding: utf-8 -*-

import json
import logging
import time
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class VippsController(http.Controller):
    """Controller for handling Vipps/MobilePay webhooks and redirects"""

    def _validate_webhook_ip(self, request_ip):
        """Validate webhook source IP against Vipps IP ranges"""
        # Vipps webhook IP ranges (these should be configurable in production)
        vipps_ip_ranges = [
            '213.52.3.0/24',    # Vipps production IPs
            '213.52.4.0/24',    # Vipps production IPs  
            '127.0.0.1',        # Localhost for testing
            '::1'               # IPv6 localhost
        ]
        
        try:
            import ipaddress
            request_addr = ipaddress.ip_address(request_ip)
            
            for ip_range in vipps_ip_ranges:
                try:
                    if '/' in ip_range:
                        network = ipaddress.ip_network(ip_range, strict=False)
                        if request_addr in network:
                            return True
                    else:
                        allowed_addr = ipaddress.ip_address(ip_range)
                        if request_addr == allowed_addr:
                            return True
                except ValueError:
                    continue
                    
            return False
            
        except (ValueError, ImportError):
            # If IP validation fails, log warning but allow (fail open)
            _logger.warning("Could not validate webhook IP: %s", request_ip)
            return True

    def _check_rate_limit(self, identifier, max_requests=100, window_seconds=300):
        """Simple rate limiting for webhook endpoints"""
        try:
            import time
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Use Odoo's cache or implement simple in-memory rate limiting
            # This is a basic implementation - in production, use Redis or similar
            cache_key = f"webhook_rate_limit_{identifier}"
            
            # For now, just log and allow (implement proper rate limiting in production)
            _logger.debug("Rate limit check for %s (allowing for now)", identifier)
            return True
            
        except Exception:
            # If rate limiting fails, allow the request (fail open)
            return True

    def _log_security_event(self, event_type, details, severity='info'):
        """Log security events for audit and monitoring"""
        try:
            log_message = f"VIPPS_SECURITY_{event_type.upper()}: {details}"
            
            if severity == 'warning':
                _logger.warning(log_message)
            elif severity == 'error':
                _logger.error(log_message)
            else:
                _logger.info(log_message)
                
            # In production, you might want to send these to a SIEM system
            # or create database records for security audit trails
            
        except Exception as e:
            _logger.error("Failed to log security event: %s", str(e))

    @http.route('/payment/vipps/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def vipps_webhook(self, **kwargs):
        """Handle incoming webhooks from Vipps/MobilePay with enhanced security"""
        webhook_id = None
        reference = None
        client_ip = 'unknown'
        
        try:
            # Get request data
            payload = request.httprequest.get_data(as_text=True)
            
            # Find the payment provider first
            provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'vipps'),
                ('state', '!=', 'disabled')
            ], limit=1)
            
            if not provider:
                _logger.error("No active Vipps provider found for webhook")
                return request.make_response('Not Found: Provider not configured', status=404)
            
            # Perform comprehensive security validation
            validation_result = provider.validate_webhook_request_comprehensive(request, payload)
            
            # Extract client IP for logging
            client_ip = validation_result.get('client_ip', 'unknown')
            
            # Log webhook reception
            _logger.info("Received Vipps webhook from %s", client_ip)
            
            # Check validation result
            if not validation_result['success']:
                # Log all errors
                for error in validation_result['errors']:
                    _logger.error("Webhook validation failed: %s", error)
                
                # Return appropriate error response
                if any('rate limit' in error.lower() for error in validation_result['errors']):
                    return request.make_response('Too Many Requests', status=429)
                elif any('signature' in error.lower() for error in validation_result['errors']):
                    return request.make_response('Unauthorized: Invalid signature', status=401)
                elif any('unauthorized ip' in error.lower() for error in validation_result['errors']):
                    return request.make_response('Forbidden: Unauthorized IP', status=403)
                elif any('replay' in error.lower() for error in validation_result['errors']):
                    return request.make_response('Conflict: Duplicate request', status=409)
                else:
                    return request.make_response('Bad Request: Validation failed', status=400)
            
            # Log warnings if any
            for warning in validation_result.get('warnings', []):
                _logger.warning("Webhook validation warning: %s", warning)
            
            # Extract validated data
            webhook_data = validation_result.get('webhook_data')
            if not webhook_data:
                _logger.error("No webhook data in validation result")
                return request.make_response('Bad Request: Invalid webhook data', status=400)
                
            reference = webhook_data.get('reference')
            webhook_id = webhook_data.get('eventId') or validation_result.get('headers', {}).get('vipps_idempotency_key')
            
            # Find transaction
            transaction = request.env['payment.transaction'].sudo().search([
                ('vipps_payment_reference', '=', reference)
            ], limit=1)
            
            if not transaction:
                _logger.warning("No transaction found for webhook reference %s", reference)
                return request.make_response('Not Found: Transaction not found', status=404)
            
            # Process webhook using Odoo 17's notification system
            try:
                transaction._process_notification_data(webhook_data)
                
                # Log successful processing
                if webhook_id:
                    _logger.info("Processed webhook %s for reference %s successfully", 
                               webhook_id, reference)
                
                # Log security event for successful processing
                if provider.vipps_webhook_security_logging:
                    request.env['vipps.webhook.security'].log_security_event(
                        'webhook_processed',
                        f"Successfully processed webhook for reference {reference}, "
                        f"state: {webhook_data.get('state')}",
                        'info',
                        client_ip=client_ip,
                        provider_id=provider.id,
                        additional_data={
                            'reference': reference,
                            'webhook_id': webhook_id,
                            'state': webhook_data.get('state')
                        }
                    )
                
                return request.make_response('OK', status=200)
                
            except Exception as processing_error:
                _logger.error("Error processing webhook for reference %s: %s", 
                            reference, str(processing_error))
                
                # Log processing failure
                if provider.vipps_webhook_security_logging:
                    request.env['vipps.webhook.security'].log_security_event(
                        'validation_failed',
                        f"Webhook processing failed for reference {reference}: {str(processing_error)}",
                        'high',
                        client_ip=client_ip,
                        provider_id=provider.id,
                        additional_data={
                            'reference': reference,
                            'error': str(processing_error)
                        }
                    )
                
                # Return 500 to trigger Vipps retry mechanism
                return request.make_response('Internal Server Error: Processing failed', status=500)
            
        except Exception as e:
            _logger.error("Critical error processing Vipps webhook (ID: %s, Ref: %s): %s", 
                        webhook_id, reference, str(e))
            
            # Log critical error
            try:
                provider = request.env['payment.provider'].sudo().search([
                    ('code', '=', 'vipps'),
                    ('state', '!=', 'disabled')
                ], limit=1)
                
                if provider and provider.vipps_webhook_security_logging:
                    request.env['vipps.webhook.security'].log_security_event(
                        'validation_failed',
                        f"Critical webhook error: {str(e)}",
                        'critical',
                        client_ip=client_ip,
                        provider_id=provider.id,
                        additional_data={
                            'webhook_id': webhook_id,
                            'reference': reference,
                            'error': str(e)
                        }
                    )
            except:
                pass  # Don't fail on logging errors
            
            return request.make_response('Internal Server Error', status=500)

    @http.route('/payment/vipps/return', type='http', auth='public', methods=['GET'], csrf=False)
    def vipps_return(self, **kwargs):
        """Handle customer return from Vipps/MobilePay payment flow"""
        reference = kwargs.get('reference')
        
        try:
            # Log return for audit
            _logger.info("Customer return from Vipps for reference: %s", reference)
            
            # Validate reference
            if not reference:
                _logger.error("No reference provided in return URL")
                return request.redirect('/shop/payment?message=missing_reference')
            
            # Find transaction by Vipps reference or fallback to transaction reference
            transaction = request.env['payment.transaction'].sudo().search([
                ('vipps_payment_reference', '=', reference)
            ], limit=1)
            
            if not transaction:
                # Try to find by transaction reference as fallback
                transaction = request.env['payment.transaction'].sudo().search([
                    ('reference', '=', reference)
                ], limit=1)
            
            if not transaction:
                _logger.error("No transaction found for return reference %s", reference)
                return request.redirect('/shop/payment?message=transaction_not_found')
            
            # Handle return processing and order confirmation
            try:
                payment_state = transaction._handle_return_from_vipps()
                _logger.info("Processed return for reference %s, final state: %s", 
                           reference, payment_state)
            except Exception as return_error:
                _logger.error("Error processing return for reference %s: %s", 
                            reference, str(return_error))
                # Continue with existing state for graceful degradation
                payment_state = transaction.vipps_payment_state
            
            # Determine redirect based on final transaction state
            if transaction.state == 'done':
                _logger.info("Payment completed successfully for reference %s", reference)
                # Redirect to order confirmation or success page
                if hasattr(transaction, 'sale_order_ids') and transaction.sale_order_ids:
                    order = transaction.sale_order_ids[0]
                    return request.redirect(f'/shop/confirmation?order_id={order.id}')
                else:
                    return request.redirect(f'/payment/status/{transaction.id}?success=1')
                
            elif transaction.state == 'authorized':
                _logger.info("Payment authorized for reference %s", reference)
                # For manual capture mode, this is success - redirect to confirmation
                if hasattr(transaction, 'sale_order_ids') and transaction.sale_order_ids:
                    order = transaction.sale_order_ids[0]
                    return request.redirect(f'/shop/confirmation?order_id={order.id}')
                else:
                    return request.redirect(f'/payment/status/{transaction.id}?success=1')
                
            elif transaction.state in ['cancel', 'error']:
                _logger.info("Payment cancelled/failed for reference %s", reference)
                error_msg = transaction.state_message or 'Payment was cancelled or failed'
                return request.redirect(f'/shop/payment?message=payment_failed&error={error_msg}')
                
            elif transaction.state == 'pending':
                _logger.info("Payment still pending for reference %s", reference)
                return request.redirect(f'/payment/status/{transaction.id}?pending=1')
                
            else:
                _logger.warning("Unknown payment state %s for reference %s", 
                              transaction.state, reference)
                return request.redirect('/shop/payment?message=payment_unknown')
                
        except Exception as e:
            _logger.error("Error processing Vipps return for reference %s: %s", 
                        reference, str(e))
            return request.redirect('/shop/payment?message=payment_error')

    @http.route('/payment/vipps/status/<string:reference>', type='json', auth='public')
    def vipps_payment_status(self, reference, **kwargs):
        """AJAX endpoint for checking payment status (for POS polling)"""
        try:
            # Validate reference
            if not reference:
                return {'error': 'Missing payment reference', 'code': 'MISSING_REFERENCE'}
            
            # Find transaction
            transaction = request.env['payment.transaction'].sudo().search([
                ('vipps_payment_reference', '=', reference)
            ], limit=1)
            
            if not transaction:
                _logger.warning("Transaction not found for status check: %s", reference)
                return {'error': 'Transaction not found', 'code': 'TRANSACTION_NOT_FOUND'}
            
            # Check current status from Vipps API
            try:
                transaction._get_payment_status()
            except Exception as status_error:
                _logger.error("Failed to get payment status for %s: %s", reference, str(status_error))
                return {
                    'error': 'Failed to check payment status',
                    'code': 'STATUS_CHECK_FAILED',
                    'details': str(status_error)
                }
            
            # Return current status
            response = {
                'success': True,
                'state': transaction.state,
                'vipps_payment_state': transaction.vipps_payment_state,
                'reference': reference,
                'amount': float(transaction.amount) if transaction.amount else 0,
                'currency': transaction.currency_id.name if transaction.currency_id else None,
            }
            
            # Add additional info for completed payments
            if transaction.state in ['done', 'authorized']:
                response.update({
                    'completed_at': transaction.write_date.isoformat() if transaction.write_date else None,
                    'provider_reference': transaction.provider_reference,
                })
            
            # Add error info for failed payments
            elif transaction.state in ['cancel', 'error']:
                response.update({
                    'error_message': transaction.state_message or 'Payment was cancelled or failed',
                    'failed_at': transaction.write_date.isoformat() if transaction.write_date else None,
                })
            
            return response
            
        except Exception as e:
            _logger.error("Critical error checking Vipps payment status for %s: %s", 
                        reference, str(e))
            return {
                'error': 'Internal server error',
                'code': 'INTERNAL_ERROR',
                'details': str(e)
            }

    @http.route('/payment/vipps/webhook/test', type='http', auth='user', methods=['POST'], csrf=False)
    def vipps_webhook_test(self, **kwargs):
        """Test endpoint for webhook configuration validation"""
        try:
            # Check if user has admin rights
            if not request.env.user.has_group('base.group_system'):
                return request.make_response('Forbidden: Admin access required', status=403)
            
            # Get test payload
            payload = request.httprequest.get_data(as_text=True)
            if not payload:
                payload = json.dumps({
                    'eventId': 'test-webhook-' + str(int(time.time())),
                    'reference': 'test-reference-123',
                    'state': 'AUTHORIZED',
                    'amount': {'value': 10000, 'currency': 'NOK'},
                    'pspReference': 'test-psp-ref-123'
                })
            
            # Find Vipps provider
            provider = request.env['payment.provider'].search([
                ('code', '=', 'vipps'),
                ('state', '!=', 'disabled')
            ], limit=1)
            
            if not provider:
                return request.make_response('No Vipps provider configured', status=404)
            
            # Test webhook processing without signature validation
            try:
                webhook_data = json.loads(payload)
                
                response_data = {
                    'success': True,
                    'message': 'Webhook endpoint is accessible and can process JSON',
                    'webhook_url': provider._get_vipps_webhook_url(),
                    'provider_name': provider.name,
                    'environment': provider.vipps_environment,
                    'webhook_configured': bool(provider.vipps_webhook_secret),
                    'received_data': webhook_data
                }
                
                return request.make_response(
                    json.dumps(response_data, indent=2),
                    headers={'Content-Type': 'application/json'}
                )
                
            except json.JSONDecodeError:
                return request.make_response('Invalid JSON payload', status=400)
            
        except Exception as e:
            _logger.error("Error in webhook test endpoint: %s", str(e))
            return request.make_response(f'Test failed: {str(e)}', status=500)

    @http.route('/pos/vipps/get_payment_config', type='json', auth='user', methods=['POST'])
    def pos_get_payment_config(self, **kwargs):
        """Get POS payment method configuration"""
        try:
            # Get Vipps payment method
            payment_method = request.env['pos.payment.method'].search([
                ('use_payment_terminal', '=', 'vipps')
            ], limit=1)
            
            if not payment_method:
                return {'error': 'No Vipps payment method found'}
            
            return {
                'payment_method': {
                    'id': payment_method.id,
                    'name': payment_method.name,
                    'vipps_enable_qr_flow': payment_method.vipps_enable_qr_flow,
                    'vipps_enable_phone_flow': payment_method.vipps_enable_phone_flow,
                    'vipps_enable_manual_flows': payment_method.vipps_enable_manual_flows,
                    'vipps_payment_timeout': payment_method.vipps_payment_timeout,
                    'vipps_polling_interval': payment_method.vipps_polling_interval,
                },
                'timeout': payment_method.vipps_payment_timeout,
                'polling_interval': payment_method.vipps_polling_interval,
            }
            
        except Exception as e:
            _logger.error("Failed to get POS payment config: %s", str(e))
            return {'error': str(e)}

    @http.route('/pos/vipps/create_payment', type='json', auth='user', methods=['POST'])
    def pos_create_payment(self, payment_data, **kwargs):
        """Create POS payment transaction"""
        try:
            result = request.env['payment.transaction'].sudo().create_pos_payment(payment_data)
            return result
            
        except Exception as e:
            _logger.error("POS payment creation failed: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/pos/vipps/poll_status', type='json', auth='user', methods=['POST'])
    def pos_poll_status(self, transaction_id, **kwargs):
        """Poll payment status for POS transaction"""
        try:
            result = request.env['payment.transaction'].sudo().poll_pos_payment_status(transaction_id)
            return result
            
        except Exception as e:
            _logger.error("Status polling failed: %s", str(e))
            return {'status': 'error', 'error': str(e)}

    @http.route('/pos/vipps/cancel_payment', type='json', auth='user', methods=['POST'])
    def pos_cancel_payment(self, transaction_id, **kwargs):
        """Cancel POS payment transaction"""
        try:
            result = request.env['payment.transaction'].sudo().cancel_pos_payment(transaction_id)
            return result
            
        except Exception as e:
            _logger.error("Payment cancellation failed: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/pos/vipps/verify_manual_payment', type='json', auth='user', methods=['POST'])
    def pos_verify_manual_payment(self, transaction_id, **kwargs):
        """Verify manual payment completion"""
        try:
            transaction = request.env['payment.transaction'].sudo().browse(transaction_id)
            if not transaction.exists():
                return {'success': False, 'error': 'Transaction not found'}
            
            # For manual payments, we need to verify with the API
            result = transaction._verify_manual_payment_completion()
            
            return {
                'success': True,
                'status': result.get('status', 'unknown'),
                'verified': result.get('verified', False)
            }
            
        except Exception as e:
            _logger.error("Manual payment verification failed: %s", str(e))
            return {'success': False, 'error': str(e)}