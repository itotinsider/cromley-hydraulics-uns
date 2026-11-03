#!/usr/bin/env bash
# RCA bot test run: build an isolated workspace, let Claude Code do the RCA, optionally grade it.
#
#   rca-demo/run_rca.sh [scenario] [--interactive] [--grade]
#
#   scenario       folder under rca-demo/history/ (default scenario-A)
#   --interactive  build the workspace and print how to start the chat yourself
#   --grade        after a headless run, score the report against ANSWER-KEY.md (separate call)
#
# The workspace lives outside the repo (Claude Code would otherwise load the repo's CLAUDE.md,
# which names the scenarios). It holds only library/, historian/ and the bot's CLAUDE.md:
# never the answer key, the simulators or run.json.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCEN="scenario-A"; MODE=headless; GRADE=0
for a in "$@"; do
  case "$a" in
    --interactive) MODE=interactive ;;
    --grade) GRADE=1 ;;
    *) SCEN="$a" ;;
  esac
done
HIST="$REPO/rca-demo/history/$SCEN"
[ -f "$HIST/run.json" ] || { echo "no $HIST/run.json: run rca-demo/build/record_history.py first" >&2; exit 1; }

WS="${CCD_RCA_WORKSPACE:-$HOME/ccd-rca}/$SCEN-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WS/work" "$WS/reports" "$WS/.claude"
cp -R "$REPO/rca-demo/library" "$WS/library"
cp -R "$HIST/historian" "$WS/historian"
cp "$REPO/rca-demo/bot/CLAUDE.md" "$WS/CLAUDE.md"
cat > "$WS/.claude/settings.json" <<EOF
{
  "permissions": {
    "allow": ["Read", "Glob", "Grep", "Write", "Edit",
              "Bash(python3:*)", "Bash(ls:*)", "Bash(head:*)", "Bash(wc:*)", "Bash(zcat:*)", "Bash(gzcat:*)"],
    "deny": ["Read(/$REPO/**)", "Grep(/$REPO/**)", "Glob(/$REPO/**)", "WebFetch", "WebSearch"]
  }
}
EOF
PROMPT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["prompt"])' "$HIST/run.json")"

if [ "$MODE" = interactive ]; then
  echo "Workspace: $WS"
  echo
  echo "  cd \"$WS\" && claude"
  echo
  echo "Then type:"
  echo "  $PROMPT"
  exit 0
fi

echo "Workspace: $WS"
echo "Prompt:    $PROMPT"
cd "$WS"
claude -p "$PROMPT" --output-format stream-json --verbose \
  --allowedTools "Read Glob Grep Write Edit Bash(python3:*) Bash(ls:*) Bash(head:*) Bash(wc:*) Bash(zcat:*) Bash(gzcat:*)" \
  > "$WS/transcript.jsonl"
python3 - "$WS/transcript.jsonl" <<'EOF' | tee "$WS/answer.md"
import json, sys
for line in open(sys.argv[1]):
    m = json.loads(line)
    if m.get("type") == "result":
        print(m.get("result", ""))
        print(f"\n_{m.get('num_turns')} turns, {m.get('duration_ms', 0) / 60000:.1f} min, "
              f"USD {m.get('total_cost_usd', 0):.2f}_")
EOF
REPORT="$(ls -t "$WS"/reports/*.md 2>/dev/null | head -1 || true)"
echo "Report:    ${REPORT:-none written}"

if [ "$GRADE" = 1 ] && [ -n "$REPORT" ]; then
  LETTER="${SCEN#scenario-}"
  GP="$(sed -e "s|{answer_key}|$REPO/rca-demo/ANSWER-KEY.md|" -e "s|{scenario}|$LETTER|" -e "s|{report}|$REPORT|" \
        "$REPO/rca-demo/bot/grade-prompt.md")"
  # graded from a neutral directory, so neither CLAUDE.md is loaded
  (cd "$(mktemp -d)" && claude -p "$GP" --allowedTools "Read" --add-dir "$REPO/rca-demo" --add-dir "$WS") \
    | tee "$WS/grade.md"
fi
