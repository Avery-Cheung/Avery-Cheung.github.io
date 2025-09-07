@echo off
:: 一键上传脚本 - add, commit, push

:: 设置提交信息，或者取消下一行注释以手动输入
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
