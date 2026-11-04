#!/usr/bin/env bash
# Replay a recorded history on the running stack, so the dam SCADA and the CH viewer show it.
#
#   rca-demo/replay.sh [scenario] [replay_history.py options]
#
#   scenario   folder under rca-demo/history/ (default scenario-A)
#   options    e.g. --from "2026-11-03 08:00" --speed 60 --slow-speed 2 (see build/replay_history.py)
#
# Stops dam-sim and ch-plc-sim for the replay (otherwise they publish the live trees over it) and
# starts them again afterwards, also on Ctrl-C. The replay runs in the tests image on the compose
# network, with the working tree mounted.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCEN="scenario-A"
if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then SCEN="$1"; shift; fi
HIST="rca-demo/history/$SCEN/historian"
[ -d "$REPO/$HIST" ] || { echo "no $HIST" >&2; exit 1; }

cd "$REPO"
docker compose ps --status running --services | grep -qx dam-scada \
  || { echo "the stack is not running: docker compose up -d --build" >&2; exit 1; }
docker compose stop dam-sim ch-plc-sim
trap 'echo "starting the simulators again"; docker compose start dam-sim ch-plc-sim >/dev/null' EXIT

echo "SCADA  http://localhost:${CH_HUB_PORT:-8120}/scada#unit/Unit1"
echo "Viewer http://localhost:${CH_VIEWER_PORT:-8122}/#CH-FR-1987-0042"
docker compose run --rm tests python -u rca-demo/build/replay_history.py --history "$HIST" "$@"
