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

## Windows runner GUI + local Place CLI experiment (2026-11-17)

**Official source references:**
- https://create.roblox.com/docs/studio/cli
- https://create.roblox.com/docs/studio/mcp
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://github.com/Roblox/rbx-test-files/tree/91182f4016e67a8d162fc41176a9ae3275463fd1/places/baseplate-413

**Run 7** https://github.com/mok9900/roblox/actions/runs/44007843463
- Roblox Studio installer/executable detected. OpenAI tunnel-client GitHub release lookup failed because of anonymous GitHub API rate limiting.
- Fixed by supplying GitHub Actions scoped GH_TOKEN to the release lookup.
**Run 8** https://github.com/mok9900/roblox/actions/runs/44007984817
- Both binaries installed and release checksum verified; login UI never became accessible within 85 seconds.
**Run 9** https://github.com/mok9900/roblox/actions/runs/44008551568
- GUI process-aware login probe needed psutil on the Windows Runner; added pip installation.
**Run 10** https://github.com/mok9900/roblox/actions/runs/44008901218
- Windows 2025: Roblox Studio processes and windows were visible, but UIA reported zero editable login fields even after explicitly launching the Studio GUI a second time.
**Run 11** https://github.com/mok9900/roblox/actions/runs/44009548446
- Windows 2025: Roblox-owned pinned local RBXLX sample downloaded, XML structurally checked and SHA256 reported (B090B0F931B48B28584279DFBAEF11327148860A27F48A20A042127E9A139ACB).
- Official Studio --task EditFile --localPlaceFile was invoked successfully, *before* authentication, but the editor itself was not confirmed.
- GUI login still reported zero editable controls across three visible Studio windows.
**Run 12** https://github.com/mok9900/roblox/actions/runs/44010102030
- Tested same pipeline on officially supported GitHub-hosted Windows Server 2022.
- Same outcome as Windows 2025: pinned local test Place downloaded and EditFile launch issued; GUI login fields were inaccessible (three Studio windows, no editable controls).

**Precise current status:** Legacy Nov 16 runs 5 and 6 proved that Gmail OTP automation can sign into Roblox Studio. This does *not* mean the login flow is stable on current GitHub Actions runner images. On Nov 17, repeat tests on Windows 2025 and 2022 encountered inaccessible GUI login controls, and no new email OTP was submitted. CLI invocation does not prove a Place editor loaded. The MCP toggle, OpenAI Tunnel client connection, and ChatGPT list_roblox_studios handshake remain **unverified**. No active tunnel session currently exists.

**Next directions:** instrument WebView2/GUI accessibility through sanitized, credential-free diagnostics; investigate a proper interactive Windows session/remote desktop to confirm what is on screen; avoid blind password entry or repeated login attempts; after GUI login loads, verify local EditFile/editor signal, Studio Assistant MCP toggle, profile-based tunnel setup and a live list_roblox_studios call. Only the last successful call establishes end-to-end completion.

## WGC / DXGI Desktop Duplication / SendInput diagnostics — November 17, 2026

- Both official Windows 2022 and 2025 hosted runners have 1024x768 interactive desktops. Real Win32 SendInput mouse button events and Unicode keystrokes succeeded when tested against a purpose-built, non-sensitive Tk window.
- The DXcam 0.2.0 package's DXCamera lacks the context-manager protocol; using manual camera.release() fixed the initial TypeError. Both DXGI Desktop Duplication and WinRT Windows.Graphics.Capture subsequently returned nonblank 1024x768 frames in both runner environments.
- Studio presented a native startup modal with buttons Close/OK and an on-screen error: "Some Studio files are missing or corrupted. Please reinstall Studio." WGC-cropped screenshot was captured only in a no-credentials diagnostic workflow. SendInput successfully clicked OK; the error quit Roblox Studio.
- Root-cause investigation found the original installer returned as soon as RobloxStudioBeta.exe appeared, before the installer completed extracting assets. The fix now waits for stable file tree, content directory, minimum size and file count, and installer-process termination.
- Updated full installation had 19,294 files, about 1.09GB, and all verification stability checks passing; the damaged-install modal disappeared.
- Studio's installed welcome/login UI appeared but its embedded controls were not reachable as UIA Edit controls. DXGI pixel inspection identified a unique blue 287x40 login-style CTA on both Windows 2022 and 2025. A foreground-validated native SendInput mouse click to that rectangle succeeded on both. This was a **credential-free proof-of-concept**, not yet a verified Roblox account sign-in.
- Credential-bearing production workflow is not enabled with these new pixel-click controls until post-click navigation and login/OTP controls are verified. Do not upload full-res auth screens or store OTP/Roblox passwords in the public repo.

Evidence:
- Original validation: https://github.com/mok9900/roblox/actions/runs/44041844655
- Capture bug diagnosis: https://github.com/mok9900/roblox/actions/runs/44042248957
- WGC/DXGI capture success: https://github.com/mok9900/roblox/actions/runs/44042606635
- Native modal OK SendInput experiment: https://github.com/mok9900/roblox/actions/runs/44043790768
- Fixed full-install verification: https://github.com/mok9900/roblox/actions/runs/44044967196
- Guarded DXGI blue CTA + SendInput click: https://github.com/mok9900/roblox/actions/runs/44045654996

Next: determine whether the button opens an external WebView/browser or changes the Studio startup view; then integrate a well-scoped visual input fallback into the assistant-connected session workflow, preserving verified Gmail 2FA and the no-secrets diagnostic safety boundary.

## Follow-up: on-screen login CTA was clicked via DXGI + SendInput (2026-11-17)

Empirical result: https://github.com/mok9900/roblox/actions/runs/44045654996
- On BOTH windows-2022 and windows-2025, WGC/DXGI successfully captured the live Roblox Studio startup screen and an ROI-constrained blue CTA was detected. Exactly one matching rectangle with width=287, height=40 appeared per runner.
- Win32 SetForegroundWindow/GetForegroundWindow guard succeeded and actual SendInput click succeeded on the ROI's center; Studio stayed running.
- UIA Edit controls in Roblox Studio were still zero after click: this does not prove a signed-in account or even an accessible login form.

Follow-up: https://github.com/mok9900/roblox/actions/runs/44046204082
- After the guarded SendInput blue-button click, WGC frames showed a **significant visual transition** from the dark Studio welcome view to a light-coloured browser-like window.
- Browser/WebView2 processes were present after the click (2022: 13 processes, 2025: 11 processes). This is compatible with external browser sign-in but not yet proof of the URL or browser login completion.
- No Roblox username/password or OTP was provided to the diagnostic workflow. No credential screens were uploaded raw. Only 48x27-pixel irreversible thumbnails were persisted for one day.
- **Next blocker:** inspect the browser's foreground process and non-sensitive UIA controls in the opened window, handle Edge first-run if it is shown, then validate a credential-secure login flow before reconnecting the existing Gmail OTP automation. No verified MCP/tunnel handshake yet.

Keep the CI diagnostic workflow separate from the credential-bearing session workflow until interactive login screen contents and target inputs can be identified safely. Never send SendInput into arbitrary screen coordinates on a credential-bearing runner.
