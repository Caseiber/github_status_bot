# github_status_bot

A Slack bot that reports GitHub's live operational status on demand. Tag it in a channel and it replies immediately with the current verdict, which components are affected, how long the outage has been ongoing, and a link to GitHub's status page.

```
@github_status_bot

GitHub is *down* because AI DevOps is a blight on our land.

Affected Area: Git Operations
Severity: Degraded
Time Down: ~1h 14m

Source: GitHub's status page
```

---

## Prerequisites

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — Python package manager
- **[tmux](https://github.com/tmux/tmux)** — keeps the bot alive after you close your terminal
  - Mac: `brew install tmux`
  - Linux: `sudo apt-get install -y tmux`
- A Slack app configured for this bot (see [Slack app setup](#slack-app-setup) below)

---

## Setup

**1. Install dependencies**

```bash
uv sync
```

**2. Create your `.env` file**

```bash
cp .env.example .env
```

Open `.env` and fill in the three values (see [where to find them](#where-to-find-the-slack-credentials) below).

---

## Running the bot

Start the bot in a background tmux session so it keeps running after you close your terminal:

```bash
tmux new-session -d -s github-bot 'uv run python -m github_status_bot.slack_handler'
```

**Check it's running:**

```bash
tmux attach -t github-bot
```

You should see slack-bolt startup logs. Detach without stopping the bot with `Ctrl-b d`.

**Stop the bot:**

```bash
tmux kill-session -t github-bot
```

**Restart after a token rotation or config change:**

```bash
tmux kill-session -t github-bot
tmux new-session -d -s github-bot 'uv run python -m github_status_bot.slack_handler'
```

---

## Slack app setup

The Slack app manifest is committed at `slack_app_manifest.yaml`. To create the app:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From a manifest**
2. Paste the contents of `slack_app_manifest.yaml`
3. Install the app to your workspace
4. Invite the bot to your channel: `/invite @github_status_bot`

### Where to find the Slack credentials

| Variable | Where to find it |
|---|---|
| `SLACK_BOT_TOKEN` | **OAuth & Permissions** → Bot User OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | **Basic Information** → App-Level Tokens → generate one with `connections:write` scope (`xapp-...`) |
| `SLACK_SIGNING_SECRET` | **Basic Information** → App Credentials → Signing Secret |

---

## Rotating Slack tokens

1. Regenerate the token in [api.slack.com/apps](https://api.slack.com/apps)
2. Update the value in `.env`
3. Restart the bot:
   ```bash
   tmux kill-session -t github-bot
   tmux new-session -d -s github-bot 'uv run python -m github_status_bot.slack_handler'
   ```

---

## Development

```bash
# Run tests (coverage gate enforced at 85%)
uv run pytest

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy --strict src/
```
