#!/bin/bash
# Claude Code status line — Plastic Beach
# Single line: model · project · jj bookmark ● · context bar

input=$(cat)

# ── Plastic Beach palette ──────────────────────────────
DIM='\033[38;2;138;154;154m'
SEP='\033[38;2;42;69;85m'
BLUE='\033[38;2;74;176;200m'
TEAL='\033[38;2;64;191;176m'
ORANGE='\033[38;2;232;133;74m'
GOLD='\033[38;2;212;160;80m'
RED='\033[38;2;208;96;96m'
RST='\033[0m'

# ── Extract data ───────────────────────────────────────
MODEL=$(echo "$input" | jq -r '.model.display_name')
PROJECT=$(echo "$input" | jq -r '.workspace.project_dir' | xargs basename)
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

# ── Context bar ────────────────────────────────────────
BAR_W=6
FILLED=$((PCT * BAR_W / 100))
[ "$FILLED" -gt "$BAR_W" ] && FILLED=$BAR_W
EMPTY=$((BAR_W - FILLED))

if [ "$PCT" -ge 90 ]; then BAR_C="$RED"
elif [ "$PCT" -ge 70 ]; then BAR_C="$GOLD"
else BAR_C="$TEAL"; fi

BAR_FILLED=""
BAR_EMPTY=""
[ "$FILLED" -gt 0 ] && BAR_FILLED=$(printf "%${FILLED}s" | tr ' ' '━')
[ "$EMPTY" -gt 0 ] && BAR_EMPTY=$(printf "%${EMPTY}s" | tr ' ' '━')
BAR="${BAR_C}${BAR_FILLED}${SEP}${BAR_EMPTY}${RST}"

# ── jj status ──────────────────────────────────────────
JJ=""
if command -v jj &>/dev/null && jj root &>/dev/null; then
  BOOKMARK=$(jj log -r @ --no-graph -T 'bookmarks.join(", ")' 2>/dev/null)
  [ -z "$BOOKMARK" ] && BOOKMARK=$(jj log -r @ --no-graph -T 'change_id.shortest(4)' 2>/dev/null)

  IS_EMPTY=$(jj log -r @ --no-graph -T 'if(empty, "clean", "dirty")' 2>/dev/null)
  if [ "$IS_EMPTY" = "dirty" ]; then
    DOT="${ORANGE}●${RST}"
  else
    DOT="${DIM}○${RST}"
  fi

  JJ=" ${SEP}·${RST} ${TEAL}${BOOKMARK}${RST} ${DOT}"
fi

# ── Assemble ───────────────────────────────────────────
echo -e "${DIM}◆ ${MODEL}${RST} ${SEP}·${RST} ${BLUE}${PROJECT}${RST}${JJ} ${SEP}·${RST} ${BAR} ${DIM}${PCT}%${RST}"
