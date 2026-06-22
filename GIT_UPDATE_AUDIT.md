# GIT_UPDATE_AUDIT.md

## 1. 当前分支

- 分支名：`merged-branch-sanitized`
- 本地与远程 `origin/merged-branch-sanitized` 一致（`Your branch is up to date`）

## 2. 当前是否有未提交改动

- 无已跟踪文件的修改（`nothing added to commit`）
- 仅存在大量 untracked 文件，全部来自 `../../`（用户 home 目录），与项目本身无关
- 无 `git diff` 输出（空 patch）

## 3. 远程仓库地址

- Fetch URL: `git@github.com:MMO1717/MDS.git`
- Push URL: `git@github.com:MMO1717/MDS.git`

## 4. 远程默认分支

- `HEAD branch: main`（`git remote show origin` 确认）
- 远程有 4 个分支：
  - `origin/main` — 宿舍能源管理系统（与 BRAG-Pipeline 无关）
  - `origin/merged-branch` — 合并分支，包含前端 + BRAG-Pipeline + 启动脚本
  - `origin/merged-branch-sanitized` — 当前所在分支的远程版本
  - `origin/frontend-work` — 前端工作分支

## 5. 本地与远程差异

- 当前分支 `merged-branch-sanitized`：**本地与远程完全同步**，无差异
- `origin/main` 与当前分支完全不相关（宿舍能源管理系统项目），不建议合并
- `origin/merged-branch` 相比当前分支多了 2 个 commit：
  - `e7d4d39` Add one-click startup scripts
  - `d92d1e8` Merge remote-tracking branch 'origin/merged-branch-sanitized' into merged-branch
  - `9bf315e` Merge remote-tracking branch 'origin/frontend-work' into merged-branch
  - 以及 `origin/merged-branch-sanitized` 的内容已经合并进 `origin/merged-branch`

## 6. 远程新增 / 修改 / 删除文件列表

- `origin/merged-branch` 相比当前分支新增：
  - `start.command` — macOS 一键启动脚本
  - `start.sh` — Shell 启动脚本
  - 以及 `origin/frontend-work` 的前端文件（`frontend/` 目录）
  - 以及 `origin/main` 的算法端文件（`algorithm/` 目录）
- 这些新增内容与 BRAG-Pipeline 比赛项目**无直接关系**（是另一个项目：宿舍能源管理系统）

## 7. 是否建议 merge / pull

- **不建议**合并 `origin/merged-branch` 或 `origin/main` 到当前分支
- 原因：`origin/merged-branch` 混合了两个不相关项目（BRAG-Pipeline + 宿舍能源管理系统），合并会引入大量无关文件
- 建议：在当前分支 `merged-branch-sanitized` 上直接开发 BRAG-Pipeline，保持干净

## 8. 合并前风险

- 如果合并 `origin/merged-branch`：会引入 `algorithm/`、`frontend/`、`backend/`、`start.sh` 等无关目录，增加项目复杂度
- 如果合并 `origin/main`：完全不同项目，不应合并

## 9. 回滚方案

- 当前分支没有未提交改动，可直接 `git reset --hard HEAD`
- 如需回滚到远程状态：`git reset --hard origin/merged-branch-sanitized`
- 建议在开始改造前创建新分支：`git checkout -b phase0-baseline`
