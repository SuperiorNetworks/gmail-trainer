# Changelog — Gmail Trainer

All notable changes are documented here.

---

## [v0.1.0] — 2026-03-24 (MVP Release)

### Summary
First complete release. Built over 7 days (March 17–24, 2026).

### Features

**Day 1 — Database + OAuth (2026-03-17)**
- SQLite schema with 7 tables (email_rules, email_audit_log, email_cache, system_state, user_preferences, email_exceptions, rule_templates)
- WAL mode + foreign keys enabled
- Indexes for search performance
- Gmail OAuth 2.0 setup script (`test_gmail_oauth.py`)
- Token management with auto-refresh

**Day 2 — Gmail API + Background Job (2026-03-17)**
- Gmail API integration (messages list, get, labels)
- MIME message decoder (HTML + plaintext)
- Email cache (SQLite + in-memory)
- Watermark tracking for incremental processing
- Background automation job (APScheduler, 5-min polling)
- Rule evaluation engine (sender + subject + condition matching)

**Day 3 — Gmail UI Three-Panel Layout (2026-03-17)**
- Flask app with Blueprint architecture
- Three-panel desktop layout (20% list / 80% reader)
- Alpine.js state management
- Email list with loading skeleton
- Email reader with iframe body rendering (XSS-safe)
- Folder selector (Inbox / Sent / Draft)
- Client-side search filtering
- Pagination with Load More
- Keyboard shortcuts (j/k/e/c/ESC)
- Mobile tab layout (List / Reader / Chat)
- Toast notifications
- Archive action

**Day 4 — Training Modal Q0-Q5 (2026-03-17)**
- Conversational training flow (6 steps)
- Pre-fills sender from selected email
- Primary action selector (6 options)
- Conditional branching (Q2-Q4 path)
- Rule review screen (Q5)
- POST to `/api/rules/create` with full payload
- Rules saved as `pending` status
- Progress indicator dots

**Day 5 — Compose / Reply / Forward (2026-03-17)**
- Compose modal with To, Cc, Subject, Body fields
- Reply pre-fills sender + "Re: " subject
- Forward pre-fills "Fwd: " subject + appends original body
- Gmail threading preserved (In-Reply-To, References headers)
- Send button disabled during send
- Dirty-check confirmation on discard
- Success toast with message ID

**Day 6 — AI Chat Panel (2026-03-17)**
- Chat panel (20% width, hidden by default)
- Opens via "Chat" button in reader
- Full message history with user/AI bubbles
- Timestamps on all messages
- Copy-to-clipboard button per message
- Loading spinner while AI responds
- AI suggestion buttons (click to send)
- Auto-scroll to latest message
- Clears when selecting a new email
- Error handling with dismissible alert + fallback bubble
- `/api/chat` proxy endpoint in Flask (→ OpenClaw port 3000)
- Graceful fallback when OpenClaw is offline
- Mobile chat tab fully wired up

**Day 7 — Documentation + Polish (2026-03-24)**
- README.md with full project overview
- SETUP.md with step-by-step setup
- API_REFERENCE.md with all endpoints
- ARCHITECTURE.md with system diagram and design decisions
- CHANGELOG.md (this file)
- Fixed `/api/gmail/messages` response schema (added `id`, `snippet`, `nextPageToken`)
- Added `requests` to requirements.txt
- Improved iframe rendering with auto-height resize
- Training modal progress dots
- "No, just X it" label in Q2
- Unified toast system (success + error types)
- Guard: shortcuts disabled when typing in inputs
- Keyboard shortcut for ESC closes modals correctly

### Known Limitations (Phase 2)

- Plaintext compose only (no rich text / HTML editor)
- No email attachments support
- No email threading view (flat list only)
- No drafts management
- No rule audit dashboard UI
- ConnectWise ticket creation is a stub (action type exists, not implemented)
- QuickBooks integration not started
- No bulk email actions
- CORS allows all origins (development setup)

### Dependencies

```
Flask==2.3.0
Flask-CORS==4.0.0
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.2.0
google-api-python-client==2.90.0
APScheduler==3.10.0
python-dotenv==1.0.0
requests>=2.28.0
```

### Git Commits

```
eda7abe  Day 1: Database schema + Gmail OAuth
52e85cd  Day 2: Gmail API integration + Background automation job
a9a5acb  Day 3: Gmail client UI with three-panel layout
ae1ab97  Day 4: Training modal with Q0-Q5 conversational flow
874af9a  Day 5: Compose, Reply, Forward (Plaintext Email Sending)
[next]   v0.1.0: Gmail Trainer MVP complete
```

---

## [Unreleased — Phase 2]

Planned features:
- HTML compose (TipTap or Quill editor)
- Attachment support (upload + download)
- Threaded email view
- Rule audit dashboard (match history, accuracy %)
- ConnectWise ticket creation (live)
- QuickBooks invoice detection
- Bulk actions (archive/label multiple)
- Rule import/export (JSON)
- Dark mode
