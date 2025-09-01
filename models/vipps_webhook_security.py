# -*- coding: utf-8 -*-

import hashlib
import hmac
import ipaddress
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)


class VippsWebhookSecurity(models.AbstractModel):
    """Enhanced webhook security manager for Vipps/MobilePay"""
    _name = 'vipps.webhook.security'
    _description = 'Vipps Webhook Security Manager'

    @api.model
    def validate_webhook_request(self, request, payload, provider):
        """
        Comprehensive webhook request validation
        
        Args:
            request: HTTP request object
            payload: Raw webhook payload
            provider: Payment provider record
            
        Returns:
            dict: Validation result with success status and details
        """
        validation_result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'security_events': []
        }
        
        try:
            # 1. Extract request information
            client_ip = self._get_client_ip(request)
            headers = self._extract_headers(request)
            
            # 2. Validate source IP
            ip_validation = self._validate_source_ip(client_ip, provider)
            if not ip_validation['valid']:
                validation_result['errors'].append(ip_validation['error'])
                validation_result['security_events'].append({
                    'type': 'unauthorized_ip',
                    'severity': 'high',
                    'details': f"Webhook from unauthorized IP: {client_ip}",
                    'ip': client_ip
                })
                # Continue validation for logging purposes
            
            # 3. Check rate limiting
            rate_limit_result = self._check_rate_limit(client_ip, headers.get('user_agent', ''))
            if not rate_limit_result['allowed']:
                validation_result['errors'].append(rate_limit_result['error'])
                validation_result['security_events'].append({
                    'type': 'rate_limit_exceeded',
                    'severity': 'medium',
                    'details': f"Rate limit exceeded for IP: {client_ip}",
                    'ip': client_ip
                })
                return validation_result
            
            # 4. Validate payload structure
            payload_validation = self._validate_payload(payload)
            if not payload_validation['valid']:
                validation_result['errors'].append(payload_validation['error'])
                return validation_result
            
            # 5. Validate HMAC signature
            signature_validation = self._validate_hmac_signature(
                payload, headers, provider
            )
            if not signature_validation['valid']:
                validation_result['errors'].append(signature_validation['error'])
                validation_result['security_events'].append({
                    'type': 'invalid_signature',
                    'severity': 'critical',
                    'details': f"Invalid webhook signature from IP: {client_ip}",
                    'ip': client_ip
                })
                return validation_result
            
            # 6. Check for replay attacks
            replay_validation = self._check_replay_attack(headers, payload_validation['data'])
            if not replay_validation['valid']:
                validation_result['errors'].append(replay_validation['error'])
                validation_result['security_events'].append({
                    'type': 'replay_attack',
                    'severity': 'high',
                    'details': f"Potential replay attack from IP: {client_ip}",
                    'ip': client_ip
                })
                return validation_result
            
            # 7. Validate idempotency
            idempotency_validation = self._validate_idempotency(
                headers, payload_validation['data']
            )
            if not idempotency_validation['valid']:
                validation_result['warnings'].append(idempotency_validation['warning'])
            
            # All validations passed
            validation_result['success'] = True
            validation_result['webhook_data'] = payload_validation['data']
            validation_result['client_ip'] = client_ip
            validation_result['headers'] = headers
            
            return validation_result
            
        except Exception as e:
            _logger.error("Critical error in webhook validation: %s", str(e))
            validation_result['errors'].append(f"Internal validation error: {str(e)}")
            return validation_result

    def _get_client_ip(self, request):
        """Extract client IP from request with proxy support"""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            # Direct connection
            client_ip = request.httprequest.environ.get('REMOTE_ADDR', 'unknown')
        
        # Additional proxy headers to check
        proxy_headers = [
            'HTTP_X_REAL_IP',
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'HTTP_X_CLUSTER_CLIENT_IP'
        ]
        
        for header in proxy_headers:
            if not client_ip or client_ip == 'unknown':
                client_ip = request.httprequest.environ.get(header, client_ip)
        
        return client_ip

    def _extract_headers(self, request):
        """Extract relevant headers for validation"""
        headers = {}
        
        # Required Vipps headers
        vipps_headers = [
            'Authorization',
            'Vipps-Timestamp', 
            'Vipps-Idempotency-Key',
            'Content-Type',
            'User-Agent'
        ]
        
        for header in vipps_headers:
            value = request.httprequest.headers.get(header)
            if value:
                headers[header.lower().replace('-', '_')] = value
        
        return headers

    def _validate_source_ip(self, client_ip, provider):
        """Validate webhook source IP against allowed ranges"""
        try:
            # Get allowed IP ranges from provider configuration or system parameters
            allowed_ranges = self._get_allowed_ip_ranges(provider)
            
            if not allowed_ranges:
                # If no IP restrictions configured, allow all (with warning)
                _logger.warning("No IP restrictions configured for webhook validation")
                return {'valid': True}
            
            # Validate IP against allowed ranges
            client_addr = ipaddress.ip_address(client_ip)
            
            for ip_range in allowed_ranges:
                try:
                    if '/' in ip_range:
                        network = ipaddress.ip_network(ip_range, strict=False)
                        if client_addr in network:
                            return {'valid': True}
                    else:
                        allowed_addr = ipaddress.ip_address(ip_range)
                        if client_addr == allowed_addr:
                            return {'valid': True}
                except ValueError as e:
                    _logger.warning("Invalid IP range configuration: %s - %s", ip_range, str(e))
                    continue
            
            return {
                'valid': False,
                'error': f"Webhook from unauthorized IP: {client_ip}"
            }
            
        except ValueError as e:
            _logger.error("Invalid client IP format: %s - %s", client_ip, str(e))
            return {
                'valid': False,
                'error': f"Invalid IP format: {client_ip}"
            }

    def _get_allowed_ip_ranges(self, provider):
        """Get allowed IP ranges for webhook validation"""
        # Check provider-specific configuration first
        if hasattr(provider, 'vipps_webhook_allowed_ips') and provider.vipps_webhook_allowed_ips:
            return provider.vipps_webhook_allowed_ips.split(',')
        
        # Fall back to system parameter
        allowed_ips = self.env['ir.config_parameter'].sudo().get_param(
            'vipps.webhook.allowed_ips', ''
        )
        
        if allowed_ips:
            return [ip.strip() for ip in allowed_ips.split(',') if ip.strip()]
        
        # Default Vipps IP ranges (should be configurable in production)
        default_ranges = [
            '213.52.3.0/24',    # Vipps production IPs
            '213.52.4.0/24',    # Vipps production IPs
            '127.0.0.1',        # Localhost for testing
            '::1'               # IPv6 localhost
        ]
        
        # In test environment, be more permissive
        if provider.vipps_environment == 'test':
            default_ranges.extend([
                '10.0.0.0/8',       # Private networks for testing
                '172.16.0.0/12',
                '192.168.0.0/16'
            ])
        
        return default_ranges

    def _check_rate_limit(self, client_ip, user_agent):
        """Check rate limiting for webhook requests"""
        try:
            # Get rate limit configuration
            max_requests = int(self.env['ir.config_parameter'].sudo().get_param(
                'vipps.webhook.rate_limit.max_requests', '100'
            ))
            window_seconds = int(self.env['ir.config_parameter'].sudo().get_param(
                'vipps.webhook.rate_limit.window_seconds', '300'
            ))
            
            # Create identifier for rate limiting (IP + User-Agent hash)
            identifier = f"{client_ip}:{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"
            
            # Check current request count
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Use database-based rate limiting for persistence
            rate_limit_key = f"webhook_rate_limit_{identifier}"
            
            # Get existing rate limit record
            existing_record = self.env['ir.config_parameter'].sudo().search([
                ('key', '=', rate_limit_key)
            ])
            
            if existing_record:
                try:
                    rate_data = json.loads(existing_record.value)
                    requests = [req_time for req_time in rate_data.get('requests', []) 
                              if req_time > window_start]
                except (json.JSONDecodeError, KeyError):
                    requests = []
            else:
                requests = []
            
            # Check if limit exceeded
            if len(requests) >= max_requests:
                return {
                    'allowed': False,
                    'error': f"Rate limit exceeded: {len(requests)}/{max_requests} requests in {window_seconds}s"
                }
            
            # Add current request
            requests.append(current_time)
            
            # Update rate limit record
            rate_data = {'requests': requests}
            if existing_record:
                existing_record.value = json.dumps(rate_data)
            else:
                self.env['ir.config_parameter'].sudo().create({
                    'key': rate_limit_key,
                    'value': json.dumps(rate_data)
                })
            
            return {'allowed': True}
            
        except Exception as e:
            _logger.error("Rate limiting check failed: %s", str(e))
            # Fail open - allow request if rate limiting fails
            return {'allowed': True}

    def _validate_payload(self, payload):
        """Validate webhook payload structure and content"""
        if not payload:
            return {
                'valid': False,
                'error': 'Empty webhook payload'
            }
        
        try:
            # Parse JSON
            webhook_data = json.loads(payload)
            
            # Validate required fields
            required_fields = ['reference']
            missing_fields = [field for field in required_fields 
                            if field not in webhook_data or not webhook_data[field]]
            
            if missing_fields:
                return {
                    'valid': False,
                    'error': f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            # Validate field formats
            reference = webhook_data.get('reference', '')
            if not isinstance(reference, str) or len(reference) < 1:
                return {
                    'valid': False,
                    'error': 'Invalid reference format'
                }
            
            # Additional validation for known fields
            if 'amount' in webhook_data:
                amount_data = webhook_data['amount']
                if not isinstance(amount_data, dict) or 'value' not in amount_data:
                    return {
                        'valid': False,
                        'error': 'Invalid amount format'
                    }
            
            return {
                'valid': True,
                'data': webhook_data
            }
            
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': f'Invalid JSON payload: {str(e)}'
            }

    def _validate_hmac_signature(self, payload, headers, provider):
        """Validate HMAC signature for webhook authenticity"""
        signature = headers.get('authorization', '')
        timestamp = headers.get('vipps_timestamp', '')
        
        if not signature:
            return {
                'valid': False,
                'error': 'Missing webhook signature'
            }
        
        if not timestamp:
            return {
                'valid': False,
                'error': 'Missing webhook timestamp'
            }
        
        try:
            # Get webhook secret
            webhook_secret = provider.vipps_webhook_secret_decrypted
            if not webhook_secret:
                return {
                    'valid': False,
                    'error': 'Webhook secret not configured'
                }
            
            # Validate timestamp format and freshness
            try:
                webhook_time = int(timestamp)
                current_time = int(time.time())
                
                # Allow 5 minutes tolerance for clock skew
                max_age = int(self.env['ir.config_parameter'].sudo().get_param(
                    'vipps.webhook.max_age_seconds', '300'
                ))
                
                if abs(current_time - webhook_time) > max_age:
                    return {
                        'valid': False,
                        'error': f'Webhook timestamp too old or in future: {timestamp}'
                    }
            except (ValueError, TypeError):
                return {
                    'valid': False,
                    'error': f'Invalid timestamp format: {timestamp}'
                }
            
            # Remove 'Bearer ' prefix if present
            if signature.startswith('Bearer '):
                signature = signature[7:]
            
            # Create message for signature verification
            # Vipps format: timestamp + "." + payload
            message = f"{timestamp}.{payload}"
            
            # Calculate expected signature
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Secure comparison
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                return {
                    'valid': False,
                    'error': 'Invalid webhook signature'
                }
            
            return {'valid': True}
            
        except Exception as e:
            _logger.error("Signature validation error: %s", str(e))
            return {
                'valid': False,
                'error': f'Signature validation failed: {str(e)}'
            }

    def _check_replay_attack(self, headers, webhook_data):
        """Check for replay attacks using idempotency keys and timestamps"""
        idempotency_key = headers.get('vipps_idempotency_key')
        event_id = webhook_data.get('eventId')
        
        # Use idempotency key or event ID for replay detection
        unique_id = idempotency_key or event_id
        
        if not unique_id:
            return {
                'valid': False,
                'error': 'Missing idempotency key or event ID for replay protection'
            }
        
        try:
            # Check if we've seen this webhook before
            cache_key = f"webhook_processed_{unique_id}"
            
            existing_record = self.env['ir.config_parameter'].sudo().search([
                ('key', '=', cache_key)
            ])
            
            if existing_record:
                # This webhook has been processed before
                processed_data = json.loads(existing_record.value)
                return {
                    'valid': False,
                    'error': f'Webhook already processed at {processed_data.get("processed_at")}'
                }
            
            # Mark as processed
            self.env['ir.config_parameter'].sudo().create({
                'key': cache_key,
                'value': json.dumps({
                    'processed_at': datetime.now().isoformat(),
                    'reference': webhook_data.get('reference')
                })
            })
            
            return {'valid': True}
            
        except Exception as e:
            _logger.error("Replay attack check failed: %s", str(e))
            # Fail open - allow if check fails
            return {'valid': True}

    def _validate_idempotency(self, headers, webhook_data):
        """Validate idempotency key format and uniqueness"""
        idempotency_key = headers.get('vipps_idempotency_key')
        
        if not idempotency_key:
            return {
                'valid': True,
                'warning': 'No idempotency key provided'
            }
        
        # Validate format (should be UUID-like)
        if len(idempotency_key) < 16:
            return {
                'valid': True,
                'warning': f'Idempotency key too short: {idempotency_key}'
            }
        
        return {'valid': True}

    @api.model
    def log_security_event(self, event_type, details, severity='info', 
                          client_ip=None, provider_id=None, additional_data=None):
        """Log security events for monitoring and alerting"""
        try:
            # Create security event log
            event_data = {
                'event_type': event_type,
                'severity': severity,
                'details': details,
                'client_ip': client_ip,
                'provider_id': provider_id,
                'timestamp': datetime.now().isoformat(),
                'additional_data': additional_data or {}
            }
            
            # Log to Odoo logger
            log_message = f"WEBHOOK_SECURITY_{event_type.upper()}: {details}"
            if client_ip:
                log_message += f" (IP: {client_ip})"
            
            if severity == 'critical':
                _logger.error(log_message)
            elif severity == 'high':
                _logger.warning(log_message)
            else:
                _logger.info(log_message)
            
            # Store in database for audit trail
            self.env['vipps.webhook.security.log'].sudo().create({
                'event_type': event_type,
                'severity': severity,
                'details': details,
                'client_ip': client_ip,
                'provider_id': provider_id,
                'event_data': json.dumps(event_data),
                'user_id': self.env.user.id if self.env.user else False
            })
            
            # Send alerts for critical events
            if severity in ['critical', 'high']:
                self._send_security_alert(event_data)
            
        except Exception as e:
            _logger.error("Failed to log security event: %s", str(e))

    def _send_security_alert(self, event_data):
        """Send security alerts for critical events"""
        try:
            # In production, this could send emails, SMS, or integrate with SIEM
            alert_message = (
                f"SECURITY ALERT: {event_data['event_type']}\n"
                f"Severity: {event_data['severity']}\n"
                f"Details: {event_data['details']}\n"
                f"Time: {event_data['timestamp']}\n"
                f"IP: {event_data.get('client_ip', 'Unknown')}"
            )
            
            _logger.critical("SECURITY ALERT: %s", alert_message)
            
            # TODO: Implement actual alerting mechanism
            # - Email notifications
            # - SMS alerts
            # - SIEM integration
            # - Slack/Teams notifications
            
        except Exception as e:
            _logger.error("Failed to send security alert: %s", str(e))

    @api.model
    def cleanup_old_security_logs(self, days_to_keep=90):
        """Clean up old security logs"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Keep critical events longer
            old_logs = self.env['vipps.webhook.security.log'].search([
                ('create_date', '<', cutoff_date),
                ('severity', 'not in', ['critical', 'high'])
            ])
            
            count = len(old_logs)
            old_logs.unlink()
            
            _logger.info("Cleaned up %d old webhook security logs", count)
            return count
            
        except Exception as e:
            _logger.error("Failed to cleanup security logs: %s", str(e))
            return 0


class VippsWebhookSecurityLog(models.Model):
    """Security event log for webhook processing"""
    _name = 'vipps.webhook.security.log'
    _description = 'Vipps Webhook Security Log'
    _order = 'create_date desc'
    _rec_name = 'event_type'

    event_type = fields.Selection([
        ('unauthorized_ip', 'Unauthorized IP'),
        ('rate_limit_exceeded', 'Rate Limit Exceeded'),
        ('invalid_signature', 'Invalid Signature'),
        ('replay_attack', 'Replay Attack'),
        ('malformed_payload', 'Malformed Payload'),
        ('webhook_processed', 'Webhook Processed'),
        ('validation_failed', 'Validation Failed'),
        ('security_scan', 'Security Scan Detected'),
    ], string='Event Type', required=True)
    
    severity = fields.Selection([
        ('info', 'Info'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity', required=True, default='info')
    
    details = fields.Text(string='Details', required=True)
    client_ip = fields.Char(string='Client IP')
    
    provider_id = fields.Many2one(
        'payment.provider',
        string='Payment Provider',
        ondelete='cascade'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user
    )
    
    event_data = fields.Text(string='Event Data (JSON)')
    
    # Computed fields for analysis
    is_blocked = fields.Boolean(
        string='Request Blocked',
        compute='_compute_is_blocked',
        store=True
    )
    
    @api.depends('event_type', 'severity')
    def _compute_is_blocked(self):
        """Compute if the request was blocked"""
        blocking_events = [
            'unauthorized_ip', 'rate_limit_exceeded', 
            'invalid_signature', 'replay_attack'
        ]
        
        for record in self:
            record.is_blocked = (
                record.event_type in blocking_events or 
                record.severity == 'critical'
            )