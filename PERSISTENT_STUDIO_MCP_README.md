# Persistent interactive Windows Studio → OpenAI MCP Tunnel

This optional route complements the existing **GitHub-hosted ephemeral** workflow.
It is for a Windows PC/VM where the owner has already signed in through Roblox
Studio's official UI, and wants to reuse that session rather than trigger a
new-device/email-OTP challenge on every run.

## Setup (one-time, on a Windows PC or Windows VM you control)

1. Open Roblox Studio, sign in normally and open an unsaved local Baseplate
   once. Keep the Windows user logged in. Confirm the built-in Assistant is
   present. This does **not** require disabling or circumventing 2FA.
2. In this repository's GitHub **Settings → Actions → Runners**, add a
   self-hosted Windows x64 runner using GitHub's current generated setup
   commands. Add the custom label `roblox-studio-interactive` when running
   `config.cmd` (or through GitHub's runner labels).
3. **Important:** Start the runner in the same logged-in Windows desktop as
   Roblox Studio with `run.cmd`. **Do not** install/start the runner as a
   Windows service: services live in a different Windows session and GUI
   capture/UI Automation/SendInput will not reach the signed-in desktop.
4. Keep existing GitHub Actions secrets
   `OPENAI_TUNNEL_RUNTIME_KEY` and `OPENAI_TUNNEL_ID` configured.
   The persistent workflow deliberately does **not** read
   `ROBLOX_USERNAME`, `ROBLOX_PASSWORD`, Gmail or email OTP.
5. From GitHub Actions, select the workflow named
   **Roblox MCP - Start persistent interactive Studio tunnel** and click
   **Run workflow**. This dispatch entrypoint is deliberately installed
   on the default `main` branch (GitHub requires that for manual workflow
   discovery). It checks out `feature/studio-openai-tunnel-assisted` for
   the actual tested code. There is **no automatic push trigger**; an online
   self-hosted runner with the exact labels is required.

## Expected secure path

- Downloads/signature-verifies official Roblox Studio installer (does not
  reinstall if the existing Studio is valid) and checksum-verifies the latest
  official `openai/tunnel-client` Windows release.
- Confirms an interactive Windows foreground desktop exists.
- Opens the pinned Roblox-owned **local** test Baseplate via official EditFile
  CLI; verifies a real Studio editor instead of merely trusting a process.
- Checks official `%LOCALAPPDATA%\Roblox\mcp.bat`; if missing, attempts
  guarded Assistant UI discovery and official MCP toggle. When detection is
  unavailable, stops with a clear user-side official UI action to perform.
  The script never manufactures or overwrites the official launcher.
- Initializes a distinct `roblox-studio-persistent` Secure MCP Tunnel stdio
  profile, runs `doctor --explain`, then keeps `run --profile` active.

If the launcher is missing and automated tooltip discovery cannot verify the
Assistant button, use the Studio UI **Assistant → … → Settings → MCP Servers
→ Enable Studio as MCP server**, then re-run the workflow. Older Roblox
versions may instead show **… → Manage MCP Servers**.

The tunnel **must** stay online in the same Windows session.
Success is only verified when the tunnel doctor succeeds **and**
`list_roblox_studios` returns an actual Studio instance. An Actions green
check for offline tests is not equivalent to a live Studio connection.

### Common errors

| Safe diagnostic | Meaning |
| --- | --- |
| `PERSISTENT_INTERACTIVE_DESKTOP_NOT_FOUND` | Runner is likely a Windows service/non-interactive; run under the active desktop with `run.cmd`. |
| `PERSISTENT_STUDIO_EDITOR_UNVERIFIED` | Roblox Studio is not currently authenticated/usable on that Windows account, or the local editor did not load. Sign in with the official UI, do not turn off 2FA. |
| `PERSISTENT_MCP_UI_UNREACHABLE` | Assistant switch not accessible; activate official switch in the signed-in editor. |
| `PERSISTENT_OFFICIAL_MCP_LAUNCHER_MISSING` | No official mcp.bat file; do not create a fake launcher. |
| `PERSISTENT_TUNNEL_DOCTOR_FAILED` | Check official launcher, local server and OpenAI tunnel runtime secrets/profile. |

Security: a self-hosted runner executes repository code on your machine.
Use a dedicated Windows account/VM, restrict GitHub repo write access,
protect your Actions secrets, and avoid running untrusted pull requests or
workflows on this runner. The runner is reserved for manual execution only.
Do not expose the Studio MCP port to the internet or share OAuth callback URIs.

Official references:
- https://create.roblox.com/docs/studio/mcp
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners
