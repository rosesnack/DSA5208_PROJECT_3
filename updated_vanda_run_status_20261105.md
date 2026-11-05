# Vanda 实验运行状态（2026-11-05 14:43 SGT）

主运行 ID：`20261102T092147Z`。仅当结果已同步、`complete.txt` 对应原作业或登记的替代作业、且独立校验通过时，才计为完成。严格清单及结论见 [`updated_experimental_conclusions_20261105.md`](updated_experimental_conclusions_20261105.md)。

| 部分 | 严格完成/已提交 | 当前情况 |
|---|---:|---|
| 固定图 Serial | 45/45 | 完成 |
| 固定图 GPU p=1/2 | 45/45 | 完成；4/8 GPU 为可选扩展 |
| 固定图 CPU MPI 强扩展 | 150/180 | 本轮新增 3 张 hub 网格图的 8 节点点；下一张正在运行 |
| 固定图 CPU 512 核 | 0/45 | 首个作业传输层失败；其余暂挂 |
| CPU 原定义弱扩展 | 常规 1/1；512 核 1/3 | uniform 已验证；hub 已解除暂挂但仍排队，controlled 未启动 |
| Kokkos OpenMP 多线程网格 | 29/139；512 核 0/4 | 45 图的 1/2/4 节点批次已全部提交免费队列；8 节点只有原有 4 图完成 |
| CPU 按核配平 T=4 弱扩展 | 常规 1/1；512 核 0/1 | uniform 常规端点完成 |
| **全部已提交批次** | **281/473** | 固定图逐格审计 **13,020/19,980**；已同步 2601 份 `validation.json` 全部 `failed=0` |

14:32 Vanda 队列有 **3 个 R、112 个 Q、79 个 H**。用户刷新额度后，项目 CPU Net Balance 从 **3151.249** 变为 **2127.249 核小时**，GPU Net Balance 为 **978.587 GPU 小时**；运行作业会预占额度，完成作业的返还尚未体现在此时查询中。14:43 付费队列作业 `1513434`（`grid_hub_n100000_d8` 的 8 节点点）已运行超过 10 分钟，尚未完成。512 核 hub 弱扩展作业 `1510691` 已解除暂挂，但因节点及队列限制仍排队。其余 79 个大作业继续暂挂。

本轮 `grid_hub_n50000_d8`、`grid_hub_n50000_d16`、`grid_hub_n100000_d4` 的 8 节点作业 `1513419/1513424/1513429` 均以 PBS `Exit_status=0` 结束，每个约 7 分钟；其各 7 份独立校验报告全部通过。已提交的 Kokkos OpenMP 1/2/4 节点批次共覆盖 45 张固定图，其中本轮新提交 123 批，已有 13 批通过校验。其余 41 张图的 Kokkos 8 节点批次尚未提交，当前免费队列的核心上限不能覆盖该布局。

已知历史问题：`synthetic_uniform` 512 核固定图作业 `1510577` 因 MPI TCP 地址绑定失败退出，详见[日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-512.o1510577)。uniform 512 核弱扩展作业 `1510690` 写出了六组完整计时后在独立校验阶段达到一小时墙钟上限，后由免费队列作业 `1521114` 补齐校验，未重跑计时。`strong_uniform` 的 1/2 节点超时续跑最终由 `1520951/1520952` 完成；先前超时的[节点 1 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515650)及[节点 2 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515651)已保留。

复核：

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
qstat -u hongxinran
hpc project
```
