# Gmail Trainer

**Gmail Trainer** is a self-hosted email automation tool that lets you teach your inbox rules using a natural, conversational training flow — then automatically applies those rules in the background.

Built for MSPs, power users, and anyone who wants intelligent email triage without giving up control.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📧 Three-panel Gmail UI | Email list, reader, and AI chat — all in one view |
| 🎓 Conversational training | Answer 6 natural-language questions to create automation rules |
| 🤖 AI Chat panel | Ask your AI assistant about any selected email |
| ✉️ Compose / Reply / Forward | Full email compose with threading support |
| ⚙️ Background automation | 5-minute polling applies active rules automatically |
| 📋 Rule management | Create, activate, archive rules with full audit log |
| 📱 Mobile responsive | Tab-based layout for small screens |
| 🔒 OAuth 2.0 | Secure Google authentication with token refresh |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Browser (Alpine.js)                │
│  ┌──────────┐  ┌────────────────┐  ┌─────────────┐ │
│  │ Email    │  │  Email Reader  │  │  AI Chat    │ │
│  │ List     │  │  + Actions     │  │  Panel      │ │
│  │ (20%)    │  │  (40–80%)      │  │  (20%)      │ │
│  └──────────┘  └────────────────┘  └─────────────┘ │
└────────────────────────┬────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────┐
│              Flask Backend (port 5000)              │
│  /api/gmail/*  — Gmail API proxy                    │
│  /api/rules/*  — Rule CRUD                          │
│  /api/chat     — OpenClaw AI proxy                  │
└────────────────────────┬────────────────────────────┘
                         │
        ┌────────────────┼───────────────┐
        ▼                ▼               ▼
  Gmail API         SQLite DB       OpenClaw
  (Google)        email_rules.db   (port 3000)
```

---

## 🚀 Quick Start

See [SETUP.md](SETUP.md) for full setup instructions.

```bash
git clone https://github.com/dwain-henderson/gmail-trainer.git
cd gmail-trainer
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 scripts/init_db.py
# Configure OAuth (see SETUP.md)
python3 dashboard/app.py
# Open http://localhost:5000/gmail
```

---

## 📂 Project Structure

```
gmail-trainer/
├── README.md
├── SETUP.md
├── API_REFERENCE.md
├── ARCHITECTURE.md
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
├── LICENSE
├── dashboard/
│   ├── app.py                  ← Flask app + chat proxy
│   ├── templates/
│   │   └── gmail_client.html   ← Alpine.js frontend
│   └── api/
│       ├── gmail.py            ← Gmail API endpoints
│       └── rules.py            ← Rules CRUD endpoints
├── scripts/
│   ├── init_db.py              ← Database initialization
│   ├── test_gmail_oauth.py     ← OAuth test/setup
│   └── email_automation.py     ← Background automation job
├── config/
│   └── gmail_oauth_credentials.json.example
└── data/                       ← git-ignored
    ├── email_rules.db
    └── gmail_tokens.json
```

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Flask 2.3, Flask-CORS
- **Frontend:** Alpine.js 3.x (CDN), Tailwind CSS (CDN)
- **Database:** SQLite 3 (WAL mode)
- **Email:** Google Gmail API v1 (OAuth 2.0)
- **Automation:** APScheduler 3.10 (5-min polling)
- **AI Chat:** OpenClaw (localhost:3000/chat)

---

## 📖 API Reference

See [API_REFERENCE.md](API_REFERENCE.md) for full endpoint documentation.

---

## 🔑 Training Modal (Q0–Q5)

The training flow converts natural language into automation rules:

| Step | Question | Example Answer |
|---|---|---|
| Q0 | Which emails? | `reports@positive-electric.com` |
| Q1 | What do you do? | `file` → folder: `Reports` |
| Q2 | Different sometimes? | Yes / No |
| Q3 | What's the indicator? | `ERROR, FAILED` |
| Q4 | Then what? | `ticket` (create CW ticket) |
| Q5 | Review & save | ✅ Rule saved as pending |

---

## 🔮 Phase 2 Roadmap

- [ ] HTML compose (rich text editor)
- [ ] Email attachments support
- [ ] Email threading view
- [ ] Drafts management
- [ ] Rule audit dashboard
- [ ] ConnectWise ticket creation
- [ ] QuickBooks invoice detection
- [ ] Bulk email actions
- [ ] Rule import/export

---

## 👤 Author

**Dwain Henderson Jr**  
Superior Networks LLC  
dhenderson@superiornetworks.biz  
(937) 985-2480

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
