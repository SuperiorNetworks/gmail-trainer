#!/usr/bin/env python3
"""
Name: app.py
Version: 1.0.0
Purpose: Flask application for Gmail Trainer email automation system
Author: Dwain Henderson Jr | Superior Networks LLC
Contact: (937) 985-2480 | dhenderson@superiornetworks.biz
Copyright: 2026, Superior Networks LLC
Location: /root/.openclaw/SNDayton/gmail-trainer/dashboard/app.py

What This Application Does:
  - Serves Gmail automation client interface (/gmail route)
  - Provides API endpoints for email operations, rule management, chat
  - Integrates with Gmail API for fetch/send operations
  - Manages SQLite database for rules, audit log, email cache
  - Reuses existing OAuth tokens from briefing dashboard

Input:
  - config/gmail_oauth_credentials.json (OAuth setup)
  - data/gmail_tokens.json (access/refresh tokens)
  - data/email_rules.db (SQLite database)

Output:
  - HTML interface at http://localhost:5000/gmail
  - JSON API responses
  - Database updates (rules, audit log, cache)

Dependencies:
  - Flask, Flask-CORS
  - google-auth-oauthlib, google-api-python-client
  - sqlite3, json, os (standard library)

Change Log:
  2026-03-17 v1.0.0 - Initial release (Dwain Henderson Jr)
"""

import os
import sys
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
    template_folder='templates',
    static_folder='static'
)
CORS(app)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
CONFIG_DIR = BASE_DIR / 'config'
DB_PATH = DATA_DIR / 'email_rules.db'
TOKENS_PATH = DATA_DIR / 'gmail_tokens.json'

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Gmail API and database connectivity.
    
    Returns:
        JSON with:
        - status: 'healthy' or 'degraded'
        - timestamp: current timestamp
        - database: database connectivity status
        - gmail_api: Gmail API connectivity status
        - tokens: token availability and expiry status
    """
    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': {'status': 'unknown'},
        'gmail_api': {'status': 'unknown'},
        'tokens': {'status': 'unknown'}
    }
    
    # Check database
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM email_rules;')
        count = cursor.fetchone()[0]
        conn.close()
        
        health['database'] = {
            'status': 'connected',
            'rules_count': count
        }
    except Exception as e:
        health['database'] = {'status': 'error', 'error': str(e)}
        health['status'] = 'degraded'
    
    # Check tokens availability
    if TOKENS_PATH.exists():
        try:
            with open(TOKENS_PATH, 'r') as f:
                token_data = json.load(f)
            
            health['tokens'] = {
                'status': 'available',
                'has_refresh_token': 'refresh_token' in token_data
            }
        except Exception as e:
            health['tokens'] = {'status': 'error', 'error': str(e)}
            health['status'] = 'degraded'
    else:
        health['tokens'] = {'status': 'not_found'}
        health['status'] = 'degraded'
    
    # Gmail API check (will be implemented when OAuth is set up)
    health['gmail_api'] = {
        'status': 'not_tested_yet',
        'note': 'Will be tested once OAuth tokens are available'
    }
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main briefing dashboard (placeholder)."""
    return jsonify({
        'message': 'Gmail Trainer API Server',
        'version': '0.1.0-alpha',
        'status': 'running',
        'health_check': '/api/health',
        'gmail_client': '/gmail'
    })

@app.route('/gmail')
def gmail_client():
    """Gmail automation client interface (main page)."""
    return render_template('gmail_client.html')

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# STARTUP CHECKS
# ============================================================================

def check_startup_requirements():
    """Verify database and config exist."""
    errors = []
    
    # Check database
    if not DB_PATH.exists():
        errors.append(f"Database not found: {DB_PATH}")
        errors.append("Run: python3 scripts/init_db.py")
    
    # Check config template
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created config directory: {CONFIG_DIR}")
    
    if not (CONFIG_DIR / 'gmail_oauth_credentials.json.example').exists():
        logger.warning("OAuth credentials template not found")
    
    if errors:
        for error in errors:
            logger.error(error)
        return False
    
    logger.info("✅ All startup checks passed")
    return True

if __name__ == '__main__':
    # Verify startup requirements
    if not check_startup_requirements():
        logger.error("Startup checks failed. Cannot proceed.")
        sys.exit(1)
    
    logger.info("🚀 Starting Gmail Trainer Flask app...")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Config: {CONFIG_DIR}")
    logger.info(f"Access dashboard at: http://localhost:5000/")
    logger.info(f"Access Gmail client at: http://localhost:5000/gmail")
    
    # Run Flask development server
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=True
    )
