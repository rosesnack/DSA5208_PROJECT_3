# Vanda 实验运行状态（2026-11-05 16:55 SGT）

## 最新状态（2026-11-06 19:00 SGT）

Vanda 已恢复并在 19:00 可登录；`hpc project` 显示 CPU 余额 **1570.921 核小时**、GPU 余额 **978.587 GPU 小时**。最新同步后进度为 **384/473 批次**、固定图 **16,116/19,980 配置**。Kokkos CPU 多线程网格 **130/139**；剩余 9 批为三张特大图 `strong_uniform/strong_hub/strong_controlled` 的 1/2/4 节点点，PBS 历史确认全部以 `Exit_status=-29` 在约 2 小时墙钟上限失败，需调整上限或拆分后续跑。

弱扩展端点的 PBS 历史已查明：hub、controlled 的 512-rank 作业 `1510691/1510692` 均因 1 小时 walltime 上限被杀，分别运行 **1:00:31 / 1:00:27**，`Exit_status=-29`，不能计为完成；按核配平的 uniform C=512 作业 `1513566` 成功，运行 **1:04:03**，`Exit_status=0` 且完成校验。因此 CPU 原定义弱扩展仍为 **1/3 个 512-rank 家族端点**，按核配平端点 uniform **1/1**。CPU 项目余额较 11 月 5 日的 2127.249 减少约 **556.328 核小时**；不把项目余额变化直接等同于上述三项作业的实际核小时，详细 PBS 时间见预算文件和 CSV。

**18:46 SGT 维护提示：**再次连接 Vanda 时，登录节点显示系统因紧急漏洞修复暂停服务，并要求用户保存工作、立即退出；SSH 随后拒绝认证。此时无法获取实时队列或额度。下方最后成功核查为 16:47 SGT；本地结果已同步至 16:55 SGT。

**2026-11-06 02:06 SGT 更新：**再次尝试连接仍收到相同维护通知，SSH keepalive 超时断开；实时 PBS 队列和额度仍无法查询。最新可验证的本地结果仍为 Kokkos CPU 网格 63/139、总批次 316/473、固定图单元 14,106/19,980。

弱扩展继续作为必跑项；4/8 GPU 已从实验计划中移除。

主运行 ID：`20261102T092147Z`。仅当结果已同步、`complete.txt` 对应原作业或登记的替代作业、且独立校验通过时，才计为完成。严格清单及结论见 [`updated_experimental_conclusions_20261105.md`](updated_experimental_conclusions_20261105.md)；每个 PBS 作业的申请资源和实际用时见 [`updated_vanda_runtime_budget_20261105.md`](updated_vanda_runtime_budget_20261105.md)。

| 部分 | 严格完成/已提交 | 当前情况 |
|---|---:|---|
| 固定图 Serial | 45/45 | 完成 |
| 固定图 GPU p=1/2 | 45/45 | 完成；4/8 GPU 不在目标内 |
| 固定图 CPU MPI 强扩展 | 151/180 | 本轮新增 4 张 hub 网格图的 8 节点点，均通过校验 |
| 固定图 CPU 512 核 | 0/45 | 首个作业传输层失败；其余暂挂 |
| CPU 原定义弱扩展 | 常规 1/1；512 核 1/3 | uniform 验证通过；hub/controlled 512-rank 作业各因 1 小时上限失败 |
| Kokkos OpenMP 多线程网格 | 130/139；512 核 0/4 | 剩余 9 批是三张特大图的 1/2/4 节点点，均因 2 小时 walltime 超限失败 |
| CPU 按核配平 T=4 弱扩展 | 常规 1/1；512 核 1/1 | uniform C=4…512 均通过校验 |
| **全部已提交批次** | **384/473** | 固定图逐格审计 **16,116/19,980**；其中 130 个 Kokkos CPU 网格批次已完成 |

11 月 5 日 16:47 的旧快照记录过上述作业因资源不足排队；维护恢复后弱扩展的三个端点及九个 Kokkos 大图批次均已运行结束。只有 uniform C=512 通过；其余十一个批次因 walltime 终止且没有完成标记。最新同步结果只把严格完成且独立校验通过的批次计入 384/473；19,980 仍不含弱扩展。

本轮 `grid_hub_n50000_d8`、`grid_hub_n50000_d16`、`grid_hub_n100000_d4/d8` 的 8 节点作业 `1513419/1513424/1513429/1513434` 均以 PBS `Exit_status=0` 结束，各 7 份独立校验报告全部通过。前三项约 7 分钟，第四项 16 分 42 秒；四项实际用时和额度估计见预算说明。已提交的 Kokkos OpenMP 1/2/4 节点批次共覆盖 45 张固定图，其中本轮新提交 123 批，已有 19 批通过校验。其余 41 张图的 Kokkos 8 节点批次尚未提交，当前免费队列的核心上限不能覆盖该布局。

已知历史问题：`synthetic_uniform` 512 核固定图作业 `1510577` 因 MPI TCP 地址绑定失败退出，详见[日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-512.o1510577)。uniform 512 核弱扩展作业 `1510690` 写出了六组完整计时后在独立校验阶段达到一小时墙钟上限，后由免费队列作业 `1521114` 补齐校验，未重跑计时。`strong_uniform` 的 1/2 节点超时续跑最终由 `1520951/1520952` 完成；先前超时的[节点 1 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515650)及[节点 2 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515651)已保留。

复核：

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
qstat -u hongxinran
hpc project
```
