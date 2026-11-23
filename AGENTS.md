# AI agent handoff — Roblox Studio MCP automation

> **For the next AI coding assistant:** Read the live work queue in [GitHub Issue #1](https://github.com/mok9900/roblox/issues/1) **FIRST**. Never assume the snapshot is current: fetch latest GitHub Actions run/jobs/logs and inspect the feature branch before editing or running anything.

## Non-negotiable owner requirements
- Use **GitHub-managed Windows Actions runners** only (`windows-2022`, `windows-2025`). **No self-hosted runner, no local desktop runner, no personal PC/VM.**
- Goal: signed-in Roblox Studio local Baseplate → official built-in AI Assistant → enable Studio as MCP server → official generated `%LOCALAPPDATA%\Roblox\mcp.bat` → OpenAI Secure MCP Tunnel → verify the exact local CI editor via `list_roblox_studios`.
- Respect official Roblox login and Gmail 2FA; no bypass or blind-click automation. Do not log or commit passwords, Gmail client secrets, OAuth/refresh/access tokens, verification codes, or unredacted credential-bearing screenshots.
- Never modify or publish an existing Roblox game. Only the pinned local test Baseplate fixture is eligible.
- A different connected cloud Place is **not** evidence of this GitHub Actions CI instance.

## Where to work
- Implementation branch: [`feature/studio-openai-tunnel-assisted`](https://github.com/mok9900/roblox/tree/feature/studio-openai-tunnel-assisted)
- Detailed runbook (feature): [`.github/AI_HANDOFF_ROBLOX_MCP.md`](https://github.com/mok9900/roblox/blob/feature/studio-openai-tunnel-assisted/.github/AI_HANDOFF_ROBLOX_MCP.md)
- Main GitHub-hosted runner entrypoint: [`.github/workflows/roblox-studio-hosted-mcp.yml`](https://github.com/mok9900/roblox/blob/main/.github/workflows/roblox-studio-hosted-mcp.yml)
- Main push trigger path: `ci/assisted/hosted-trigger.txt` (the workflow also supports `workflow_dispatch`).
- User only wants Github-hosted Windows Actions; the old self-hosted proposal is obsolete.

## Verified checkpoint — 2026-11-23 19:50 KST

- Latest authenticated hosted Windows Studio run: [#45007915428](https://github.com/mok9900/roblox/actions/runs/45007915428), job `137163540483`, **completed/cancelled after diagnostics** (do not mistake cancellation for Studio login failure). The official Gmail 2FA, local Baseplate, official Roblox-generated launcher, auth token initialization, OpenAI tunnel doctor and stdio MCP startup all passed.
- Local tunnel was `ready=true` on **12/12** checks, with control-plane `polling, ok` for **9/12** checks; MCP discovery stayed `not_observed` on **12/12**. ChatGPT's connected `Roblox_Studio.list_roblox_studios` failed `Tunnel-client has not been seen for 300 seconds` even while the tunnel was polling in prior live checks.
- **First unresolved gate:** ChatGPT **custom MCP app's actual Tunnel selection**, and Platform tunnel **ChatGPT workspace association / Tunnels Read + Use permissions**. The owned plugin package `plugin_asdk_app_6af977ff6cd8819197a693633993f550` exposes only alias manifest files and NOT its backend transport binding. Therefore GitHub code edits, package-only changes or repeated Roblox logins cannot establish the missing association by themselves.
- Existing intended Platform tunnel: `Roblox Studio MCP Auto Chatgpt with GitHub Action`. Official setup: [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels), ChatGPT Plugins → `+` → `Add custom MCP server` → `Connection: Tunnel`. Reuse the matching verified tunnel; avoid blindly replacing the plugin or regenerating credentials.
- Last checked live GitHub Actions list contains no later authenticated Studio run. No authenticated run was started during this checkpoint. The owner explicitly removed the **self-imposed** fixed 24-hour cooldown; retain non-overlapping jobs and bounded legitimate login/2FA attempts.
- **Next agent:** verify/fix app tunnel binding using an authorized signed-in ChatGPT/Platform UI session. Once corrected, execute no-auth 5-job GitHub-hosted regression; then start **one** real hosted Studio workflow. While its tunnel is running, call `list_roblox_studios` and require local `ci_only_baseplate_test` with `persistedToCloud=false`, then a harmless read-only MCP call. Update Issue #1 and the feature runbook with verified evidence only.

**Historical note:** Earlier first-step instructions about run #44889043027 were superseded by subsequent tests. Do not follow them as current priorities.

**This file is a durable instruction pointer, not proof of any currently running process or autonomous AI continuation.**
