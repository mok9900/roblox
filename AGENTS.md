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

## Next actions
1. Refresh run [#44889043027](https://github.com/mok9900/roblox/actions/runs/44889043027), fetch job logs when completed and classify `EMAIL_2FA_*`, `PLACE_EDITOR_*`, `MCP_*`, `ASSISTANT_*`, `TUNNEL_*` markers. This was the first full-HD 1920×1080 integration at snapshot time (Nov 21, 2026 KST); its state can change.
2. Fix only the earliest unsatisfied gate, add tests and verify them using GitHub-hosted Actions.
3. Launch no overlapping authenticated Studio sessions. The documented single-instance concurrency group exists for this reason.
4. Update [Issue #1](https://github.com/mok9900/roblox/issues/1) and the feature runbook with exact verified outcomes, run IDs, error markers and relevant commits, without secrets.
5. Do not mark complete until the local **CI Baseplate** is seen through MCP, not just an existing unrelated cloud Studio.

**This file is a durable instruction pointer, not proof of any currently running process or autonomous AI continuation.**
