# Vanda 实验运行状态（2026-11-05 02:36 SGT）

主运行 ID：`20261102T092147Z`。只把完整 `complete.txt` 标记和独立校验通过的批次计为完成；PBS 运行或已退出不等于实验完成。

严格完成清单、全部缺口和阶段性性能结论见 [`updated_experimental_conclusions_20261105.md`](updated_experimental_conclusions_20261105.md)。

本地同步后，固定图逐格审计为 **12,300/19,980** 个配置；这不包含仍在 scratch 的 1/2 节点部分结果。

| 部分 | 已校验/已提交批次 | 状态 |
|---|---:|---|
| 固定图 Serial | 45/45 | 完成 |
| 固定图 GPU p=1/2 | 45/45 | 完成；4/8 GPU 是可选扩展 |
| 固定图 CPU MPI 强扩展 | 145/180 | 1/2 节点大图续跑中；其余 8 节点还有缺口 |
| 固定图 CPU 512 核 | 0/45 | 首个启动失败；其余暂挂待运输层排查 |
| CPU 原定义弱扩展 | 1/1；512 核 0/3 | uniform 六组输出已计算，但独立校验未结束；校验续作业已提交 |
| Kokkos OpenMP 多线程网格 | 16/16；512 核 0/4 | 已提交常规节点批次全部完成；剩余图还未提交 |
| CPU 按核配平 T=4 弱扩展 | 1/1；512 核 0/1 | uniform 家族常规端点完成 |
| **合计** | **262/350** | 较 11 月 4 日 22:31 增加 4 个校验批次 |

02:36 PBS 为 **2 个 R、2 个 Q、84 个 H**。正在运行的是 `1520951/1520952`（`strong_uniform` 的 1/2 节点续跑）；新增的免费队列独立校验作业 `1521114` 排队中。CPU Net Balance **270.378 核小时**，GPU Net Balance **978.587 GPU 小时**；这是正在运行作业预扣之后的余额，不等于最终消耗。现有排队的 **51 个 512 核 CPU 作业已由用户暂挂**，另 33 个 CPU 作业此前被 `am_hook` 暂挂。没有释放这些作业。

`strong_uniform` 的 1/2 节点 4 小时重跑 `1515650/1515651` 均因墙钟上限退出，PBS `Exit_status=-29`（[节点 1 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515650)、[节点 2 日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-retry.o1515651)）。日志显示已完成 24 组 MPI/Kokkos 测量并开始验证或混合配置；scratch 中每节点有 25 个完整 `summary.json`、对应的 `ranks.csv` 和五次计时文件。新增续跑脚本只复用具备完整文件的测量与已通过的校验报告，其余布局照常运行并最终重新校验。两个 8 小时续跑 `1520951/1520952` 已启动；不会把部分结果当作完整批次。

首个 `synthetic_uniform` 512 核作业 `1510577` 以 PBS `Exit_status=16` 结束，[日志](results/updated_vanda_scaling/20261102T092147Z/dsa5208-mpi-512.o1510577)最早的实际错误是 MPI TCP 在节点 `GN-A40-066` 绑定本地地址时返回 `Address already in use`；后续大量连接重置是进程退出后的连锁错误。第二个 512 核弱扩展作业 `1510690` 在 02:30 达到一小时墙钟上限，PBS `Exit_status=-29`。它的 uniform 六组输出均有 `summary.json`、`ranks.csv` 和五次计时；纯 MPI 两种通信策略的独立校验通过，Kokkos Halo 的校验中途被终止。免费队列续作业 `1521114` 只补校验并同步已有输出，不重跑计时；进入队列后提示 `Insufficient amount of resource: node_pool`，尚未开始。51 个后续 512 核作业继续暂挂，以免在确认原因前连续重复失败。

续跑代码已通过 Bash 语法检查与完整/不完整五次计时文件的复用烟雾检查；Vanda 真实结果以续跑作业结束后的独立校验为准。01:52 核对 scratch：两个旧 MPI `summary.json` 的修改时间仍是 11 月 4 日 20:15–20:17，说明续跑没有覆盖它们；节点 2 的结果目录已从 25 增至 27 个 `summary.json`，开始补算缺失的混合配置。此时 512 核作业已运行 22 分钟，仍未结束。

复核命令：

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
qstat -u hongxinran
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
```
