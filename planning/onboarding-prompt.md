# Claude Code Onboarding — github_status_bot

You are continuing development on **`github_status_bot`**, a Slack bot that tells engineers whether GitHub or Claude is
currently down by checking their official status APIs. This document is your complete orientation — read it fully before
writing any code.

---

## Getting Started Checklist

- [ ] Read this document top to bottom
- [ ] Read `planning/prd.md` (the authoritative requirements document)
- [ ] Read `planning/tasks.md` to find the current task status
- [ ] Check `git status` and `git log --oneline -10` to orient yourself

---

## Project Overview

**What it is**: A Slack bot that responds when `@github_status_bot` is mentioned in a channel. It fetches the named
service's status API in real time and replies with a clear up/down verdict, affected components, severity, duration, and
source. Supports GitHub and Claude out of the box; adding a new service requires one line in `services.py`.

**What it is NOT**: Does not use Down Detector or any unofficial source. Does not proactively post anything in Phase 1.

**Vision**: Give engineers an instant, authoritative answer to "is [service] actually down?" without leaving Slack — and
(in Phase 2) alert the team proactively when any configured service reports an outage.

**Current status**: Phase 1 complete. Phase 3 (multi-service support) core implemented on branch
`feat/phase3-multi-service`. Phase 2 (proactive alerting) not yet started — do not begin until Phase 1 has been stable
for ≥2 weeks.

---

## Three-Phase Scope

### Phase 1 — On-Demand Bot (complete)

Bot is silent until `@`-mentioned. On mention:

1. Parses service name from mention text (e.g. `github`, `claude`)
2. Fetches `{base_url}/status.json` + `{base_url}/incidents/unresolved.json` concurrently (2s timeout)
3. Fetches `{base_url}/components.json` (optional — failure returns `components=[]`)
4. Replies once in the same channel/thread with verdict + affected components + severity + duration + source

For bare mentions (no service name) or unrecognised service names, defaults to GitHub — the primary use case.

**Requirements**: F1–F5 in `planning/prd.md`. No database. No polling. No scheduled work.

### Phase 3 — Multi-Service Support (core implemented, pending live validation)

Service registry in `services.py` maps short names (`github`, `claude`) to Statuspage.io base URLs and config.
Named mentions (`@bot github`) return full detail for that service. Bare mentions return a compact summary for all
services. Implemented out of order before Phase 2.

**Requirements**: M1–M6 in `planning/prd.md`.

### Phase 2 — Proactive Alerting (do NOT start until Phase 1 stable for ≥2 weeks)

A background `asyncio` task in the same process polls all configured services every `POLL_INTERVAL_MINUTES` (default: 5)
and posts to `ALERT_CHANNEL_ID` when any service transitions between up and down. State persisted in a JSON file on disk.

**Requirements**: P1–P5 in `planning/prd.md`.

---

## Technology Stack

| Layer               | Tool                        | Notes                                               |
|---------------------|-----------------------------|-----------------------------------------------------|
| Language            | Python 3.12                 |                                                     |
| Package manager     | `uv`                        | Fast, deterministic; use instead of pip             |
| Slack framework     | `slack-bolt` (Python)       | Socket mode — outbound WebSocket, no inbound HTTP   |
| HTTP                | `httpx`                     | Async, with timeout + retry config                  |
| Testing             | `pytest` + `pytest-httpx`   | Mock all external HTTP in unit tests                |
| Linting             | `ruff`                      |                                                     |
| Type checking       | `mypy --strict`             |                                                     |
| Hosting             | Long-running local process  | `uv run python -m github_status_bot.slack_handler`  |
| Secrets             | `.env` file on host machine | Never committed; `.env.example` documents variables |
| Observability       | Python `logging` to stdout  | Redirect to file as needed                          |
| Phase 2 persistence | JSON file on disk           | Atomic write; path via `STATE_FILE_PATH` env var    |

---

## Architecture — Phase 1 / Phase 3

```
Slack mention
    → Slack WebSocket (socket mode, outbound connection managed by slack-bolt)
    → local process (slack_handler.py)
        1. Receive app_mention event
        2. Parse service name from event text
        3a. Named service (e.g. "github"): fetch that service's 3 endpoints
        3b. Bare mention: fetch all services concurrently, build compact summary
        4. Compute verdict per service (using ServiceConfig.ignored_components)
        5. POST chat.postMessage
```

**No database. No inbound HTTP. No cloud infrastructure. Stateless except for the idempotency cache.**

### Phase 2 (additive — same process)

```
asyncio.create_task(run_poller(app))  ← started alongside socket-mode handler
    every POLL_INTERVAL_MINUTES:
        1. Fetch all services
        2. Read state file from disk (keyed by service name)
        3. If any service transitioned → post alert/recovery to ALERT_CHANNEL_ID → write new state
        4. If unchanged → no-op
```

---

## Key API Facts

All configured services use the Statuspage.io API shape. Endpoints are derived from a `base_url`:

**`{base_url}/status.json`**
```json
{ "status": { "indicator": "none | minor | major | critical" } }
```
"Down" = indicator is `minor`, `major`, or `critical`.

**`{base_url}/incidents/unresolved.json`**
```json
{ "incidents": [{ "id": "...", "started_at": "...", "resolved_at": null }] }
```
"Down" also triggered by any incident with `resolved_at: null`. Duration from `started_at` — never `created_at`.
If `started_at` is missing, report down without duration.

**`{base_url}/components.json`**
```json
{ "components": [{ "name": "Git Operations", "status": "operational | degraded_performance | partial_outage | major_outage" }] }
```
Non-operational statuses are surfaced as `affected_components`. Some components are ignored per service
(configured in `ServiceConfig.ignored_components` in `services.py`). GitHub ignores: Pages, Webhooks,
Codespaces, Copilot AI Model Providers.

---

## Service Registry

Defined in `src/github_status_bot/services.py`:

```python
SERVICES: dict[str, ServiceConfig] = {
    "github": ServiceConfig(
        display_name="GitHub",
        base_url="https://www.githubstatus.com/api/v2",
        status_page_url="https://www.githubstatus.com",
        ignored_components=frozenset({"Pages", "Webhooks", "Codespaces", "Copilot AI Model Providers"}),
    ),
    "claude": ServiceConfig(
        display_name="Claude",
        base_url="https://status.claude.com/api/v2",
        status_page_url="https://status.claude.com",
    ),
}
```

To add a new service: add one entry here and restart the bot.

---

## Verdict Logic

```
if indicator in {minor, major, critical} OR any incident has resolved_at == null:
    verdict = DOWN
    duration = now - earliest_incident.started_at  (if started_at present)
else:
    verdict = UP
```

The verdict module must have **100% unit test coverage**.

---

## Reply Formats

**Named service — up** (`@bot github`):
```
GitHub appears to be *up*... for NOW.

Source: <https://www.githubstatus.com|GitHub's status page>
```

**Named service — down** (`@bot github`):
```
GitHub is *down* because AI DevOps is a blight on our land.

Affected Area: Git Operations
Severity: Degraded
Time Down: ~2h 12m

Source: <https://www.githubstatus.com|GitHub's status page>
```

`Affected Area` omitted when all components are operational or components endpoint failed.
`Time Down` omitted when no `started_at` is available.
Severity labels: `minor` → `Degraded`, `major` → `Major Outage`, `critical` → `Critical Outage`.

**Bare mention or unknown service** (`@bot` / `@bot jenkins`):

Same as `@bot github` — returns the full GitHub reply. GitHub is the default service.

**API unreachable**:
```
Couldn't check GitHub's status right now — the status API didn't respond. Try again in a moment.
```

---

## Idempotency

The handler deduplicates Slack event retries using the message `ts` field (from the inner event object — slack-bolt
does **not** expose `event_id` in the inner event dict; it lives only in the outer envelope). Each `ts` is recorded in
an in-memory cache (TTL 60s, capacity 100). The same message `ts` seen twice produces only one reply.

There is **no per-channel rate-limit cooldown** — every distinct mention gets a reply regardless of timing. Duplicate
suppression is idempotency-only (same Slack retry), not time-based throttling.

---

## Development Workflow

### Git Rules

- **Base branch is `cs-bot`** — never commit directly to `cs-bot` or `main`
- Every feature or task gets its own branch off `cs-bot`: `feat/tXXX-<short-description>`
- Bug fixes: `fix/tXXX-<short-description>`
- Merge via PR even when working solo — it keeps history clean
- Commit messages: imperative mood, present tense ("add verdict module", not "added" or "adding")

### Branch Naming Examples

```
feat/t013-error-handling
feat/t015-idempotency
feat/t019-integration-tests
feat/phase3-multi-service
feat/t031-poller
```

### Before Every Commit

```bash
/workspace/.venv/bin/ruff check src/ tests/
/workspace/.venv/bin/mypy --strict src/
/workspace/.venv/bin/pytest --cov=src --cov-report=term-missing
```

All three must pass. Fix failures before committing — do not use `--no-verify`.

### Testing Standards

- Unit tests mock all external HTTP (`pytest-httpx`) — no live network calls in unit suite
- Coverage target: ≥85% overall, **100%** on the verdict module and (Phase 2) state-transition module
- Fixture JSONs for API responses committed to `tests/fixtures/`
- Slack event fixtures use `ts` as the unique key (not `event_id`)

---

## Project Structure

```
github_status_bot/
├── planning/
│   ├── prd.md                    ← authoritative requirements
│   ├── tasks.md                  ← task list with status
│   └── onboarding-prompt.md      ← this file
├── src/
│   └── github_status_bot/
│       ├── __init__.py           ✅ done
│       ├── services.py           ✅ done — ServiceConfig dataclass + SERVICES registry
│       ├── github_status.py      ✅ done — fetch_service_status(base_url); Component/Incident/ServiceStatusResponse
│       ├── verdict.py            ✅ done — pure verdict logic incl. ignored_components param (100% coverage)
│       ├── formatter.py          ✅ done — format_reply, format_summary_line, format_summary_reply (100% coverage)
│       ├── slack_handler.py      ✅ done — service routing, idempotency (ts-based), thread-aware replies
│       └── poller.py             ← Phase 2 asyncio background task (not yet written)
├── tests/
│   ├── fixtures/
│   │   ├── status_none.json                   ✅
│   │   ├── status_minor.json                  ✅
│   │   ├── status_major.json                  ✅
│   │   ├── unresolved_empty.json              ✅
│   │   ├── unresolved_active.json             ✅
│   │   ├── unresolved_missing_started_at.json ✅
│   │   ├── components_all_operational.json    ✅
│   │   ├── components_partial_outage.json     ✅
│   │   ├── slack_mention_channel.json         ✅ (text includes service name)
│   │   ├── slack_mention_thread.json          ✅
│   │   ├── slack_mention_retry.json           ✅ (same ts as channel — simulates Slack retry)
│   │   └── slack_mention_bare.json            ✅ (no service name — triggers summary)
│   ├── conftest.py               ✅ resets _seen_events between tests
│   ├── test_github_status.py     ✅ (fetch_service_status, 100% coverage)
│   ├── test_verdict.py           ✅ (100% coverage)
│   ├── test_formatter.py         ✅ (format_reply + summary functions, 100% coverage)
│   ├── test_slack_handler.py     ✅ (T015/T017 + service routing)
│   ├── test_integration.py       ✅ (full pipeline, all services)
│   └── test_poller.py            ← Phase 2 (T033)
├── slack_app_manifest.yaml       ✅
├── .env.example                  ✅
├── Makefile                      ✅
├── pyproject.toml                ✅
└── README.md                     ✅
```

---

## Common Commands

```bash
# Install dependencies
uv sync

# Run tests — uv is NOT available in the Claude Code sandbox; use the venv directly
/workspace/.venv/bin/pytest tests/ -q

# Run tests with coverage
/workspace/.venv/bin/pytest --cov=src --cov-report=term-missing

# Lint
/workspace/.venv/bin/ruff check src/ tests/

# Type check
/workspace/.venv/bin/mypy --strict src/

# Start the bot in a persistent tmux session (survives terminal close)
# Install tmux first if needed: brew install tmux (Mac) or sudo apt-get install -y tmux (Linux)
tmux new-session -d -s github-bot 'uv run python -m github_status_bot.slack_handler'

# Attach to watch logs
tmux attach -t github-bot
# Detach without stopping: Ctrl-b d

# Stop the bot
tmux kill-session -t github-bot
```

---

## Environment Variables

| Variable                | Phase | Description                                                       |
|-------------------------|-------|-------------------------------------------------------------------|
| `SLACK_BOT_TOKEN`       | 1 + 2 | Bot OAuth token (`xoxb-...`)                                      |
| `SLACK_SIGNING_SECRET`  | 1 + 2 | App signing secret (from Basic Information in api.slack.com/apps) |
| `SLACK_APP_TOKEN`       | 1 + 2 | App-level token for socket mode (`xapp-...`)                      |
| `ALERT_CHANNEL_ID`      | 2     | Slack channel ID for proactive alerts                             |
| `POLL_INTERVAL_MINUTES` | 2     | Polling frequency (default: 5, range: 1–60)                       |
| `STATE_FILE_PATH`       | 2     | Path for JSON state file (default: `gh_status_state.json`)        |

All secrets live in **`.env` on the host machine**. Never commit `.env`. `.env.example` is committed and documents all
variables.

---

## Key Constraints to Remember

1. **Bot speaks only when tagged (Phase 1/3)** — zero unsolicited messages is a hard success metric.
2. **Never fabricate status** — if the API is unreachable, say so explicitly. A fake "up" during a real outage
   permanently destroys trust.
3. **Exactly one reply per mention** — no reactions, no DMs, no follow-ups.
4. **`started_at` not `created_at`** — use `started_at` for duration; both fields exist in the incidents response.
5. **Idempotency key is `ts`** — slack-bolt does not expose `event_id` in the inner event dict. Use `event.get("ts")`
   for deduplication. The idempotency cache is in-memory only (no persistence across restarts).
6. **No time-based rate limiting** — every distinct mention gets a reply. The only suppression is Slack retry
   deduplication via `ts`.
7. **Phase 2 is additive** — the Phase 1/3 handler must not be modified when building Phase 2.
8. **Phase 2 deduplication** — one alert per status transition, not one per poll. JSON state file on disk is the gate.
9. **No cloud infrastructure** — the bot runs as a local process via socket mode. No Lambda, API Gateway, or AWS.

---

## Where to Find More Detail

| Topic                                       | Location                           |
|---------------------------------------------|------------------------------------|
| Full requirements + acceptance criteria     | `planning/prd.md`                  |
| Task list with status and DoD               | `planning/tasks.md`                |
| GitHub/Claude Status API structure          | §4 API Design in `planning/prd.md` |
| Phase 1–3 roadmap                           | §7 in `planning/prd.md`            |
| Risk register                               | §10 in `planning/prd.md`           |
| Environment variables                       | `.env.example` in repo root        |
