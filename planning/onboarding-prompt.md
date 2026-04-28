# Claude Code Onboarding — github_status_bot

You are continuing development on **`github_status_bot`**, a Slack bot that tells engineers whether GitHub is currently
down by checking GitHub's official status API. This document is your complete orientation — read it fully before writing
any code.

---

## Getting Started Checklist

- [ ] Read this document top to bottom
- [ ] Read `planning/prd.md` (the authoritative requirements document)
- [ ] Confirm you understand the two-phase scope before touching any feature code
- [ ] Check `git status` and `git log --oneline -10` to orient yourself

---

## Project Overview

**What it is**: A Slack bot that responds when `@github_status_bot` is mentioned in a channel, fetches GitHub's own
status API in real time, and replies with a clear up/down verdict, the source, and how long the outage has been
ongoing (if applicable).

**What it is NOT**: It does not use Down Detector or any source other than GitHub's official Statuspage API. It does not
proactively post anything in Phase 1.

**Vision**: Give engineers an instant, authoritative answer to "is GitHub actually down?" without leaving Slack — and (
in Phase 2) alert the team proactively when GitHub reports an outage.

**Current status**: Phase 1 in progress. E001–E004 complete (T001, T002, T004–T012). Next: T013 (API unreachable error
handling), T014 (missing started_at end-to-end), T015 (idempotency).

---

## Two-Phase Scope

### Phase 1 — On-Demand Bot (build this first)

Bot is silent until `@`-mentioned. On mention:

1. Fetches `https://www.githubstatus.com/api/v2/status.json`
2. Fetches `https://www.githubstatus.com/api/v2/incidents/unresolved.json`
3. Replies once in the same channel/thread with verdict + source + duration

**Requirements**: F1–F5 in `planning/prd.md`. No database. No polling. No scheduled work.

### Phase 2 — Proactive Alerting (do NOT start until Phase 1 is stable for ≥2 weeks)

A separate EventBridge-triggered Lambda polls GitHub Status every `POLL_INTERVAL_MINUTES` (default: 5) and posts to
`ALERT_CHANNEL_ID` when status transitions between up and down. Adds DynamoDB for deduplication state.

**Requirements**: P1–P5 in `planning/prd.md`. Phase 1 Lambda is untouched.

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

## Architecture — Phase 1

```
Slack mention
    → Slack WebSocket (socket mode, outbound connection managed by slack-bolt)
    → local process (slack_handler.py)
        1. Receive app_mention event
        2. Concurrent fetches: status.json + unresolved.json (2s timeout each)
        3. Compute verdict
        4. POST chat.postMessage
```

**No database. No inbound HTTP. No cloud infrastructure. Everything is stateless.**

## Architecture — Phase 2 (additive — same process)

```
asyncio.create_task(run_poller(app))  ← started alongside socket-mode handler
    every POLL_INTERVAL_MINUTES:
        1. Fetch status.json + unresolved.json
        2. Read gh_status_state.json from disk
        3. If status changed → post alert/recovery to ALERT_CHANNEL_ID → write new state
        4. If unchanged → no-op
```

---

## Key GitHub Status API Facts

Verified during PRD research — these are the actual response shapes:

**`status.json`**

```json
{
  "status": {
    "indicator": "none | minor | major | critical",
    "description": "All Systems Operational"
  }
}
```

"Down" = `indicator` is `minor`, `major`, or `critical`.

**`unresolved.json`**

```json
{
  "incidents": [
    {
      "id": "...",
      "status": "investigating | identified | monitoring",
      "started_at": "2026-04-27T16:31:07.236Z",
      "resolved_at": null
    }
  ]
}
```

"Down" also triggered by any incident with `resolved_at: null`. Duration comes from `started_at` (not `created_at`). If
`started_at` is missing, report down without duration — never fabricate.

---

## Verdict Logic

```
if indicator in {minor, major, critical} OR any incident has resolved_at == null:
    verdict = DOWN
    duration = now - earliest_incident.started_at  (if started_at present)
else:
    verdict = UP
```

The verdict module must have **100% unit test coverage**. Test matrix:

- `indicator=none`, empty incidents → UP
- `indicator=major`, no incidents → DOWN, no duration
- `indicator=none`, incident with `resolved_at=null` and valid `started_at` → DOWN with duration
- `indicator=none`, incident with `resolved_at=null` and missing `started_at` → DOWN, no duration
- GitHub Status API unreachable → reply "couldn't check right now" — never fake UP

---

## Reply Format

**When up:**
> GitHub appears to be **up**... for NOW. Source: GitHub's official status page (all systems operational).

**When down:**
> GitHub is **down** because AI DevOps is a blight on our land. Source: GitHub's official status page (indicator: major, ~2h 12m).

**When API unreachable:**
> Couldn't check GitHub's status right now — the status API didn't respond because AI DevOps is a blight on our land. Try again in a moment.

---

## Development Workflow

### Git Rules

- **Base branch is `cs-initial`** — never commit directly to `cs-initial` or `main`
- Every feature or task gets its own branch off `cs-initial`: `feat/tXXX-<short-description>`
- Bug fixes: `fix/tXXX-<short-description>`
- Merge via PR even when working solo — it keeps history clean
- Commit messages: imperative mood, present tense ("add verdict module", not "added" or "adding")

### Branch Naming Examples

```
feat/t013-error-handling
feat/t015-idempotency
feat/t016-rate-limit-guard
feat/t019-integration-tests
feat/t031-poller
```

### Before Every Commit

```bash
uv run ruff check src/ tests/
uv run mypy --strict src/
uv run pytest --cov=src --cov-report=term-missing
```

All three must pass. Fix failures before committing — do not use `--no-verify`.

### Testing Standards

- Unit tests mock all external HTTP (`pytest-httpx`) — no live network calls in unit suite
- Live calls only in an integration suite tagged `@pytest.mark.integration`
- Coverage target: ≥85% overall, **100%** on the verdict module and (Phase 2) state-transition module
- Fixture JSONs for GitHub Status responses committed to `tests/fixtures/`

---

## Project Structure (target)

```
github_status_bot/
├── planning/
│   ├── prd.md                    ← authoritative requirements
│   └── onboarding-prompt.md      ← this file
├── src/
│   └── github_status_bot/
│       ├── __init__.py           ✅ done
│       ├── github_status.py      ✅ done — fetches + parses GitHub Status API
│       ├── verdict.py            ✅ done — pure verdict logic (100% coverage)
│       ├── formatter.py          ✅ done — format_reply() pure function (100% coverage)
│       ├── slack_handler.py      ✅ done — socket-mode app_mention handler
│       └── poller.py             ← Phase 2 asyncio background task (not yet written)
├── tests/
│   ├── fixtures/
│   │   ├── status_none.json      ✅ done
│   │   ├── status_minor.json     ✅ done
│   │   ├── status_major.json     ✅ done
│   │   ├── unresolved_empty.json ✅ done
│   │   ├── unresolved_active.json           ✅ done
│   │   └── unresolved_missing_started_at.json ✅ done
│   ├── test_github_status.py     ✅ done (19 tests, 100% coverage)
│   ├── test_verdict.py           ✅ done (10 tests, 100% coverage)
│   ├── test_formatter.py         ✅ done (14 tests, 100% coverage)
│   ├── test_slack_handler.py     ← to be written with T015–T017
│   └── test_poller.py            ← Phase 2 (T033)
├── slack_app_manifest.yaml       ✅ done
├── .env.example                  ✅ done
├── Makefile                      ✅ done
├── pyproject.toml                ✅ done
└── README.md                     ← to be written (T027)
```

---

## Common Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=term-missing

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy --strict src/

# Start the bot (requires .env populated — see .env.example)
uv run python -m github_status_bot.slack_handler

# Keep running across terminal sessions
nohup uv run python -m github_status_bot.slack_handler &> bot.log &
# or use tmux/screen
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

1. **Bot speaks only when tagged (Phase 1)** — zero unsolicited messages is a hard success metric.
2. **Never fabricate status** — if the API is unreachable, say so explicitly. A fake "up" during a real outage
   permanently destroys trust.
3. **Exactly one reply per mention** — no reactions, no DMs, no follow-ups.
4. **`started_at` not `created_at`** — use `started_at` for duration; both fields exist in the incidents response.
5. **Phase 2 is additive** — the Phase 1 handler must not be modified when building Phase 2.
6. **Phase 2 deduplication** — one alert per status transition, not one per poll. JSON state file on disk is the gate.
7. **No cloud infrastructure** — the bot runs as a local process via socket mode. No Lambda, API Gateway, SAM, or AWS
   accounts required.

---

## Where to Find More Detail

| Topic                                       | Location                           |
|---------------------------------------------|------------------------------------|
| Full requirements + acceptance criteria     | `planning/prd.md`                  |
| Task list with status and DoD               | `planning/tasks.md`                |
| Coding standards, PR process, quality gates | `ai/development-guidelines.md`     |
| GitHub Status API structure (verified live) | §4 API Design in `planning/prd.md` |
| Phase 1 roadmap (day-by-day)                | §7 in `planning/prd.md`            |
| Phase 2 roadmap                             | §7 in `planning/prd.md`            |
| Risk register                               | §10 in `planning/prd.md`           |
| Environment variables                       | `.env.example` in repo root        |
