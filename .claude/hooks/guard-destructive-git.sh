#!/bin/bash
# PreToolUse(Bash) guard: subagents may not run git commands that destroy
# uncommitted work.
#
# Why this exists: on 2026-07-25 a design subagent asked for a read-only second
# opinion ran `git checkout --` across the tree "to restore a clean state" and
# deleted an entire uncommitted implementation. From its side, unexpected
# modifications during its run looked like something to clean up — it could not
# tell the main agent's work from its own delegate's.
#
# Why a hook rather than a deny rule: permission rules are not scoped by caller,
# so denying these commands outright disarms the main agent too. The PreToolUse
# payload carries agent_id only for subagent calls, which is the one place the
# distinction is available.
set -euo pipefail
payload=$(cat)

# No agent_id => the main agent. Untouched.
agent=$(jq -r '.agent_id // empty' <<<"$payload" 2>/dev/null || true)
[ -z "$agent" ] && exit 0

cmd=$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null || true)
[ -z "$cmd" ] && exit 0

# Destructive to *uncommitted* work specifically. Committing is fine, branching
# is fine, reading is fine — losing work that exists nowhere else is not.
# `git -C <dir>` and any position in a compound command are both covered.
if grep -Eqi '(^|[;&|`]|&&|\|\|)[[:space:]]*git([[:space:]]+-C[[:space:]]+[^[:space:]]+)*[[:space:]]+(checkout|restore|clean|reset[[:space:]]+--hard|stash[[:space:]]+(drop|clear|pop))' <<<"$cmd"; then
  jq -nc --arg r "Blocked: subagents may not run git commands that discard uncommitted work (checkout/restore/clean/reset --hard/stash drop). A subagent once deleted an entire uncommitted implementation this way. If you believe the working tree needs restoring, report what you found and let the main agent decide." \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
fi
exit 0
