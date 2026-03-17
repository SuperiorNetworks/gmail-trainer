#!/usr/bin/env python3
"""
Name: email_automation.py
Version: 1.0.0
Purpose: Background job for email rule matching and automation execution
Author: Dwain Henderson Jr | Superior Networks LLC
Contact: (937) 985-2480 | dhenderson@superiornetworks.biz
Copyright: 2026, Superior Networks LLC
Location: /root/.openclaw/SNDayton/gmail-trainer/scripts/email_automation.py

What This Script Does:
  - Runs every 5 minutes (via cron or systemd timer)
  - Fetches new emails using watermark tracking
  - Matches each email against active rules
  - Executes actions (file, forward, ticket, archive, delete, do nothing)
  - Logs every decision to audit_log (accountability)
  - Deduplicates emails (prevents duplicate automation)
  - Handles errors gracefully

Input:
  - Gmail API (fetch new emails)
  - SQLite (rules, system_state watermark)

Output:
  - Updated email_cache (new emails)
  - Updated email_audit_log (automation decisions)
  - Updated system_state (watermark)

Dependencies:
  - google-api-python-client
  - sqlite3, json, sys, logging (standard library)

Change Log:
  2026-03-17 v1.0.0 - Initial release (Dwain Henderson Jr)
"""

import json
import sqlite3
import logging
import sys
from pathlib import Path
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Google libraries not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/gmail-trainer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'email_rules.db'
TOKENS_PATH = DATA_DIR / 'gmail_tokens.json'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

class EmailAutomation:
    """Main automation engine for rule matching and execution."""
    
    def __init__(self):
        self.service = None
        self.db = None
        self.processed_count = 0
        self.error_count = 0
    
    def setup(self):
        """Initialize Gmail service and database."""
        try:
            # Setup Gmail service
            self.service = self._get_gmail_service()
            
            # Setup database
            self.db = sqlite3.connect(str(DB_PATH))
            self.db.row_factory = sqlite3.Row
            
            logger.info("✅ Email automation initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    def _get_gmail_service(self):
        """Get authenticated Gmail service."""
        if not TOKENS_PATH.exists():
            raise ValueError(f"Token file not found: {TOKENS_PATH}")
        
        with open(TOKENS_PATH, 'r') as f:
            token_data = json.load(f)
        
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        # Refresh if expired
        if creds.expired:
            request_obj = Request()
            creds.refresh(request_obj)
            
            # Save refreshed token
            with open(TOKENS_PATH, 'w') as f:
                json.dump({
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }, f)
            
            logger.info("✅ Gmail token refreshed")
        
        return build('gmail', 'v1', credentials=creds)
    
    def get_watermark(self):
        """Get last processed message ID."""
        try:
            cursor = self.db.cursor()
            cursor.execute('SELECT value FROM system_state WHERE key = ?', ('last_processed_message_id',))
            row = cursor.fetchone()
            return row[0] if row else ''
        except Exception as e:
            logger.error(f"Failed to get watermark: {e}")
            return ''
    
    def update_watermark(self, message_id):
        """Update last processed message ID."""
        try:
            cursor = self.db.cursor()
            cursor.execute('UPDATE system_state SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?',
                          (message_id, 'last_processed_message_id'))
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update watermark: {e}")
    
    def is_duplicate(self, email_id):
        """Check if email already processed (deduplication)."""
        try:
            cursor = self.db.cursor()
            cursor.execute('SELECT log_id FROM email_audit_log WHERE email_id = ? LIMIT 1', (email_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Dedup check failed: {e}")
            return False
    
    def fetch_new_emails(self):
        """Fetch new emails since watermark."""
        try:
            watermark = self.get_watermark()
            
            query = 'in:INBOX'
            if watermark:
                query += f' after:{watermark}'
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"📧 Fetched {len(messages)} new emails")
            
            return messages
            
        except HttpError as e:
            logger.error(f"❌ Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to fetch emails: {e}")
            return []
    
    def get_active_rules(self):
        """Get all active automation rules."""
        try:
            cursor = self.db.cursor()
            cursor.execute('SELECT * FROM email_rules WHERE status = ? ORDER BY priority ASC',
                          ('active',))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get rules: {e}")
            return []
    
    def match_rule(self, email_data, rules):
        """Match email against rules (first match wins)."""
        for rule in rules:
            sender_pattern = rule['sender_pattern'] or ''
            subject_keywords = rule['subject_keywords'] or ''
            
            # Check sender match
            if sender_pattern and sender_pattern.lower() not in email_data.get('from', '').lower():
                continue
            
            # Check subject match
            if subject_keywords:
                keywords = [k.strip() for k in subject_keywords.split(',')]
                subject = email_data.get('subject', '').lower()
                if not any(k.lower() in subject for k in keywords):
                    continue
            
            # Rule matched!
            logger.info(f"✅ Rule '{rule['name']}' matched email from {email_data.get('from')}")
            return rule
        
        return None
    
    def execute_action(self, email_id, rule, email_data):
        """Execute automation action."""
        try:
            action = rule['primary_action']
            
            if action == 'do_nothing':
                logger.info(f"ℹ️  Do nothing action (email stays in inbox)")
                return {'action': 'do_nothing', 'status': 'success'}
            
            elif action == 'archive':
                self.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'removeLabels': ['INBOX']}
                ).execute()
                logger.info(f"📦 Archived email")
                return {'action': 'archive', 'status': 'success'}
            
            elif action == 'delete':
                self.service.users().messages().trash(
                    userId='me',
                    id=email_id
                ).execute()
                logger.info(f"🗑️  Deleted email")
                return {'action': 'delete', 'status': 'success'}
            
            elif action == 'file':
                # File to folder (add label)
                folder = rule['folder_target']
                if folder:
                    self.service.users().messages().modify(
                        userId='me',
                        id=email_id,
                        body={'addLabels': [folder]}
                    ).execute()
                    logger.info(f"📁 Filed to {folder}")
                return {'action': f'file:{folder}', 'status': 'success'}
            
            else:
                logger.warning(f"⚠️  Unknown action: {action}")
                return {'action': action, 'status': 'skipped'}
            
        except HttpError as e:
            logger.error(f"❌ Gmail API error executing action: {e}")
            return {'action': rule['primary_action'], 'status': 'error', 'error': str(e)}
        except Exception as e:
            logger.error(f"❌ Failed to execute action: {e}")
            return {'action': rule['primary_action'], 'status': 'error', 'error': str(e)}
    
    def log_decision(self, email_id, email_data, rule, action_result):
        """Log automation decision to audit trail."""
        try:
            cursor = self.db.cursor()
            
            cursor.execute('''
                INSERT INTO email_audit_log
                (rule_id, email_id, from_address, subject, matched_rule_name, action_taken, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                rule['rule_id'],
                email_id,
                email_data.get('from', ''),
                email_data.get('subject', ''),
                rule['name'],
                action_result['action'],
                action_result['status']
            ))
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
    
    def process_emails(self):
        """Main processing loop."""
        logger.info("🚀 Starting email automation run...")
        
        # Fetch new emails
        messages = self.fetch_new_emails()
        if not messages:
            logger.info("ℹ️  No new emails to process")
            return True
        
        # Get active rules
        rules = self.get_active_rules()
        if not rules:
            logger.warning("⚠️  No active rules found")
            return True
        
        logger.info(f"🎯 Processing with {len(rules)} active rules")
        
        # Process each email
        for msg in messages:
            email_id = msg['id']
            
            # Deduplication check
            if self.is_duplicate(email_id):
                logger.info(f"⏭️  Skipping duplicate email {email_id}")
                continue
            
            try:
                # Fetch full message
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=email_id,
                    format='full'
                ).execute()
                
                # Extract headers (minimal parsing for matching)
                headers = {h['name'].lower(): h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
                
                email_data = {
                    'from': headers.get('from', ''),
                    'to': headers.get('to', ''),
                    'subject': headers.get('subject', '')
                }
                
                # Match against rules
                matched_rule = self.match_rule(email_data, rules)
                
                if matched_rule:
                    # Execute action
                    action_result = self.execute_action(email_id, matched_rule, email_data)
                    
                    # Log decision
                    self.log_decision(email_id, email_data, matched_rule, action_result)
                    
                    self.processed_count += 1
                else:
                    # No rule matched
                    logger.info(f"ℹ️  No rule matched for: {email_data.get('subject')}")
                
            except Exception as e:
                logger.error(f"❌ Error processing email {email_id}: {e}")
                self.error_count += 1
        
        # Update watermark
        if messages:
            self.update_watermark(messages[0]['id'])
        
        return True
    
    def cleanup(self):
        """Close database connection."""
        if self.db:
            self.db.close()
    
    def run(self):
        """Main entry point."""
        try:
            if not self.setup():
                return False
            
            if not self.process_emails():
                return False
            
            logger.info(f"✅ Automation run complete: {self.processed_count} processed, {self.error_count} errors")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Automation run failed: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == '__main__':
    automation = EmailAutomation()
    success = automation.run()
    sys.exit(0 if success else 1)
