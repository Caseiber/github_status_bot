# github_status_bot — Development Tasks

**Generated from**: `planning/prd.md` on 2026-04-27
**Development Phase**: Phase 1 MVP → Phase 2 Proactive Alerting

---

## Quick Status Overview

| Epic | Total | Completed | In Progress | Not Started |
|---|---|---|---|---|
| E001: Project Foundation | 2 | 2 | 0 | 0 |
| E002: GitHub Status Client | 3 | 3 | 0 | 0 |
| E003: Verdict Engine | 2 | 2 | 0 | 0 |
| E004: Slack Bot | 4 | 4 | 0 | 0 |
| E005: Resilience & Edge Cases | 5 | 0 | 0 | 5 |
| E006: Integration Tests | 3 | 0 | 0 | 3 |
| E007: Phase 1 Launch | 1 | 0 | 0 | 1 |
| E008: Phase 1 Validation | 2 | 0 | 0 | 2 |
| E009: Phase 2 — State Model | 3 | 0 | 0 | 3 |
| E010: Phase 2 — Poller | 3 | 0 | 0 | 3 |
| E011: Phase 2 — Validation | 2 | 0 | 0 | 2 |
| **Total** | **30** | **11** | **0** | **19** |

**Last Updated**: 2026-04-28

---

## Next Priority Tasks

1. ~~**T001**~~ — ✅ Initialize Python project with `uv` and `src/` layout
2. ~~**T002**~~ — ✅ Configure `ruff`, `mypy --strict`, `pytest`
3. ~~**T004**~~ — ✅ Create GitHub Status API test fixtures
4. ~~**T005**~~ — ✅ Implement `github_status.py` fetcher
5. ~~**T006**~~ — ✅ Unit tests for `github_status.py`
6. ~~**T007**~~ — ✅ Implement `verdict.py`
7. ~~**T008**~~ — ✅ Unit tests for `verdict.py` — full matrix, 100% coverage
8. ~~**T009**~~ — ✅ Create Slack app and manifest
9. ~~**T010**~~ — ✅ Implement `slack_handler.py` mention handler
10. ~~**T011**~~ — ✅ Implement reply formatting
11. ~~**T012**~~ — ✅ Socket-mode runner and `.env.example`
12. **T013** — Handle GitHub Status API unreachable
13. **T014** — Handle missing `started_at` on incidents

---

## Epic Breakdown

---

### Epic E001: Project Foundation

**Priority**: High — must be done before any feature work
**Dependencies**: None

---

#### Task T001: Initialize Python project with `uv` and `src/` layout

**Priority**: High
**Effort**: 1 hour
**Dependencies**: None
**PRD Reference**: §4 Technology Stack

**Acceptance Criteria**:

- [x] `pyproject.toml` created with Python 3.12, `slack-bolt`, `httpx`, `slack-sdk` as dependencies
- [x] `pytest`, `pytest-httpx`, `pytest-cov`, `ruff`, `mypy` in dev dependencies
- [x] `src/github_status_bot/__init__.py` exists (empty)
- [x] `uv sync` runs cleanly with no errors
- [x] `src/` layout is importable: `from github_status_bot import ...` works

**Definition of Done**:

- [x] All acceptance criteria met; `uv.lock` committed; `.gitignore` covers `__pycache__`, `.mypy_cache`, `.pytest_cache`, `dist/`, `.env`

---

#### Task T002: Configure `ruff`, `mypy --strict`, `pytest`

**Priority**: High
**Effort**: 1 hour
**Dependencies**: T001
**PRD Reference**: §5 Tech stack optimizations

**Acceptance Criteria**:

- [x] `ruff` config in `pyproject.toml`
- [x] `mypy --strict` config in `pyproject.toml` with `src/` as source root
- [x] `pytest` config in `pyproject.toml` (testpaths, integration marker)
- [x] `Makefile` with `check` (lint + typecheck + test) and `test` (pytest with coverage) targets

**Definition of Done**:

- [x] All three tool commands verified passing

---

### Epic E002: GitHub Status Client

**Priority**: High
**Dependencies**: E001

---

#### Task T004: Create GitHub Status API test fixtures

**Priority**: High
**Effort**: 1 hour
**Dependencies**: T001

**Acceptance Criteria**:

- [x] `tests/fixtures/status_none.json`
- [x] `tests/fixtures/status_minor.json`
- [x] `tests/fixtures/status_major.json`
- [x] `tests/fixtures/unresolved_empty.json`
- [x] `tests/fixtures/unresolved_active.json` — one incident with `resolved_at: null`, valid `started_at`
- [x] `tests/fixtures/unresolved_missing_started_at.json` — one incident, `started_at` absent
- [x] All fixtures match the actual GitHub Statuspage API response shape

**Definition of Done**:

- [x] All fixtures committed under `tests/fixtures/`

---

#### Task T005: Implement `github_status.py` fetcher

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T004
**PRD Reference**: F2

**Acceptance Criteria**:

- [x] `fetch_github_status()` async function makes concurrent requests to both endpoints
- [x] Per-request timeout: 2 seconds
- [x] One retry on 5xx or timeout; second failure → `fetch_error: True`
- [x] Returns typed dataclass: `{indicator: str, incidents: list[Incident], fetch_error: bool}`
- [x] `Incident` includes `started_at: datetime | None` and `resolved_at: datetime | None`
- [x] `mypy --strict` passes

**Definition of Done**:

- [x] All acceptance criteria met; `ruff` and `mypy --strict` clean

---

#### Task T006: Unit tests for `github_status.py`

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T005
**PRD Reference**: F2, §5

**Acceptance Criteria**:

- [x] All HTTP calls mocked with `pytest-httpx`
- [x] Test: both endpoints 200 — parsed correctly
- [x] Test: `status.json` 500 both attempts → `fetch_error: True`
- [x] Test: `unresolved.json` timeout → `fetch_error: True`
- [x] Test: `started_at` missing → `Incident.started_at` is `None`
- [x] Test: retry — first 500, second 200 — succeeds
- [x] Coverage on `github_status.py` = 100%

**Definition of Done**:

- [x] All acceptance criteria met; no live network calls

---

### Epic E003: Verdict Engine

**Priority**: High — 100% coverage required
**Dependencies**: E002

---

#### Task T007: Implement `verdict.py`

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T005
**PRD Reference**: F2, F3, F4

**Acceptance Criteria**:

- [x] `compute_verdict(status_response) -> VerdictResult` is a pure function
- [x] `VerdictResult`: `{is_down: bool, indicator: str, duration_seconds: int | None, has_fetch_error: bool}`
- [x] `is_down = True` when `indicator` ∈ `{minor, major, critical}`
- [x] `is_down = True` when any incident has `resolved_at = None`
- [x] `is_down = False` when `indicator = none` AND all incidents resolved or list empty
- [x] `duration_seconds` = seconds since earliest unresolved incident's `started_at`
- [x] `duration_seconds = None` when `started_at` missing — never fabricated
- [x] `has_fetch_error = True` propagated from fetcher
- [x] `mypy --strict` passes

**Definition of Done**:

- [x] All acceptance criteria met; 100% branch coverage verified

---

#### Task T008: Unit tests for `verdict.py` — full matrix, 100% coverage

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T007
**PRD Reference**: F2, F3, F4, §5

**Acceptance Criteria**:

- [x] Test: `indicator=none`, empty incidents → `is_down=False`, `duration=None`
- [x] Test: `indicator=major`, no incidents → `is_down=True`, `duration=None`
- [x] Test: active incident with valid `started_at` → `is_down=True`, `duration` ≥ 0
- [x] Test: active incident with missing `started_at` → `is_down=True`, `duration=None`
- [x] Test: incident with `resolved_at` set → `is_down=False`
- [x] Test: `has_fetch_error=True` propagated
- [x] Test: multiple incidents — duration from earliest `started_at`
- [x] Coverage on `verdict.py` = 100%

**Definition of Done**:

- [x] All acceptance criteria met; 100% confirmed via `make test`

---

### Epic E004: Slack Bot

**Priority**: High
**Dependencies**: E003

---

#### Task T009: Create Slack app and manifest

**Priority**: High
**Effort**: 1 hour
**Dependencies**: None

**Acceptance Criteria**:

- [x] Slack app created at api.slack.com/apps
- [x] Bot scopes granted: `app_mentions:read`, `chat:write`
- [x] Event subscription enabled: `app_mention`
- [x] Socket mode enabled on the app (required for socket-mode deployment)
- [x] `slack_app_manifest.yaml` committed to repo root
- [x] Bot can be `@`-mentioned and added to channels

**Definition of Done**:

- [x] Manifest committed; bot responding to mentions in workspace

---

#### Task T010: Implement `slack_handler.py` mention handler

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T007, T009
**PRD Reference**: F1, F2, §4 Integration Strategy Phase 1

**Acceptance Criteria**:

- [x] `slack-bolt` `App` listens for `app_mention` events via socket mode
- [x] Handler fetches GitHub status and computes verdict on each mention
- [x] Calls `format_reply()` and posts via `say()`
- [x] Reply goes to same thread if mention was in a thread (`thread_ts` preserved)
- [x] No Lambda/API Gateway code in the module — socket mode is the deployment target
- [x] `mypy --strict` passes

**Testing Requirements**:

- [x] Manual test: `@github_status_bot` in a channel returns a reply (confirmed by user)

**Definition of Done**:

- [x] All acceptance criteria met

**Git Workflow**:

- Branch: `feat/t010-slack-handler`

---

#### Task T011: Implement reply formatting

**Priority**: High
**Effort**: 1 hour
**Dependencies**: T007
**PRD Reference**: F3, F4, F5

**Acceptance Criteria**:

- [x] `format_reply(verdict: VerdictResult) -> str` pure function in `formatter.py`
- [x] Up reply: `"GitHub appears to be *up*. Source: GitHub's official status page (all systems operational)."`
- [x] Down reply with duration: `"GitHub appears to be *down*. Source: GitHub's official status page (indicator: major, ~2h 12m)."`
- [x] Down reply without duration: `"GitHub appears to be *down*. Source: GitHub's official status page (indicator: major)."`
- [x] Error reply: `"Couldn't check GitHub's status right now — the status API didn't respond. Try again in a moment."`
- [x] Duration: `< 60s` → `"less than a minute"`; `< 60m` → `"~Xm"`; `≥ 60m` → `"~Xh Ym"`
- [x] `mypy --strict` passes

**Definition of Done**:

- [x] All acceptance criteria met; unit tests passing; 100% coverage

---

#### Task T012: Socket-mode runner and local setup

**Priority**: High
**Effort**: 1 hour
**Dependencies**: T010
**PRD Reference**: §8 Deployment Standards

**Acceptance Criteria**:

- [x] `uv run python -m github_status_bot.slack_handler` starts bot when env vars are set
- [x] `.env.example` committed with all required variable names and descriptions
- [x] `.env` in `.gitignore`

**Definition of Done**:

- [x] All acceptance criteria met

---

### Epic E005: Resilience & Edge Cases

**Priority**: High
**Dependencies**: E004

---

#### Task T013: Handle GitHub Status API unreachable

**Priority**: High
**Effort**: 1 hour
**Dependencies**: T010, T011
**PRD Reference**: F5, Edge Cases

**Acceptance Criteria**:

- [ ] When `fetch_github_status()` returns `fetch_error=True`, bot posts the error copy
- [ ] Error reply never says "up" or "down" — only that it couldn't check
- [ ] No unhandled exceptions propagate out of the handler

**Testing Requirements**:

- [ ] Unit test: `compute_verdict` with `fetch_error=True` → error verdict
- [ ] Unit test: `format_reply` with error verdict → correct error string

**Definition of Done**:

- [ ] All acceptance criteria met; unit tests passing

**Git Workflow**:

- Branch: `feat/t013-error-handling`

---

#### Task T014: Handle missing `started_at` on incidents

**Priority**: Medium
**Effort**: 1 hour
**Dependencies**: T007, T008
**PRD Reference**: F4, Edge Cases

**Acceptance Criteria**:

- [ ] Active incident with no `started_at` → `is_down=True`, `duration_seconds=None`
- [ ] Reply omits duration rather than fabricating or crashing
- [ ] Full path confirmed: fixture → verdict → formatter → correct reply string

**Definition of Done**:

- [ ] Integration test verifies end-to-end with `unresolved_missing_started_at.json` fixture

**Git Workflow**:

- Branch: `feat/t014-missing-started-at`

---

#### Task T015: Idempotency for Slack event retries

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T010
**PRD Reference**: Epic B — B2

**Acceptance Criteria**:

- [ ] Same `event_id` received twice → only one `chat.postMessage` call
- [ ] In-memory cache of recently seen `event_id` values (TTL ≥ 60s, capacity ≥ 100)
- [ ] Different `event_id` with same text → two replies (idempotency is on ID, not content)

**Testing Requirements**:

- [ ] Unit test: duplicate `event_id` → one post
- [ ] Unit test: distinct `event_id` → two posts

**Definition of Done**:

- [ ] All acceptance criteria met; unit tests passing

**Git Workflow**:

- Branch: `feat/t015-idempotency`

---

#### Task T016: Per-channel rate-limit guard

**Priority**: Medium
**Effort**: 1 hour
**Dependencies**: T010
**PRD Reference**: §4 Security & Performance

**Acceptance Criteria**:

- [ ] After replying in a channel, bot ignores further mentions in that channel for 5 seconds
- [ ] Cooldown is per-channel (channel A blocked does not affect channel B)
- [ ] In-memory dict of `{channel_id: last_reply_ts}`

**Testing Requirements**:

- [ ] Unit test: two mentions same channel within 5s → one reply
- [ ] Unit test: mentions in two channels within 5s → two replies

**Definition of Done**:

- [ ] All acceptance criteria met; unit tests passing

**Git Workflow**:

- Branch: `feat/t016-rate-limit-guard`

---

#### Task T017: Thread-aware replies

**Priority**: Medium
**Effort**: 1 hour
**Dependencies**: T010
**PRD Reference**: Edge Cases — "Bot mentioned in a thread"

**Acceptance Criteria**:

- [ ] Mention with `thread_ts` → reply posted with matching `thread_ts`
- [ ] Mention in channel root → reply in channel root

**Testing Requirements**:

- [ ] Unit test: event with `thread_ts` → `say()` called with `thread_ts`
- [ ] Unit test: event without `thread_ts` → `say()` called without `thread_ts`

**Definition of Done**:

- [ ] All acceptance criteria met; verified manually in workspace

**Git Workflow**:

- Branch: `feat/t017-thread-replies`

---

### Epic E006: Integration Tests

**Priority**: High
**Dependencies**: E005

---

#### Task T018: Record Slack event payload fixtures

**Priority**: High
**Effort**: 1 hour
**Dependencies**: T009
**PRD Reference**: §7 Day 5

**Acceptance Criteria**:

- [ ] `tests/fixtures/slack_mention_channel.json` — `app_mention` event from channel root
- [ ] `tests/fixtures/slack_mention_thread.json` — `app_mention` event from a thread
- [ ] `tests/fixtures/slack_mention_retry.json` — payload simulating a Slack retry
- [ ] All payloads anonymized (no real user/channel IDs)

**Definition of Done**:

- [ ] Fixtures committed under `tests/fixtures/`

**Git Workflow**:

- Branch: `feat/t018-slack-fixtures`

---

#### Task T019: Integration tests — full handler flow

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T015, T016, T017, T018
**PRD Reference**: §5, §8

**Acceptance Criteria**:

- [ ] Test: channel mention + GitHub up → `say()` with "up" copy
- [ ] Test: channel mention + GitHub down with `started_at` → `say()` with "down" + duration
- [ ] Test: thread mention → `say()` includes `thread_ts`
- [ ] Test: API unreachable → `say()` with error copy
- [ ] Test: duplicate `event_id` → exactly one `say()` call
- [ ] Test: two mentions same channel within 5s → one `say()` call
- [ ] All external HTTP mocked with `pytest-httpx`

**Testing Requirements**:

- [ ] `uv run pytest tests/test_integration.py -v` passes; no live network or Slack calls

**Definition of Done**:

- [ ] All acceptance criteria met; overall coverage ≥ 85%

**Git Workflow**:

- Branch: `feat/t019-integration-tests`

---

#### Task T020: Coverage gate verification

**Priority**: Medium
**Effort**: 1 hour
**Dependencies**: T008, T019
**PRD Reference**: §8 Code Quality Standards

**Acceptance Criteria**:

- [ ] `pyproject.toml` sets `--cov-fail-under=85` for overall coverage
- [ ] `verdict.py` and `formatter.py` maintain 100% coverage
- [ ] Coverage report shows per-file breakdown

**Definition of Done**:

- [ ] Coverage gates enforced; thresholds documented in README

**Git Workflow**:

- Branch: `feat/t020-coverage-gates`

---

### Epic E007: Phase 1 Launch

**Priority**: High — gates Phase 1 completion
**Dependencies**: E006

---

#### Task T021: Configure `.env` and run bot persistently

**Priority**: High
**Effort**: 1 hour
**Dependencies**: T012
**PRD Reference**: §8 Deployment Standards

**Acceptance Criteria**:

- [ ] `.env` file created on the host machine with `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`
- [ ] Bot started with `uv run python -m github_status_bot.slack_handler` and left running
- [ ] Bot reconnects automatically if the WebSocket drops (slack-bolt handles this)
- [ ] Process kept alive across terminal sessions (e.g. `nohup`, `screen`, `tmux`, or a system service)

**Definition of Done**:

- [ ] Bot running persistently; any team member can `@`-mention it and receive a reply

**Git Workflow**:

- Branch: `feat/t021-phase1-launch`

---

### Epic E008: Phase 1 Validation

**Priority**: High — confirms Phase 1 is production-ready
**Dependencies**: E007

---

#### Task T026: Phase 1 soak test

**Priority**: High
**Effort**: 2 hours
**Dependencies**: T021
**PRD Reference**: §8 Phase 1 MVP Ready Criteria

**Acceptance Criteria**:

- [ ] 20 consecutive `@github_status_bot` mentions across different channels — every mention receives exactly one reply
- [ ] At least one mention in a thread — reply appears in thread
- [ ] At least one mention while GitHub Status API is blocked — error reply returned, not silence
- [ ] No unsolicited messages during a 1-hour monitoring window

**Definition of Done**:

- [ ] All 20 mentions passed; test log attached to PR

**Git Workflow**:

- Branch: `feat/t026-soak-test`

---

#### Task T027: README and project documentation

**Priority**: Medium
**Effort**: 1 hour
**Dependencies**: T021
**PRD Reference**: §8 README

**Acceptance Criteria**:

- [ ] README covers: prerequisites (`uv`, Slack app setup)
- [ ] README covers: creating `.env` from `.env.example`
- [ ] README covers: starting the bot (`uv run python -m github_status_bot.slack_handler`)
- [ ] README covers: keeping the bot alive (tmux / nohup / system service)
- [ ] README covers: rotating Slack tokens (update `.env`, restart process)
- [ ] `.env.example` describes all variables with one-line explanations

**Definition of Done**:

- [ ] README committed; project is reproducible from docs alone

**Git Workflow**:

- Branch: `feat/t027-readme`

---

### Epic E009: Phase 2 — State Model

> **Do not begin until Phase 1 has been stable for ≥ 2 weeks.**

**Priority**: Medium (Phase 2)
**Dependencies**: E008 fully complete

---

#### Task T028: JSON file state store for Phase 2

**Priority**: Medium
**Effort**: 1 hour
**Dependencies**: None (can be designed before Phase 1 completes)
**PRD Reference**: P4

**Acceptance Criteria**:

- [ ] `state.py` module with `read_state() -> StoredState | None` and `write_state(state: StoredState) -> None`
- [ ] State file path configurable via `STATE_FILE_PATH` env var (default: `gh_status_state.json`)
- [ ] File written atomically (write to `.tmp`, then rename) to avoid corrupt reads
- [ ] `read_state()` returns `None` if file missing or JSON invalid (does not raise)
- [ ] `mypy --strict` passes

**Testing Requirements**:

- [ ] Unit tests: read missing file → `None`; read valid file → `StoredState`; write then read → round-trips correctly; corrupt file → `None`

**Definition of Done**:

- [ ] Module implemented; unit tests passing; 100% coverage

**Git Workflow**:

- Branch: `feat/t028-state-store`

---

#### Task T029: Implement state-transition module

**Priority**: Medium
**Effort**: 2 hours
**Dependencies**: T028
**PRD Reference**: P4

**Acceptance Criteria**:

- [ ] `compute_transition(current_verdict: VerdictResult, stored_state: StoredState | None) -> Transition` pure function
- [ ] `Transition`: `UP_TO_DOWN | DOWN_TO_UP | NO_CHANGE`
- [ ] `UP_TO_DOWN` when prior state was up (or no state) and current is down
- [ ] `DOWN_TO_UP` when prior state was down and current is up
- [ ] `NO_CHANGE` otherwise
- [ ] `mypy --strict` passes

**Definition of Done**:

- [ ] Module implemented; 100% coverage verified in T030

**Git Workflow**:

- Branch: `feat/t029-state-transition`

---

#### Task T030: Unit tests for state-transition module — 100% coverage

**Priority**: Medium
**Effort**: 2 hours
**Dependencies**: T029
**PRD Reference**: P4, §5

**Acceptance Criteria**:

- [ ] Test: no stored state + down current → `UP_TO_DOWN`
- [ ] Test: stored=up + down current → `UP_TO_DOWN`
- [ ] Test: stored=down + up current → `DOWN_TO_UP`
- [ ] Test: stored=down + still down → `NO_CHANGE`
- [ ] Test: stored=up + still up → `NO_CHANGE`
- [ ] Coverage on state-transition module = 100%

**Definition of Done**:

- [ ] All acceptance criteria met

**Git Workflow**:

- Branch: `feat/t030-state-transition-tests`

---

### Epic E010: Phase 2 — Poller

**Priority**: Medium (Phase 2)
**Dependencies**: E009

---

#### Task T031: Implement `poller.py` as an asyncio background task

**Priority**: Medium
**Effort**: 2 hours
**Dependencies**: T029, T005
**PRD Reference**: P1, P2, P3, P4

**Acceptance Criteria**:

- [ ] `async def run_poller(app: App) -> None` — infinite loop with `asyncio.sleep(POLL_INTERVAL_MINUTES * 60)`
- [ ] On each iteration: fetch status, read state, compute transition, act, write state
- [ ] On `UP_TO_DOWN`: post outage alert to `ALERT_CHANNEL_ID`, write new state
- [ ] On `DOWN_TO_UP`: post recovery alert to `ALERT_CHANNEL_ID`, write new state
- [ ] On `NO_CHANGE`: no-op
- [ ] On state file read failure: log error, skip alert (do not crash)
- [ ] On state file write failure after posting: log warning
- [ ] Started as `asyncio.create_task(run_poller(app))` from the `__main__` block alongside the socket-mode handler
- [ ] `mypy --strict` passes

**Definition of Done**:

- [ ] All acceptance criteria met

**Git Workflow**:

- Branch: `feat/t031-poller`

---

#### Task T032: Poller alert message formatting

**Priority**: Medium
**Effort**: 1 hour
**Dependencies**: T011, T031
**PRD Reference**: P2, P3

**Acceptance Criteria**:

- [ ] `format_outage_alert(verdict: VerdictResult) -> str` — mirrors on-demand down reply format
- [ ] `format_recovery_alert() -> str` — e.g., `"GitHub is back up. Source: GitHub's official status page (all systems operational)."`
- [ ] Both functions covered by unit tests
- [ ] Outage alert includes duration when available; omits when not

**Definition of Done**:

- [ ] All acceptance criteria met; unit tests passing

**Git Workflow**:

- Branch: `feat/t032-alert-formatting`

---

#### Task T033: Integration tests for poller

**Priority**: Medium
**Effort**: 2 hours
**Dependencies**: T031, T032
**PRD Reference**: §8 Phase 2 Ready Criteria

**Acceptance Criteria**:

- [ ] All HTTP calls mocked with `pytest-httpx`; state file mocked via `tmp_path` fixture
- [ ] Test: no prior state + GitHub down → alert posted + state file written
- [ ] Test: stored=down + GitHub still down → no alert, no file write
- [ ] Test: stored=down + GitHub now up → recovery posted + state file written
- [ ] Test: stored=up + GitHub still up → no alert
- [ ] Test: state file corrupt → no alert, handler exits cleanly

**Definition of Done**:

- [ ] All acceptance criteria met; no live network or Slack calls

**Git Workflow**:

- Branch: `feat/t033-poller-tests`

---

### Epic E011: Phase 2 — Validation

**Priority**: Medium (Phase 2)
**Dependencies**: E010

---

#### Task T036: End-to-end Phase 2 validation

**Priority**: Medium
**Effort**: 2 hours
**Dependencies**: T031, T032, T033
**PRD Reference**: §8 Phase 2 Ready Criteria

**Acceptance Criteria**:

- [ ] Set `POLL_INTERVAL_MINUTES=1` temporarily for testing
- [ ] Observe outage alert in `ALERT_CHANNEL_ID` within 1 minute of a real or simulated GitHub outage status
- [ ] Observe recovery alert within 1 minute of status returning to normal
- [ ] 10 consecutive polls during sustained "down" state → exactly 1 alert
- [ ] Phase 1 `@`-mention still works correctly throughout

**Definition of Done**:

- [ ] All acceptance criteria met; restore `POLL_INTERVAL_MINUTES=5`

**Git Workflow**:

- Branch: `feat/t036-phase2-validation`

---

#### Task T037: Update README for Phase 2

**Priority**: Low
**Effort**: 1 hour
**Dependencies**: T036
**PRD Reference**: §8 README

**Acceptance Criteria**:

- [ ] README documents `POLL_INTERVAL_MINUTES` (purpose, default, valid range)
- [ ] README documents `ALERT_CHANNEL_ID` (how to find the channel ID in Slack)
- [ ] README documents `STATE_FILE_PATH` (purpose, default)
- [ ] `.env.example` updated with Phase 2 variables

**Definition of Done**:

- [ ] README committed; Phase 2 fully documented

**Git Workflow**:

- Branch: `feat/t037-phase2-docs`

---

## Task Completion Workflow

```bash
# Start a task
git checkout cs-initial && git pull
git checkout -b feat/tXXX-description

# Run checks before committing
uv run ruff check src/ tests/
uv run mypy --strict src/
uv run pytest --cov=src --cov-report=term-missing

# Update tasks.md status, then open PR
```

---

*Generated from `planning/prd.md` — updated 2026-04-28. Update the Quick Status Overview table as tasks are completed.*
