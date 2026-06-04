@echo off
setlocal
pushd "%~dp0."
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

pyw -B scripts\desktop_app.py
if errorlevel 1 (
  py -B scripts\desktop_app.py
)

popd
endlocal
