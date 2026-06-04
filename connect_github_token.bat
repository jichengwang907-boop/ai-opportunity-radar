@echo off
setlocal
cd /d "%~dp0"

where gh >nul 2>nul
if errorlevel 1 (
  echo GitHub CLI not found.
  echo Install it first:
  echo   winget install --id GitHub.cli
  echo.
  echo Then run:
  echo   gh auth login
  echo   connect_github_token.bat
  exit /b 1
)

gh auth status >nul 2>nul
if errorlevel 1 (
  echo GitHub CLI is installed but not logged in.
  echo A browser login may open now.
  gh auth login -h github.com -p https -w
  if errorlevel 1 (
    echo GitHub login failed.
    exit /b 1
  )
)

py -B scripts\setup_tokens.py --init --import-gh --verify github --status
if errorlevel 1 (
  echo Token import failed.
  exit /b 1
)

echo.
echo GitHub token setup complete.
endlocal
