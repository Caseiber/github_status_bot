# Product Requirements Document — GitHub Status Slack Bot

## 1. Executive Summary

- **Project Name & Version**: `github_status_bot` — v0.1 (MVP draft)
- **Date & Status**: 2026-04-27 — In development — Phase 1 (E001–E003 complete)
- **Vision Statement**: Give engineers an instant, authoritative answer to "is GitHub actually down?" without leaving Slack — and proactively alert the team the moment GitHub reports an outage.
- **Success Metrics**:
  1. **Zero false alarms** — bot reports "down" only when GitHub's own status API confirms it.
  2. **Phase 1: Zero unsolicited messages** — in Phase 1 the bot speaks only in direct response to an `@github_status_bot` mention, exactly once per mention.
  3. **Source-truthful answers** — every response reflects live data fetched at request time; no fabricated answers.
  4. **Sub-3-second median response time** from `@`-mention to Slack message posted (Phase 1).
  5. **Phase 2: Proactive alerting** — team is notified in a designated channel within one polling interval of GitHub reporting an outage.

## 2. Problem Statement

### Current Pain Points
- When CI/clones/pushes fail, engineers waste minutes context-switching to `githubstatus.com` to triage whether the problem is theirs or GitHub's.
- "Is it just me?" debates in team channels are noisy and frequently inconclusive.
- GitHub's own status page can lag real user-reported issues, but it remains the most authoritative signal available via a public API.
- Engineers only find out GitHub is down reactively — after hitting errors — rather than being notified proactively.

### Target User Personas
- **Primary — Engineer in a Slack channel**: actively trying to push/pull/merge, hits an error, wants a 3-second answer in the channel they're already in.
- **Secondary — Eng manager / on-call**: triaging an incident, needs a quick external-confirmation signal before declaring an outage.
- **Tertiary — Anyone in the workspace**: occasional curious user wanting a sanity check before filing a ticket.

### Market Opportunity
This is internal tooling, not a market product. The "opportunity" is reclaiming engineer minutes during GitHub incidents (which happen multiple times per quarter) and reducing channel noise. Build cost is low; payoff scales with team size and GitHub reliance.

## 3. Product Requirements

### Phase 1 — Core Functionality (MVP)

**F1 — Mention-triggered response**
- Bot responds **only** to messages that `@`-mention `@github_status_bot`.
- Bot replies in the same channel/thread as the mention.
- Bot posts exactly one message per mention. No DMs, no follow-ups, no reactions.
- *Acceptance*: Posting `@github_status_bot` in any channel the bot is a member of yields exactly one reply within 3 seconds (p50) / 8 seconds (p95).

**F2 — GitHub Status check**
- Bot fetches `https://www.githubstatus.com/api/v2/status.json` and `https://www.githubstatus.com/api/v2/incidents/unresolved.json` on every mention.
- "Down" is defined as `status.indicator` ∈ {`minor`, `major`, `critical`} OR any incident in the unresolved list with `resolved_at: null`.
- Duration uses the incident's `started_at` field.
- *Acceptance*: When indicator is `none` and incidents array is empty, bot reports "up." When indicator is `major`, bot reports "down" with duration derived from `started_at`.

**F3 — Verdict and source attribution**
- The reply explicitly states the verdict and cites GitHub's status API, e.g.:
  - "GitHub appears to be **down**. Source: GitHub's official status page (indicator: major, ~2h 12m)."
  - "GitHub appears to be **up**. Source: GitHub's official status page (all systems operational)."
- *Acceptance*: Every reply contains an explicit source attribution. Replies never assert "down" without naming the triggering indicator or incident.

**F4 — Outage duration**
- When verdict is "down," bot reports human-friendly duration derived from the earliest unresolved incident's `started_at`: "~12 minutes," "~1h 40m," "less than a minute."
- If no `started_at` is present on the incident, bot reports "down" without a duration rather than fabricating one.
- *Acceptance*: When GitHub Status shows a `started_at` 23 minutes ago, reply contains "~23 minutes."

**F5 — Live data only**
- No cached responses older than 60 seconds may be returned. (A short cache is acceptable to absorb mention bursts within that window.)
- The bot must never fabricate status — it returns only what it derived from a successful HTTP fetch.
- *Acceptance*: Code review confirms no hardcoded/mocked responses ship to production. Manual test: network-block the GitHub Status API → bot replies with an explicit "couldn't check right now" message, never a fake "up."

### Phase 2 — Proactive Alerting

**P1 — Configurable polling**
- A scheduler (EventBridge) invokes a polling Lambda on a configurable interval (default: every 5 minutes; valid range: 1–60 minutes, set via environment variable `POLL_INTERVAL_MINUTES`).
- The poller fetches the same two GitHub Status endpoints as Phase 1.
- *Acceptance*: Changing `POLL_INTERVAL_MINUTES` and redeploying changes the polling frequency. Poller runs independently of any user mention.

**P2 — Outage alert**
- When the poller detects a status transition from "up" to "down," it posts a message to a designated alert channel (configured via `ALERT_CHANNEL_ID` environment variable).
- Alert message format mirrors the on-demand reply: verdict, indicator, duration since `started_at`.
- *Acceptance*: Within one polling interval of GitHub reporting an outage, a message appears in the configured alert channel.

**P3 — Recovery alert**
- When the poller detects a transition from "down" back to "up" (indicator returns to `none` and incidents list is empty or all resolved), it posts a recovery message to the same alert channel.
- *Acceptance*: Within one polling interval of GitHub resolving an incident, a recovery message appears in the alert channel.

**P4 — No duplicate alerts**
- The poller persists the last-known status in DynamoDB (single record). It only posts if the status has changed since the last poll. Repeated "down" polls do not produce repeated alerts.
- *Acceptance*: 10 consecutive polls during an ongoing outage produce exactly 1 alert message, not 10.

**P5 — Alert channel configuration**
- `ALERT_CHANNEL_ID` is set at deploy time. No runtime configuration command required in Phase 2.
- *Acceptance*: Alerts appear in the correct channel after deploy with `ALERT_CHANNEL_ID` set.

## 4. Technical Architecture

### Technology Stack
- **Language**: Python 3.12.
- **Slack framework**: `slack-bolt` (Python) in socket mode — the bot connects outbound to Slack's WebSocket API; no inbound HTTP server or public URL required.
- **HTTP**: `httpx` (async, timeouts, retries) for GitHub Status API calls.
- **Hosting (Phase 1)**: Long-running process on a team-managed machine. Started via `uv run python -m github_status_bot.slack_handler`. No cloud infrastructure required.
- **Hosting (Phase 2 addition)**: Background `asyncio` task running in the same process as Phase 1. No additional infrastructure.
- **Secrets**: `.env` file on the host machine (never committed to git). Variables: `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`.
- **Phase 2 persistence**: JSON file on disk for polling state — `{indicator: <str>, last_alerted_at: <unix>}`.
- **Observability**: Python `logging` to stdout; redirect to a log file as needed via shell redirection.

### Integration Strategy

**Phase 1 — Mention handler:**
- Slack (WebSocket, socket mode) → local process.
  1. Receive `app_mention` event over persistent WebSocket connection (managed by slack-bolt).
  2. Fetch both GitHub Status endpoints concurrently (2s timeout each).
  3. Post reply via `chat.postMessage`.

**Phase 2 — Poller (additive, runs in same process as Phase 1):**
- Background `asyncio` task, sleeping `POLL_INTERVAL_MINUTES` between polls.
  1. Fetch both GitHub Status endpoints.
  2. Read current state from JSON file on disk.
  3. If status changed → post alert or recovery to `ALERT_CHANNEL_ID` → write new state to file.
  4. If status unchanged → no-op.

### API Design
- **Inbound (Phase 1)**: `app_mention` events received over Slack's WebSocket (socket mode). No inbound HTTP endpoint required.
- **Outbound (both phases)**:
  - `GET https://www.githubstatus.com/api/v2/status.json`
  - `GET https://www.githubstatus.com/api/v2/incidents/unresolved.json`
  - `POST https://slack.com/api/chat.postMessage`
- **Persistence (Phase 2)**: JSON file on disk — `{indicator: <str>, last_alerted_at: <unix>}`.

### Security & Performance Requirements
- **Authentication**: socket mode uses an app-level token (`xapp-...`) to authenticate the WebSocket connection. Slack initiates no inbound HTTP, so there is no per-request signature to verify.
- **No PII** is processed or logged. Channel/user IDs may appear in logs only at DEBUG level.
- **Secrets** never in source or committed files; stored in `.env` on the host machine only.
- **Rate limiting (Phase 1)**: per-channel cooldown of 5 seconds to prevent spam loops.
- **Timeouts**: 2s per GitHub Status endpoint.
- **Retries**: one retry per endpoint on transient failure (5xx, timeout); after that, treat as unavailable.

## 5. Claude Code Development Considerations

### Strengths to Leverage
- **Single-purpose service, well-bounded scope** — small surface area means Claude Code can implement, test, and iterate the whole thing in a tight loop.
- **Public, well-documented JSON API** (GitHub Statuspage) — clean, stable structure with no scraping risk.
- **Easy unit-test surface** — pure functions for parsing the status JSON and computing verdict/duration map cleanly to TDD.
- **Phase 2 is purely additive** — the poller is a new Lambda that shares the status-check logic from Phase 1; no Phase 1 code needs to change.

### Development Strategy Adaptations
- **Requirements precision**: keep this PRD as the single source of truth; reference F1–F5 (Phase 1) and P1–P5 (Phase 2) when prompting Claude Code.
- **Test-driven development**:
  - Unit tests for the verdict function: `{indicator: none, empty incidents}` → up; `{indicator: major}` → down with duration; `{resolved_at: null}` → down; malformed/missing `started_at` → down without duration.
  - Integration test: invoke the Lambda handler with a recorded Slack event payload, assert on the outbound `chat.postMessage` call.
  - Phase 2: unit tests for the state-transition logic (up→down, down→up, no change).
  - Coverage target: **≥85%** overall; **100%** on verdict and state-transition modules.
- **Continuous feedback**: deploy to a private Slack workspace from day one; iterate on copy and edge cases against real `@`-mentions.
- **Tech stack optimizations**: `uv` for dependency management, `pytest` + `pytest-httpx` for HTTP mocking, `ruff` + `mypy --strict` in pre-commit, AWS SAM for IaC.

## 6. User Stories & Acceptance Criteria

### Epic A — Answer "Is GitHub down?" on demand (Phase 1)
- **A1.** As an engineer, when I `@github_status_bot` in a channel, I see a reply within 3 seconds telling me up/down with attribution.
  - *AC*: F1, F3 satisfied.
- **A2.** As an engineer, if GitHub is down, the reply tells me roughly how long.
  - *AC*: F4 satisfied; duration within ±2 minutes of `started_at`.
- **A3.** As a user, if the GitHub Status API is unreachable, the bot tells me it couldn't check.
  - *AC*: F5 satisfied; explicit "couldn't check right now" — never a fabricated "up."

### Epic B — Don't be annoying (Phase 1)
- **B1.** As a channel member, the bot never speaks unless tagged.
  - *AC*: 24h manual soak in a busy channel — zero unsolicited messages.
- **B2.** As an admin, the bot doesn't post duplicate replies if Slack retries an event.
  - *AC*: Idempotency key = Slack `event_id`; retry header handled correctly.

### Epic C — Don't lie (Phase 1)
- **C1.** As a user, the bot never says "down" without citing the indicator or incident that triggered it.
  - *AC*: Verdict-function unit tests assert source-attribution invariant.

### Epic D — Proactive outage notification (Phase 2)
- **D1.** As a team member, I receive an alert in `#<alert-channel>` when GitHub goes down, without having to ask.
  - *AC*: P1, P2 satisfied; alert posted within one polling interval of status change.
- **D2.** As a team member, I receive a recovery notice when GitHub comes back up.
  - *AC*: P3 satisfied.
- **D3.** As an admin, I don't get spammed with repeated alerts during a prolonged outage.
  - *AC*: P4 satisfied; exactly 1 alert per state transition.

### Edge Cases & Error Scenarios
- Slack retries the same event → idempotency on `event_id`.
- GitHub Status API returns 500 → "couldn't check right now," never assumed-up.
- GitHub Status `incidents` array present but `started_at` missing → report down without duration.
- Bot mentioned in a thread → reply in thread, not channel root.
- Cold start exceeds Slack's 3s ack window → ack first, post reply after.
- Phase 2: DynamoDB write fails during state transition → log error, do not post alert (avoids phantom alerts on next poll).
- Phase 2: Poller and mention handler observe different states momentarily (race) → acceptable; each uses live data.

## 7. Implementation Roadmap

### Phase 1 — MVP (target: ~1.5 weeks, single developer + Claude Code)

**Week 1 — Core logic & bot**
- Day 1: Repo scaffold (uv, ruff, mypy, pytest). Pure-function verdict module + unit tests.
- Day 2: GitHub Status fetcher + tests against fixture JSONs (status.json + unresolved.json).
- Day 3: Slack bolt handler wiring `app_mention` → verdict → reply. Socket-mode runner. Install bot in workspace.
- Day 4: Error paths (API unreachable, malformed response, missing `started_at`) + copy finalization.
- Day 5: Integration tests with recorded Slack payloads and mocked HTTP responses.

**Week 2 — Harden & validate**
- Day 6: Idempotency for Slack retries, rate-limit guard.
- Day 7: Soak test in workspace; finalize copy.
- Day 8: README, `.env.example`, run instructions. Buffer for any issues.

### Phase 2 — Proactive Alerting (target: ~1 week, after Phase 1 stable for ≥2 weeks)
- Day 1: JSON file state model + unit tests for state-transition logic (up→down, down→up, no change).
- Day 2: Background asyncio poller task running alongside the Phase 1 bot.
- Day 3: Alert and recovery message formatting + integration tests.
- Day 4: Validate end-to-end in workspace (temporarily set `POLL_INTERVAL_MINUTES=1` to test).
- Day 5: Tune interval default, monitor for noise.

### Risk Mitigation per Phase
- **Phase 1**: GitHub Status API outage → bot reports "couldn't check"; never fails silently.
- **Phase 2**: DynamoDB write failure on state change → do not post alert; log and retry next poll. Prevents phantom duplicate alerts on recovery.

## 8. Definition of Done

### Phase 1 MVP Ready Criteria
- All F1–F5 acceptance criteria pass in production Slack workspace.
- All Epic A/B/C acceptance criteria pass.
- Manual test: 20 consecutive `@`-mentions — every reply correct, none missing, none duplicated.

### Phase 2 Ready Criteria
- All P1–P5 and Epic D acceptance criteria pass.
- End-to-end test: deploy with low poll interval, confirm alert fires within one interval of a real or simulated status change, confirm recovery message fires on resolution, confirm no duplicate alerts during sustained "down."

### Technical Performance Standards
- Phase 1 p50 reply time ≤ 3s, p95 ≤ 8s.
- Lambda error rate < 0.5% over 7-day window.
- Phase 2 poller error rate < 1% (transient API failures are retried; persistent failures alarm).

### Integration & Deployment Standards
- Bot started with a single command: `uv run python -m github_status_bot.slack_handler`.
- Credentials in `.env` on the host machine — never committed to git. `.env.example` documents all required variables.
- Slack app manifest checked into repo so app config is reproducible.

### Code Quality Standards
- `ruff` clean, `mypy --strict` clean, `pytest` green.
- Coverage ≥ 85% overall; 100% on verdict and state-transition modules.
- Every external HTTP call mocked in unit tests; live calls only in a separately tagged integration suite.
- README covers: prerequisites, running the bot, rotating Slack tokens, configuring `POLL_INTERVAL_MINUTES` and `ALERT_CHANNEL_ID`.

### User Validation
- 1-week trial in primary engineering Slack workspace with ≥10 distinct users.
- Phase 1 survey target: "Did the bot ever lie to you?" = 0 yes; "Was it faster than checking yourself?" ≥ 80% yes.

## 9. Success Criteria & Metrics

### Development Velocity
- Phase 1 MVP delivered in ≤ 2 weeks of focused work.
- Phase 2 delivered in ≤ 1 week after Phase 1 stabilizes.

### Quality Assurance
- Zero P1 incidents (false "up" during real outage, false "down" during normal operation) in first 30 days per phase.
- ≥ 99% successful reply rate for Phase 1 mentions.
- ≥ 99% alert delivery rate for Phase 2 (every outage onset generates exactly one alert).

### User Experience
- ≥ 80% of users prefer the bot to checking manually (Phase 1 survey).
- Zero complaints about unsolicited messages in Phase 1.
- Zero duplicate outage alerts in Phase 2.

## 10. Risk Assessment

### Technical Risks
- **R1 — GitHub Status API lags real outages**. GitHub's own status page is the only source; it is known to sometimes lag user-reported problems by several minutes.
  - *Likelihood*: medium. *Impact*: medium (bot says "up" while some engineers are seeing errors).
  - *Mitigation*: Acknowledged trade-off — Down Detector was evaluated and found technically infeasible (Cloudflare blocks server-side scraping). The bot's replies note it reflects GitHub's official status, setting correct expectations.
- **R2 — Process restarts** drop in-flight events; socket mode reconnects automatically, but an event received during reconnect may be missed.
  - *Likelihood*: low. *Impact*: low (missed mention yields no reply; user can re-mention).
  - *Mitigation*: slack-bolt handles reconnection transparently; idempotency on `event_id` prevents duplicates on replay.
- **R3 — JSON state file unreadable or corrupt during Phase 2 poll** — poller can't determine prior state.
  - *Likelihood*: very low. *Impact*: medium (could send a duplicate alert on next poll).
  - *Mitigation*: On read/parse failure, poller skips the alert decision and logs an error. File is small and written atomically to minimise corruption risk.

### Product Risks
- **R4 — False "up" during a real outage** undermines trust.
  - *Likelihood*: low-medium (GitHub's lag, per R1). *Impact*: high.
  - *Mitigation*: Reply copy always says "per GitHub's official status page" so users understand the data source and its limitations.
- **R5 — Phase 2 alert fatigue** if GitHub has a prolonged degraded period with rapid indicator fluctuations.
  - *Likelihood*: low. *Impact*: medium.
  - *Mitigation*: P4 deduplication ensures exactly one alert per transition. If rapid oscillation becomes a problem, a minimum-time-between-alerts cooldown can be added as a follow-on.
- **R6 — Bot stops being used** because users don't remember the `@` handle.
  - *Likelihood*: medium. *Impact*: low (Phase 2 proactive alerting reduces reliance on recall anyway).
  - *Mitigation*: Pin a one-liner in `#engineering`. Phase 2 proactive alerts keep the bot visible.

---

*This document is the single source of truth for `github_status_bot`. Use git for all revisions — do not version this file via filename.*
