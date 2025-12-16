#!/usr/bin/env python3
"""
Add webhook columns to payment_transaction table
Run this in Odoo shell to add the missing columns
"""

# Add the columns directly to the database
import logging
_logger = logging.getLogger(__name__)

print("Adding webhook columns to payment_transaction table...")

# First, rollback any failed transaction
try:
    env.cr.rollback()
    print("✅ Rolled back previous transaction")
except:
    pass

try:
    # Check if columns exist
    env.cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='payment_transaction' 
        AND column_name IN ('vipps_webhook_id', 'vipps_webhook_secret')
    """)
    existing_columns = [row[0] for row in env.cr.fetchall()]
    
    print(f"Existing webhook columns: {existing_columns}")
    
    # Add vipps_webhook_id if missing
    if 'vipps_webhook_id' not in existing_columns:
        print("Adding vipps_webhook_id column...")
        env.cr.execute("""
            ALTER TABLE payment_transaction 
            ADD COLUMN vipps_webhook_id VARCHAR
        """)
        print("✅ Added vipps_webhook_id column")
    else:
        print("✅ vipps_webhook_id column already exists")
    
    # Add vipps_webhook_secret if missing
    if 'vipps_webhook_secret' not in existing_columns:
        print("Adding vipps_webhook_secret column...")
        env.cr.execute("""
            ALTER TABLE payment_transaction 
            ADD COLUMN vipps_webhook_secret VARCHAR
        """)
        print("✅ Added vipps_webhook_secret column")
    else:
        print("✅ vipps_webhook_secret column already exists")
    
    # Commit the changes
    env.cr.commit()
    
    # Verify columns were added
    env.cr.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='payment_transaction' 
        AND column_name IN ('vipps_webhook_id', 'vipps_webhook_secret')
        ORDER BY column_name
    """)
    
    print("\nVerification - Webhook columns in payment_transaction:")
    for row in env.cr.fetchall():
        print(f"  - {row[0]}: {row[1]}")
    
    print("\n✅ Database schema updated successfully!")
    print("\nYou can now:")
    print("1. Run cleanup_orphaned_webhooks.py to clean up old webhooks")
    print("2. Create a new test payment to verify webhook registration")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    env.cr.rollback()

print("\n" + "="*80)
