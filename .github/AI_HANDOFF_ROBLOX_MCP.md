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
