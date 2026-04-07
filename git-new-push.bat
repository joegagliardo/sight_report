@echo off

:: Check if both arguments are provided
if "%~1"=="" goto usage
if "%~2"=="" goto usage

:: 1. Remove old history (Quietly and recursively)
if exist .git (
    rd /s /q .git
)

:: 2. Re-initialize
git init
git add .
git commit -m "0.0.0"

:: 3. Link to new destination using %1 and %2
git remote add origin https://github.com/%~1/%~2.git
git branch -M main

:: 4. Push
git push -u origin main
goto :eof

:usage
echo Error: Missing arguments.
echo Usage: fresh-push.bat <github-username> <repo-name>
pause
exit /b 1
