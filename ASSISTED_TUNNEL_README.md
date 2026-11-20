> **Current implementation (2026-11-21): GitHub-hosted Windows Actions only.**
> The earlier self-hosted/persistent-runner proposals below are historical and
> **must not be used** for this project. Use the new [GitHub-hosted-only
> instructions](GITHUB_HOSTED_ONLY_README.md) and the default-branch
> `Roblox Studio MCP - GitHub-hosted Windows only` Actions workflow instead.
> The live MCP connection still requires successful user-authorized Gmail
> OAuth provisioning and an actual tunnel/client handshake.

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

## November 17 (late KST): primary browser login reproduced; 2FA method selection pending

- Action run: https://github.com/mok9900/roblox/actions/runs/44095190257 (completed, failure at challenge method selection).
- WGC-driven Studio blue login CTA activated. The official Roblox login form in Edge exposed a unique username/password pair and accepted the login form submission. This is evidence of **primary credentials submitted**, not proof of a completed session.
- After the mobile-app approval window, the Roblox challenge's `More Options` control was activated. A privacy-restricted UIA diagnostic reported exactly three generic `MenuItem` nodes, zero matching email method choices, and no newly received Roblox email OTP.
- No email OTP was entered in this run. The local Baseplate editor, Studio MCP, and OpenAI Secure MCP Tunnel were not reached.
- The diagnostic intentionally did not log browser URLs, account names, OTPs or unredacted screenshots.
- A proposed automatic 2FA menu-selection edit was **not applied** because the GitHub action rejected the attempted update; keep the existing code and security boundary unchanged until a supported verification approach is available.
- The optional next step is user-approved interactive verification through Roblox's official login challenge UI, followed by the already-scripted local Place open and MCP activation. Do not randomly choose the three unidentified menu entries or request secret codes in issue comments.

## Automatic Studio MCP retry — 2026-11-18 (KST)

- Run https://github.com/mok9900/roblox/actions/runs/44242530193: Authenticated Secrets check, complete Studio installation and tunnel binary check, per-run RSA public key generation, WGC/SendInput Studio login button, verified Edge Roblox login fields and primary credentials submission. No app approval arrived. Prior generic `More options` click led to 3 MenuItem entries but no email option and likely targeted Edge browser toolbar instead of Roblox page. Runner stopped at `EMAIL_METHOD_UNAVAILABLE`; no Place/MCP/Tunnel started.
- Patched `login-ui.py`: challenge_controls() now scopes UI elements to a unique Roblox-titled Edge window **inside the document body**, excluding the toolbar/address bar (top 125px); no generic browser `More options` action. Added four geometry tests to the email-menu selection tests. Selector tests passed: https://github.com/mok9900/roblox/actions/runs/44243476541.
- Run https://github.com/mok9900/roblox/actions/runs/44243533648: again completed Studio/tunnel installation, primary Roblox browser credentials submitted; app approval not confirmed. Safe page-only 2FA UIA diagnostics returned zero MenuItems, two Buttons (whitelisted label: Cancel), three Text controls, and zero OTP inputs. There was no in-page email alternative to select. It ended at `EMAIL_METHOD_UNAVAILABLE`. Connected Gmail showed no new Roblox verification email. No Place editor or MCP/Tunnel connection reached.
- This does NOT imply the email account is unverified or that email 2FA never works. On earlier 2026-11-16 Studio-native challenge, email OTP was delivered and login succeeded. The browser approval flow currently doesn't expose an email fallback to this automation. Do not select unknown UI controls, bypass 2FA, or claim a tunnel is connected.
- Required to complete end-to-end: approve an official Roblox mobile-app sign-in during a live CI run, or have Roblox present a clearly identified official email-OTP option. After successful sign-in the existing scripts must still validate opening local Baseplate, enabling Assistant MCP and checking `list_roblox_studios`.

## November 18 (evening KST): verified Studio sign-in + local editor; browser callback still blocking full MCP

Evidence from real GitHub Actions runs (all use isolated temporary Windows runners and an unmodified local Roblox Baseplate fixture):

- [44266876028](https://github.com/mok9900/roblox/actions/runs/44266876028): official native Studio login and RSA-OAEP email OTP succeeded. `STUDIO_LOGIN_UI_VERIFIED` / `EMAIL_FALLBACK_SUCCEEDED` logged; local Place launch issued but previous editor probe was overly strict.
- [44272282614](https://github.com/mok9900/roblox/actions/runs/44272282614): isolated Studio-only signed-in detector succeeded after official email OTP; local Place title/toolbar confirmation did not stabilize before its old 120-second limit.
- [44273716755](https://github.com/mok9900/roblox/actions/runs/44273716755): **both official Studio login and real local Place editor were verified.** `PLACE_EDITOR_VERIFIED`, `file_title=True`, ribbon `plugins,test,view`. Assistant UI was not accessible and MCP toggle was not enabled.
- [44280475256](https://github.com/mok9900/roblox/actions/runs/44280475256): browser sign-in, emailed OTP and Verify submission were performed; standalone Edge authentication never yielded an authenticated Studio UI. Do not mistake a Roblox new-device email for Studio login.
- [44281977607](https://github.com/mok9900/roblox/actions/runs/44281977607): official Edge login, but email verification method was not exposed unambiguously; job failed closed.
- [44283310611](https://github.com/mok9900/roblox/actions/runs/44283310611): official Edge OTP submitted. A Roblox-titled Edge window remained but it had no uniquely labeled `Open Roblox Studio` / `Return to Studio` handoff action. Authenticated Studio UI was not verified. Do not click unknown `Allow` / `Continue` controls.
- [44284679297](https://github.com/mok9900/roblox/actions/runs/44284679297): credential-free signed Roblox Studio installation and Windows protocol registry probe **succeeded**. The `roblox-studio-auth:` URL protocol is registered in HKLM and HKCR and points to the Studio executable. Missing scheme registration is therefore not the explanation for failed Edge-to-Studio handoff on this runner image.

Recent code additions: native-first login with bounded pre-credential restart, Windows Graphics Capture/DXGI + guarded SendInput Edge fallback, safe post-OTP browser-to-Studio handoff detection, isolated Studio process login verification, strict locally-open Place editor probe (240 seconds), Assist-ant top-right UI Automation candidate scanning, official `mcp.bat` launcher presence check, and safety-focused unit tests. Encrypted, consumed OTP relay files are removed from the active branch after runs. Only ciphertext remains in historical Git objects.

**Actual working boundary:** signed-in Roblox Studio and the local Baseplate editor have both been demonstrated. **Not yet demonstrated:** built-in Studio MCP toggle enabled, `tunnel-client doctor` success, a live OpenAI Tunnel connection, or `list_roblox_studios` returning the CI instance. No active CI tunnel is available after the failed runs. Do not report end-to-end success.

**Next recommended work:** inspect only credential-redacted UIA / browser-to-Studio protocol-handoff state after official 2FA; avoid additional blind auth retries. The official Windows protocol handler exists, so do not overwrite it. Another option is a persistent, interactive **self-hosted Windows** runner with user-approved Studio sign-in and the official Assistant MCP toggle: a fresh GitHub-hosted runner loses its login state at the end of every job. Keep the local Place and Roblox credentials isolated, never log OAuth callback URIs/tokens, and require an actual MCP tool handshake before declaring completion.

## 2026-11-19 (KST): browser OAuth repaired; Assistant custom UI remains a blocker

Validated official sources:
- Roblox Creator Hub: `Assistant → … → Manage MCP Servers → Enable Studio as MCP server`, then `%LOCALAPPDATA%\\Roblox\\mcp.bat`.
- Microsoft Edge: `AutoLaunchProtocolsFromOrigins` policy (REG_SZ, narrowly restricted to trusted official Roblox HTTPS origins for `roblox-studio-auth` on the disposable current-user runner).

GitHub Action evidence:
- [44413282803](https://github.com/mok9900/roblox/actions/runs/44413282803): tests and Windows current-user Edge policy validation **passed**. Exactly one protocol (`roblox-studio-auth`), three explicit official Roblox HTTPS origins; no wildcard.
- [44413507975](https://github.com/mok9900/roblox/actions/runs/44413507975): **full browser-to-Studio authentication succeeded**, including official Gmail email OTP supplied by ephemeral RSA-OAEP-SHA256 encrypted per-run relay. Both `STUDIO_LOGIN_UI_VERIFIED` and `PLACE_EDITOR_VERIFIED` appeared after official `--task EditFile` opened the pinned local Roblox Baseplate. In the signed-in local editor, `StudioMCP.exe` existed but `%LOCALAPPDATA%\\Roblox\\mcp.bat` did not; Studio exposed 171–211 UIA controls but no accessible Assistant name or mezzanine buttons. Ended safely with `ASSISTANT_UI_NOT_ACCESSIBLE`; did **not** claim MCP toggle or tunnel success.
- [44414768960](https://github.com/mok9900/roblox/actions/runs/44414768960): Python compilation and authentication GUI safety tests passed for tooltip-identification fallback. On native custom-drawn mezzanine buttons, the algorithm now searches by non-mutating hover, clicking only after an exact Studio Assistant tooltip is seen in the Studio process.
- [44414861909](https://github.com/mok9900/roblox/actions/runs/44414861909): signed Studio installer, official protocol registry guard, first-party Roblox Edge login form all verified. This time the Roblox challenge exposed only `Cancel` (no email option/code field), so login stopped at `EMAIL_METHOD_UNAVAILABLE`. No workaround that weakens or bypasses Roblox account verification was used.
- [44415926772](https://github.com/mok9900/roblox/actions/runs/44415926772): separate **credential-free and no-click** offline UIA/tooltip diagnostic. Official Studio installation and local Baseplate `--task EditFile` dispatch succeeded, but a signed-out runner did not expose the local editor title or Assistant metadata. Therefore offline tests cannot validate signed-in Assistant automation; future UI fixes require an authenticated Studio editor.

Current practical boundary: **OAuth browser → Roblox Studio login and local Baseplate editor is proved** (run 44413507975); **Studio Assistant UI, MCP toggle and OpenAI Tunnel remain unproven**. Neither an OAuth URI nor a code/token/password was logged in workflows; the per-run encrypted OTP ciphertext was deleted from the branch after consumption. The public repo has no plaintext OTP.

Recommended next engineering step: prioritize a persistent interactive Windows Studio session for Assistant accessibility discovery, so expensive, rate-limit-prone repeated OTP logins aren't required. A dedicated **self-hosted Windows Actions runner** can retain the user-approved logged-in Studio session; once the official Assistant MCP switch is enabled, verify the generated launcher and the official tunnel `doctor`, then call `list_roblox_studios`. On ephemeral GitHub-hosted runners, retry only when Roblox exposes an official email challenge or mobile approval; never bypass it or guess UI clicks.

### Final code-only hardening (no new account login triggered)
- `ci/assisted/activate-mcp-ui.py` now limits its expanded accessibility search to **RobloxStudioBeta.exe and that process's own descendants**, including possible Studio-owned WebView2 windows; it does NOT inspect unrelated Edge OAuth windows. The hover fallback still only clicks after identifying the exact official Assistant tooltip.
- [44416837946](https://github.com/mok9900/roblox/actions/runs/44416837946) passed Python GUI-selector tests and Windows PowerShell static validation. **This does not prove the Assistant MCP switch works**; a fresh authenticated Studio session must exercise the updated script. Avoid frequent login attempts when the Roblox challenge offers no email option.

## 2026-11-19 evening KST — three user-authorized authenticated retries

All attempts used official Roblox Studio installers, repository GitHub Actions secrets, registered `roblox-studio-auth` protocol and origin-limited Edge policy. No published experience was modified; no plaintext credentials, OTP, or OAuth URLs were logged.

- [44484398903](https://github.com/mok9900/roblox/actions/runs/44484398903): WGC-identified Studio login CTA and unique Edge login form submitted official credentials. Roblox did not expose a unique email 2FA choice. Aborted `EMAIL_METHOD_UNAVAILABLE` before Place or MCP.
- [44485632833](https://github.com/mok9900/roblox/actions/runs/44485632833): **native Studio login form was found** (two Edit controls + unique login button) and submitted, but no mobile approval arrived and no recognized email verification field became accessible. A format-string mistake in a new *diagnostic print only* caused early termination before all safe method categories could be logged. This was corrected in `login-ui.py` and a regression test was added.
- [44486530892](https://github.com/mok9900/roblox/actions/runs/44486530892): latest real Windows run **again found and submitted official native Roblox Studio username/password UI**, then waited for official app approval. The logged-in Studio editor was NOT detected. Safe challenge diagnostics reported `primary_form_still_exposed=False`, `captcha_hint=False`, `edits=0`, `menuitems=2`, both menu items `categories=unclassified` and `name_email=False`; no acceptable official email OTP field/selection. The runner stopped with `EMAIL_METHOD_UNAVAILABLE`. No new Roblox email OTP was delivered to connected Gmail for the run, and no OTP ciphertext was transmitted.
- [44486451288](https://github.com/mok9900/roblox/actions/runs/44486451288): final Python selector and formatting regression tests and Windows PowerShell static check **passed**.

**Verified status**: browser OAuth -> authenticated Studio -> local Baseplate editor succeeded previously in run `44413507975`; neither an active Studio MCP server nor an OpenAI Tunnel was demonstrated in the evening November 19 runs. The actual blocking step is now Roblox's account-side challenge: the account did not approve the mobile app verification request during the verification window, and the Roblox 2FA menu did not offer an accessible Email option. There is no safe reason to click unrecognized menu items or reuse a previous OTP. A user-confirmed official mobile-app approval when a new login request arrives, or an accessible official email code form, is needed before continuing into Assistant.

**Next safe workflow**: start a single authenticated run when the account owner can approve the Roblox mobile sign-in notification; immediately follow `STUDIO_LOGIN_UI_VERIFIED` with pinned local Baseplate, verified Assistant UI / Studio-owned WebView2 and exact tooltip detection, official `mcp.bat` and tunnel doctor, then `list_roblox_studios`. Avoid blind repeated logins while Roblox account verification methods remain unrecognized.

## 2026-11-19 evening — owner-confirmed Email 2SV, email-first remediation

The account owner explicitly confirmed that **Email 2-Step Verification is already enabled**. Do not infer it is disabled from a separate second-device challenge. Roblox's official support documentation states that a second-device approval can be shown at login independently from the Email 2SV configuration.

Current branch remediation:
- `ci/assisted/session.ps1` marks the real, successfully verified primary-login source as `ROBLOX_LOGIN_MODE=native|browser`.
- `ci/assisted/login-ui.py` uses that source to inspect the **matching official login host** rather than a stale Edge window; searches for an existing official Email code field **before** opening other authentication methods or waiting for optional device approval; supports unique masked Email destinations (`s***@...`), `AutomationId`, `HelpText`, `ValuePattern`, and a single Email label nested beneath a generically named parent item. Unknown challenges always fail closed.
- `ci/assisted/tests/test_email_method.py` checks source routing, masked/ambiguous addresses and nested Email choices. [44490581011](https://github.com/mok9900/roblox/actions/runs/44490581011) and the subsequent [44491828717](https://github.com/mok9900/roblox/actions/runs/44491828717) verified tests after fixes.

Real Windows Actions [44490655426](https://github.com/mok9900/roblox/actions/runs/44490655426):
- Official Studio installer and `roblox-studio-auth` Windows protocol: verified.
- Native login fields were not exposed; safe guarded Edge fallback **verified a unique 2-field Roblox login form and submitted credentials**.
- `EMAIL_2FA_PRIORITY` ran immediately. The Roblox challenge exposed a `More options` control but **no unique email code field or email-labeled choice**. In the Edge UIA tree the old username/password edits were still visible (`primary_form_still_exposed=True`), two MenuItems were present but neither was an identifiable Email method. No fresh email OTP was received in connected Gmail.
- `OFFICIAL_EMAIL_CHALLENGE_NOT_OFFERED` and no verified second-device approval: safe abort. **Neither local Place nor Assistant MCP nor OpenAI Secure Tunnel was reached**.
- This does **not** prove Email 2SV is turned off. It means the *particular new-device challenge* did not offer an identifiable Email verification option. The only positively verified successful Email OTP session remains [44413507975](https://github.com/mok9900/roblox/actions/runs/44413507975).
- Do not repeatedly retry a credential login merely to wait for email when Roblox has not issued an email-code challenge. The protected-screen diagnostic proposal was **not installed** and its temporary key material was discarded; the repository still contains only privacy-safe boolean/control-type diagnostics.

Recommended next supported option: consider the first-party `Email Me a One-Time Code` initial sign-in flow if actually shown by Roblox, with the verified mailbox supplied securely (not committed to this public repository); Roblox states this separate passwordless login option is only available to some users. It is **not equivalent** to Email 2SV, and Roblox can still require other sign-in protection. For persistent automation, a user-controlled already-authenticated interactive Windows environment avoids repeated new-device challenges.

## 2026-11-20 — Temporary WGC / DXGI + SendInput pilot

User requested direct Windows graphics-assisted UI automation, preserving the final fully-scripted Studio MCP objective.

Added ci/assisted/visual_twofactor.py: guarded first-party Roblox UI region capture through DXGI Desktop Duplication with WGC/WinRT fallback, volatile OCR selection of a unique Email entry within a real UI Automation control, confirmation on two frames and Win32 SendInput click only then. No screenshots or private text are logged or stored. The existing visual-browser-login.py already provides DXGI + SendInput guarded login CTA and form input.

Added ci/assisted/tests/test_visual_twofactor.py; run 44654740648 passed 54 credential-free Python tests and Windows PowerShell checks: https://github.com/mok9900/roblox/actions/runs/44654740648

An attempted optional RapidOCR dependency installation in the credentialed session was blocked by a tool safety check, so the new 2FA image-recognition path is not yet proven to function on hosted runners. This is an explicit limitation; the implementation safely refuses unknown target clicks.

Real run 44655043493: https://github.com/mok9900/roblox/actions/runs/44655043493 . A fresh Roblox six-digit verification code arrived through connected Gmail, was encrypted using the run-specific public RSA artifact and delivered as encrypted GitHub Actions relay. A fresh new-login notification followed. The encrypted relay file was removed from the branch after the verification period; plaintext secrets were never stored in GitHub. At last check the combined login/MCP/tunnel job was still in progress, while list_roblox_studios showed the MCP tunnel not connected. Email notices alone are not sufficient to establish Studio editor or MCP success.

## 2026-11-20 evening KST — Assistant visual discovery hardening and verification

- GitHub Actions run [44725385070](https://github.com/mok9900/roblox/actions/runs/44725385070) passed Python compile, selector unit tests and PowerShell syntax checks.
- Credential-free Windows integration run [44725686180](https://github.com/mok9900/roblox/actions/runs/44725686180) passed all three jobs, including installing RapidOCR/ONNX on Windows and recognizing a synthetic Assistant label entirely in memory.
- New `ci/assisted/assistant_visual.py` uses DXGI and optional local OCR only on the verified local Baseplate editor's top-right chrome. It only uses SendInput after two unique high-confidence exact Assistant tooltip observations and foreground validation. No account text, screenshots, or OCR text are persisted or printed.
- `activate-mcp-ui.py` tries this bounded visual pass before its narrowed Win32/UIA tooltip hover fallback. The prior full UIA-descendant scan on each of 50 points had taken more than 40 minutes and is removed. The test workflow also had a malformed path filter; it is corrected.
- User-authorized authenticated follow-up [44726022471](https://github.com/mok9900/roblox/actions/runs/44726022471) was started. A fresh official Roblox email 2FA challenge was issued and the run-specific RSA public key artifact was retrieved, but connector safety validation blocked writing the encrypted OTP relay back to the repository. No alternate path was used to circumvent the block. The new run therefore cannot be treated as authenticated or MCP-connected; allow the existing guarded OTP wait to exit naturally.
- Direct `list_roblox_studios` returned `Tunnel-client has not been seen for 300 seconds`. Neither Assistant enablement nor OpenAI Tunnel handshake has been demonstrated.
- Next supported step: use a persistent, user-authorized signed-in Windows Studio session to inspect and activate the official Assistant MCP switch, then verify `%LOCALAPPDATA%\\Roblox\\mcp.bat`, `tunnel-client doctor` and `list_roblox_studios`. Never bypass official Roblox verification or claim success based on a test-only OCR pass.

## 2026-11-20: Persistent interactive Windows runner fallback

Following run [44726022471](https://github.com/mok9900/roblox/actions/runs/44726022471),
the hosted Windows 2FA flow reached the verified official Email code field
but expired with `OTP_RELAY_TIMEOUT` (the encrypted OTP write was blocked).
This is not a Roblox password failure and not a successful MCP connection.

Added:
- `ci/assisted/session-persistent.ps1`: fail-closed interactive desktop guard,
  opens only a pinned local Baseplate, reuses the already signed-in Windows
  account without Roblox password or OTP relay, activates official Assistant
  MCP only when identifiable, requires official `mcp.bat` and tunnel doctor.
- `.github/workflows/studio-openai-tunnel-persistent.yml`: **manual-only**
  workflow for `[self-hosted, Windows, X64, roblox-studio-interactive]`.
  Not usable on a default disposable GitHub-hosted runner.
- `PERSISTENT_STUDIO_MCP_README.md`: one-time `config.cmd`/interactive
  `run.cmd` instructions, security cautions and verification gates.
- Unit tests reject credential/OTP injection into the persistent workflow;
  PowerShell syntax is checked on Windows CI.

This fallback has passed code-level checks, but has **not** been run on an
actual user-provided interactive self-hosted runner. Live success requires
a running official OpenAI tunnel client and a valid response from
`list_roblox_studios`; no connection is claimed yet.
