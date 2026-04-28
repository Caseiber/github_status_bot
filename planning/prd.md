# Product Requirements Document — Dev Tools Status Slack Bot

## 1. Executive Summary

- **Project Name & Version**: `github_status_bot` — v0.1 (MVP draft)
- **Date & Status**: 2026-04-28 — In development — Phase 1 (E001–E005 complete, component-status display implemented); Phase 3 requirements added
- **Vision Statement**: Give engineers an instant, authoritative answer to "is [service] actually down?" without leaving Slack — starting with GitHub, extending to any development tool the team relies on — and proactively alert the team the moment any configured service reports an outage.
- **Success Metrics**:
  1. **Zero false alarms** — bot reports "down" only when the service's own status API confirms it.
  2. **Phase 1: Zero unsolicited messages** — in Phase 1 the bot speaks only in direct response to an `@github_status_bot` mention, exactly once per mention.
  3. **Source-truthful answers** — every response reflects live data fetched at request time; no fabricated answers.
  4. **Sub-3-second median response time** from `@`-mention to Slack message posted (Phase 1).
  5. **Phase 2: Proactive alerting** — team is notified in a designated channel within one polling interval of GitHub reporting an outage.
  6. **Phase 3: Multi-service coverage** — engineers can check any configured development tool (initially GitHub and Claude) with a single mention; adding a new service requires no code changes.

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
- Bot fetches `https://www.githubstatus.com/api/v2/status.json` and `https://www.githubstatus.com/api/v2/incidents/unresolved.json` concurrently on every mention.
- Bot also fetches `https://www.githubstatus.com/api/v2/components.json`; failure is non-fatal and results in no component detail in the reply.
- "Down" is defined as `status.indicator` ∈ {`minor`, `major`, `critical`} OR any incident in the unresolved list with `resolved_at: null`.
- Duration uses the incident's `started_at` field.
- Affected components = any component with status in {`degraded_performance`, `partial_outage`, `major_outage`}.
- *Acceptance*: When indicator is `none` and incidents array is empty, bot reports "up." When indicator is `major`, bot reports "down" with duration derived from `started_at` and lists any non-operational components.

**F3 — Verdict and source attribution**
- The reply uses a structured multi-line format. Source is a Slack mrkdwn hyperlink to `https://www.githubstatus.com`.
- Down reply includes: opening line, blank line, optional `Affected Area` (non-operational components), `Severity` label (`Degraded` / `Major Outage` / `Critical Outage`), optional `Time Down`, blank line, `Source` hyperlink.
- Up reply: opening line, blank line, `Source` hyperlink.
- Example down reply:
  ```
  GitHub is *down* because AI DevOps is a blight on our land.

  Affected Area: Git Operations
  Severity: Degraded
  Time Down: ~2h 12m

  Source: <https://www.githubstatus.com|GitHub's status page>
  ```
- *Acceptance*: Every reply contains an explicit source hyperlink. Replies never assert "down" without a Severity line. `Affected Area` line present iff at least one non-operational component exists.

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

### Phase 3 — Multi-Service Status Checks

**M1 — Service registry**
- The bot maintains a registry of status services to check. Each entry has a short name (e.g. `github`, `claude`), a `status.json` URL, and an `incidents/unresolved.json` URL (Statuspage.io shape, which both GitHub and Claude use).
- The default registered services are `github` (`https://www.githubstatus.com/api/v2`) and `claude` (`https://status.claude.com/api/v2`).
- Additional services can be added via environment variable without code changes: `STATUS_SERVICES=github,claude,linear` plus per-service base-URL vars (e.g. `STATUS_URL_LINEAR=https://linea...`).
- *Acceptance*: Adding a new service name and its base URL to the environment causes the bot to check that service on next mention.

**M2 — Named-service query**
- When the mention text includes a recognised service name (e.g. `@github_status_bot claude`), the bot checks and replies with only that service's status, using the same verdict + duration format as Phase 1.
- When the mention includes an unrecognised name, the bot replies with the list of available service names.
- *Acceptance*: `@github_status_bot claude` returns Claude's status only. `@github_status_bot foobar` returns a "I don't know that service — available: github, claude" reply.

**M3 — All-services query**
- When the mention contains no service name (or the word `all`), the bot checks all configured services concurrently and replies with a combined summary — one line per service.
- Concurrency model mirrors Phase 1: both endpoints for each service are fetched concurrently, subject to the same 2 s timeout and single-retry policy.
- *Acceptance*: With GitHub and Claude configured, a bare `@github_status_bot` mention returns a reply with one status line per service.

**M4 — Backward compatibility**
- A bare `@github_status_bot` mention continues to return GitHub's status as the first (or only) line of the reply. If GitHub is the only configured service, the reply is functionally identical to Phase 1.
- *Acceptance*: Existing Phase 1 users who don't change their mention text see no regression.

**M5 — Phase 2 poller extended to all services**
- The Phase 2 background poller checks every configured service on each poll interval. Per-service state is stored independently in the JSON state file (keyed by service name).
- A transition on any service triggers an appropriately labelled alert in `ALERT_CHANNEL_ID`. Services that have not transitioned produce no alert.
- *Acceptance*: With GitHub and Claude configured — if only GitHub transitions to "down," exactly one alert is posted for GitHub; Claude's state is unchanged and no Claude alert fires.

**M6 — Multi-service reply format**
- All-services reply: one line per service. Each line states the service name, verdict, and attribution. Example:
  ```
  *GitHub*: up — all systems operational (source: GitHub's official status page)
  *Claude*: down — indicator: major, ~12m (source: Claude's official status page)
  ```
- Single-service reply: same as Phase 1 format with the service name substituted for "GitHub."
- Per-service error: one "couldn't check [service] right now" line per unreachable endpoint; other services in the reply are unaffected.
- *Acceptance*: Every line in a multi-service reply independently identifies its source and verdict.

## 4. Technical Architecture

### Technology Stack
- **Language**: Python 3.12.
- **Slack framework**: `slack-bolt` (Python) in socket mode — the bot connects outbound to Slack's WebSocket API; no inbound HTTP server or public URL required.
- **HTTP**: `httpx` (async, timeouts, retries) for all status API calls.
- **Hosting (Phase 1)**: Long-running process on a team-managed machine. Started via `uv run python -m github_status_bot.slack_handler`. No cloud infrastructure required.
- **Hosting (Phase 2 addition)**: Background `asyncio` task running in the same process as Phase 1. No additional infrastructure.
- **Hosting (Phase 3)**: No new infrastructure. Service registry and fetcher abstraction live in the same process; Phase 3 extends the existing fetcher module.
- **Secrets**: `.env` file on the host machine (never committed to git). Variables: `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`.
- **Phase 2 persistence**: JSON file on disk for polling state — `{<service_name>: {indicator: <str>, last_alerted_at: <unix>}, ...}` (keyed by service name from Phase 3 onward).
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
- **Outbound (Phases 1–2)**:
  - `GET https://www.githubstatus.com/api/v2/status.json`
  - `GET https://www.githubstatus.com/api/v2/incidents/unresolved.json`
  - `GET https://www.githubstatus.com/api/v2/components.json` (optional — failure is non-fatal)
  - `POST https://slack.com/api/chat.postMessage`
- **Outbound (Phase 3 additions)**:
  - `GET https://status.claude.com/api/v2/status.json`
  - `GET https://status.claude.com/api/v2/incidents/unresolved.json`
  - Any additional service endpoints configured via environment variables
- **Persistence (Phase 2+)**: JSON file on disk — `{<service_name>: {indicator: <str>, last_alerted_at: <unix>}, ...}`.

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

### Epic E — Check any dev tool on demand (Phase 3)
- **E1.** As an engineer, I can type `@github_status_bot claude` and receive Claude's status without knowing which URL to visit.
  - *AC*: M2 satisfied; reply attributes to Claude's official status page.
- **E2.** As an engineer, typing `@github_status_bot` (no service name) shows me the status of all configured tools in one reply.
  - *AC*: M3 satisfied; one line per service, all fetched concurrently.
- **E3.** As an engineer, my existing `@github_status_bot` workflow for GitHub is unchanged.
  - *AC*: M4 satisfied; bare mention still includes GitHub's status.
- **E4.** As a team member, I'm alerted in the designated channel when Claude goes down, just as I am for GitHub.
  - *AC*: M5 satisfied; per-service transition alerts fire independently.
- **E5.** As an admin, I can add a new service (e.g., Linear) by setting two environment variables, with no code changes.
  - *AC*: M1 satisfied; bot checks the new service on next restart.

### Edge Cases & Error Scenarios
- Slack retries the same event → idempotency on `event_id`.
- GitHub Status API returns 500 → "couldn't check right now," never assumed-up.
- GitHub Status `incidents` array present but `started_at` missing → report down without duration.
- Bot mentioned in a thread → reply in thread, not channel root.
- Cold start exceeds Slack's 3s ack window → ack first, post reply after.
- Phase 2: DynamoDB write fails during state transition → log error, do not post alert (avoids phantom alerts on next poll).
- Phase 2: Poller and mention handler observe different states momentarily (race) → acceptable; each uses live data.
- Phase 3: One service's API is unreachable while another's succeeds → reply includes the successful result and a "couldn't check [service]" line for the failed one; never suppress partial results.
- Phase 3: A configured service's response shape diverges from the expected Statuspage.io schema → treat as a fetch error for that service; log the parse failure; other services unaffected.
- Phase 3: User types a service name with different casing (e.g. `Claude`) → match case-insensitively.

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

### Phase 3 — Multi-Service Status Checks (target: ~1 week, after Phase 2 stable for ≥2 weeks)
- Day 1: Abstract the GitHub-specific fetcher into a generic `StatusClient(base_url)`. Add service registry (env-var driven). Unit tests for registry loading and generic fetcher.
- Day 2: Update mention handler to parse service name from mention text; route to named-service or all-services path. Unit tests for routing logic.
- Day 3: Add Claude as a registered service; validate response shape against `https://status.claude.com/api/v2`. Update fixtures.
- Day 4: Extend Phase 2 poller to iterate over all registered services; extend state file schema to key by service name. Migrate existing GitHub state entry.
- Day 5: Integration tests for multi-service all-services reply, single-service named query, partial-failure reply, and poller multi-service transitions. Validate end-to-end in workspace.

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

### Phase 3 Ready Criteria
- All M1–M6 acceptance criteria pass in production Slack workspace.
- All Epic E acceptance criteria pass.
- Manual test: `@github_status_bot`, `@github_status_bot github`, `@github_status_bot claude`, `@github_status_bot all`, and `@github_status_bot foobar` each return the correct response.
- Adding a third service via environment variables (no code change) and restarting the bot causes it to appear in all-services replies.

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
- **R7 — Claude status API response shape diverges from Statuspage.io standard**.
  - *Likelihood*: low (Anthropic uses Statuspage.io, which has a stable schema). *Impact*: medium (Claude status silently treated as an error).
  - *Mitigation*: Validate response shape in the generic fetcher and log a descriptive parse error; surface it in the bot reply so the failure is visible rather than silent.
- **R8 — Combined all-services reply becomes verbose** as more services are added.
  - *Likelihood*: medium if team adds many services. *Impact*: low (annoying but not incorrect).
  - *Mitigation*: Keep default service list short (GitHub + Claude). Consider a compact one-liner-per-service format; if the list grows, a "summary" mode (e.g. show only degraded services) can be added as a follow-on.
- **R9 — State file schema migration** when Phase 3 re-keys the JSON by service name, breaking any existing Phase 2 state file.
  - *Likelihood*: high (schema change is intentional). *Impact*: low (worst case: one spurious alert on first Phase-3 poll due to missing prior state).
  - *Mitigation*: On first read after upgrade, if the file is in the old single-service shape, treat prior state as unknown for all services (triggers at most one alert per service if they happen to be down at that moment).

---

*This document is the single source of truth for `github_status_bot`. Use git for all revisions — do not version this file via filename.*
