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

## 2026-11-21 official GitHub-hosted Gmail OAuth diagnosis

After the owner updated the three GitHub Actions secrets, run
[44839948912](https://github.com/mok9900/roblox/actions/runs/44839948912)
confirmed their **presence**, then safely stopped before Roblox login
because the Google OAuth refresh-token exchange returned HTTP 401. A
follow-up with sanitized error classification,
[44840108422](https://github.com/mok9900/roblox/actions/runs/44840108422),
confirmed the precise Google error category:
`GMAIL_OAUTH_OR_API_UNAUTHORIZED_CLIENT`.

Per Google's OpenID Connect error definitions, `unauthorized_client`
means the OAuth client is not authorized to use the requested grant type.
This does **not** prove the Roblox credentials or Studio MCP are broken.

**Correct OAuth association in the user's own browser (no local runner):**
1. Google Cloud Console → Google Auth Platform → Clients → open the
   intended **web application** client (e.g. the user's RS w GA A client).
   Use its own Client ID and newly rotated active Client Secret. The
   browser screenshots from the prior attempt showed Google OAuth
   Playground's own default Client ID, not demonstrably the newly
   created client. Do not mix these identities.
2. In OAuth Playground **settings gear**, enable
   **Use your own OAuth credentials**, then enter that **same new
   client's** ID and Client Secret. Request **only**
   `https://www.googleapis.com/auth/gmail.readonly`.
3. Start OAuth Playground's authorization **from Step 1 again** with
   offline access enabled. Complete consent under the Gmail account
   that receives Roblox email codes, then exchange the **new**
   authorization code for a **new Refresh Token** under that same client.
   A refresh token issued to a different OAuth client cannot be
   transferred by just updating GitHub's Client ID/Secret.
4. Replace all **three** repository Secrets with this matching set.
   Do not post their contents, screenshot them, commit them, or use
   broad Gmail scopes.
5. Trigger **Roblox Studio MCP - GitHub-hosted Windows only** again.
   Its read-only Gmail OAuth preflight must pass *before* logging into
   Roblox. If Google still refuses `refresh_token` grant, inspect the
   OAuth client type, consent-screen access, and Google Cloud client
   status. The current action must remain stopped until Google
   authenticates this client.

The upgraded `gmail_otp.py` distinguishes `INVALID_CLIENT`,
`UNAUTHORIZED_CLIENT`, `INVALID_GRANT` and similar allowlisted
categories without logging Google error descriptions or response
bodies. Code compilation, Python regression tests, PowerShell static
checks and Windows offline OCR tests all succeeded in
[44840048758](https://github.com/mok9900/roblox/actions/runs/44840048758).

Official references:
- https://developers.google.com/identity/openid-connect/reference
- https://developers.google.com/identity/protocols/oauth2/web-server

## 2026-11-21 17:21 KST: GitHub-hosted real OAuth retry

The owner confirmed rotating/replacing Google OAuth credentials. Triggered
GitHub-hosted Windows run
[44884508623](https://github.com/mok9900/roblox/actions/runs/44884508623)
from main using the supported `hosted-trigger.txt` push.

- The GitHub-hosted runner started and all required GitHub Actions secret
  presence checks passed (Roblox, tunnel, three Gmail OAuth secrets).
- The live Google refresh-token grant returned
  **`GMAIL_OAUTH_OR_API_INVALID_CLIENT`**. This is distinct from the prior
  `UNAUTHORIZED_CLIENT` and was safely classified without printing the
  client ID, client secret, refresh token or Google response body.
- Roblox sign-in, a new verification email, Assistant MCP and the tunnel
  did **not** start; the preflight correctly failed closed.

**Owner's next configuration check (browser only, no local runner):**
open Google Cloud Console → Google Auth Platform → Clients →
the newly created `RS w GA A` web client. Verify the ID stored under
`GMAIL_OAUTH_CLIENT_ID` is this client's actual
`...apps.googleusercontent.com` ID, **not** the old OAuth Playground
default client. Verify the active **rotated secret for this exact same
client** is stored under `GMAIL_OAUTH_CLIENT_SECRET` (client secrets
typically start `GOCSPX-`). Do not put a `GOCSPX-` secret into the ID
field. Generate a fresh authorization/refresh token from OAuth Playground
with **Use your own OAuth credentials** enabled and the identical
client ID+secret, and replace `GMAIL_OAUTH_REFRESH_TOKEN` accordingly.
Only authorize Gmail readonly; do not share any credential or code.

Once the secret pair is valid, the hosted workflow's Gmail OAuth preflight
will resume before official Roblox GUI login. No attempt to bypass 2FA
or run on local/self-hosted infrastructure is made.

## 2026-11-21: hosted retry after matching OAuth client settings

The owner requested another real GitHub-hosted run:
[44885329003](https://github.com/mok9900/roblox/actions/runs/44885329003).
GitHub-hosted Windows executed successfully and all required Actions secret
presence checks passed. Google OAuth token grant **failed with
`GMAIL_OAUTH_OR_API_INVALID_GRANT`**, a new and different response from the
earlier `INVALID_CLIENT`. No Studio login, Roblox 2FA or MCP handoff was
attempted.

**Owner action:** replace only `GMAIL_OAUTH_REFRESH_TOKEN` with a newly
exchanged refresh token minted under the **exact OAuth client whose ID and
current active secret are already in GitHub**. In OAuth Playground, enable
"Use your own OAuth credentials", use this identical Client ID and Secret,
start authorization from Step 1 with `gmail.readonly`, choose offline
access, exchange the new code for tokens, then copy the *refresh* token
(not the access token or authorization code). Do not print or share it.
If consent testing restrictions or a revocation affect the token, reauthorize
the user in that OAuth client. The existing workflow can be rerun after
the secret is replaced. No additional unauthenticated retries should run
until the credential change is made.
