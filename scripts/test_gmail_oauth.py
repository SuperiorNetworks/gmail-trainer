#!/usr/bin/env python3
"""
Name: test_gmail_oauth.py
Version: 1.0.0
Purpose: Test Gmail OAuth token management and refresh logic
Author: Dwain Henderson Jr | Superior Networks LLC
Contact: (937) 985-2480 | dhenderson@superiornetworks.biz
Copyright: 2026, Superior Networks LLC
Location: /root/.openclaw/SNDayton/gmail-trainer/scripts/test_gmail_oauth.py

What This Script Does:
  - Tests Gmail OAuth token loading from config
  - Verifies token refresh mechanism
  - Tests API health check (Gmail API connectivity)
  - Validates OAuth scopes
  - Tests token expiry handling

Input:
  - config/gmail_oauth_credentials.json (OAuth credentials)
  - data/gmail_tokens.json (access/refresh tokens)

Output:
  - Console output confirming token status
  - Refreshed tokens saved back to file (if expired)

Dependencies:
  - google-auth-oauthlib
  - google-auth-httplib2
  - google-api-python-client
  - json, os (standard library)

Change Log:
  2026-03-17 v1.0.0 - Initial release (Dwain Henderson Jr)
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("❌ Google auth libraries not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# Paths
CONFIG_DIR = Path(__file__).parent.parent / 'config'
DATA_DIR = Path(__file__).parent.parent / 'data'
CREDENTIALS_FILE = CONFIG_DIR / 'gmail_oauth_credentials.json'
TOKENS_FILE = DATA_DIR / 'gmail_tokens.json'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

class GmailOAuthTester:
    """Test Gmail OAuth token management."""
    
    def __init__(self):
        self.creds = None
        self.service = None
    
    def load_tokens(self):
        """Load OAuth tokens from file."""
        if not TOKENS_FILE.exists():
            print(f"⚠️  Token file not found: {TOKENS_FILE}")
            print("   Run dashboard/app.py to authenticate")
            return False
        
        try:
            with open(TOKENS_FILE, 'r') as f:
                token_data = json.load(f)
            
            self.creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            print(f"✅ Loaded tokens from {TOKENS_FILE}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load tokens: {e}")
            return False
    
    def refresh_tokens(self):
        """Refresh OAuth tokens if expired."""
        if not self.creds:
            print("❌ No credentials loaded")
            return False
        
        if not self.creds.expired:
            print("✅ Token is still valid (not expired)")
            return True
        
        try:
            request = Request()
            self.creds.refresh(request)
            print("✅ Token refreshed successfully")
            
            # Save refreshed token back to file
            self._save_tokens()
            return True
            
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            return False
    
    def _save_tokens(self):
        """Save tokens to file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        token_data = {
            'token': self.creds.token,
            'refresh_token': self.creds.refresh_token,
            'token_uri': self.creds.token_uri,
            'client_id': self.creds.client_id,
            'client_secret': self.creds.client_secret,
            'scopes': self.creds.scopes
        }
        
        with open(TOKENS_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✅ Tokens saved to {TOKENS_FILE}")
    
    def test_api_health(self):
        """Test Gmail API connectivity."""
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            
            # Simple API call to test connectivity
            profile = self.service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'Unknown')
            
            print(f"✅ Gmail API health check passed")
            print(f"   Email: {email}")
            print(f"   Messages in inbox: {profile.get('messagesTotal', '0')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Gmail API health check failed: {e}")
            return False
    
    def test_scopes(self):
        """Verify OAuth scopes."""
        if not self.creds or not self.creds.scopes:
            print("❌ No scopes found in credentials")
            return False
        
        required_scopes = set(SCOPES)
        granted_scopes = set(self.creds.scopes)
        
        missing = required_scopes - granted_scopes
        
        if missing:
            print(f"⚠️  Missing scopes: {missing}")
            return False
        
        print(f"✅ All required scopes granted:")
        for scope in SCOPES:
            print(f"   ✅ {scope}")
        
        return True
    
    def run_tests(self):
        """Run all tests."""
        print("\n" + "="*70)
        print("GMAIL OAUTH TOKEN TESTING")
        print("="*70 + "\n")
        
        print("1️⃣  Loading OAuth tokens...")
        if not self.load_tokens():
            print("\n❌ Cannot proceed without tokens")
            return False
        
        print("\n2️⃣  Checking token expiry...")
        if not self.refresh_tokens():
            print("⚠️  Token refresh failed, but proceeding anyway...")
        
        print("\n3️⃣  Testing Gmail API connectivity...")
        if not self.test_api_health():
            print("\n❌ Gmail API not accessible")
            return False
        
        print("\n4️⃣  Verifying OAuth scopes...")
        if not self.test_scopes():
            print("⚠️  Some scopes missing")
        
        print("\n" + "="*70)
        print("✅ GMAIL OAUTH TESTING COMPLETE")
        print("="*70 + "\n")
        
        return True

if __name__ == '__main__':
    tester = GmailOAuthTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)
