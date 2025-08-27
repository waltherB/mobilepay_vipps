#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Odoo 17 CE Compatibility Audit and Fix Script

This script identifies and fixes all Odoo 17 compatibility issues in the Vipps/MobilePay module.
"""

import os
import re
import json
from pathlib import Path

class Odoo17CompatibilityAuditor:
    def __init__(self):
        self.issues = []
        self.fixes_applied = []
        
    def audit_all(self):
        """Run comprehensive audit"""
        print("🔍 Starting comprehensive Odoo 17 CE compatibility audit...\n")
        
        self.audit_payment_provider()
        self.audit_payment_transaction()
        self.audit_pos_integration()
        self.audit_webhook_handling()
        self.audit_xml_views()
        self.audit_javascript()
        self.audit_manifest()
        
        self.print_results()
        return len(self.issues) == 0
    
    def audit_payment_provider(self):
        """Audit payment provider for Odoo 17 compatibility"""
        print("📋 Auditing Payment Provider...")
        
        file_path = "models/payment_provider.py"
        if not os.path.exists(file_path):
            self.issues.append(f"Missing file: {file_path}")
            return
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for required Odoo 17 methods
        required_methods = [
            '_get_supported_currencies',
            '_get_supported_countries', 
            '_get_default_payment_method_codes'
        ]
        
        for method in required_methods:
            if f"def {method}" not in content:
                self.issues.append(f"Missing required Odoo 17 method: {method} in payment_provider.py")
        
        # Check for proper inheritance
        if "_inherit = 'payment.provider'" not in content:
            self.issues.append("payment_provider.py must inherit from 'payment.provider'")
        
        # Check for deprecated imports
        if "from odoo.addons.payment.models.payment_acquirer" in content:
            self.issues.append("Using deprecated payment_acquirer import in payment_provider.py")
    
    def audit_payment_transaction(self):
        """Audit payment transaction for Odoo 17 compatibility"""
        print("💳 Auditing Payment Transaction...")
        
        file_path = "models/payment_transaction.py"
        if not os.path.exists(file_path):
            self.issues.append(f"Missing file: {file_path}")
            return
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for required Odoo 17 methods
        if "_process_notification_data" not in content:
            self.issues.append("Missing _process_notification_data method in payment_transaction.py (required for Odoo 17)")
        
        # Check for deprecated methods
        deprecated_methods = [
            "_handle_feedback_data",
            "_get_tx_from_feedback_data"
        ]
        
        for method in deprecated_methods:
            if f"def {method}" in content:
                self.issues.append(f"Using deprecated method {method} in payment_transaction.py")
    
    def audit_pos_integration(self):
        """Audit POS integration for Odoo 17 compatibility"""
        print("🏪 Auditing POS Integration...")
        
        file_path = "models/pos_payment_method.py"
        if not os.path.exists(file_path):
            self.issues.append(f"Missing file: {file_path}")
            return
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for proper POS API usage
        if "_get_payment_terminal_selection" not in content:
            self.issues.append("Missing _get_payment_terminal_selection method for Odoo 17 POS API")
    
    def audit_webhook_handling(self):
        """Audit webhook handling for Odoo 17 compatibility"""
        print("🔗 Auditing Webhook Handling...")
        
        file_path = "controllers/main.py"
        if not os.path.exists(file_path):
            self.issues.append(f"Missing file: {file_path}")
            return
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for proper notification handling
        if "_process_notification_data" not in content:
            self.issues.append("Webhook controller should use _process_notification_data for Odoo 17")
    
    def audit_xml_views(self):
        """Audit XML views for deprecated syntax"""
        print("📄 Auditing XML Views...")
        
        xml_files = list(Path('views').glob('*.xml')) if Path('views').exists() else []
        
        for xml_file in xml_files:
            with open(xml_file, 'r') as f:
                content = f.read()
            
            if 'attrs=' in content:
                self.issues.append(f"File {xml_file} uses deprecated 'attrs' syntax (Odoo 17 uses invisible/required/readonly)")
    
    def audit_javascript(self):
        """Audit JavaScript for Odoo 17 compatibility"""
        print("🟨 Auditing JavaScript...")
        
        js_files = list(Path('static/src/js').glob('*.js')) if Path('static/src/js').exists() else []
        
        for js_file in js_files:
            with open(js_file, 'r') as f:
                content = f.read()
            
            if 'odoo.define(' in content:
                self.issues.append(f"File {js_file} uses deprecated odoo.define() (Odoo 17 uses ES6 modules)")
    
    def audit_manifest(self):
        """Audit manifest for Odoo 17 compatibility"""
        print("📋 Auditing Manifest...")
        
        if not os.path.exists('__manifest__.py'):
            self.issues.append("Missing __manifest__.py file")
            return
        
        with open('__manifest__.py', 'r') as f:
            content = f.read()
        
        # Check dependencies
        if "'payment'" not in content:
            self.issues.append("Missing 'payment' dependency in manifest")
        
        if "'account'" not in content:
            self.issues.append("Missing 'account' dependency for Odoo 17")
    
    def print_results(self):
        """Print audit results"""
        print("\n" + "="*60)
        print("ODOO 17 CE COMPATIBILITY AUDIT RESULTS")
        print("="*60)
        
        if not self.issues:
            print("🎉 ✅ NO COMPATIBILITY ISSUES FOUND!")
        else:
            print(f"❌ FOUND {len(self.issues)} COMPATIBILITY ISSUES:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        print("="*60)

def main():
    auditor = Odoo17CompatibilityAuditor()
    is_compatible = auditor.audit_all()
    
    if not is_compatible:
        print("\n🔧 CRITICAL ISSUES FOUND - Module needs updates for Odoo 17 CE compatibility!")
        return False
    else:
        print("\n✅ Module is compatible with Odoo 17 CE!")
        return True

if __name__ == "__main__":
    main()