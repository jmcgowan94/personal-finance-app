#!/usr/bin/env bash
#
# Starts Personal Finance. The first run also installs everything it needs.
#
#   ./start.sh          start the app and open it in your browser
#   ./start.sh --demo   also load made-up example data to try it out
#
# Nothing is installed system-wide and no administrator password is needed:
# tools go in your home folder (uv) or in this folder (.tools/).

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

PORT="${PORT:-8000}"
URL="http://localhost:$PORT"
NODE_VERSION="22.12.0"
TOOLS_DIR="$APP_DIR/.tools"

# ---------------------------------------------------------------- helpers ---

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }

fail() {
  printf '\n\033[1;31mSomething went wrong:\033[0m %s\n' "$*"
  printf '\nIf you get stuck, copy everything in this window and ask for help.\n'
  pause_before_exit
  exit 1
}

pause_before_exit() {
  # When started by double-clicking, keep the window open so messages can be read.
  if [ -t 0 ]; then
    read -r -p "Press Enter to close this window..." _ || true
  fi
}

trap 'fail "the step above did not finish (line $LINENO)."' ERR

open_browser() {
  if command -v open >/dev/null 2>&1; then
    open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  else
    info "Open this address in your web browser: $URL"
  fi
}

# Run a command quietly; show its output only if it fails.
quietly() {
  local log
  if ! log=$("$@" 2>&1); then
    printf '%s\n' "$log"
    return 1
  fi
}

app_is_running() {
  curl -fsS "$URL/api/health" 2>/dev/null | grep -q '"ok"'
}

port_in_use() {
  (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null
}

# ------------------------------------------------------------ preflight ---

say "Personal Finance"

if app_is_running; then
  info "The app is already running. Opening it in your browser..."
  open_browser
  exit 0
fi
if port_in_use; then
  fail "another program is using port $PORT. Close it, or start with a different port: PORT=8001 ./start.sh"
fi

command -v curl >/dev/null 2>&1 || fail "the 'curl' program is required but was not found."

case "$(uname -s)" in
  Darwin) OS=darwin ;;
  Linux)  OS=linux ;;
  *) fail "this script supports macOS and Linux only." ;;
esac
case "$(uname -m)" in
  arm64|aarch64) ARCH=arm64 ;;
  x86_64|amd64)  ARCH=x64 ;;
  *) fail "unsupported processor type: $(uname -m)" ;;
esac

# ------------------------------------------------------------------- uv ---
# uv installs Python and the app's Python packages.

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv (manages Python for this app)..."
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
  command -v uv >/dev/null 2>&1 || fail "uv could not be installed."
fi

# ----------------------------------------------------------------- Node ---
# Node.js is only needed to build the web pages. Use the computer's copy if it
# is recent enough; otherwise download a private copy into .tools/.

node_ok() {
  command -v node >/dev/null 2>&1 &&
    [ "$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -ge 20 ]
}

NODE_DIR="$TOOLS_DIR/node-v$NODE_VERSION-$OS-$ARCH"
if [ -x "$NODE_DIR/bin/node" ]; then
  export PATH="$NODE_DIR/bin:$PATH"
elif ! node_ok; then
  say "Downloading Node.js $NODE_VERSION (builds the web pages)..."
  mkdir -p "$TOOLS_DIR"
  curl -fL --progress-bar "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-$OS-$ARCH.tar.gz" \
    | tar -xz -C "$TOOLS_DIR"
  export PATH="$NODE_DIR/bin:$PATH"
  node_ok || fail "Node.js could not be set up."
fi

# ------------------------------------------------------------ app setup ---

say "Checking the app is up to date (the first run takes a few minutes)..."

info "Python packages..."
(cd backend && uv sync --quiet)

# Rebuild the web pages only when they have changed since the last build.
needs_build() {
  [ ! -f frontend/dist/index.html ] ||
    [ -n "$(find frontend/src frontend/index.html frontend/package-lock.json frontend/vite.config.ts \
            -newer frontend/dist/index.html -print -quit)" ]
}
if [ ! -d frontend/node_modules ] || [ frontend/package-lock.json -nt frontend/node_modules/.package-lock.json ]; then
  info "Web page packages..."
  (cd frontend && quietly npm ci --no-audit --no-fund --no-update-notifier)
  rm -f frontend/dist/index.html  # force a rebuild with the new packages
fi
if needs_build; then
  info "Building the web pages..."
  (cd frontend && quietly npx --no-install vite build)
fi

info "Database..."
(cd backend && quietly uv run alembic upgrade head) || fail "the database could not be prepared."


if [ "${1:-}" = "--demo" ]; then
  info "Loading example data..."
  (cd backend && quietly uv run python -m app.scripts.seed_demo)
fi

# ---------------------------------------------------------------- start ---

say "Starting Personal Finance at $URL"
info "Your data is stored in: $APP_DIR/data"
info ""
info "Keep this window open while you use the app."
info "To stop the app, close this window or press Control+C."

trap - ERR
(
  # Open the browser once the server is answering.
  for _ in $(seq 1 60); do
    if app_is_running; then open_browser; exit 0; fi
    sleep 0.5
  done
) &

cd backend
exec uv run uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --log-level warning
