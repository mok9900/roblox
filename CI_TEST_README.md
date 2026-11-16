# Roblox Studio on GitHub Actions - isolation experiment

This branch experiments with installing and actually executing Roblox Studio on GitHub-hosted windows-2025 (4 vCPU / 16 GB) public repository runner.

- The default main branch is not modified.
- ci/probe-studio.ps1 downloads the official Roblox installer, verifies its Authenticode signature, waits for installation, launches Roblox Studio with its documented --task RunScript CLI, and checks for a Luau-generated success marker.
- Installation, successful process spawn, and verified Luau execution are separate states.
- The workflow uploads studio-probe-output containing report.json, CLI output and relevant logs even on failure.
- No Roblox credentials are configured or collected. MCP connectivity is not tested until Studio itself is proven usable.
- GitHub-hosted runners are ephemeral, and standard Windows runners have no dedicated GPU. This experiment may fail because of graphics, interactive-session, login, or installer requirements.
- Run limit: 18 minutes. One-time test on push to this experiment branch.

Official references:
- https://create.roblox.com/docs/studio/cli
- https://github.com/Roblox/roblox-studio-agent-plugin/blob/main/skills/roblox-get-started/references/install.md
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
