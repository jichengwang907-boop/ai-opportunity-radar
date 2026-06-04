@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

echo [1/7] Checking account/API connector status...
py -B scripts\check_credentials.py
if errorlevel 1 (
  echo Credential check failed.
  exit /b 1
)

echo [2/7] Validating no-token/exported platform data...
py -B scripts\validate_external_sources.py
if errorlevel 1 (
  echo External data quality check failed.
  exit /b 1
)

echo [3/7] Importing no-token/exported platform data...
py -B scripts\import_external_sources.py
if errorlevel 1 (
  echo External import failed.
  exit /b 1
)

echo [4/7] Collecting realtime AI platform signals...
py -u -B scripts\realtime_ai_platform_monitor.py --once --config config.realtime-ai-platforms.json --report-out reports\realtime-ai
if errorlevel 1 (
  echo Realtime collection failed.
  exit /b 1
)

echo [5/7] Generating product feedback and trend report...
py -B scripts\generate_product_feedback_report.py --products data\products.realtime-ai.csv --search data\search_results.realtime-ai.csv --out reports\product-feedback
if errorlevel 1 (
  echo Product feedback report failed.
  exit /b 1
)

echo [6/7] Generating opportunity ranking...
py -B scripts\generate_opportunity_report.py --analysis reports\realtime-ai\analysis.json --out reports\opportunity-radar
if errorlevel 1 (
  echo Opportunity ranking failed.
  exit /b 1
)

echo [7/7] Generating product demand source catalog...
py -B scripts\generate_demand_source_report.py --config config.product-demand-sources.json --out reports\product-demand-sources
if errorlevel 1 (
  echo Demand source catalog failed.
  exit /b 1
)

echo.
echo Done.
echo Realtime report: reports\realtime-ai\summary.md
echo Product feedback: reports\product-feedback\products.md
echo Opportunity report: reports\opportunity-radar\opportunities.md
echo Demand sources: reports\product-demand-sources\sources.md
endlocal
