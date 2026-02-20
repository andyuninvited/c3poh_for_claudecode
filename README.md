# 📡🤖 C3Poh — Telegram Bridge for Claude Code

> *"I am fluent in over six million forms of communication."*
> C-3PO handled comms for the Rebellion. C3Poh handles comms for your Claude Code agent.

**C3Poh** lets you DM your Claude Code agent via Telegram and get answers back — from anywhere, on any device.

You're on your phone. You think of something. You message your agent. Claude Code handles it and replies. That's it.

Zero external dependencies. Allowlist-based access control baked in. Takes 5 minutes to set up.

---

## Why this exists

OpenClaw ships first-party Telegram integration with allowlist-based DM policies. Claude Code has no messaging — it's terminal-only.

C3Poh fills that gap. It's a lightweight Telegram bot that:
1. Receives your messages (allowlisted users only by default)
2. Forwards them to Claude Code via `claude --print`
3. Sends Claude's response back to you in Telegram
4. Listens for notifications from [TinMan](https://github.com/andyuninvited/tinman_for_claudecode) and forwards heartbeat alerts

---

## Install

**One-liner:**
```bash
curl -fsSL https://raw.githubusercontent.com/andyuninvited/c3poh_for_claudecode/main/install.sh | bash
```

**Or pip:**
```bash
pip install c3poh-for-claudecode
```

**Requirements:**
- Python 3.9+
- [Claude Code](https://claude.ai/code) (`claude` CLI in your PATH)
- A Telegram bot token (from [@BotFather](https://t.me/botfather) — free, takes 30 seconds)

---

## Quick start

**Step 1: Get a bot token**

1. Open Telegram → search [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow prompts
3. Copy the token (looks like `123456789:ABCdefGHI...`)

**Step 2: Find your Telegram user ID**

Message [@userinfobot](https://t.me/userinfobot) on Telegram. It replies with your numeric user ID.

**Step 3: Run setup**

```bash
c3poh init
```

Interactive prompts walk you through token, DM policy, and allowlist.

**Step 4: Start**

```bash
TELEGRAM_BOT_TOKEN=your_token_here c3poh start
```

Now DM your bot on Telegram. Claude Code replies.

---

## Commands

```
c3poh init                          Interactive first-time setup
c3poh start                         Start the bot
c3poh test                          Verify Telegram connection
c3poh test --send-to 123456789      Send a test message to yourself
c3poh status                        Show config and connection status
```

---

## DM policies (access control)

**Don't skip this. OpenClaw users get burned by leaving this on `open`.**

| Policy | Who can DM | Use when |
|--------|-----------|----------|
| `allowlist` | Only your Telegram user IDs | **default — recommended always** |
| `pairing` | First person to /start becomes owner | Single-user, no ID lookup |
| `open` | Anyone with your bot link | ⚠️ Demos only, never in production |
| `disabled` | Nobody | Notify-only mode (outbound only) |

Set via config or env var:
```bash
# Allowlist (recommended)
C3POH_ALLOW_FROM=123456789,987654321 c3poh start

# Pairing (first-user-wins)
C3POH_DM_POLICY=pairing c3poh start
```

---

## Configuration

C3Poh looks for config at `./c3poh.json` then `~/.c3poh/config.json`.

```json
{
  "dm_policy": "allowlist",
  "allow_from": ["123456789"],
  "require_mention": true,
  "notify_port": 7734,
  "notify_host": "127.0.0.1",
  "claude_timeout_seconds": 300,
  "log_messages": true
}
```

**Token is never saved to disk** — always set via env var:
```bash
export TELEGRAM_BOT_TOKEN=your_token_here
```

**Environment variable overrides:**
```bash
TELEGRAM_BOT_TOKEN=...          # required
C3POH_ALLOW_FROM=111,222        # comma-separated Telegram user IDs
C3POH_DM_POLICY=allowlist
C3POH_NOTIFY_PORT=7734
C3POH_CLAUDE_TIMEOUT=300
```

---

## TinMan integration

Pair C3Poh with [TinMan](https://github.com/andyuninvited/tinman_for_claudecode) to get heartbeat alerts on your phone:

**In TinMan's config (`tinman.json`):**
```json
{
  "notify_c3poh": true,
  "c3poh_endpoint": "http://localhost:7734/notify"
}
```

Now when TinMan detects something (disk space low, failing tests, stale branches), it sends the alert to C3Poh → you get a Telegram message.

**The full stack:**
```
[launchd/cron] → TinMan heartbeat → C3Poh → your Telegram
      ↑                                            ↓
      └──────── you DM the bot ───────────────────┘
                    Claude Code replies
```

---

## Security notes

**What C3Poh protects:**
- All traffic goes Telegram API → your machine (outbound only)
- `notify_host` defaults to `127.0.0.1` — the notify server is never public
- Bot token is never written to disk
- Blocked user IDs are logged

**What C3Poh does not do:**
- Store your messages anywhere except a local log (opt-out: `"log_messages": false`)
- Use webhooks (long-polling only — no inbound ports needed)
- Require any cloud account beyond Telegram

**What you should do:**
- Use `dm_policy: allowlist` with your user ID
- Keep your bot token in an env var or password manager, not in a file
- Don't share your bot link publicly if you care about who can use it

---

## How it works

```
You (Telegram) → Telegram API → C3Poh (long-polling)
                                    ↓
                             access check (allowlist)
                                    ↓
                            claude --print "your message"
                                    ↓
                             Claude Code response
                                    ↓
                        Telegram API → You (Telegram)
```

Long-polling (not webhooks): C3Poh calls Telegram's API every few seconds to check for new messages. No inbound ports, no reverse proxy, no ngrok. Runs from anywhere.

---

## Run tests

```bash
pip install c3poh-for-claudecode[dev]
pytest tests/ -v
```

---

## Roadmap

- [ ] v0.2: Slack support
- [ ] v0.2: Discord support
- [ ] v0.2: Message history context (multi-turn conversations)
- [ ] v0.3: `/status` and `/help` bot commands
- [ ] v0.3: File/image send support
- [ ] v1.0: Webhook mode (for production deployments)

---

## Related

- [TinMan](https://github.com/andyuninvited/tinman_for_claudecode) — Heartbeat for Claude Code (the heart to C3Poh's voice)
- [Claude Code](https://claude.ai/code) — the agentic CLI this is built for
- [OpenClaw](https://openclaw.ai) — the inspiration (Telegram + heartbeat for a different runtime)

---

## License

GNU GPLv3 — copy-left, and let's evolve together.

See [LICENSE](LICENSE) for the full text.

---

*Built by [@andyuninvited](https://github.com/andyuninvited). Star if you've ever wished you could text your agent.*
