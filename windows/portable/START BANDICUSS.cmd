@echo off
setlocal DisableDelayedExpansion
if not exist "%~dp0runtime\python.exe" (
    echo Please choose Extract All on the ZIP, then open START BANDICUSS in the extracted folder.
    pause
    exit /b 1
)
pushd "%~dp0"
"%~dp0runtime\python.exe" -B -X utf8 "%~dp0support\start.py"
set "bandicussExit=%errorlevel%"
popd
exit /b %bandicussExit%
