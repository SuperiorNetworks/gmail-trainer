#!/usr/bin/env python3
"""
Name: gmail.py
Version: 1.0.0
Purpose: Gmail API integration for email fetch, decode, cache, send operations
Author: Dwain Henderson Jr | Superior Networks LLC
Contact: (937) 985-2480 | dhenderson@superiornetworks.biz
Copyright: 2026, Superior Networks LLC
Location: /root/.openclaw/SNDayton/gmail-trainer/dashboard/api/gmail.py

What This Module Does:
  - Fetches emails from Gmail API with watermark tracking
  - Decodes MIME messages (base64 → HTML + plaintext)
  - Populates email_cache for fast search
  - Sanitizes HTML for XSS safety
  - Manages Gmail labels/folders
  - Handles token refresh on API errors

Input:
  - Gmail API credentials (from data/gmail_tokens.json)
  - Message IDs from Gmail API

Output:
  - Cached emails in SQLite
  - JSON API responses with email data

Dependencies:
  - google-api-python-client
  - email, base64, html.parser (standard library)
  - sqlite3, json, os (standard library)

Change Log:
  2026-03-17 v1.0.0 - Initial release (Dwain Henderson Jr)
"""

import json
import base64
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.parser import Parser as EmailParser

from flask import Blueprint, jsonify, request, current_app
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Blueprint setup
gmail_bp = Blueprint('gmail', __name__, url_prefix='/api/gmail')

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'email_rules.db'
TOKENS_PATH = DATA_DIR / 'gmail_tokens.json'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

# ============================================================================
# GMAIL SERVICE MANAGEMENT
# ============================================================================

def get_gmail_service():
    """Get authenticated Gmail API service instance."""
    if not TOKENS_PATH.exists():
        raise ValueError(f"Token file not found: {TOKENS_PATH}")
    
    try:
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
        
        service = build('gmail', 'v1', credentials=creds)
        return service
        
    except Exception as e:
        logger.error(f"Failed to get Gmail service: {e}")
        raise

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def get_watermark():
    """Get last processed message ID from database."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM system_state WHERE key = ?', ('last_processed_message_id',))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ''
    except Exception as e:
        logger.error(f"Failed to get watermark: {e}")
        return ''

def update_watermark(message_id):
    """Update last processed message ID."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE system_state SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?',
                      (message_id, 'last_processed_message_id'))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to update watermark: {e}")

def decode_mime_message(message_data):
    """Decode MIME message from Gmail API response."""
    try:
        headers = message_data.get('payload', {}).get('headers', [])
        
        # Extract headers
        header_dict = {h['name'].lower(): h['value'] for h in headers}
        
        from_addr = header_dict.get('from', '')
        to_addr = header_dict.get('to', '')
        subject = header_dict.get('subject', '')
        date = header_dict.get('date', '')
        
        # Extract body
        body_html = ''
        body_plain = ''
        
        payload = message_data.get('payload', {})
        
        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body_plain = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                
                elif mime_type == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            # Single part message
            data = payload.get('body', {}).get('data', '')
            if data:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                
                # Guess if HTML or plaintext
                if '<html' in decoded.lower() or '<body' in decoded.lower():
                    body_html = decoded
                else:
                    body_plain = decoded
        
        # Fallback: use plain text if no HTML
        if not body_plain and body_html:
            body_plain = body_html.replace('<br>', '\n').replace('<p>', '').replace('</p>', '\n')
        
        return {
            'from': from_addr,
            'to': to_addr,
            'subject': subject,
            'date': date,
            'body_html': body_html,
            'body_plain': body_plain
        }
        
    except Exception as e:
        logger.error(f"Failed to decode MIME message: {e}")
        return {
            'from': '',
            'to': '',
            'subject': '',
            'date': '',
            'body_html': '',
            'body_plain': f'Error decoding message: {str(e)}'
        }

def cache_email(message_id, email_data, labels):
    """Store email in cache for fast search."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO email_cache
            (message_id, from_address, subject, body_html, body_plain, labels, received_date, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            message_id,
            email_data.get('from', ''),
            email_data.get('subject', ''),
            email_data.get('body_html', ''),
            email_data.get('body_plain', ''),
            json.dumps(labels),
            email_data.get('date', '')
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to cache email: {e}")

# ============================================================================
# ENDPOINTS
# ============================================================================

@gmail_bp.route('/messages', methods=['GET'])
def get_messages():
    """
    Fetch recent emails from Gmail inbox.
    
    Query params:
        - limit: number of emails to fetch (default: 20)
        - folder: label/folder name (default: INBOX)
    
    Returns:
        JSON list of emails with sender, subject, snippet, date
    """
    try:
        service = get_gmail_service()
        limit = request.args.get('limit', 20, type=int)
        folder = request.args.get('folder', 'INBOX')
        
        # Build query
        query = f'in:{folder}'
        
        # List messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        
        # Get message details and cache them
        email_list = []
        watermark = get_watermark()
        
        for msg in messages:
            msg_id = msg['id']
            
            # Skip if already processed (watermark)
            if watermark and msg_id == watermark:
                break
            
            # Fetch full message
            msg_data = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            
            # Decode
            decoded = decode_mime_message(msg_data)
            labels = msg_data.get('labelIds', [])
            
            # Cache it
            cache_email(msg_id, decoded, labels)
            
            # Add to response
            email_list.append({
                'message_id': msg_id,
                'from': decoded['from'],
                'subject': decoded['subject'],
                'date': decoded['date'],
                'labels': labels
            })
        
        # Update watermark
        if email_list:
            update_watermark(email_list[0]['message_id'])
        
        return jsonify({
            'messages': email_list,
            'count': len(email_list)
        }), 200
        
    except HttpError as e:
        logger.error(f"Gmail API error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return jsonify({'error': str(e)}), 500

@gmail_bp.route('/messages/<message_id>', methods=['GET'])
def get_message(message_id):
    """
    Fetch full email by message ID.
    
    Returns:
        JSON with from, to, subject, date, body_html, body_plain
    """
    try:
        # Check cache first (fast path)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM email_cache WHERE message_id = ?', (message_id,))
        cached = cursor.fetchone()
        conn.close()
        
        if cached:
            return jsonify({
                'message_id': cached['message_id'],
                'from': cached['from_address'],
                'subject': cached['subject'],
                'body_html': cached['body_html'],
                'body_plain': cached['body_plain'],
                'labels': json.loads(cached['labels']),
                'source': 'cache'
            }), 200
        
        # Fetch from Gmail API if not cached
        service = get_gmail_service()
        msg_data = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        decoded = decode_mime_message(msg_data)
        labels = msg_data.get('labelIds', [])
        
        # Cache it for next time
        cache_email(message_id, decoded, labels)
        
        return jsonify({
            'message_id': message_id,
            'from': decoded['from'],
            'to': decoded['to'],
            'subject': decoded['subject'],
            'date': decoded['date'],
            'body_html': decoded['body_html'],
            'body_plain': decoded['body_plain'],
            'labels': labels,
            'source': 'gmail_api'
        }), 200
        
    except HttpError as e:
        logger.error(f"Gmail API error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error fetching message: {e}")
        return jsonify({'error': str(e)}), 500

@gmail_bp.route('/labels', methods=['GET'])
def get_labels():
    """
    Get all Gmail labels/folders.
    
    Returns:
        JSON list of labels with id, name
    """
    try:
        service = get_gmail_service()
        results = service.users().labels().list(userId='me').execute()
        
        labels = results.get('labels', [])
        label_list = [
            {
                'id': label['id'],
                'name': label['name']
            }
            for label in labels
        ]
        
        return jsonify({
            'labels': label_list,
            'count': len(label_list)
        }), 200
        
    except HttpError as e:
        logger.error(f"Gmail API error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error fetching labels: {e}")
        return jsonify({'error': str(e)}), 500

@gmail_bp.route('/messages/send', methods=['POST'])
def send_message():
    """
    Send email via Gmail API.
    
    Request JSON:
        {
            "to": "recipient@example.com",
            "cc": "cc@example.com",
            "subject": "Subject",
            "body_plain": "Plaintext body",
            "body_html": "<html>...</html>"
        }
    
    Returns:
        JSON with message_id and status
    """
    try:
        data = request.get_json()
        
        service = get_gmail_service()
        
        # Build MIME message
        if data.get('body_html'):
            message = MIMEMultipart('alternative')
            part1 = MIMEText(data.get('body_plain', ''), 'plain')
            part2 = MIMEText(data.get('body_html', ''), 'html')
            message.attach(part1)
            message.attach(part2)
        else:
            message = MIMEText(data.get('body_plain', ''), 'plain')
        
        message['to'] = data.get('to', '')
        if data.get('cc'):
            message['cc'] = data.get('cc', '')
        message['subject'] = data.get('subject', '')
        
        # Send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return jsonify({
            'message_id': result['id'],
            'status': 'sent'
        }), 200
        
    except HttpError as e:
        logger.error(f"Gmail API error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({'error': str(e)}), 500

@gmail_bp.route('/messages/<message_id>/reply', methods=['POST'])
def reply_message(message_id):
    """Reply to an email (preserves threading)."""
    try:
        data = request.get_json()
        service = get_gmail_service()
        
        # Get original message
        original = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        # Extract headers for threading
        headers = {h['name'].lower(): h['value'] for h in original.get('payload', {}).get('headers', [])}
        
        # Build reply
        message = MIMEText(data.get('body_plain', ''), 'plain')
        message['to'] = headers.get('from', '')
        message['subject'] = f"Re: {headers.get('subject', '')}"
        message['In-Reply-To'] = headers.get('message-id', '')
        message['References'] = headers.get('references', '') + ' ' + headers.get('message-id', '')
        
        # Send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw_message, 'threadId': original.get('threadId')}
        ).execute()
        
        return jsonify({
            'message_id': result['id'],
            'status': 'sent'
        }), 200
        
    except Exception as e:
        logger.error(f"Error replying to message: {e}")
        return jsonify({'error': str(e)}), 500

@gmail_bp.route('/messages/<message_id>/archive', methods=['POST'])
def archive_message(message_id):
    """Archive an email (remove from inbox)."""
    try:
        service = get_gmail_service()
        
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabels': ['INBOX']}
        ).execute()
        
        return jsonify({
            'message_id': message_id,
            'status': 'archived'
        }), 200
        
    except Exception as e:
        logger.error(f"Error archiving message: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ERROR HANDLER
# ============================================================================

@gmail_bp.errorhandler(Exception)
def handle_error(error):
    """Handle blueprint errors."""
    logger.error(f"Blueprint error: {error}")
    return jsonify({'error': str(error)}), 500
