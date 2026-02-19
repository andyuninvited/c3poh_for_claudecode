"""
C3Poh CLI entry point.
Usage: python -m c3poh [command] [options]
       c3poh [command] [options]   (after pip install)
"""

import argparse
import sys
from pathlib import Path

from .config import C3PohConfig, DM_POLICIES, DM_POLICY_ALLOWLIST


def cmd_start(args, config: C3PohConfig):
    """Start the C3Poh bot (Telegram polling + notify server)."""
    from .telegram_bot import TelegramBot
    from .notify_server import NotifyServer

    bot = TelegramBot(config)

    # Start notify server (TinMan integration)
    server = NotifyServer(
        host=config.notify_host,
        port=config.notify_port,
        callback=bot.notify_all_allowed,
    )
    server.start()

    # Run bot (blocking)
    try:
        bot.run()
    finally:
        server.stop()


def cmd_init(args, config: C3PohConfig):
    """Interactive first-time setup."""
    print("\n╔══════════════════════════════════════╗")
    print("║  C3Poh Setup - Claude Code Comms     ║")
    print("╚══════════════════════════════════════╝\n")
    print("You'll need a Telegram bot token. Get one from @BotFather on Telegram.")
    print("  1. Open Telegram, search @BotFather")
    print("  2. Send /newbot, follow prompts")
    print("  3. Copy the token (looks like: 123456789:ABCdef...)\n")

    token = input("Telegram bot token: ").strip()
    if not token:
        print("❌ Token is required.")
        sys.exit(1)

    print("\nDM policy (who can message the bot):")
    print("  allowlist  - only your Telegram user ID (recommended)")
    print("  pairing    - first person to /start becomes owner")
    print("  open       - anyone (⚠️ dangerous)\n")

    policy = input("DM policy [allowlist]: ").strip().lower() or "allowlist"
    if policy not in DM_POLICIES:
        print(f"Unknown policy '{policy}', using 'allowlist'.")
        policy = "allowlist"

    allow_from = []
    if policy == DM_POLICY_ALLOWLIST:
        print("\nYour numeric Telegram user ID:")
        print("  Get it by messaging @userinfobot on Telegram")
        uid_input = input("Your Telegram user ID: ").strip()
        if uid_input:
            allow_from = [uid_input]
        else:
            print("⚠️  No user ID provided. Add it later in c3poh.json: allow_from")

    cfg = C3PohConfig(
        telegram_bot_token=token,
        dm_policy=policy,
        allow_from=allow_from,
    )

    config_path = str(Path.home() / ".c3poh" / "config.json")
    saved = cfg.save(config_path)
    print(f"\n[C3Poh] Config saved (token NOT saved to disk - use env var)")
    print(f"[C3Poh] Config at: {saved}")
    print(f"\n[C3Poh] To start the bot, run:")
    print(f"  TELEGRAM_BOT_TOKEN='{token}' c3poh start")
    print(f"\nOr set the env var permanently:")
    print(f"  export TELEGRAM_BOT_TOKEN='{token}'  # add to ~/.zshrc")
    print(f"  c3poh start\n")


def cmd_test(args, config: C3PohConfig):
    """Test Telegram connection and send a test message."""
    errors = config.validate()
    fatal = [e for e in errors if not e.startswith("WARNING")]
    if fatal:
        for e in fatal:
            print(f"❌ {e}")
        sys.exit(1)

    from .telegram_bot import TelegramBot, TelegramError
    bot = TelegramBot(config)

    try:
        me = bot.get_me()
        print(f"✓ Connected as @{me.get('username')} ({me.get('first_name')})")
    except TelegramError as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    if args.send_to:
        try:
            bot.send_message(int(args.send_to), "👋 C3Poh test message. If you received this, it's working!")
            print(f"✓ Test message sent to {args.send_to}")
        except (TelegramError, ValueError) as e:
            print(f"❌ Send failed: {e}")
            sys.exit(1)


def cmd_status(args, config: C3PohConfig):
    """Show current C3Poh config (token redacted)."""
    print(f"[C3Poh] DM policy:      {config.dm_policy}")
    print(f"[C3Poh] Allow from:     {config.allow_from or '(none)'}")
    print(f"[C3Poh] Notify port:    {config.notify_host}:{config.notify_port}")
    print(f"[C3Poh] Claude timeout: {config.claude_timeout_seconds}s")
    print(f"[C3Poh] Token set:      {'yes' if config.telegram_bot_token else 'NO - set TELEGRAM_BOT_TOKEN'}")

    errors = config.validate()
    if errors:
        print()
        for e in errors:
            prefix = "⚠️ " if e.startswith("WARNING") else "❌ "
            print(f"  {prefix}{e}")


def main():
    parser = argparse.ArgumentParser(
        prog="c3poh",
        description="C3Poh - Telegram bridge for Claude Code. Because CC needed a comms droid.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  init      Interactive first-time setup (start here)
  start     Start the bot (Telegram polling + notify server)
  test      Test Telegram connection
  status    Show current configuration

examples:
  c3poh init
  TELEGRAM_BOT_TOKEN=your_token c3poh start
  c3poh test --send-to 123456789
  c3poh status
        """,
    )
    parser.add_argument("--config", "-c", help="Path to config JSON file")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Interactive first-time setup")

    sub.add_parser("start", help="Start the bot")

    p_test = sub.add_parser("test", help="Test Telegram connection")
    p_test.add_argument("--send-to", metavar="USER_ID", help="Send a test message to this Telegram user ID")

    sub.add_parser("status", help="Show configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    config = C3PohConfig.load(args.config)

    dispatch = {
        "init": cmd_init,
        "start": cmd_start,
        "test": cmd_test,
        "status": cmd_status,
    }
    dispatch[args.command](args, config)


if __name__ == "__main__":
    main()
