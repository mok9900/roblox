# AI-to-AI continuity runbook: GitHub-hosted Roblox Studio MCP

**Permanent work ticket:** https://github.com/mok9900/roblox/issues/1  
**Agent entrypoint:** `AGENTS.md` on both `main` and `feature/studio-openai-tunnel-assisted`.  
**Last human user requirement:** keep going; all Windows automation MUST run on GitHub's own hosted Actions runners. No self-hosted or local runner.

**IMPORTANT:** This file is a *historical snapshot* written 2026-11-21 ~18:43 KST. A subsequent AI must fetch new GitHub runs, issue updates, branch HEAD, and logs before deciding what is currently true. Do not confuse queued/in-progress with a successful MCP connection.

## 1. Architecture (do not replace it unnecessarily)

```text
main/ci/assisted/hosted-trigger.txt push
   or main/.github/workflows/roblox-studio-hosted-mcp.yml dispatch
       -> GitHub-hosted Windows 2022 (default) / Windows 2025 (optional)
       -> verify all GitHub Actions secrets are present, without printing
       -> official Google OAuth refresh + Gmail readonly messages.list preflight
       -> configure-hosted-display.ps1: Set-DisplayResolution 1920x1080 + verify
       -> configure-edge.ps1: official Roblox-only browser callback setup
       -> install-windows.ps1: official signed Roblox Studio + verified tunnel-client
       -> session.ps1: Studio official login (native UIA or guarded Edge fallback)
       -> official email 2FA (gmail_otp.py, no plaintext secrets in logs)
       -> pinned local Roblox Baseplate fixture via official EditFile CLI
       -> unique verified editor foreground + maximize
       -> activate-mcp-ui.py: UIA / Win32 tooltip or local-only DXGI OCR hover
       -> official Studio MCP toggle; validate Roblox-generated mcp.bat
       -> tunnel-client init; doctor --explain; tunnel-client run
       -> ChatGPT Roblox_Studio list_roblox_studios must show non-cloud CI Baseplate
```

Implementation: `feature/studio-openai-tunnel-assisted` checked out from main workflow, with `persist-credentials: false`. Do not migrate to self-hosted. Some older documentation historically discussed self-hosted runners; ignore those obsolete suggestions.

## 2. Verified historical results / source links

- [Run 44886034785](https://github.com/mok9900/roblox/actions/runs/44886034785): **confirmed** `GMAIL_READONLY_PREFLIGHT_SUCCEEDED`, `GMAIL_2FA_FRESH_CODE_READY`, `EMAIL_CODE_ENTERED`, `EMAIL_2FA_STUDIO_LOGIN_SUCCEEDED`, `PLACE_EDITOR_VERIFIED`. Assistant failed `editor_not_foreground`. This led to guarded verified-HWND foreground activation.
- [Run 44886873489](https://github.com/mok9900/roblox/actions/runs/44886873489): official 2FA and Baseplate again succeeded; foreground problem no longer appeared; but `MCP_VISUAL_DIAG: scanned=18 tooltip_verified=False`, `ASSISTANT_UI_NOT_ACCESSIBLE`.
- [Run 44888495024](https://github.com/mok9900/roblox/actions/runs/44888495024), job `136798925108`: again login/Baseplate success, Assistant failure: `MCP_VISUAL_DIAG: scanned=21 text_hints=0 tooltip_verified=False`, `MCP_HOVER_SAFE_DIAG: points=18 tooltip_found=False`, `ASSISTANT_UI_NOT_ACCESSIBLE`. This was **still 1024x768** and had no 1080p editor fix.
- [Windows display test 44888774981](https://github.com/mok9900/roblox/actions/runs/44888774981): confirmed native display change `HOSTED_DISPLAY_BEFORE width=1024 height=768` → `HOSTED_DISPLAY_AFTER width=1920 height=1080` on GitHub-hosted windows-2022. No private VM or self-hosted runner.
- [All green offline suite 44888964857](https://github.com/mok9900/roblox/actions/runs/44888964857): Python selector, PowerShell syntax, Windows local OCR, and Windows display-mode jobs all green.
- [First full-HD *authenticated* run 44889043027](https://github.com/mok9900/roblox/actions/runs/44889043027): started 2026-11-21T09:19:38Z; at the time of this snapshot it was **in_progress** at combined `Official Roblox email 2FA → local Baseplate → Assistant MCP → tunnel`. **Must read final job `136801371258` logs and classify its outcome before new changes.** A new official Roblox security email was observed at 2026-11-21T09:27:01Z; this does NOT prove code submission/Studio login success.

## 3. Files and why they matter

| File | Role |
| --- | --- |
| `AGENTS.md` | Short always-visible handoff at repository root |
| `.github/AI_HANDOFF_ROBLOX_MCP.md` | This detailed continuation runbook |
| `ci/assisted/activate-mcp-ui.py` | Finds Assistant using UIA/verified hover, then official overflow/MCP toggle; refuses unlabeled guessed targets |
| `ci/assisted/assistant_visual.py` | Verified local editor foreground+maximize, local-only DXGI/RapidOCR; exact twice-observed Assistant tooltip before SendInput |
| `ci/assisted/configure-hosted-display.ps1` | Verified native `1920x1080` expansion, falls back safely |
| `ci/assisted/session.ps1` | Master CI Studio login/2FA/Baseplate/MCP/Tunnel procedure |
| `ci/assisted/gmail_otp.py` | Gmail OAuth readonly poll for fresh official Roblox 2FA mail |
| `ci/assisted/otp_relay.py` | Legacy RSA relay compatibility, not necessary when Gmail OAuth works |
| `ci/assisted/open-test-place-cli.ps1` | Official EditFile local test fixture; no cloud editing |
| `ci/assisted/tests/test_assistant_visual.py` | Tooltip + guarded foreground tests |
| `ci/assisted/tests/test_mcp_uia_control_types.py` | UIA name and control type comparison tests |
| `ci/assisted/tests/ocr_runtime_smoke.py` | Synthetic light/dark AI Assistant OCR |
| `.github/workflows/test-roblox-auth-selector.yml` | GitHub-hosted/static CI tests |
| `main/.github/workflows/roblox-studio-hosted-mcp.yml` | Default-branch actual hosted Actions workflow |
| `main/ci/assisted/hosted-trigger.txt` | Allowed push trigger from GitHub main when manual workflow dispatch unavailable via connector |

No repo file should contain Roblox or Google secrets. GitHub Actions repository secrets are configured and preflight succeeded in later runs. Do **not** request or expose their values.

## 4. Success/failure criteria

**Verified already:** Google OAuth token refresh & Gmail readonly API, official Roblox login/2FA via Gmail, Studio authenticated, local Baseplate Editor (prior runs), GitHub-hosted 1080p display & editor-maximize logic (maximization verified by synthetic tests; actual Studio needs live proof).

**NOT verified at the snapshot:** actual AI Assistant panel opened in hosted Studio; enabled official MCP toggle; official `%LOCALAPPDATA%\Roblox\mcp.bat` generated; Tunnel `doctor --explain` success or persistent `run`; ChatGPT seeing the **specific local CI Baseplate** through `list_roblox_studios`.

An unrelated cloud-persisted Place (e.g. an already connected tower defense experience) is NOT this CI Baseplate.

## 5. Safe next steps for the next AI

1. **Refresh GitHub job status** for `44889043027`; if complete, get `fetch_workflow_job_logs` for job `136801371258`. Extract only non-sensitive diagnostic markers; redact six-digit OTP-like numbers and all secret env values. If running, do not trigger another authenticated job just to gather logs.
2. If Assistant is still undiscoverable with 1080p+maximize, investigate *what the Studio toolbar actually exposes* without guessing or clicking unverified pixels. Consider adding a **top-right toolbar-only diagnostic artifact** that is cropped and validated to exclude Roblox account identifiers, browser contents, credentials and editor scene. Preserve it only if the pixel region can be proven safe; prefer structured non-secret UIA metadata and OCR text categories over screenshots.
3. Consult current Roblox documentation for actual Assistant/MCP switch UI changes. Do not synthesize `mcp.bat` or assume StudioMCP.exe presence means toggle activated.
4. Fix minimal issue, add credential-free tests, verify green tests on hosted Windows, then trigger a single new main-branch hosted run; monitor until the earliest failing gate is known.
5. Check official OpenAI `tunnel-client` CLI `init`, `doctor`, `run` directly from the run logs. Do not invent secure tunnel availability. Query `mcp__Roblox_Studio__list_roblox_studios` only to confirm an actual **CI Baseplate**, not an unrelated user's existing Studio.
6. Update permanent [Issue #1](https://github.com/mok9900/roblox/issues/1) (edit body or add status) and this runbook with exact run ID, commit, date, failure marker or confirmed success. For the next AI, this is the work queue.

## 6. Security & operational constraints

- Never call a Google/GitHub API with private tokens in URLs or commit OTP in a file. Keep OAuth secrets and passwords in GitHub Actions Secrets. Do not paste secrets, Gmail contents, whole OTPs or screenshots with identity/session information into Issues, PRs, logs or chat.
- Only interact with the verified uniquely named local Baseplate `ci_only_baseplate_test`; no third-party or cloud Place modifications.
- Do not bypass Roblox MFA, CAPTCHA, approval gates, security restrictions, or API terms. Use only official account login and Gmail authorization with readonly scope.
- Never claim a background task/always-on service was established. A GitHub-hosted Windows job is ephemeral. An issue is a durable ticket, **not a running AI**.
- Keep the no-blind-click invariant: exact Assistant/AI Assistant tooltip or verified UIA control identity and unique foreground HWND before any click.
- User specifically prohibited self-hosted/local runners. Do not propose those alternatives as next steps.

## 7. AI succession checklist

The next AI should explicitly verify and update these fields in GitHub Issue #1 each time:
- last validated implementation commit SHA
- last GitHub-hosted integration run ID and status
- last green tests run ID
- first unresolved gate and exact log marker
- whether official `mcp.bat` was present
- whether tunnel doctor/run succeeded
- whether `list_roblox_studios` returned *local CI Baseplate*
- next smallest safe code change and associated test

**Durable handoff mechanism:** `main/AGENTS.md` → Issue #1 → `feature/AGENTS.md` → this runbook. No dependence on chat session memory.

## 8. Automatic checkpointing for future sessions

The default branch also contains `.github/workflows/roblox-mcp-ai-handoff.yml`, a **separate GitHub-hosted Ubuntu Actions workflow** triggered by completion of `Roblox Studio MCP - GitHub-hosted Windows only`. It has minimal `contents: read` and `issues: write` permissions. It posts to [Issue #1](https://github.com/mok9900/roblox/issues/1) with only the run ID, completion timestamp, conclusion and link.

It does **not** read/private-post GitHub Actions logs, Roblox credentials, Gmail data or OTPs, and it does not start an AI model, schedule follow-up runs, or assert MCP readiness. The next AI must still inspect actual run logs and update the issue manually with evidence. Verify reporter operation by checking Issue #1 after the next **completed** hosted Studio run.

Never treat the reporter as a self-hosted runner. It uses `ubuntu-latest`, a GitHub-hosted runner, only for posting safe status metadata.

## 9. Two distinct Actions stages for easier live AI diagnosis (new code)

Implementation as of feature commit `f30ecd9f` and main commit `e0292e91`: `session.ps1` now supports `ROBLOX_MCP_SETUP_ONLY='1'`. This returns exit 0 **only after** the original `tunnel-client doctor --profile roblox-studio-ci --explain` has passed. Default-branch workflow now has two **separate** steps:

1. `Verify Roblox email 2FA, local Baseplate, official Assistant MCP and tunnel doctor` (hosted Windows, `timeout-minutes: 32`, `ROBLOX_MCP_SETUP_ONLY: '1'`). A green check proves the preceding official Studio MCP/doctor gate; a failure here reveals the correct place to inspect logs.
2. `Run verified OpenAI Secure MCP Tunnel (GitHub-hosted foreground)`. Invokes `tunnel-client run --profile roblox-studio-ci` only after the first step succeeds. It is normal for this step to remain **in progress** while the tunnel stays alive; verify actual MCP tool calls separately, not just process longevity.

Earlier run `44889043027` started with the old *combined* single-step workflow; it cannot display these separate gates. Once the earlier run has completed, trigger one new GitHub-hosted run, then inspect the two new step statuses. New runs must never overlap old authenticated Studio sessions. An extra GitHub-hosted status reporter posts run outcomes to Issue #1 after completion, but never claims MCP functionality.

All tests after the split passed in [44891326634](https://github.com/mok9900/roblox/actions/runs/44891326634). Keep any future modifications to `session.ps1` compatible with the standalone feature workflow unless intentionally deprecating it.

## 10. 1080p run failure, reporter proven, safe OCR diagnostic iteration

At 2026-11-21 18:50 KST full-HD authenticated run [44889043027](https://github.com/mok9900/roblox/actions/runs/44889043027) **finished with failure**. Final job `136801371258` proved actual Google OAuth/Gmail 2FA, Studio login and local Baseplate, plus `HOSTED_DISPLAY_AFTER width=1920 height=1080` and `MCP_EDITOR_MAXIMIZED width=1920 height=1017`. Assistant still absent, shown by `MCP_VISUAL_DIAG scanned=21 text_hints=0 tooltip_verified=False`, `ASSISTANT_UI_NOT_ACCESSIBLE`. No `mcp.bat`, tunnel doctor or CI Baseplate MCP call was proven.

The new reporter **actually worked**: [reporter run 44891442721](https://github.com/mok9900/roblox/actions/runs/44891442721) completed successfully and posted safe metadata to [Issue #1 comment 7060837248](https://github.com/mok9900/roblox/issues/1#issuecomment-7060837248). So future completed hosted runs will be summarized even after the current chat ends.

Feature changes for the next real run:
- `activate-mcp-ui.py` commit `225a4535`: avoid repeatedly enumerating Studio UIA descendants for ~4-6 min each; run verified editor hover-only OCR first, followed by **one** UIA labeled-button fallback, then fail closed. All existing no-blind-click restrictions remain.
- `assistant_visual.py` commit `84bd0389`: adds only numeric `baseline_items`, `nonempty_frames`, `max_items` alongside `scanned`, `text_hints`. No OCR text or screenshot is persisted or logged. This distinguishes an empty/unreadable DXGI crop from a visible toolbar that lacks Assistant.
- GitHub-hosted unit/PowerShell/display/OCR tests: [44891571458](https://github.com/mok9900/roblox/actions/runs/44891571458), check actual completion before running new authenticated tests.

The default branch main workflow already splits **MCP setup/doctor** from **foreground tunnel run**. When the next integration runs, the GitHub Actions steps should show the exact boundary rather than staying indefinitely inside the old combined step. The official Roblox Assistant panel remains the unresolved blocker.

## 11. 2026-11-22 KST: first-party per-account MCP setting experiment (read latest run before acting)

Full signed Studio integration [#44896591519](https://github.com/mok9900/roblox/actions/runs/44896591519) **failed** at Assistant UI. The signed Studio **contains** `Assistant.rbxm` (`version_present=true`), and examined logs show `load_failure_logged=false`. This disproves the earlier theory of Assistant plugin completely missing. No successful `mcp.bat` or tunnel handshake was observed.

A Roblox developer report [4858349](https://devforum.roblox.com/t/studio-windows-sometimes-fail-to-connect-to-mcp-when-place-opens-before-assistant/4858349) documents `Roblox/AssistantSettings/<userid>.json` with `{"mcp-server":{"enabled":true}}`. Another analysis of Roblox `AssistantApplication:SetUserSettingsAsync` identifies this same account-specific settings location on Windows. Roblox's official `users.roblox.com/v1/usernames/users` API resolves the *exact* requested username to a numeric ID without credentials. This approach is distinct from official documented GUI instructions and is experimental, not proven by Roblox documentation as a supported headless enable method.

Feature helper: `ci/assisted/enable-official-mcp-preference.py`. It runs ONLY on a disposable GitHub Actions Windows machine **after** official Roblox login/2FA and successful pinned local Baseplate open. It validates exact public account ID, atomically adds the first-party `mcp-server.enabled=true` value, preserves all other JSON keys, does not print identities or contents, and never fabricates `mcp.bat`. `session.ps1` restarts the signed Studio and reopens *only* the local test Baseplate, then checks whether **Studio itself** generated the launcher. If not, the guarded GUI fallback remains. If the secret `ROBLOX_USERNAME` is not a valid public username (e.g. email), the helper fails closed without changing any file.

Synthetic Python tests, PowerShell syntax, Windows OCR and display smoke all passed [#44953940221](https://github.com/mok9900/roblox/actions/runs/44953940221). New authenticated GitHub-hosted Windows run [#44954027272](https://github.com/mok9900/roblox/actions/runs/44954027272) began at 2026-11-22 06:55 KST. **Refresh its real-time status/jobs/logs before claiming success or retrying.** Critical evidence markers: `MCP_PREF_SAFE_DIAG`, `MCP_FIRST_PARTY_PREF_RESTART_RESULT`, `MCP_OFFICIAL_LAUNCHER_VERIFIED`, `STUDIO_MCP_SETUP_AND_TUNNEL_DOCTOR_VERIFIED`, `TUNNEL_FOREGROUND_STARTED`, and exact local `ci_only_baseplate_test` through connected Roblox_Studio tool.

The existing GitHub Actions `roblox-mcp-ai-handoff.yml` reporter posts each completed run's safe outcome automatically to Issue #1, but no coding agent acts while the chat is closed. Never start concurrent 2FA runs or change published Places.


## 2026-11-22 07:43 KST — live run checkpoint (not final proof)

- Official GitHub-hosted Windows workflow [#44954027272](https://github.com/mok9900/roblox/actions/runs/44954027272), job `136998032907`: **in_progress**.
- GitHub job-step API reports step 9 `Verify Roblox email 2FA, local Baseplate, official Assistant MCP and tunnel doctor` **completed/success**, and step 10 `Run verified OpenAI Secure MCP Tunnel (GitHub-hosted foreground)` **in_progress**. This is a new gate-level milestone compared with previous failures, but is NOT proof of a live MCP client handshake or local `ci_only_baseplate_test` enumeration.
- Job log retrieval returned GitHub 404 `BlobNotFound` while job is running. No raw logs or secrets were retrieved; exact `MCP_PREF_SAFE_DIAG`, `MCP_OFFICIAL_LAUNCHER_VERIFIED` and doctor markers remain pending log inspection after completion.
- No code change or additional authenticated workflow run; avoid overlap. Next check: refresh job and retrieve sanitized log markers when available, then invoke `list_roblox_studios` for exact local CI fixture and a safe read-only MCP call. Do not claim completion from step status alone.

- At the same 07:43 KST checkpoint, direct read-only `mcp__Roblox_Studio__list_roblox_studios({})` failed with exact connector error: `McpServerError: Tunnel-client has not been seen for 300 seconds. Ensure tunnel-client is running and connected.` Thus step 10 in_progress does **not** establish remote tunnel connectivity; investigate tunnel-client connection/registration and log markers without restarting real auth.


## 2026-11-22 11:21 KST — live log recovered; stdio child path failure isolated

- [Run #44954027272](https://github.com/mok9900/roblox/actions/runs/44954027272), hosted Windows job 136998032907 remains in progress (step 9 success; step 10 foreground running). Unlike prior 404 responses, the GitHub job log is now retrievable.
- Safe observed markers: `MCP_PREF_SAFE_DIAG: official_identity_confirmed=true settings_file_present=true changed=true enabled=true`; `MCP_FIRST_PARTY_PREF_RESTART_RESULT: official_launcher_present=True`; `STUDIO_MCP_SETUP_AND_TUNNEL_DOCTOR_VERIFIED`. The signed Studio created its own launcher. No fabricated mcp.bat.
- Tunnel doctor accepted `cmd.exe /d /s /c "cd /d ""%LOCALAPPDATA%\\Roblox"" && call mcp.bat"`, but this only checks command presence, not child execution. Foreground tunnel repeatedly reports `stdio MCP command exited` and `stdio MCP command failed; restarting child` (2,335 restart warnings in fetched log). Windows repeatedly prints `The system cannot find the path specified.` This strongly implicates incorrect working-directory/path expansion or cmd quoting in the stdio command, **not** an absent official launcher; the exact failing path remains to be proven without exposing account paths.
- Direct read-only `list_roblox_studios` still fails: `McpServerError: Tunnel-client has not been seen for 300 seconds. Ensure tunnel-client is running and connected.` No successful CI fixture enumeration or tool call. Do not declare success.
- Next safe code step: inspect the tunnel profile builder and add credential-free Windows regression tests for `cmd.exe` argument quoting and `%LOCALAPPDATA%` expansion; test actual invocation using a harmless temporary synthetic batch file, **never** substitute or fabricate Roblox's official `mcp.bat`. After passing no-auth tests, make only the minimal quoting/path fix. No new authenticated retry while current run remains active or within 24h restriction.


## 2026-11-22 12:36 KST — completed run inspection and guarded next test

- Authenticated hosted Windows [run #44954027272](https://github.com/mok9900/roblox/actions/runs/44954027272), job `136998032907`, has **completed/cancelled** (step 9 success; step 10 cancelled). Issue reporter also recorded cancellation at `2026-11-22T03:25:51.613Z`. Do not confuse cancellation with successful tunnel connectivity.
- Retrieved completed job log (14,922 lines): official launcher appeared after authenticated preference/restart; `STUDIO_MCP_SETUP_AND_TUNNEL_DOCTOR_VERIFIED` was printed. Foreground step repeatedly printed `The system cannot find the path specified.` and `stdio MCP command exited` / `stdio MCP command failed; restarting child` through `2026-11-22T03:25:26Z`. The log does not identify which path failed. No actual `ci_only_baseplate_test` MCP enumeration or safe tool call succeeded.
- Current `ci/assisted/session.ps1` line 144 passes `cmd.exe /d /s /c "cd /d ""%LOCALAPPDATA%\Roblox"" && call mcp.bat"` as the tunnel `--mcp-command`. Doctor accepted this configuration, but doctor success is not proof of child execution. Working-directory quoting and runtime expansion remain hypotheses, not confirmed root cause.
- **Next no-auth gate**: on official GitHub-hosted Windows, test `cmd.exe` quoting/expansion with a harmless temporary `probe.cmd` under a path containing spaces, never create or replace a Roblox `mcp.bat`; assert the probe executes and returns expected exit code. Also verify the profile command serialization with secrets absent. Only after this gate passes, apply a minimal launcher invocation fix and rerun no-auth tests.
- **No new authenticated run**: the prior authenticated run was initiated at 2026-11-21T21:55Z, within the last 24h of this checkpoint. Wait until the rolling 24h gate and all preflight tests pass, with no newer real-auth retry. Never overlap sessions.
