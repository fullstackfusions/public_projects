# Troubleshooting: Notifications Not Arriving

You configured Mailpit (email), WAHA (WhatsApp), and ntfy (push) but nothing is showing up. This doc is an investigation playbook — work top-down and stop when you find the cause.

> **Heads-up on terminology**: in this stack, what's labelled "SMS" is actually **ntfy push notifications** to the ntfy mobile app. There is no real SMS adapter (no Twilio, no carrier integration). If you need true SMS, that's a missing adapter, not a misconfiguration.

---

## 1. TL;DR — five fastest checks

1. `docker-compose ps` — all of `notification-backend`, `mailpit`, `ntfy`, `waha`, `postgres`, `redis` must be `Up (healthy)`.
2. `curl http://localhost:8008/ready` — must return 200. If 503, DB or Redis is the blocker.
3. Did the caller create user preferences first? Without a row in `user_preferences` with `enabled_channels` populated AND the matching recipient field (`email` / `phone` / `ntfy_topic`), `POST /notify/template` returns `200 OK` with `{"results": []}`. **Silent.**
4. WhatsApp: open `http://localhost:3000` (admin / localdev-admin), confirm session `default` status is `WORKING` (QR scanned).
5. ntfy: phone app installed AND subscribed to the **exact** topic string stored in `user_preferences.ntfy_topic`, using your Mac's LAN IP (not `localhost`).

---

## 2. Architecture refresher

```
producer (e.g. tax-py)
    │  POST /notify/template  +  Bearer JWT
    ▼
notification-backend (:8008)
    │  loads user_preferences from Postgres
    │  fans out per enabled_channels
    ▼
┌─────────────┬───────────────┬──────────────┐
│ EmailAdapter│ WhatsAppAdapter│ PushAdapter │
│  → mailpit  │   → waha:3000  │  → ntfy:80  │
│   :1025 SMTP│   /api/sendText│  POST /topic│
└─────────────┴───────────────┴──────────────┘
```

Key files:
- [backends/notification-py/app/services/dispatcher.py](../backends/notification-py/app/services/dispatcher.py) — fan-out, dedup via `notification_log`, retry, DLQ to Redis list `notification:dlq` (DB 2).
- [backends/notification-py/app/domain/adapters/email.py](../backends/notification-py/app/domain/adapters/email.py) — aiosmtplib.
- [backends/notification-py/app/domain/adapters/whatsapp.py](../backends/notification-py/app/domain/adapters/whatsapp.py) — WAHA `/api/sendText`.
- [backends/notification-py/app/domain/adapters/push.py](../backends/notification-py/app/domain/adapters/push.py) — ntfy `POST /{topic}`.
- [backends/notification-py/app/routers/notify.py](../backends/notification-py/app/routers/notify.py), [backends/notification-py/app/routers/preferences.py](../backends/notification-py/app/routers/preferences.py).
- [backends/tax-py/app/services/notifications.py](../backends/tax-py/app/services/notifications.py) — producer side.
- [docker-compose.yml](../docker-compose.yml) — env vars and ports.

---

## 3. Silent-failure decision tree

Run through these in order.

### 3.1 Are there any logs in `notification-backend` at all when you expect a notification?

```bash
docker-compose logs --tail=200 notification-backend
```

**No relevant log line → the producer never called us.** Check:

- `docker-compose exec tax-backend env | grep NOTIFICATION_API_URL` — must be `http://notification-backend:8008`.
- [backends/tax-py/app/services/notifications.py](../backends/tax-py/app/services/notifications.py) silently returns if that env var is unset. There will be **no error** in tax-py logs.
- Verify the trigger that's supposed to fire `notify_filing_deadlines(...)` actually runs. Search call sites in `backends/tax-py/`.

If logs **do** appear, continue.

### 3.2 Does the response have an empty `results` array?

```json
{ "results": [] }
```

This means the dispatcher loaded preferences and found `enabled_channels` empty (or no row at all).

```bash
TOKEN=...  # see §6 for how to get one
curl -H "Authorization: Bearer $TOKEN" http://localhost:8008/preferences/me
```

- 404 / empty / `enabled_channels: []` → caller must `PUT /preferences/me` first.
- Otherwise → check §3.3.

### 3.3 Does `results` contain `status: "skipped"` with `error: "No recipient address"`?

Channel is enabled but the matching field is NULL:

| channel    | required field in `user_preferences` |
| ---------- | ------------------------------------ |
| `email`    | `email`                              |
| `push`     | `ntfy_topic`                         |
| `whatsapp` | `phone` (E.164, e.g. `+14155552671`) |

Fix via `PUT /preferences/me` (§6).

### 3.4 Does `results` contain `status: "failed"`?

Read the `error` field. Then jump to the matching per-channel section in §4.

Cross-reference the audit log:

```bash
docker-compose exec postgres psql -U scheduler -d notification_db -c \
  "SELECT created_at, channel, status, error FROM notification_log ORDER BY created_at DESC LIMIT 20;"
```

### 3.5 `results` says `"sent"` but the message never arrives

The adapter got a 2xx but downstream delivery didn't happen. Go to §4 for that channel.

---

## 4. Per-channel deep dives

### 4.1 Email (Mailpit)

Mailpit is a **catcher** — it accepts every email and shows it in a UI. Nothing leaves your machine.

- Open `http://localhost:8025`. Every successfully-sent email appears here regardless of `to:` address.
- Empty? SMTP failed. Look for `SMTP send failed` in `notification-backend` logs.
- Env to verify:
  - `SMTP_HOST=mailpit` (container name, **not** `localhost`).
  - `SMTP_PORT=1025`.
  - `SMTP_FROM=noreply@taxapp.local` (any value works for Mailpit).
  - Leave `SMTP_USERNAME` / `SMTP_PASSWORD` unset — Mailpit needs no auth.
- Direct test from inside the backend container:
  ```bash
  docker-compose exec notification-backend python - <<'PY'
  import asyncio, aiosmtplib
  from email.message import EmailMessage
  async def main():
      m = EmailMessage()
      m["From"] = "noreply@taxapp.local"
      m["To"] = "you@example.com"
      m["Subject"] = "direct smtp test"
      m.set_content("hello from notification-backend container")
      await aiosmtplib.send(m, hostname="mailpit", port=1025)
      print("ok")
  asyncio.run(main())
  PY
  ```

### 4.2 WhatsApp (WAHA)

Most failures live here.

**Step 1 — Session must be WORKING**

```bash
curl -H "X-Api-Key: localdev-waha-api-key" http://localhost:3000/api/sessions
```

Look for `"status": "WORKING"`. Anything else (`SCAN_QR_CODE`, `STARTING`, `STOPPED`, `FAILED`) means it cannot send.

**Step 2 — Scan the QR code**

1. Open `http://localhost:3000`.
2. Log in with `admin` / `localdev-admin` (set in [docker-compose.yml](../docker-compose.yml)).
3. Find session `default`. If stopped, click Start.
4. On your phone: WhatsApp → Settings → Linked Devices → Link a Device → scan the QR on the dashboard.
5. Session is persisted in the `waha_sessions` Docker volume — survives restarts.

**Step 3 — API key parity**

The adapter sends `X-Api-Key: <WAHA_API_KEY>`. Both sides must match:

- `notification-backend` env: `WAHA_API_KEY=localdev-waha-api-key`.
- `waha` container env: `WAHA_API_KEY=localdev-waha-api-key`.

Don't confuse this with `WAHA_DASHBOARD_PASSWORD` — that's only the web UI login.

**Step 4 — Phone format**

E.164, leading `+`, no spaces or dashes: `+14155552671`. The adapter strips the `+` and posts to `{digits}@c.us`.

**Step 5 — Recipient must be on WhatsApp**

WAHA cannot message a number that has no WhatsApp account. First test by sending to your own number.

**Step 6 — Engine**

Compose uses `WHATSAPP_DEFAULT_ENGINE=NOWEB`. If you see persistent odd errors, try switching to `WEBJS` (heavier, uses Chromium, but sometimes more compatible). Restart the `waha` container after changing.

**Step 7 — Apple Silicon**

`platform: linux/amd64` is pinned. You need Rosetta 2:
```bash
softwareupdate --install-rosetta --agree-to-license
```
Without it the container will crash on startup. Check with `docker-compose logs waha`.

**Common WAHA errors**

| HTTP from WAHA | Likely cause                                                  |
| -------------- | ------------------------------------------------------------- |
| 401            | `X-Api-Key` mismatch (or missing) between adapter and WAHA    |
| 400            | Session not WORKING, or `chatId` malformed                    |
| 404            | `WAHA_SESSION=default` doesn't match an existing session name |
| 5xx            | WAHA internal — check `docker-compose logs waha`              |

**Direct WAHA test** (bypasses notification-backend entirely):

```bash
curl -X POST http://localhost:3000/api/sendText \
  -H "X-Api-Key: localdev-waha-api-key" \
  -H "Content-Type: application/json" \
  -d '{"session":"default","chatId":"14155552671@c.us","text":"direct test"}'
```

If this fails, the problem is WAHA, not notification-backend.

### 4.3 Push (ntfy) — not SMS

**Reminder**: this is push to the ntfy mobile app, **not** SMS. No carrier is involved.

**Step 1 — Install the ntfy app**

iOS or Android, from your respective app store. Or test in browser at `http://localhost:8088`.

**Step 2 — Point the app at your server**

The app's default server is `ntfy.sh`. You must change it to your machine's LAN IP, e.g. `http://192.168.1.42:8088`. **`localhost` won't work** — the phone isn't on the same network namespace as your Mac.

Find your LAN IP:
```bash
ipconfig getifaddr en0
```

**Step 3 — Subscribe to the exact topic**

The dispatcher POSTs to `http://ntfy/{user_preferences.ntfy_topic}`. The mobile app must be subscribed to that **exact** topic string. Topic names are case-sensitive and have no namespacing — pick something hard to guess in production.

**Step 4 — Direct test**

From your Mac:
```bash
curl -d "hello from curl" http://localhost:8088/my_test_topic
```

Subscribe `my_test_topic` in the app first. If this works but app messages from notification-backend don't, the topic strings don't match.

**Step 5 — Access control**

Current compose does **not** set `NTFY_AUTH_DEFAULT_ACCESS`. Default is open. If you added auth config, watch for `permission denied` in `docker-compose logs ntfy`.

**Step 6 — App-side delivery**

If ntfy server returns 200 but your phone is silent:

- ntfy app must be running in the background with notifications enabled in iOS/Android settings.
- iOS: ntfy must have `instant delivery` enabled (paid feature on iOS) **or** you must be on the same Wi-Fi as your Mac for the local server to deliver.
- Battery optimization on Android can suspend the app — exempt it.

---

## 5. Observability

### App logs

```bash
docker-compose logs -f notification-backend
```

Grep for:
- `notification_sent` — success.
- `notification_failed` — adapter error (has `channel`, `error`).
- `notification_skipped` — dedup or missing recipient.
- `SMTP send failed` / `WAHA send failed` / `ntfy send failed` — adapter exceptions.

### Audit log table

```bash
docker-compose exec postgres psql -U scheduler -d notification_db
```

```sql
-- Recent failures
SELECT created_at, user_id, channel, status, error
FROM notification_log
WHERE status = 'failed' AND created_at > now() - interval '1 hour'
ORDER BY created_at DESC;

-- All attempts for a user
SELECT created_at, channel, status, external_id, error
FROM notification_log
WHERE user_id = 'demo'
ORDER BY created_at DESC LIMIT 50;

-- Dedup verification (should be 1 row per attempt)
SELECT COUNT(*) FROM notification_log
WHERE user_id = 'demo' AND dedup_key = 'tax_deadline_demo_T2_2025_30';
```

### Redis DLQ

Failed-after-retry payloads land in Redis DB **2**, list `notification:dlq`. There is **no consumer** — manual inspection only.

```bash
docker-compose exec redis redis-cli -n 2 LLEN notification:dlq
docker-compose exec redis redis-cli -n 2 LRANGE notification:dlq 0 -1
```

### Per-adapter dashboards

- Mailpit UI: `http://localhost:8025`
- WAHA dashboard: `http://localhost:3000` (admin / localdev-admin)
- ntfy server health: `curl http://localhost:8088/v1/health`
- ntfy logs: `docker-compose logs --tail=200 ntfy`

---

## 6. End-to-end smoke test

Copy-paste this as a single block when you come back to debug.

```bash
# 1. Get a JWT
TOKEN=$(curl -s -X POST http://localhost:8005/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=demo&password=demo123' | jq -r .access_token)
echo "TOKEN=$TOKEN"

# 2. Set preferences (replace email/phone/topic with yours)
curl -X PUT http://localhost:8008/preferences/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "phone": "+14155552671",
    "ntfy_topic": "tax_reminders_demo",
    "enabled_channels": ["email", "push", "whatsapp"]
  }'

# 3. Verify the row
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8008/preferences/me | jq .

# 4. Fire a template notification
curl -X POST http://localhost:8008/notify/template \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"demo\",
    \"template_id\": \"tax_deadline\",
    \"dedup_key\": \"smoke-$(date +%s)\",
    \"context\": {
      \"corp_name\": \"Acme Corp\",
      \"filing_type\": \"T2\",
      \"period_label\": \"FY2025\",
      \"due_date\": \"2026-06-30\",
      \"days_before\": 30
    }
  }" | jq .

# 5. Inspect audit log
docker-compose exec -T postgres psql -U scheduler -d notification_db -c \
  "SELECT created_at, channel, status, error FROM notification_log ORDER BY created_at DESC LIMIT 5;"
```

Expected response from step 4 — one entry per enabled channel:

```json
{
  "results": [
    { "channel": "email",    "status": "sent", "external_id": "<...>", "error": null },
    { "channel": "push",     "status": "sent", "external_id": "<...>", "error": null },
    { "channel": "whatsapp", "status": "sent", "external_id": "<...>", "error": null }
  ]
}
```

Then verify the actual delivery in each channel.

---

## 7. Direct adapter tests (isolate the broken layer)

Use these to confirm whether the problem is notification-backend or the downstream service.

**SMTP direct** — see §4.1 inline script.

**WAHA direct**:
```bash
curl -X POST http://localhost:3000/api/sendText \
  -H "X-Api-Key: localdev-waha-api-key" \
  -H "Content-Type: application/json" \
  -d '{"session":"default","chatId":"14155552671@c.us","text":"direct test"}'
```

**ntfy direct**:
```bash
curl -d "direct test" -H "Title: hi" -H "Priority: 3" http://localhost:8088/my_test_topic
```

If a direct test fails, the downstream container is the problem. If a direct test succeeds but the same channel fails through `/notify/template`, the bug is in notification-backend config or preferences.

---

## 8. Known-gotcha quick reference

| #   | Misconfiguration                                             | Symptom                                          | Fix                                                            |
| --- | ------------------------------------------------------------ | ------------------------------------------------ | -------------------------------------------------------------- |
| 1   | `NOTIFICATION_API_URL` unset in `tax-py`                     | No request to notification-backend, no error     | Set env var in `docker-compose.yml` `tax-backend` service      |
| 2   | No `user_preferences` row                                    | `200 OK { results: [] }`                         | `PUT /preferences/me` first                                    |
| 3   | `enabled_channels: []`                                       | `200 OK { results: [] }`                         | Populate `enabled_channels`                                    |
| 4   | Recipient field NULL (e.g. `email` is null, email enabled)   | `status: "skipped"` with `No recipient address`  | Set the field in preferences                                   |
| 5   | `WAHA_API_KEY` mismatch                                      | WAHA returns 401                                 | Match value across both `notification-backend` and `waha`      |
| 6   | WAHA session not scanned                                     | `status != WORKING`, WAHA returns 400            | Scan QR in dashboard                                           |
| 7   | WAHA `chatId` malformed (raw phone, no `@c.us`)              | WAHA 400                                         | Adapter handles this — confirm phone is E.164                  |
| 8   | Apple Silicon, no Rosetta                                    | WAHA container crashes                           | `softwareupdate --install-rosetta`                             |
| 9   | ntfy app pointed at `localhost`                              | Subscribes but nothing arrives                   | Use Mac LAN IP                                                 |
| 10  | ntfy topic in preferences ≠ topic in app                     | Server returns 200, phone silent                 | Match exactly (case-sensitive)                                 |
| 11  | iOS ntfy without instant delivery                            | Messages arrive late or only on Wi-Fi            | Enable instant delivery or accept Wi-Fi limitation             |
| 12  | `SMTP_HOST=localhost` (instead of `mailpit`)                 | SMTP connection refused                          | Use container name `mailpit` inside the compose network        |
| 13  | Non-deterministic `dedup_key` (random UUID each call)        | Notification re-sent every retry                 | Use stable hash, e.g. `tax_deadline_{user}_{filing}_{offset}`  |
| 14  | Stale dedup row from earlier test                            | New attempt skipped due to unique constraint     | Change `dedup_key` or delete row in `notification_log`         |
| 15  | Missing template file under `templates/{id}/{channel}.txt`   | Body falls back to `str(context)` — garbled text | Create the template; check `backends/notification-py/templates/` |

---

## 9. Open production gaps (context, not blockers)

These are known limitations in the current implementation — useful to know when interpreting symptoms:

- **No DLQ consumer.** Failed-after-retry payloads accumulate in `notification:dlq` (Redis DB 2). Nothing replays them. Drain manually for now.
- **No metrics endpoint.** No Prometheus counters for sent/failed/skipped per channel.
- **Silent template fallback.** If the Jinja file is missing, dispatcher uses `str(context)` and logs a warning — recipient gets garbled text instead of an error.
- **No per-adapter rate limiting.** WAHA in particular has rate limits; bulk sends can get the session banned.
- **No backoff on producer side.** `tax-py` calls notification-backend best-effort and swallows HTTP errors.

When you're ready to harden this, those are the five things to tackle.
