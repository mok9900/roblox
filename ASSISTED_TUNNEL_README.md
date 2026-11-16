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

## App-first → email fallback experiment (2026-11-16)

- Run #3: https://github.com/mok9900/roblox/actions/runs/43850623794
  Studio installed; app approval not confirmed. Alternative-method UI opened but the initial UIA selector could not identify the email method. No OTP issued to the connected Gmail inbox.
- Run #4: https://github.com/mok9900/roblox/actions/runs/43851413276
  Studio installed and started. Login submitted. App approval not confirmed after the prompt window. The alternative-method chooser exposed a ListItem and Button named "email", and a separate "backup code" option. The "email" option was successfully clicked.
  However, a numerical one-time email login code was never relayed; the job ended with OTP_RELAY_TIMEOUT and the tunnel never launched.
  A Roblox email seen in the connected Gmail inbox at 2026-11-16 10:52 UTC was an **email-address verification link** for XOX_OWNER, not a numerical login OTP. This distinction matters; it is not evidence of successful sign-in.
- On next attempt, login-ui.py now verifies an actual accessible email OTP input before beginning the encrypted relay wait.
- Account owner must follow the official email-address verification instructions if the address is not yet verified. Never put the Roblox verification ticket/URL, original OTP, password or recovery codes in the repository.
- **No active Actions Studio or OpenAI MCP tunnel session remains from these failed runs.**

## Live Gmail OTP login verification — November 16, 2026

**Run 5: https://github.com/mok9900/roblox/actions/runs/43855667540**
- Authenticated via Roblox official GUI login form.
- Mobile app approval wasn't confirmed; clicked official "email" alternative.
- Connected Gmail received a six-digit 2FA challenge for the intended account.
- A *run-bound RSA-3072 OAEP-SHA256 ciphertext* was delivered through GitHub; plaintext was not put in the public repo.
- Runner logs confirm: OTP_RELAY_RECEIVED, EMAIL_CODE_ENTERED, STUDIO_LOGIN_UI_VERIFIED, EMAIL_FALLBACK_SUCCEEDED.
- Roblox additionally sent a new Windows login security notification from the expected Actions host location.
- **Failure after successful login**: Assistant UI was not available. Studio did not have a place open.

**Run 6: https://github.com/mok9900/roblox/actions/runs/43857010505**
- Fixed step order to first open a new unsaved local Baseplate editor after successful login.
- Again received a fresh Gmail 2FA email and delivered a run-bound encrypted OTP. Verified login via Studio UI.
- **Failure after successful login**: BASEPLATE_TEMPLATE_NOT_ACCESSIBLE. UI Automation could not find a Baseplate template / New Experience button in Studio's visible accessibility tree.
- Thus MCP toggle and OpenAI Tunnel were never reached. A successful Roblox login does not by itself prove MCP connectivity.
- The temporary encrypted OTP relay text files for these completed runs were removed from the active branch. The historical git objects remain ciphertext only.

**Current next issue:** Open an unsaved Roblox Studio place reliably after GUI sign-in in an unattended Windows 2025 GitHub-hosted runner. Studio Assistant and its built-in MCP settings only show with an editor/place open. After solving this, validate Assistant → Settings → MCP Servers → Enable Studio as MCP server, followed by tunnel-client connectivity and list_roblox_studios handshake.
