# Vanda 实验运行状态（2026-11-06 19:45 SGT）

## 当前进度

Vanda 登录和 PBS 查询现已恢复。严格完成审计为 **384/473 个已提交批次**；固定图矩阵逐格审计为 **16,116/19,980 个配置**。固定图矩阵不包含弱扩展。只有本地存在完成标记、标记对应原作业或登记的替代作业，并且校验通过的批次才计为完成。

| 实验部分 | 严格完成 | 当前状态 |
|---|---:|---|
| Serial，固定图 | 45/45 | 完成 |
| GPU 强扩展，固定图 | 45/45 | 完成；4/8 GPU 扩展按要求移除 |
| CPU MPI 强扩展 | 151/180 | 尚缺 29 批；部分旧 PBS 作业仍暂挂 |
| CPU MPI 512 核强扩展端点 | 0/45 | 未完成；多数旧作业暂挂或未通过 |
| CPU 弱扩展 | 常规 1/1；512 rank 1/3 | uniform 完成；hub 与 controlled 正在补跑/补校验 |
| Kokkos OpenMP 网格（1/2/4 节点） | 130/139 | 剩余 9 批已重投，尚未完成校验 |
| Kokkos OpenMP 512 核端点 | 0/4 | 旧作业仍待处理 |
| CPU 按核配平弱扩展 | 常规 1/1；512 核 1/1 | uniform 已通过校验 |

## 目前队列和重跑

19:45 SGT 的 PBS 状态汇总为 **2 个运行、10 个排队、77 个用户暂挂**。其中：

- Kokkos CPU 大图的 9 个重跑 `1526604–1526612` 使用免费 CPU 队列和 6 小时上限；`1526604`（strong_uniform，1 节点）运行 12:55，`1526607`（strong_hub，1 节点）运行 6:11，其余 7 个排队。
- controlled 的既有 p=512 结果已安排免费校验续跑 `1526615`，当前排队。它复用已写出的计时并补齐独立验证，不重跑计时。
- hub 的 p=512 弱扩展作业 `1526616` 已提交到付费 CPU 队列，申请 8 节点、512 rank、2 小时；当前因节点资源不足排队。旧作业 `1510691` 曾在 1 小时上限失败。
- 旧队列中 74 个作业处于用户暂挂状态，PBS 记录显示 hold 类型为用户暂挂。维护结束不会自动解除这些 hold；目前没有批量释放，以免在 CPU 额度有限时误启动大批任务。

当前 `hpc project` 余额为 **1,570.921 CPU 核小时**、**978.587 GPU 小时**。这不足以据此承诺所有剩余 CPU 批次都能完成；付费队列的 512 核作业会消耗大量额度。免费队列当前允许运行的 Kokkos 重跑和校验续跑已优先提交。

## 复核方法

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
qstat -u hongxinran
hpc project
```

Vanda 上的替代作业映射已同步至 [`retry_jobs.tsv`](results/updated_vanda_scaling/20261102T092147Z/retry_jobs.tsv)。之前的快照及每批历史说明见 [`updated_vanda_run_status_20261105.md`](updated_vanda_run_status_20261105.md)；实验结论与 PBS 用时记录仍分别见 [`updated_experimental_conclusions_20261105.md`](updated_experimental_conclusions_20261105.md) 和 [`updated_vanda_runtime_budget_20261105.md`](updated_vanda_runtime_budget_20261105.md)。
