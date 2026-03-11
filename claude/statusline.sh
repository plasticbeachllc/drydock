#!/bin/bash
# Claude Code status line — themed by setup.py
# Single line: model · project · jj bookmark ● · context bar

input=$(cat)

# ── Theme palette ──────────────────────────────────────
__THEME_PALETTE__
RST='\033[0m'

# ── Extract data ───────────────────────────────────────
read -r MODEL PROJECT PCT < <(echo "$input" | jq -r '[.model.display_name, ((.workspace.project_dir // "unknown") | split("/") | last), (.context_window.used_percentage // 0 | floor | tostring)] | @tsv')

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
  JJ_INFO=$(jj log -r @ --no-graph -T 'separate("\t", if(bookmarks, bookmarks.join(", "), change_id.shortest(4)), if(empty, "clean", "dirty"))' 2>/dev/null)
  BOOKMARK=$(echo "$JJ_INFO" | cut -f1)
  IS_EMPTY=$(echo "$JJ_INFO" | cut -f2)

  if [ "$IS_EMPTY" = "dirty" ]; then
    DOT="${ORANGE}●${RST}"
  else
    DOT="${DIM}○${RST}"
  fi

  JJ=" ${SEP}·${RST} ${TEAL}${BOOKMARK}${RST} ${DOT}"
fi

# ── Assemble ───────────────────────────────────────────
echo -e "${DIM}◆ ${MODEL}${RST} ${SEP}·${RST} ${BLUE}${PROJECT}${RST}${JJ} ${SEP}·${RST} ${BAR} ${DIM}${PCT}%${RST}"
