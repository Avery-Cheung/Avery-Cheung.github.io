@echo off
:: 自动同步脚本 - pull 最新、commit 本地修改、push 到 GitHub

:: 设置仓库路径（改成你的仓库路径）
set REPO_PATH=E:\InformationInUniversity\CSC\personalWebsite\Avery-Cheung.github.io

:: 设置默认提交信息
set COMMIT_MSG=Auto sync local changes

echo Changing directory to repository...
cd /d "%REPO_PATH%"

echo Pulling latest changes from GitHub...
git pull origin main

echo Checking repository status...
git status

:: 暂存本地修改
git add .

:: 检查是否有修改可以提交
git diff --cached --quiet
if %errorlevel%==0 (
    echo No local changes to commit.
) else (
    echo Committing local changes...
    git commit -m "%COMMIT_MSG%"
    echo Pushing changes to GitHub...
    git push origin main
)

echo ------------------------
echo Sync completed!
pause
