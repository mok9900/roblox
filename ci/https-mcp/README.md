# Private HTTPS MCP relay — current operation

Production experiment: fixed Cloudflare workers.dev endpoint, owner-only Managed OAuth, GitHub OIDC authenticated outbound Windows runner, and official Roblox Studio MCP stdio. No local or self-hosted runner, custom domain changes, or public game editing.

Endpoint: https://roblox-mcp.parcel-mcp-seojun.workers.dev/mcp
ChatGPT connector: rstest (already authorized). The separately created private plugin roblox-studio-https uses the same endpoint. No reinstall is needed when a runner expires.

## Evidence and limits
- [OIDC/Access probe 45964171208](https://github.com/mok9900/roblox/actions/runs/45964171208): authenticated runner and negative auth checks succeeded.
- Real rstest call reached the authorized Worker, returned the relay-unavailable error. This is not a verified Studio connection.
- [HTTP/stdio/runner/relay regression 45966761402](https://github.com/mok9900/roblox/actions/runs/45966761402): 13 synthetic tests passed. No real game or account is used.
- [Official GUI regression 46105851268](https://github.com/mok9900/roblox/actions/runs/46105851268): all five jobs succeeded; 127 selector tests passed.
- [Current live run 46105911928](https://github.com/mok9900/roblox/actions/runs/46105911928): inspect actual job state before taking action. No end-to-end success claimed until rstest returns a verified official local fixture.
- Latest upstream diagnostic changes emit only fixed stage markers, not raw tool responses. Tests cover structured/text duplicate proof and conflicting structured evidence.

## Start/restart
Use the existing [private HTTPS workflow](https://github.com/mok9900/roblox/actions/workflows/roblox-workers-relay-live.yml) on main with windows-2022 (default) or windows-2025. It shares the single-instance concurrency group with the existing OpenAI Tunnel workflow. Do not queue redundant runs. Check current jobs before dispatch; no blind retries after credential submission, independent security challenge, or login rate limit. The previous user-approved fixed 24h cooldown is not a requirement; respect actual Roblox security responses. A run uses official Studio installation and its official launcher, then exposes only read-only verification for up to 15000 seconds, subject to the 330-minute job timeout. Runner expiration disconnects Studio; the fixed HTTPS endpoint and OAuth configuration remain.

## Completion gates
1. Check Windows runner OIDC preflight, successful official Roblox login and 2FA, local Baseplate verification and actual official MCP initialization.
2. Require WORKERS_LOCAL_OFFICIAL_STUDIO_MCP_VERIFIED and WORKERS_RELAY_READY; then call rstest verify_ci_studio during the active run. Expected result verified=true, matching_local_fixtures=1, source=official_studio_mcp. An offline/unavailable error is not success.
3. Confirm actual owner-authorized round trip before expanding any tools. Do not silently expose arbitrary RPC execution, cloud-place edits, credentials or raw Studio data.
4. First prove a second clean authorized hosted run can reconnect without reinstalling rstest. Continuous service is not established; no endless authentication restart loop is enabled. GitHub hosted runners have finite lifetimes and usage limits; reauthentication may require user approval. Operational monitoring should report failure rather than claim success.

## Diagnostics and recovery
- WORKERS_LIVE_PREFLIGHT_VERIFIED means only GitHub-to-Worker authentication succeeded.
- If EMAIL_CODE_FORM_NOT_PRESENT_AFTER_OFFICIAL_CHALLENGE, inspect safe selector diagnostics. Do not guess coordinates, bypass security, or fetch/submit an OTP for an unverified challenge.
- OFFICIAL_STDIO_STAGE identifies launcher, initialization, tool catalog, list_studios or fixture evidence failures (new code applies to subsequent runs).
- If the final long-running step is not reached, do not attribute the problem to the ChatGPT plugin.
- A canceled/expired run cannot be repaired in place. Re-dispatch only after checking the prior failure and existing concurrency group. Never store secrets in repository files or issue comments.

See Issue #1 for current evidence and handoff. Original OpenAI Tunnel route remains intact.
