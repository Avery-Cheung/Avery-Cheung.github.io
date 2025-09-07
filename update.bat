@echo off
:: 一键上传脚本 - 自动 add, commit, push

:: 设置提交说明
set COMMIT_MSG=更新网站

echo 当前仓库状态：
git status
echo ------------------------

echo 暂存修改...
git add .

echo 提交修改...
git commit -m "%COMMIT_MSG%"

echo 上传到 GitHub...
git push origin main

echo ------------------------
echo 上传完成！
pause
