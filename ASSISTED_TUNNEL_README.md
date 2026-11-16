# Assisted Roblox Studio + OpenAI Secure MCP Tunnel

Experimental setup. main is unchanged.

## Required GitHub Actions Secrets
Configure at https://github.com/mok9900/roblox/settings/secrets/actions:
- ROBLOX_USERNAME
- ROBLOX_PASSWORD
- OPENAI_TUNNEL_ID (from https://platform.openai.com/settings/organization/tunnels)
- OPENAI_TUNNEL_RUNTIME_KEY (runtime key with Tunnels Read + Use)

Do not publish account credentials, sessions, screenshots, or OTP codes. Prefer a dedicated testing account because this is a public repo.

## Steps
1. Provision Secure MCP Tunnel in OpenAI Platform, associate it with ChatGPT workspace.
2. Set the four GitHub Actions secrets yourself.
3. Create (first run) or update (later runs) ci/assisted/start-session.txt via a GitHub commit on feature/studio-openai-tunnel-assisted.
4. Actions Windows 2025 installs Roblox Studio and OpenAI tunnel-client, attempts GUI sign-in and MCP toggle, and starts the private tunnel.
5. ChatGPT web → Plugins → Add custom MCP server → Tunnel → select tunnel ID. Install plugin after successful discovery.
6. Stop the job in GitHub Actions. Workflow cap is 330 minutes.

## Verification boundary
Only Studio installation, process, software graphics and login UI initialization were proven in earlier runs. GUI auth, MCP toggle and tunnel connections remain UNTESTED and may fail with changes to Studio UI, accessibility labels, or extra authentication.
The workflow fails closed on missing secrets or unverifiable UI. No CAPTCHA/2FA bypass.
GitHub's manual Run Workflow UI may require the workflow to be on the default branch. Updating the trigger file works on this experimental branch.

Official docs:
https://create.roblox.com/docs/studio/mcp
https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
https://developers.openai.com/api/docs/guides/custom-mcp-server

## Preflight evidence
- Windows 2025 Studio installation: passed.
- Official OpenAI tunnel-client download and SHA256 verification: passed. Installed client version 0.0.21.
- Local Roblox MCP launcher before login: not present; enabling Studio MCP after login remains necessary.
- Last successful installation preflight: https://github.com/mok9900/roblox/actions/runs/43840837997
- GUI accessibility preflight: https://github.com/mok9900/roblox/actions/runs/43841253999

## GUI access probe (2026-11-16)
- Verified on an actual Windows 2025 Actions runner: 2 Studio/login windows, exactly 1 accessible username field, 1 password field, and 1 login button.
- Credential-free UIA probe succeeded; no credentials submitted and no Roblox login succeeded or failed.
- https://github.com/mok9900/roblox/actions/runs/43841253999

## On-demand session results — 2026-11-16
- Run #1: https://github.com/mok9900/roblox/actions/runs/43845956553 — Secrets check and installs passed; UI automation submitted Roblox login form, then detected additional verification and exited safely.
- Run #2: https://github.com/mok9900/roblox/actions/runs/43846388259 — Secrets check and installs passed; submitted Roblox login form, detected additional verification and kept waiting approximately four minutes for an authorized approval. No verified sign-in by timeout; exited safely.
- Neither run activated Studio MCP nor connected OpenAI Tunnel. There is **no active session** after these failures.
- Next needed: a supported user-facing approval or secure temporary remote GUI access for interactive account verification. Never send OTP, Roblox password, or recovery codes to a public issue or the chat.
