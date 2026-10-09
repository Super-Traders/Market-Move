#!/bin/bash
# Double-click to set up (first time) and launch the screener on a Mac.
cd "$(dirname "$0")" || exit 1
echo "=================================================="
echo "   Sector Rotation Screener"
echo "=================================================="
echo

# 1. Python check
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed."
  echo "Install it (free) from https://www.python.org/downloads/  (version 3.11 or newer),"
  echo "then double-click this file again."
  echo; read -r -p "Press Return to close."; exit 1
fi

# 2. Create the environment (first time only)
if [ ! -d ".venv" ]; then
  echo "First-time setup: creating the Python environment (about a minute)..."
  python3 -m venv .venv || { echo "Could not create environment."; read -r -p "Press Return."; exit 1; }
fi

# 3. Install packages (quiet; quick after first run)
echo "Checking required packages..."
./.venv/bin/python -m pip install --quiet --upgrade pip
if ! ./.venv/bin/python -m pip install --quiet -r requirements.txt; then
  echo "Package install failed. Check your internet connection and try again."
  read -r -p "Press Return."; exit 1
fi

# 4. Stop any copy of the app already running (prevents port conflicts / "Internal Server Error")
lsof -ti tcp:8501 2>/dev/null | xargs kill -9 2>/dev/null
pkill -f "streamlit run app.py" 2>/dev/null
sleep 1

# 5. Open the browser shortly after the server starts
( sleep 6; open "http://localhost:8501" >/dev/null 2>&1 ) &

echo
echo "=================================================="
echo "  ✅ The screener is running."
echo "  It will open in your browser automatically."
echo "  If it doesn't, open this link yourself:"
echo
echo "        http://localhost:8501"
echo
echo "  >>> KEEP THIS WINDOW OPEN while you use the app. <<<"
echo "  Closing this window stops the app (that's normal)."
echo "  To use it again later, just double-click this file."
echo "=================================================="
echo

# 5. Run (config.toml makes this start with no prompts)
./.venv/bin/python -m streamlit run app.py
