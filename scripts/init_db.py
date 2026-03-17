#!/usr/bin/env python3
"""
Name: init_db.py
Version: 1.0.0
Purpose: Initialize SQLite database with all Gmail Trainer tables
Author: Dwain Henderson Jr | Superior Networks LLC
Contact: (937) 985-2480 | dhenderson@superiornetworks.biz
Copyright: 2026, Superior Networks LLC
Location: /root/.openclaw/SNDayton/gmail-trainer/scripts/init_db.py

What This Script Does:
  - Creates SQLite database at data/email_rules.db
  - Initializes all required tables (email_rules, email_audit_log, etc.)
  - Adds indexes for search performance
  - Enables WAL mode and foreign keys
  - Ready for Gmail Trainer application

Input:
  - (None — creates database from scratch)

Output:
  - data/email_rules.db (SQLite database file)
  - Console output confirming schema creation

Dependencies:
  - sqlite3 (standard library)
  - os, sys (standard library)

Change Log:
  2026-03-17 v1.0.0 - Initial release (Dwain Henderson Jr)
"""

import sqlite3
import os
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / 'data' / 'email_rules.db'

def init_database():
    """Initialize SQLite database with Gmail Trainer schema."""
    
    # Create data directory if it doesn't exist
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database (creates it if doesn't exist)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Enable WAL mode (concurrent read/write)
        cursor.execute('PRAGMA journal_mode=WAL;')
        
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys=ON;')
        
        print("✅ Database initialized with WAL mode and foreign keys enabled")
        
        # Create email_rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                sender_pattern TEXT,
                subject_keywords TEXT,
                condition_logic JSON,
                primary_action TEXT NOT NULL,
                exception_action TEXT,
                folder_target TEXT,
                ticket_board INTEGER,
                forward_to TEXT,
                priority INTEGER DEFAULT 100,
                notify_on_match TEXT DEFAULT 'none',
                notify_channel TEXT,
                status TEXT DEFAULT 'pending',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        print("✅ Created email_rules table")
        
        # Create email_audit_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER REFERENCES email_rules(rule_id),
                email_id TEXT NOT NULL,
                from_address TEXT,
                subject TEXT,
                matched_rule_name TEXT,
                condition_evaluated JSON,
                action_taken TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        print("✅ Created email_audit_log table")
        
        # Create email_cache table (critical for search performance)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_cache (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT,
                from_address TEXT NOT NULL,
                subject TEXT,
                snippet TEXT,
                body_html TEXT,
                body_plain TEXT,
                labels TEXT,
                has_attachments BOOLEAN DEFAULT 0,
                received_date TIMESTAMP,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        print("✅ Created email_cache table")
        
        # Create system_state table (watermark tracking + config)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        print("✅ Created system_state table")
        
        # Create user_preferences table (remember last choices)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        print("✅ Created user_preferences table")
        
        # Create email_exceptions table (user feedback)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_exceptions (
                exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                rule_id INTEGER REFERENCES email_rules(rule_id),
                reason TEXT,
                user_action TEXT,
                user_feedback TEXT,
                suggest_rule_change BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        print("✅ Created email_exceptions table")
        
        # Create rule_templates table (for Phase 2)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rule_templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                base_condition JSON,
                example_senders TEXT,
                example_keywords TEXT,
                recommended_action TEXT
            );
        ''')
        print("✅ Created rule_templates table")
        
        # Add indexes for search performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_rule_id ON email_audit_log(rule_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_email_id ON email_audit_log(email_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON email_audit_log(timestamp);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_from ON email_audit_log(from_address);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rules_active ON email_rules(status);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_from ON email_cache(from_address);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_date ON email_cache(received_date);')
        print("✅ Created indexes for search performance")
        
        # Initialize system_state with default values
        cursor.execute('INSERT OR IGNORE INTO system_state (key, value) VALUES (?, ?)',
                      ('last_processed_message_id', ''))
        cursor.execute('INSERT OR IGNORE INTO system_state (key, value) VALUES (?, ?)',
                      ('last_run_timestamp', ''))
        print("✅ Initialized system_state defaults")
        
        # Commit all changes
        conn.commit()
        print(f"\n✅ Database initialized successfully: {DB_PATH}")
        print(f"✅ All tables created with proper indexes and constraints")
        print(f"✅ Ready for Gmail Trainer application\n")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
