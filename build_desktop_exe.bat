@echo off
setlocal
pushd "%~dp0."
chcp 65001 >nul

py -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo PyInstaller is not installed.
  echo To build an exe, run: py -m pip install pyinstaller
  popd
  exit /b 1
)

py -m PyInstaller --noconfirm --onefile --windowed --name "AI机会雷达" scripts\desktop_app.py
if errorlevel 1 (
  popd
  exit /b 1
)

echo.
echo Built: dist\AI机会雷达.exe
popd
endlocal
