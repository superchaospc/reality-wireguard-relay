#!/usr/bin/env bash
# install.sh — make this skill usable by BOTH Claude Code and Codex.
#
# Claude Code and Codex use the identical skill format (SKILL.md + name/description
# frontmatter); they only scan different directories. This script links this skill
# into each one's skill dir so it auto-discovers (and auto-triggers) in both:
#   - Claude Code : ~/.claude/skills/
#   - Codex       : ~/.codex/skills/ , ~/.agents/skills/
#
# Self-contained (no other skill required), portable (agents that aren't installed
# are skipped), idempotent, and it never overwrites a real directory.

set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)"   # this skill's real directory (the source)
NAME="$(basename "$SELF")"
CLAUDE_SKILLS="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

err()  { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; }
ok()   { printf '\033[32m✓ %s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }

# Candidate target dirs. Claude Code's dir is included only if we're not already
# inside it. An agent dir counts as "installed" if it (or its parent) exists.
CANDIDATES=()
[ "$(dirname "$SELF")" = "$CLAUDE_SKILLS" ] || CANDIDATES+=("$CLAUDE_SKILLS")
for c in "$HOME/.codex/skills" "$HOME/.agents/skills"; do
  if [ -d "$c" ] || [ -d "$(dirname "$c")" ]; then CANDIDATES+=("$c"); fi
done

if [ "$(dirname "$SELF")" = "$CLAUDE_SKILLS" ]; then
  ok "Claude Code: in place ($SELF)"
fi

linked=0
for t in "${CANDIDATES[@]}"; do
  link="$t/$NAME"
  if [ -L "$link" ]; then
    [ "$(readlink "$link")" = "$SELF" ] && { ok "already linked: $link"; continue; }
    rm "$link"; ln -s "$SELF" "$link"; ok "relinked: $link -> $SELF"; linked=1; continue
  fi
  if [ -e "$link" ]; then err "$link exists and is NOT a symlink — skipped"; continue; fi
  mkdir -p "$t"; ln -s "$SELF" "$link"; ok "linked: $link -> $SELF"; linked=1
done

echo
if [ "$linked" -eq 1 ]; then
  info "Done. Restart Codex (and/or Claude Code) so it rescans its skill dirs."
else
  info "Already fully linked. Nothing to do."
fi
