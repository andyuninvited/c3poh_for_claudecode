# Telegram Setup Guide

Complete walkthrough for getting C3Poh connected to Telegram.

---

## Step 1: Create a Telegram bot

1. Open Telegram (mobile or desktop)
2. Search for **@BotFather** (the official Telegram bot for managing bots)
3. Start a chat and send: `/newbot`
4. Follow the prompts:
   - Choose a name (e.g., "My Claude Agent")
   - Choose a username (must end in `bot`, e.g., `my_claude_bot`)
5. BotFather sends you a token — looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`
6. Copy and save it somewhere safe (password manager recommended)

---

## Step 2: Find your Telegram user ID

Your Telegram user ID is a numeric identifier (not your username). C3Poh needs it for allowlist mode.

**Easiest method:**
1. Search for **@userinfobot** on Telegram
2. Send it any message
3. It replies with your user ID, e.g.: `Your user ID: 123456789`

**Alternative:**
- Use @RawDataBot

---

## Step 3: Configure C3Poh

Run the interactive setup:
```bash
c3poh init
```

Or set environment variables directly:
```bash
export TELEGRAM_BOT_TOKEN=123456789:ABCdef...
export C3POH_ALLOW_FROM=123456789
c3poh start
```

---

## Step 4: Test the connection

```bash
c3poh test --send-to 123456789  # replace with your user ID
```

If it works, you'll receive a test message in Telegram.

---

## Step 5: DM your bot

1. In Telegram, search for your bot by its username (e.g., @my_claude_bot)
2. Press **Start**
3. Send any message
4. Claude Code replies

---

## Security checklist

- [ ] `dm_policy` is set to `allowlist` (not `open`)
- [ ] Your user ID is in `allow_from`
- [ ] Bot token is in an env var, not in a committed file
- [ ] You haven't shared the bot link publicly
- [ ] `notify_host` is `127.0.0.1` (default — don't change unless you know why)

---

## Troubleshooting

**"Bot token not found"**
→ Set `TELEGRAM_BOT_TOKEN` env var before running

**"Connection failed: 401 Unauthorized"**
→ Token is wrong or revoked. Get a new one from @BotFather with `/token`

**"You're not authorized"**
→ Your user ID isn't in `allow_from`. Check your ID via @userinfobot and add to config

**Bot doesn't reply in groups**
→ `require_mention: true` means you must @mention the bot in groups. This is intentional.

**Timeout errors**
→ Increase `claude_timeout_seconds` in config (default 300s). Some Claude requests take longer.

---

## Adding the bot to a group

1. Create or open a Telegram group
2. Add your bot: Group Settings → Add Members → search for your bot username
3. Grant it admin permissions to read messages (optional, but needed if you want it to see all messages not just @mentions)
4. By default, `require_mention: true` means you must @mention the bot to trigger it

---

## Running C3Poh persistently (always-on)

**macOS (recommended: launchd)**

Create `~/Library/LaunchAgents/com.c3poh.bot.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.c3poh.bot</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>-m</string>
    <string>c3poh</string>
    <string>start</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TELEGRAM_BOT_TOKEN</key>
    <string>YOUR_TOKEN_HERE</string>
    <key>C3POH_ALLOW_FROM</key>
    <string>YOUR_USER_ID</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/YOUR_USERNAME/.c3poh/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOUR_USERNAME/.c3poh/launchd.err.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.c3poh.bot.plist
```

**Linux (systemd)**

Create `/etc/systemd/system/c3poh.service`:
```ini
[Unit]
Description=C3Poh Telegram Bridge for Claude Code
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
Environment=TELEGRAM_BOT_TOKEN=your_token_here
Environment=C3POH_ALLOW_FROM=your_user_id
ExecStart=/usr/bin/python3 -m c3poh start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable c3poh
sudo systemctl start c3poh
sudo systemctl status c3poh
```
