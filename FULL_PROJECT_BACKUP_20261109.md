# 本地项目完整备份：2026-11-09

用户确认本次范围为**本地项目完整上传**，不包含尚未下载到 Mac 的 Vanda 远端原始工作文件。

**已完成上传并发布到现有私有仓库。** 11 个附件的远端 SHA-256 和大小全部匹配，仓库可见性保持 private，访问范围没有扩大。

## 下载入口

- [完整源码、脚本、文档和已同步结果：GitHub main](https://github.com/rosesnack/DSA5208_PROJECT_3)
- [原始数据、逐点输出及依赖源码附件](https://github.com/rosesnack/DSA5208_PROJECT_3/releases/tag/full-project-backup-20261109)

原项目快照为 `1dadf5d9982f28640070bef4a87ae5c756e4163a`，共有 **73,332 个受 Git 管理的文件**。这些文件均已推送并核对远端提交一致。其余本地项目原始附件通过同仓库 Release 保存，避免将多 GB 逐点输出直接写入普通 Git 历史。

| 补充归档 | 文件数 |
|---|---:|
| 原始图、生成图和对应输入文件 | 124 |
| 本地完整 CPU 实验的逐点 PageRank 输出 | 1,890 |
| 本地弱扩展实验的逐点输出 | 216 |
| 已下载到本机的 Vanda smoke 逐点输出 | 53 |
| 固定版本 Kokkos 源码 | 1,481 |
| 非敏感运行日志与监控快照 | 10 |
| **合计** | **3,774** |

附件无损去重压缩后共 **960,888,737 字节**，共 7 个不超过 512 MiB 的归档分卷，另附清单、恢复工具和说明。所有原文件路径都保留；恢复工具会将重复内容展开为互相独立的文件。原始文件逐项读取、解压及 SHA-256 对比均通过；源码和受管结果由 Git 的提交/对象哈希核对。

## 恢复

先克隆仓库，再下载该 Release 的全部附件到同一个目录。按附件中的 `RESTORE.md` 操作：先运行 `shasum -a 256 -c SHA256SUMS`，再运行 `python3 restore_backup.py --assets . --destination /path/to/DSA5208_PROJECT_3`，恢复到新克隆的项目目录。工具会自动读取分卷、检查每个原文件 SHA-256，并还原独立文件。

仓库也保留可审计清单：

- [每个附件原文件的路径、大小与 SHA-256](backups/20261109/manifest.json)
- [所有归档内容的解压校验结果](backups/20261109/archive_verification.json)
- [上传范围及文件数量](backups/20261109/upload_inventory.json)
- [分卷校验和](backups/20261109/SHA256SUMS)
- [恢复命令](backups/20261109/RESTORE.md)
- [GitHub 远端附件大小、SHA-256 及下载链接核验](backups/20261109/github_release_receipt.json)
- [仓库私有范围及附件内容检查](backups/20261109/publication_scope_check.json)

## 排除项

不公开账户认证信息和私人 `amgr` 账单 CSV；不备份可重建的编译产物/缓存、进程 PID/锁文件和嵌套 Git 元数据。它们不是项目源码、原始实验数据或性能结果。Vanda 上没有下载到本机的大型原始工作文件仍保留在 Vanda，不在用户确认的这次本地备份范围内。

有效结果继续按原实验矩阵和校验标记统计，原始向量归档不会把尚未校验的实验变成“通过”，也不会把本地时间混入 Vanda 性能表。
