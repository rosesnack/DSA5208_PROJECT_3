# Vanda 实验运行状态（2026-11-05 16:55 SGT）

**18:46 SGT 维护提示：**再次连接 Vanda 时，登录节点显示系统因紧急漏洞修复暂停服务，并要求用户保存工作、立即退出；SSH 随后拒绝认证。此时无法获取实时队列或额度。下方最后成功核查为 16:47 SGT；本地结果已同步至 16:55 SGT。

弱扩展继续作为必跑项；4/8 GPU 已从实验计划中移除。

主运行 ID：`20261102T092147Z`。仅当结果已同步、`complete.txt` 对应原作业或登记的替代作业、且独立校验通过时，才计为完成。严格清单及结论见 [`updated_experimental_conclusions_20261105.md`](updated_experimental_conclusions_20261105.md)；每个 PBS 作业的申请资源和实际用时见 [`updated_vanda_runtime_budget_20261105.md`](updated_vanda_runtime_budget_20261105.md)。

| 部分 | 严格完成/已提交 | 当前情况 |
|---|---:|---|
| 固定图 Serial | 45/45 | 完成 |
| 固定图 GPU p=1/2 | 45/45 | 完成；4/8 GPU 不在目标内 |
| 固定图 CPU MPI 强扩展 | 151/180 | 本轮新增 4 张 hub 网格图的 8 节点点，均通过校验 |
| 固定图 CPU 512 核 | 0/45 | 首个作业传输层失败；其余暂挂 |
| CPU 原定义弱扩展 | 常规 1/1；512 核 1/3 | uniform 已验证；hub 排队，controlled 暂挂 |
| Kokkos OpenMP 多线程网格 | 63/139；512 核 0/4 | 45 图的 1/2/4 节点批次已提交免费队列；已有 63 批完成校验；8 节点只有原有 4 图完成 |
| CPU 按核配平 T=4 弱扩展 | 常规 1/1；512 核 0/1 | uniform 常规端点完成 |
| **全部已提交批次** | **316/473** | 固定图逐格审计 **14,106/19,980**；其中 63 个 Kokkos CPU 网格批次已完成 |

16:47 查询 `hpc project` 时，CPU Net Balance 为 **2127.249 核小时**，GPU Net Balance 为 **978.587 GPU 小时**。弱扩展按 rank 的 hub/controlled p=512 作业 `1510691/1510692` 和按核配平 uniform C=512 作业 `1513566` 均在 Q，PBS 等待原因为 `Insufficient amount of resource: ncpus`。16:55 将 Vanda 的 Kokkos CPU 网格输出及最新 `submitted_jobs.tsv` 同步到本机，进度由本地旧快照 35/139 更新到 **63/139**；同一批次核查由 288/473 更新到 **316/473**。固定图审计现为 **14,106/19,980**。弱扩展结果可复用范围及其待跑项见上表；19,980 不含弱扩展。

本轮 `grid_hub_n50000_d8`、`grid_hub_n50000_d16`、`grid_hub_n100000_d4/d8` 的 8 节点作业 `1513419/1513424/1513429/1513434` 均以 PBS `Exit_status=0` 结束，各 7 份独立校验报告全部通过。前三项约 7 分钟，第四项 16 分 42 秒；四项实际用时和额度估计见预算说明。已提交的 Kokkos OpenMP 1/2/4 节点批次共覆盖 45 张固定图，其中本轮新提交 123 批，已有 19 批通过校验。其余 41 张图的 Kokkos 8 节点批次尚未提交，当前免费队列的核心上限不能覆盖该布局。

已知历史问题：`synthetic_uniform` 512 核固定图作业 `1510577` 因 MPI TCP 地址绑定失败退出，详见[日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-512.o1510577)。uniform 512 核弱扩展作业 `1510690` 写出了六组完整计时后在独立校验阶段达到一小时墙钟上限，后由免费队列作业 `1521114` 补齐校验，未重跑计时。`strong_uniform` 的 1/2 节点超时续跑最终由 `1520951/1520952` 完成；先前超时的[节点 1 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515650)及[节点 2 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515651)已保留。

复核：

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
qstat -u hongxinran
hpc project
```
