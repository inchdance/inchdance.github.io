#!/bin/bash

# 切换到主分支
git checkout -b master

# 添加所有文件
latest_tag=$(git describe --tags --abbrev=0)

# 构建站点
mkdocs build

# 切换到站点目录
cd site

# 添加所有文件
git checkout gh-pages
git add .

# 提交更改
commit_message="Deployed $(git rev-parse --short HEAD) from branch $current_branch with tag $latest_tag using MkDocs version: $(mkdocs --version)"
git commit -m "$commit_message"

# 添加远程仓库
# git remote add deploy1 git@github.com:inchdance/inchdance.github.io.git

# 强制推送到远程仓库的 main 分支（或者 master 分支，取决于您的默认分支名称）
git push --set-upstream deploy1 gh-pages

echo "Deployment complete"