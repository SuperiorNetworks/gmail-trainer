# Architecture — Gmail Trainer

## Overview

Gmail Trainer is a single-server Flask application that proxies Gmail API calls, manages automation rules in SQLite, and serves an Alpine.js frontend.

---

## System Diagram

```
┌────────────────────────────────────────────────────────────┐
│                     Browser Client                         │
│                                                            │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │  Email List │  │  Email Reader    │  │  AI Chat    │  │
│  │  Panel      │  │  + Header        │  │  Panel      │  │
│  │  (20%)      │  │  + Body (iframe) │  │  (20%)      │  │
│  │             │  │  + Actions       │  │             │  │
│  │  Alpine.js  │  │  Alpine.js       │  │  Alpine.js  │  │
│  └─────────────┘  └──────────────────┘  └─────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Modals: Training (Q0-Q5) | Compose/Reply/Forward   │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────┬───────────────────────────────┘
                             │ HTTP REST
                             ▼
┌────────────────────────────────────────────────────────────┐
│                Flask Backend (port 5000)                   │
│                                                            │
│  Routes:                                                   │
│    /gmail              → serves gmail_client.html          │
│    /api/gmail/*        → gmail.py blueprint                │
│    /api/rules/*        → rules.py blueprint                │
│    /api/chat           → OpenClaw proxy                    │
│    /api/health         → health check                      │
└──────────┬─────────────────────┬──────────────────────────┘
           │                     │
           ▼                     ▼
  ┌─────────────────┐   ┌─────────────────┐
  │  Google Gmail   │   │   SQLite DB     │
  │  API v1         │   │  email_rules.db │
  │  (OAuth 2.0)    │   │                 │
  └─────────────────┘   └─────────────────┘
                                 │
                         ┌───────▼────────┐
                         │  APScheduler   │
                         │  (every 5 min) │
                         │  email_auto-   │
                         │  mation.py     │
                         └───────────────┘
```

---

## Three-Panel Layout

| Panel | Width (desktop) | Content |
|---|---|---|
| Email List | 20% always | Search, folder select, paginated list |
| Email Reader | 80% (chat closed) / 40% (chat open) | Header, action buttons, iframe body |
| AI Chat | 0% (hidden) / 20% (open) | Context, message history, input |

Mobile uses a tab-based layout (List / Reader / Chat) with one panel visible at a time.

The grid switches using CSS `grid-template-columns` with a 300ms transition driven by Alpine.js `:style` binding.

---

## Email Caching Strategy

1. **List endpoint** (`GET /api/gmail/messages`) fetches metadata only (fast, no body)
2. **Select email** → checks `emailCache` (JS Map in Alpine state)
3. If not cached → `GET /api/gmail/messages/<id>` fetches full body
4. Full body stored in `emailCache[id]` (in-memory) AND `email_cache` SQLite table
5. Re-selecting same email = instant (memory cache hit)
6. Re-loading page = SQLite cache hit (no Gmail API call)

This avoids redundant API calls and stays well within Gmail API quotas.

---

## Training Modal (Q0–Q5)

The conversational training flow converts natural-language answers into structured rules:

```
Q0: Which emails?          → sender_pattern, subject_keywords
Q1: What do you do?        → primary_action, folder_target / forward_to / ticket_board
Q2: Different sometimes?   → hasCondition (Yes → Q3, No → skip to Q5)
Q3: What keywords?         → conditionKeywords
Q4: Then what?             → exception_action
Q5: Review & confirm       → POST /api/rules/create (status: "pending")
```

Rules start as **pending** and must be manually activated. This prevents untested rules from running immediately.

---

## Background Automation

`email_automation.py` runs via APScheduler (every 5 minutes):

1. Load all `active` rules from database
2. Fetch new emails since last watermark (`system_state.last_processed_message_id`)
3. For each email, evaluate rules in priority order:
   - Match `sender_pattern` (substring/regex)
   - Match `subject_keywords` (comma-separated, any match)
   - Evaluate `condition_logic` (keyword_match on body)
4. Apply matched action: file, archive, delete, forward, ticket
5. Log to `email_audit_log`
6. Update watermark to latest processed message ID

---

## Rule Evaluation Logic

```
For each new email:
  For each active rule (ordered by priority ASC):
    if sender_pattern matches email.from:
      if subject_keywords match email.subject (optional):
        if condition_logic matches email.body:
          apply exception_action
        else:
          apply primary_action
        log to audit_log
        break (first matching rule wins)
```

---

## Database Schema (7 Tables)

### `email_rules`
Core automation rules.

| Column | Type | Description |
|---|---|---|
| `rule_id` | INTEGER PK | Auto-increment |
| `name` | TEXT UNIQUE | Human-readable name |
| `sender_pattern` | TEXT | Sender match string |
| `subject_keywords` | TEXT | Comma-separated keywords |
| `condition_logic` | JSON | Conditional branching logic |
| `primary_action` | TEXT | Default action |
| `exception_action` | TEXT | Action when condition matches |
| `folder_target` | TEXT | Gmail label for "file" action |
| `forward_to` | TEXT | Email for "forward" action |
| `ticket_board` | INTEGER | CW board ID for "ticket" action |
| `priority` | INTEGER | Evaluation order (lower = first) |
| `status` | TEXT | `pending`, `active`, `archived` |

### `email_audit_log`
Every rule application is logged here.

### `email_cache`
Cached email bodies and metadata for fast retrieval.

### `system_state`
Key-value store for watermark and config.

### `user_preferences`
Persistent UI preferences.

### `email_exceptions`
User feedback on incorrect rule matches.

### `rule_templates`
Pre-built rule templates (Phase 2).

---

## Security

- **Email iframe:** uses `sandbox="allow-same-origin"` to block scripts/forms
- **OAuth tokens:** stored in `data/` (git-ignored), never in code
- **No sensitive data in logs:** token values masked, email bodies not logged
- **CORS:** enabled for all origins (dev setup; lock down in production)
- **SQL injection:** all queries use parameterized statements
