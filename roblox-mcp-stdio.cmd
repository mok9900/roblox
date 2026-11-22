@echo off
REM Stdio transport bridge for the *official* Roblox-generated MCP launcher.
REM This file is NOT mcp.bat and must never synthesize or replace it.
REM Running from the checked-out GitHub Actions working directory only.
if /I not "%GITHUB_ACTIONS%"=="true" (
  >&2 echo STUDIO_MCP_GITHUB_HOSTED_ONLY
  exit /b 11
)
if not defined LOCALAPPDATA (
  >&2 echo STUDIO_MCP_LOCALAPPDATA_MISSING
  exit /b 12
)
if not exist "%LOCALAPPDATA%\Roblox\mcp.bat" (
  >&2 echo STUDIO_MCP_OFFICIAL_LAUNCHER_MISSING
  exit /b 13
)
cd /d "%LOCALAPPDATA%\Roblox"
if errorlevel 1 (
  >&2 echo STUDIO_MCP_WORKDIR_UNAVAILABLE
  exit /b 14
)
call "%LOCALAPPDATA%\Roblox\mcp.bat"
exit /b %ERRORLEVEL%
