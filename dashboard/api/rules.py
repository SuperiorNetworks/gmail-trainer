#!/usr/bin/env python3
"""
Name: rules.py
Version: 1.0.0
Purpose: Rule management API (create, read, update, delete automation rules)
Author: Dwain Henderson Jr | Superior Networks LLC
Contact: (937) 985-2480 | dhenderson@superiornetworks.biz
Copyright: 2026, Superior Networks LLC
Location: /root/.openclaw/SNDayton/gmail-trainer/dashboard/api/rules.py

What This Module Does:
  - Create new automation rules from training modal
  - Retrieve rules (all, active, by ID)
  - Update rule status (pending → active)
  - Delete rules (archive, not hard delete)
  - Validate rule data
  - Store in SQLite database

Input:
  - POST /api/rules/create (training Q0-Q5 answers)
  - GET /api/rules/list (retrieve active rules)
  - PATCH /api/rules/{id}/activate (activate pending rule)

Output:
  - JSON with rule_id, status, validation errors

Dependencies:
  - sqlite3, json (standard library)
  - Flask (routing)

Change Log:
  2026-03-17 v1.0.0 - Initial release (Dwain Henderson Jr)
"""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Blueprint setup
rules_bp = Blueprint('rules', __name__, url_prefix='/api/rules')

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'email_rules.db'

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================================
# ENDPOINTS
# ============================================================================

@rules_bp.route('/create', methods=['POST'])
def create_rule():
    """
    Create a new automation rule from training modal answers.
    
    Request JSON:
        {
            "name": "reports@positive-electric.com - file",
            "sender_pattern": "reports@positive-electric.com",
            "subject_keywords": "report, status",
            "primary_action": "file",
            "folder_target": "Reports",
            "forward_to": null,
            "ticket_board": null,
            "exception_action": null,
            "condition_logic": {
                "type": "keyword_match",
                "field": "body",
                "keywords": ["ERROR", "FAILED"],
                "match": "any",
                "case_sensitive": false
            },
            "status": "pending"
        }
    
    Returns:
        JSON with rule_id, status, name
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Rule name required'}), 400
        
        if not data.get('sender_pattern'):
            return jsonify({'error': 'Sender pattern required'}), 400
        
        if not data.get('primary_action'):
            return jsonify({'error': 'Primary action required'}), 400
        
        # Insert rule
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO email_rules
                (name, sender_pattern, subject_keywords, primary_action, 
                 folder_target, forward_to, ticket_board, exception_action,
                 condition_logic, status, created_date, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                data.get('name'),
                data.get('sender_pattern'),
                data.get('subject_keywords'),
                data.get('primary_action'),
                data.get('folder_target'),
                data.get('forward_to'),
                data.get('ticket_board'),
                data.get('exception_action'),
                json.dumps(data.get('condition_logic')) if data.get('condition_logic') else None,
                data.get('status', 'pending')
            ))
            
            conn.commit()
            rule_id = cursor.lastrowid
            
            logger.info(f"✅ Rule created: {rule_id} - {data.get('name')}")
            
            return jsonify({
                'rule_id': rule_id,
                'name': data.get('name'),
                'status': data.get('status', 'pending')
            }), 201
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.error(f"Rule creation error: {e}")
            return jsonify({'error': f'Rule name already exists'}), 400
        
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        return jsonify({'error': str(e)}), 500

@rules_bp.route('/list', methods=['GET'])
def list_rules():
    """
    Get all rules (optionally filter by status).
    
    Query params:
        - status: 'active', 'pending', or all (default)
    
    Returns:
        JSON list of rules
    """
    try:
        status = request.args.get('status')
        
        conn = get_db()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM email_rules WHERE status = ? ORDER BY created_date DESC',
                          (status,))
        else:
            cursor.execute('SELECT * FROM email_rules ORDER BY created_date DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        rules = [
            {
                'rule_id': row['rule_id'],
                'name': row['name'],
                'sender_pattern': row['sender_pattern'],
                'subject_keywords': row['subject_keywords'],
                'primary_action': row['primary_action'],
                'status': row['status'],
                'created_date': row['created_date'],
                'last_modified': row['last_modified']
            }
            for row in rows
        ]
        
        return jsonify({
            'rules': rules,
            'count': len(rules)
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        return jsonify({'error': str(e)}), 500

@rules_bp.route('/<int:rule_id>', methods=['GET'])
def get_rule(rule_id):
    """Get a specific rule by ID."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM email_rules WHERE rule_id = ?', (rule_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Rule not found'}), 404
        
        rule = {
            'rule_id': row['rule_id'],
            'name': row['name'],
            'sender_pattern': row['sender_pattern'],
            'subject_keywords': row['subject_keywords'],
            'primary_action': row['primary_action'],
            'folder_target': row['folder_target'],
            'forward_to': row['forward_to'],
            'ticket_board': row['ticket_board'],
            'exception_action': row['exception_action'],
            'condition_logic': json.loads(row['condition_logic']) if row['condition_logic'] else None,
            'status': row['status'],
            'priority': row['priority'],
            'created_date': row['created_date'],
            'last_modified': row['last_modified']
        }
        
        return jsonify(rule), 200
    
    except Exception as e:
        logger.error(f"Error getting rule: {e}")
        return jsonify({'error': str(e)}), 500

@rules_bp.route('/<int:rule_id>/activate', methods=['PATCH'])
def activate_rule(rule_id):
    """Activate a pending rule."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE email_rules SET status = ?, last_modified = CURRENT_TIMESTAMP WHERE rule_id = ?',
                      ('active', rule_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Rule activated: {rule_id}")
        
        return jsonify({
            'rule_id': rule_id,
            'status': 'active'
        }), 200
    
    except Exception as e:
        logger.error(f"Error activating rule: {e}")
        return jsonify({'error': str(e)}), 500

@rules_bp.route('/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    """Delete (archive) a rule."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Soft delete: set status to 'archived'
        cursor.execute('UPDATE email_rules SET status = ?, last_modified = CURRENT_TIMESTAMP WHERE rule_id = ?',
                      ('archived', rule_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Rule archived: {rule_id}")
        
        return jsonify({
            'rule_id': rule_id,
            'status': 'archived'
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ERROR HANDLER
# ============================================================================

@rules_bp.errorhandler(Exception)
def handle_error(error):
    """Handle blueprint errors."""
    logger.error(f"Blueprint error: {error}")
    return jsonify({'error': str(error)}), 500
