#!/usr/bin/env bash
# C3Poh one-line installer
# curl -fsSL https://raw.githubusercontent.com/andyuninvited/c3poh_for_claudecode/main/install.sh | bash

set -euo pipefail

REPO="https://github.com/andyuninvited/c3poh_for_claudecode"
PYPI_NAME="c3poh-for-claudecode"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  C3Poh Installer - Claude Code Comms ║"
echo "╚══════════════════════════════════════╝"
echo ""

if ! command -v python3 &>/dev/null; then
  echo "❌  python3 not found. Install Python 3.9+: https://python.org"
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓  Python $PYTHON_VERSION found"

if ! command -v claude &>/dev/null; then
  echo "⚠️   claude CLI not found."
  echo "    Install Claude Code first: https://claude.ai/code"
fi

echo ""
echo "Installing C3Poh..."

if pip3 install --quiet --upgrade "$PYPI_NAME" 2>/dev/null; then
  echo "✓  Installed from PyPI"
else
  echo "PyPI unavailable, installing from GitHub..."
  pip3 install --quiet --upgrade "git+$REPO.git"
  echo "✓  Installed from GitHub"
fi

if ! command -v c3poh &>/dev/null; then
  if python3 -m c3poh --version &>/dev/null; then
    C3POH_CMD="python3 -m c3poh"
  else
    echo "❌  Install succeeded but 'c3poh' command not found."
    exit 1
  fi
else
  C3POH_CMD="c3poh"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  C3Poh installed! 🤖📡"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Before you start, get a Telegram bot token:"
echo "  1. Open Telegram → search @BotFather"
echo "  2. Send /newbot and follow the prompts"
echo "  3. Copy the token"
echo ""
echo "Then run setup:"
echo "  $C3POH_CMD init"
echo ""
echo "Or start directly:"
echo "  TELEGRAM_BOT_TOKEN=your_token $C3POH_CMD start"
echo ""
echo "Docs: $REPO"
echo ""
