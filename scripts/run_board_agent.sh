#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

export RK_BOX_MODE="${RK_BOX_MODE:-auto}"
export RK_BOX_HOST="${RK_BOX_HOST:-0.0.0.0}"
export RK_BOX_PORT="${RK_BOX_PORT:-8080}"

exec python3 -m board_agent
