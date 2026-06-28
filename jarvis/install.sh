#!/usr/bin/env bash
#
# install.sh — clean local installer for Jarvis, your local personal AI assistant.
#
# This script is intentionally minimal and fully local:
#   - NO telemetry, NO analytics, NO beacons.
#   - NO `curl | bash` of remote scripts, NO hardcoded IPs, NO network calls
#     except the pip install of the local package (which fetches the 'anthropic'
#     dependency from PyPI).
#
# What it does:
#   1. Refuses to run as root.
#   2. Requires python3 (>= 3.9).
#   3. Creates a virtualenv at $JARVIS_HOME/.venv (default ~/.jarvis/.venv).
#   4. pip-installs the jarvis package from this directory into that venv.
#   5. Symlinks the venv's 'jarvis' entry point into ~/.local/bin/jarvis.
#   6. Reminds you to set ANTHROPIC_API_KEY and to put ~/.local/bin on PATH.

set -euo pipefail

# --- Refuse to run as root -------------------------------------------------
if [ "$(id -u)" -eq 0 ]; then
    echo "Error: do not run this installer as root." >&2
    echo "Jarvis installs into your user home (~/.jarvis and ~/.local/bin)." >&2
    exit 1
fi

# --- Locate this script's directory (the project root) ---------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Require python3 -------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found on your PATH." >&2
    echo "Please install Python 3.9 or newer and try again." >&2
    exit 1
fi

# --- Resolve install locations ---------------------------------------------
JARVIS_HOME="${JARVIS_HOME:-$HOME/.jarvis}"
VENV_DIR="$JARVIS_HOME/.venv"
BIN_DIR="$HOME/.local/bin"

echo "Installing Jarvis..."
echo "  Project dir : $SCRIPT_DIR"
echo "  Jarvis home : $JARVIS_HOME"
echo "  Virtualenv  : $VENV_DIR"
echo "  Launcher    : $BIN_DIR/jarvis"
echo

# --- Create the virtualenv -------------------------------------------------
mkdir -p "$JARVIS_HOME"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtualenv at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
else
    echo "Reusing existing virtualenv at $VENV_DIR"
fi

# --- Install the package into the venv -------------------------------------
echo "Upgrading pip and installing the jarvis package ..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install "$SCRIPT_DIR"

# --- Symlink the entry point into ~/.local/bin -----------------------------
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/jarvis" "$BIN_DIR/jarvis"

echo
echo "Jarvis installed successfully."
echo

# --- Post-install guidance -------------------------------------------------
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "Next step: set your Anthropic API key so Jarvis can talk to the Claude API:"
    echo
    echo "    export ANTHROPIC_API_KEY=\"sk-ant-...\""
    echo
    echo "Add that line to your shell profile (~/.bashrc, ~/.zshrc, etc.) to persist it."
    echo
fi

case ":$PATH:" in
    *":$BIN_DIR:"*)
        : # already on PATH
        ;;
    *)
        echo "Note: $BIN_DIR is not on your PATH."
        echo "Add it so you can run 'jarvis' from anywhere:"
        echo
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo
        echo "Add that line to your shell profile to persist it."
        echo
        ;;
esac

echo "Then just run:  jarvis"
