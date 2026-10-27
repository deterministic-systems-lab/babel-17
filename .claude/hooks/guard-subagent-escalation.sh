#!/bin/bash
# PreToolUse guard: a subagent may not grant itself more authority than it was
# given.
#
# Why this exists: on 2026-07-26 the antigravity delegate ran its wrapper with
# `--yolo`, which disables approval gates for an agent that can then take
# arbitrary shell and file actions. Nothing bad came of it — it created the one
# file it was asked to — but nobody authorised the bypass, and the plugin's own
# instructions tell it to reach for that flag, so it will happen again.
#
# The distinction this draws is between *capability* and *approval*. A delegate
# that writes files is the point of delegating; the workflow depends on it. What
# it may not do is decide on its own that the human is no longer in the loop.
# Bounded modes (codex `workspace-write` with on-failure approval, agy without
# `--yolo`) are untouched; only the full-bypass forms are refused.
#
# Why a hook rather than a deny rule: permission rules are not scoped by caller,
# so denying these outright disarms the main agent too — and the main agent's
# calls are the ones a human is actually watching. The PreToolUse payload
# carries agent_id only for subagent calls, which is the one place the
# distinction is available. Same mechanism as guard-destructive-git.sh.
set -euo pipefail
payload=$(cat)

# No agent_id => the main agent, whose tool calls the user sees and approves.
agent=$(jq -r '.agent_id // empty' <<<"$payload" 2>/dev/null || true)
[ -z "$agent" ] && exit 0

deny() {
  jq -nc --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

reason_suffix="A subagent may use the capabilities it was given, but may not turn off the approval gate on them. Re-run without the bypass flag; if the task genuinely needs it, say so in your report and let the main agent decide."

tool=$(jq -r '.tool_name // empty' <<<"$payload" 2>/dev/null || true)

# The built-in Bash tool ships its own sandbox override.
if [ "$(jq -r '.tool_input.dangerouslyDisableSandbox // false' <<<"$payload" 2>/dev/null || echo false)" = "true" ]; then
  deny "Blocked: dangerouslyDisableSandbox is an approval bypass. $reason_suffix"
fi

case "$tool" in
  mcp__codex-cli__*)
    # The codex MCP surface spells the same escalation as structured fields.
    yolo=$(jq -r '.tool_input.yolo // false' <<<"$payload" 2>/dev/null || echo false)
    sandbox=$(jq -r '.tool_input.sandboxMode // empty' <<<"$payload" 2>/dev/null || true)
    approval=$(jq -r '(.tool_input.approvalPolicy // .tool_input.approval) // empty' <<<"$payload" 2>/dev/null || true)
    [ "$yolo" = "true" ] && deny "Blocked: codex yolo bypasses every safety check. $reason_suffix"
    [ "$sandbox" = "danger-full-access" ] && deny "Blocked: sandboxMode=danger-full-access. Use read-only, or workspace-write if the task must write. $reason_suffix"
    [ "$approval" = "never" ] && deny "Blocked: approvalPolicy=never removes the human from the loop. $reason_suffix"
    exit 0
    ;;
  Bash) ;;
  *) exit 0 ;;
esac

cmd=$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null || true)
[ -z "$cmd" ] && exit 0

# Word-boundary matched so a path or a quoted string containing the text is not
# mistaken for the flag. Covers the delegate wrappers (agy --yolo, grok --yolo),
# codex's bypass flags, and one Claude Code instance spawning another with
# permissions skipped.
if grep -Eq -- '(^|[[:space:]])--(yolo|dangerously-bypass-approvals(-and-sandbox)?|dangerously-skip-permissions|no-sandbox)([[:space:]=]|$)' <<<"$cmd"; then
  flag=$(grep -Eo -- '--(yolo|dangerously-bypass-approvals(-and-sandbox)?|dangerously-skip-permissions|no-sandbox)' <<<"$cmd" | head -1)
  deny "Blocked: $flag disables approval gates for an agent that can run arbitrary shell and file actions. $reason_suffix"
fi

# `--sandbox danger-full-access` / `--sandbox-mode danger-full-access` on a CLI.
if grep -Eq -- '--sandbox(-mode)?[[:space:]=]+danger-full-access' <<<"$cmd"; then
  deny "Blocked: --sandbox danger-full-access. Use read-only, or workspace-write if the task must write. $reason_suffix"
fi

exit 0
