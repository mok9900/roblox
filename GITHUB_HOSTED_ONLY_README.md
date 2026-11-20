# Roblox Studio → ChatGPT MCP: GitHub-hosted Actions only

> Supported runner types: GitHub-managed `windows-2022` and `windows-2025`.
> **No self-hosted runner, local PC automation runner, or persistent VM is used.**

## Where to run

On the repository's **Actions** page, select:

`Roblox Studio MCP - GitHub-hosted Windows only`

The workflow is registered on `main` and checks out the tested scripts from
`feature/studio-openai-tunnel-assisted`. Choose a GitHub-hosted Windows image.
Alternatively, a push modifying `ci/assisted/hosted-trigger.txt` on `main`
starts the default `windows-2022` hosted run.

GitHub Actions URL:
https://github.com/mok9900/roblox/actions/workflows/roblox-studio-hosted-mcp.yml

## Why the Nov 21 preflight currently stops

Run `44837521431` executed on GitHub's Windows runner. The Roblox and OpenAI
tunnel secrets passed presence checks, but the new **fully automatic Gmail
OAuth** path stopped with `GMAIL_OAUTH_READONLY_SECRETS_MISSING`.

This is intentional: abort **before** submitting Roblox credentials or
requesting a new email verification code if the Actions runner cannot
retrieve it itself. The old RSA encrypted-code relay remains in the
legacy workflow for compatibility, but it is not the autonomous path.

## One-time, browser-only Gmail OAuth authorization (no local runner)

The ChatGPT Gmail connector does **not** export its OAuth credentials to
GitHub Actions. GitHub must receive its own narrowly authorized Gmail
credentials, stored in repository **Actions secrets**, not repository files.

1. In Google Cloud Console, create/select a project and enable the **Gmail
   API**. Configure the OAuth consent screen (add your own Gmail account as a
   test user when in Testing mode) and create an OAuth client ID appropriate
   to your browser-based authorization flow.
2. Use Google's official OAuth 2.0 Playground in a browser with **your own**
   client ID/secret. Request the single
   `https://www.googleapis.com/auth/gmail.readonly` scope, with
   offline/refresh-token access. Authorize the actual Gmail mailbox that
   receives Roblox verification mail. Exchange the authorization code for
   OAuth tokens and securely copy the **refresh token**.
3. In GitHub repository **Settings → Secrets and variables → Actions →
   New repository secret**, configure exactly these three secrets:

   | Secret name | Value |
   | --- | --- |
   | `GMAIL_OAUTH_CLIENT_ID` | OAuth client's ID |
   | `GMAIL_OAUTH_CLIENT_SECRET` | OAuth client's secret |
   | `GMAIL_OAUTH_REFRESH_TOKEN` | OAuth refresh token for the Gmail inbox |

   Do **not** paste any values in chat or commit them to this public repo.
   Maintain existing `ROBLOX_USERNAME`, `ROBLOX_PASSWORD`,
   `OPENAI_TUNNEL_RUNTIME_KEY`, and `OPENAI_TUNNEL_ID` secrets.

4. Run the hosted workflow again. It performs an OAuth refresh + Gmail API
   permission check **before any Roblox login**. Only if that passes does
   it install Studio and proceed with official UI email verification.

Google's OAuth testing mode may issue short-lived (e.g. 7-day) refresh
tokens. If one expires, the fail-closed preflight reports the OAuth API error,
rather than repeatedly triggering Roblox 2FA. Gmail read-only is a restricted
scope; comply with Google's applicable OAuth app rules and approvals.

Official reference:
- https://developers.google.com/workspace/gmail/api/guides/list-messages
- https://developers.google.com/identity/protocols/oauth2/web-server
- https://developers.google.com/oauthplayground/

## GitHub-hosted execution flow

1. Verify all required repository secrets are present (no values in logs).
2. Refresh Gmail OAuth token and verify readonly mailbox API access.
3. Configure only official Roblox HTTPS → `roblox-studio-auth` callback policy.
4. Install signed Roblox Studio and SHA256-verified OpenAI tunnel-client.
5. Use guarded native Studio login, or official Edge Roblox UI fallback.
6. Select official email 2FA when available, and read only fresh official
   Roblox verification mail in **the same hosted runner**. Code never
   appears in a log, repository file, artifact, or Actions output.
7. Confirm actual logged-in Studio UI and open the pinned **local-only**
   Baseplate fixture; do not modify any user's published Place.
8. Resolve Assistant via corrected UI Automation control types and a
   guarded in-memory DXGI/OCR fallback. Activate the official Studio MCP
   switch. Require Roblox-generated `mcp.bat`; do not fabricate it.
9. Initialize OpenAI Secure MCP Tunnel, run official `doctor --explain`,
   then `run`.
10. A **real** `list_roblox_studios` tool response is the end-to-end
    success gate. Test green checks alone do not prove a live connection.

**Limits:** GitHub-hosted Windows instances are ephemeral. The session
cannot survive after the job ends; restarting triggers a new official Roblox
sign-in and possibly another 2FA challenge. Keep the job within GitHub's
execution limits. No perpetual 24/7 Studio session is claimed.

## Current verified status

- Assistant UIA capitalization mismatch fixed and regression tested.
- Credential-free Python/PowerShell/OCR tests passed on GitHub Actions.
- Hosted workflow preflight run `44837521431` was launched and stopped
  safely because the three Gmail OAuth secrets were not configured.
- Actual Assistant toggle, official `mcp.bat`, tunnel doctor, and
  `list_roblox_studios` are **not yet end-to-end verified**.

All code and test jobs continue to execute on GitHub-managed runners only.
