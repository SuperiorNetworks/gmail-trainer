# Setup Guide — Gmail Trainer

## Prerequisites

- Python 3.9 or higher
- `pip` (Python package manager)
- Google account with Gmail
- Google Cloud project with Gmail API enabled
- OpenClaw running on `localhost:3000` (for AI Chat feature)

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/dwain-henderson/gmail-trainer.git
cd gmail-trainer
```

---

## Step 2 — Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows
```

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Configure OAuth Credentials

### 4a. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable the **Gmail API** for your project
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth 2.0 Client ID**
6. Application type: **Desktop app**
7. Download the JSON file

### 4b. Place Credentials File

```bash
cp /path/to/downloaded-credentials.json config/gmail_oauth_credentials.json
```

The file should look like:
```json
{
  "installed": {
    "client_id": "...",
    "client_secret": "...",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
  }
}
```

### 4c. Run OAuth Setup

```bash
python3 scripts/test_gmail_oauth.py
```

This opens a browser for Google login. After authorizing, it saves tokens to `data/gmail_tokens.json`.

---

## Step 5 — Initialize Database

```bash
python3 scripts/init_db.py
```

This creates `data/email_rules.db` with all required tables and indexes.

---

## Step 6 — Start the Flask Server

```bash
python3 dashboard/app.py
```

You should see:
```
INFO - ✅ All startup checks passed
INFO - 🚀 Starting Gmail Trainer Flask app...
INFO - Access Gmail client at: http://localhost:5000/gmail
```

---

## Step 7 — Open Gmail Trainer

Open your browser and navigate to:
```
http://localhost:5000/gmail
```

---

## Optional: Background Automation

To run the background email automation job separately:

```bash
python3 scripts/email_automation.py
```

Or it runs automatically when Flask starts (via APScheduler, every 5 minutes).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Token file not found` | Run `scripts/test_gmail_oauth.py` to authenticate |
| `Database not found` | Run `scripts/init_db.py` |
| `401 Unauthorized` | Token expired — re-run `test_gmail_oauth.py` |
| `Failed to load emails` | Check Gmail API is enabled in Google Cloud Console |
| Chat not working | Ensure OpenClaw is running on `localhost:3000` |

---

## Directory Structure After Setup

```
gmail-trainer/
├── config/
│   └── gmail_oauth_credentials.json   ← your credentials (git-ignored)
└── data/
    ├── email_rules.db                 ← SQLite database (git-ignored)
    └── gmail_tokens.json              ← OAuth tokens (git-ignored)
```

> ⚠️ **Never commit** `config/gmail_oauth_credentials.json` or `data/gmail_tokens.json` — they contain sensitive credentials.
