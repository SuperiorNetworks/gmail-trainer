# API Reference — Gmail Trainer

Base URL: `http://localhost:5000`

All endpoints return JSON. Error responses include `{ "error": "..." }`.

---

## Health Check

### `GET /api/health`

Returns server health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-17T10:00:00",
  "database": { "status": "connected", "rules_count": 5 },
  "gmail_api": { "status": "not_tested_yet" },
  "tokens": { "status": "available", "has_refresh_token": true }
}
```

---

## Gmail Endpoints

### `GET /api/gmail/messages`

List emails from a folder.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `limit` | int | 20 | Number of emails to return |
| `folder` | string | `INBOX` | Gmail label (INBOX, SENT, DRAFT) |
| `pageToken` | string | — | Pagination token from previous response |

**Response:**
```json
{
  "messages": [
    {
      "id": "18db2a3f...",
      "from": "sender@example.com",
      "to": "me@example.com",
      "subject": "Weekly Report",
      "date": "Mon, 17 Mar 2026 08:00:00 -0500",
      "snippet": "Here is this week's status...",
      "labels": ["INBOX", "UNREAD"]
    }
  ],
  "count": 20,
  "nextPageToken": "abc123..."
}
```

---

### `GET /api/gmail/messages/<message_id>`

Get full email body by message ID.

**Response:**
```json
{
  "message_id": "18db2a3f...",
  "from": "sender@example.com",
  "to": "me@example.com",
  "subject": "Weekly Report",
  "date": "Mon, 17 Mar 2026 08:00:00 -0500",
  "body_html": "<html>...</html>",
  "body_plain": "Here is this week's status...",
  "labels": ["INBOX"],
  "source": "cache"
}
```

`source` is `"cache"` (fast) or `"gmail_api"` (first fetch).

---

### `GET /api/gmail/labels`

List all Gmail labels/folders.

**Response:**
```json
{
  "labels": [
    { "id": "INBOX", "name": "INBOX" },
    { "id": "Label_123", "name": "Reports" }
  ],
  "count": 12
}
```

---

### `POST /api/gmail/messages/send`

Send a new email.

**Request:**
```json
{
  "to": "recipient@example.com",
  "cc": "cc@example.com",
  "subject": "Hello",
  "body_plain": "Message body here."
}
```

**Response:**
```json
{
  "message_id": "18db2a3f...",
  "status": "sent"
}
```

---

### `POST /api/gmail/messages/<message_id>/reply`

Reply to an email (preserves Gmail threading).

**Request:**
```json
{
  "to": "sender@example.com",
  "subject": "Re: Original Subject",
  "body_plain": "My reply text.",
  "cc": null
}
```

**Response:** Same as send.

---

### `POST /api/gmail/messages/<message_id>/forward`

Forward an email. The original message is appended automatically.

**Request:**
```json
{
  "to": "colleague@example.com",
  "cc": null,
  "body_plain": "FYI - see below."
}
```

**Response:** Same as send.

---

### `POST /api/gmail/messages/<message_id>/archive`

Remove an email from the inbox (remove INBOX label).

**Response:**
```json
{
  "message_id": "18db2a3f...",
  "status": "archived"
}
```

---

## Chat Endpoint

### `POST /api/chat`

Proxy AI chat messages to OpenClaw (port 3000).

**Request:**
```json
{
  "message": "Why was this email filed as urgent?",
  "context": {
    "email_id": "18db2a3f...",
    "from": "sender@example.com",
    "subject": "CRITICAL: Server Down",
    "body": "The production server is down..."
  }
}
```

**Response:**
```json
{
  "response": "This email was flagged as urgent because it contains the word CRITICAL in the subject line...",
  "confidence": 0.95,
  "suggestions": [
    "Create a rule for this sender",
    "Archive this conversation"
  ]
}
```

If OpenClaw is not running, returns a graceful fallback message (HTTP 200).

---

## Rules Endpoints

### `POST /api/rules/create`

Create a new automation rule.

**Request:**
```json
{
  "name": "reports@positive-electric.com → file",
  "sender_pattern": "reports@positive-electric.com",
  "subject_keywords": "report, status",
  "primary_action": "file",
  "folder_target": "Reports",
  "forward_to": null,
  "ticket_board": null,
  "exception_action": "ticket",
  "condition_logic": {
    "type": "keyword_match",
    "field": "body",
    "keywords": ["ERROR", "FAILED"],
    "match": "any",
    "case_sensitive": false
  },
  "status": "pending"
}
```

**Actions:** `file` | `archive` | `delete` | `forward` | `ticket` | `do_nothing`

**Response (201):**
```json
{
  "rule_id": 7,
  "name": "reports@positive-electric.com → file",
  "status": "pending"
}
```

---

### `GET /api/rules/list`

Get all rules (optionally filtered by status).

**Query Parameters:**

| Param | Values | Description |
|---|---|---|
| `status` | `active`, `pending`, `archived` | Filter by status (optional) |

**Response:**
```json
{
  "rules": [
    {
      "rule_id": 7,
      "name": "reports → file",
      "sender_pattern": "reports@positive-electric.com",
      "subject_keywords": "report",
      "primary_action": "file",
      "status": "pending",
      "created_date": "2026-03-17T10:00:00",
      "last_modified": "2026-03-17T10:00:00"
    }
  ],
  "count": 1
}
```

---

### `GET /api/rules/<rule_id>`

Get full details of a specific rule.

**Response:** Full rule object including `condition_logic`, `folder_target`, `forward_to`, `ticket_board`, `exception_action`, `priority`.

---

### `PATCH /api/rules/<rule_id>/activate`

Activate a pending rule (sets status to `active`).

**Response:**
```json
{
  "rule_id": 7,
  "status": "active"
}
```

---

### `DELETE /api/rules/<rule_id>`

Soft-delete a rule (sets status to `archived`).

**Response:**
```json
{
  "rule_id": 7,
  "status": "archived"
}
```

---

## Error Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (missing/invalid fields) |
| 401 | Unauthorized (OAuth token expired) |
| 404 | Not found |
| 500 | Server error |
| 502 | Bad gateway (AI backend error) |
| 503 | Service degraded (health check) |
| 504 | Gateway timeout (AI backend) |
