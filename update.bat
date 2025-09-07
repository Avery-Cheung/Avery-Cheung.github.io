@echo off
:: One-click upload script - add, commit, push

:: Set commit message, or uncomment next line to input manually
set COMMIT_MSG=Update website
:: set /p COMMIT_MSG=Enter commit message: 

echo Current repository status:
git status
echo ------------------------

echo Staging changes...
git add .

echo Committing changes...
git commit -m "%COMMIT_MSG%"

echo Pushing to GitHub...
git push origin main

echo ------------------------
echo Upload completed!
pause
