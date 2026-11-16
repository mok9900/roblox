# GitHub Actions Windows Roblox Studio feasibility test

This is an isolated experiment branch in the existing public repository. The main branch is unchanged. Creating a new repository was not available through the connected GitHub API capabilities.

## Verified results — November 16, 2026

GitHub hosted runner: windows-2025, Windows Server 2025, x64, 4 logical CPUs (AMD EPYC 7763), 15.99 GB RAM.

### Run 1 — https://github.com/mok9900/roblox/actions/runs/43835532804

- Official Roblox Studio installer downloaded; Authenticode signature status Valid, signed by Roblox Corporation.
- Installer log says "Reporting Installer Success".
- Installer installed Studio at C:\Program Files\Roblox\Versions\version-63eb6055af4e4688\RobloxStudioBeta.exe.
- Installer successfully launched a RobloxStudioBeta process (PID 4860).
- Studio initialized graphics via Microsoft Basic Render Driver / D3D11 feature level 11.1 and opened the login dialog.
- Probe incorrectly reported installed=false because its initial path discovery omitted C:\Program Files\Roblox. The first result was a **probe false negative**, not a failed installation.

### Run 2 — https://github.com/mok9900/roblox/actions/runs/43836867886

- Path detection fixed. Studio executable discovered under C:\Program Files\Roblox.
- is_installed=true; process_launched=true.
- The official --task RunScript CLI invocation did not complete the smoke test: its initial process returned exit code 1 and no Luau success marker was written.
- A RobloxStudioBeta process was still present at job cleanup; Studio log showed login UI initialization (login not completed).
- mcp_launcher_present=false at %LOCALAPPDATA%\Roblox\mcp.bat.

## Conclusion

**YES** — Roblox Studio can be installed and the program can launch on the standard free Windows GitHub-hosted runner. Software Direct3D 11 rendering and login UI initialization were observed in its own log.

**NOT YET VERIFIED** — unattended Studio editing, authenticated place loading, RunScript execution, or Studio MCP connectivity. The unauthenticated RunScript probe failed. Avoid treating this as proof that Studio MCP works on Actions.

Do not commit Roblox credentials/tokens into this public repository. GitHub-hosted runners are ephemeral and jobs have a six-hour maximum duration; this is not a permanent Windows PC.

## Repository files

- .github/workflows/roblox-studio-windows-probe.yml — reproducible experiment
- ci/probe-studio.ps1 — installer and run diagnostic
- ci/smoke.luau — test Luau script

Official documentation:
- https://create.roblox.com/docs/studio/cli
- https://create.roblox.com/docs/studio/mcp
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
