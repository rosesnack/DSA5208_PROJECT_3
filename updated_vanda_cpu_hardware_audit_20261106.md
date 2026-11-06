# Vanda CPU 队列与硬件一致性审计（2026-11-06）

## 结论先说

付费/免费队列不只是收费不同，它们默认调度到不同的 PBS 节点池。免费并行池里确实有一台 Platinum 8452Y 节点 CN-161，但没有证据能让免费并行队列把多节点作业全部放在 Platinum 上；本次 32 核主机限定探针因 `node_pool` 资源不足而排队，随后取消。不能据此把免费队列当作完成整条 Platinum 扩展曲线的途径。

**仓库清理记录：**清理前的 114 个免费 Kokkos CPU 网格性能批次、uniform 弱扩展 `p=512` 错误布局结果和 6 个本地忽略的旧免费 CPU 归档目录均已从当前工作树删除。逐项 PBS job ID 和排除原因见[`excluded_invalid_performance_results_20261106.tsv`](results/updated_vanda_scaling/20261102T092147Z/excluded_invalid_performance_results_20261106.tsv)。下文 114 批的硬件分布与时间只作为审计和重跑预算依据，不再是仓库内可引用的性能测量。

若报告要求 CPU Kokkos/OpenMP 扩展曲线在同型号节点上比较，已有的 **114 个免费队列 Kokkos CPU 网格批次都要重跑**到付费 `batch_cpu` 节点池；已在 `batch_cpu` 完成的 16 项可保留。Uniform 弱扩展 p=512 的 `1521114` 也必须重跑，因为它实际只有 1 节点、32 核。Controlled p=512 的计时则来自有效的付费 8 节点、512 核作业 `1510692`；`1526615` 只做了验证，不重跑计时，且校验全部通过。

## 队列和节点池

2026-11-06 在 Vanda 登录节点查询 `qstat -Qf` 与 `pbsnodes -av`：

| 队列 | 节点池 | CPU 上限 | 收费率 |
|---|---|---:|---:|
| `cpu_serial` | `cpu_free` | 1 CPU | 0 |
| `cpu_parallel` | `cpu_free` | 160 CPU、最多 10 节点 | 0 |
| `batch_cpu` | `cpu_node` | 720 CPU、最多 10 节点 | 1 |

`cpu_free` 的可见物理主机包括 `IN-001`–`IN-020` 与 `CN-161`。实验环境记录显示 `IN-018`、`IN-020` 为 Gold 6438N，`CN-161` 为 Platinum 8452Y。付费 `batch_cpu` 的已记录 Serial、MPI 和 Kokkos CPU 作业均报告 Platinum 8452Y。

本次主机限定校验：作业 `1527045` 的 `select=1:ncpus=1:host=cn-161` 经 `auto_free` 被送入 `cpu_serial`，成功落在 `CN-161`，`lscpu` 确认为 Platinum 8452Y。由于 `cpu_serial` 每作业最多 1 CPU，这不能运行本项目的 32 核单节点配置。作业 `1527046` 的 `select=1:ncpus=32:host=cn-161` 被送入 `cpu_parallel`，PBS 报 `Insufficient amount of resource: node_pool`，已取消。也就是说，目前未验证出可用的免费 32 核 Platinum 主机绑定方式。

## 免费 Kokkos CPU 网格批次实际用了哪些节点

将 130 个 `complete.txt` 的作业 ID 与 PBS 历史、每批 `environment.txt` 中的 `PBS_NODEFILE` 对齐。114 个免费队列批次按节点数分布如下：

| 申请节点数 | 批次数 | 节点记录 | 同型号 Platinum？ |
|---:|---:|---|---|
| 1 | 38 | 全部只分配 `IN-*` 主机；采样到的 `IN-018/020` 是 Gold 6438N | 否 |
| 2 | 15 | 两台均为 `IN-*` | 否 |
| 2 | 23 | `CN-161` 加一台 `IN-*` | 否，混合型号 |
| 4 | 15 | 四台均为 `IN-*` | 否 |
| 4 | 23 | `CN-161` 加三台 `IN-*` | 否，混合型号 |
| **合计** | **114** | **68 个 IN-only，46 个 Platinum+IN 混合** | **0 个全 Platinum** |

这里的 46 个是**混合节点批次**，不是 46 个纯 Platinum 批次。原先把 PBS 作业 leader 上的一行 `lscpu` 当成整个多节点分配的 CPU 型号，是不准确的；节点文件里的完整主机列表才揭示了混合分配。

按 PBS 实际用时 × 分配 CPU 核数估算，这 114 个已完成免费批次合计约 **670.35 核小时**，分节点数为：1 节点 95.43、2 节点 202.54、4 节点 372.37 核小时。各节点数每组 38 项；墙钟中位数分别约 3.57、4.04、3.47 分钟，P90 分别约 8.28、9.05、9.53 分钟。这个 670.35 是历史实际用量估算，不是付费重跑的预留额度；Platinum 上的运行时间、项目余额对账和其他排队作业都会影响能否全部重跑。

## 哪些结果应该重跑

| 结果 | 判定 | 处理 |
|---|---|---|
| `kokkos_cpu_grid` 中 114 个 `cpu_parallel` 已完成批次 | 主实验，但全 Gold 或 Gold+Platinum 混合；性能文件已删除 | 需在 `batch_cpu` 重跑，才能形成同型号 Platinum 曲线 |
| `kokkos_cpu_grid` 中 16 个 `batch_cpu` 已完成批次 | 付费节点池；记录的 CPU 型号为 Platinum | 保留 |
| 单独 OpenMP、单独 Kokkos OpenMP 的 270+270 个配置 | 保存于 paid `batch_cpu` 的 45 个 Serial 作业目录；CPU 记录为 Platinum | 保留，不因免费池差异重跑 |
| Kokkos `strong_*` 的 9 个 n=1/2/4 重试 `1526604–1526612` | 尚无完整结果；2 小时旧作业超时，6 小时免费重跑已取消 | 若保留完整大图矩阵，改到付费池并按大图实测设置时限 |
| MPI `strong_uniform` n=4、`strong_hub/controlled` n=1/2/4 的 7 批 `1526954–1526960` | 尚无完整结果；免费作业已取消 | 若保留这些矩阵点，改到付费池；不能用普通网格用时替代大图预算 |
| Uniform 弱扩展 p=512，作业 `1521114` | PBS 记录为 `cpu_parallel`、1 节点/32 CPU；不符合 p=512/8 节点；错误布局输出已删除 | 需要有效 512 核结论时以付费 8×64 重跑 |
| Controlled 弱扩展 p=512，作业 `1510692` | 原计时作业在 `batch_cpu` 申请 8×64=512 核，Platinum 8452Y；虽 walltime 超时，保存的两通信计时经 `1526615` 独立校验，3 项检查通过 | 可保留通过校验的已有计时；`1526615` 是 1 节点/32 核验证续跑，不是性能来源 |
| Hub 弱扩展 p=512，作业 `1526616` | 付费 8×64 重跑 | 等待运行和校验 |
| 其他已完成 CPU-only `batch_cpu` MPI/Serial 数据 | PBS 记录及环境为 Platinum CPU 节点 | 无需为硬件型号重跑；按配置自身校验状态纳入 |

## 当前费用限制与最近的 8 节点作业

最近一次 `hpc project` 显示 CPU 余额 **1,144.255 核小时**、GPU 余额 **978.587 GPU 小时**。`1527001` 已在付费 `batch_cpu` 完成，实际墙钟 **8:44**，PBS `Exit_status=0`，本地结果通过校验。`1527002` 也以 `Exit_status=0` 结束，墙钟 **34:41**；本地 67 项 validation checks 通过。但 PBS 给它分配 3 台 CN 与 5 台 GN-A40 主机，`environment.txt` 只报告 leader CN-003 的 CPU 型号为 Platinum。GN-A40 节点属于 PBS `cpu_node` 池，但其 CPU 型号未从逐节点环境中核实，所以原始结果留在工作树，暂不计同型号 CPU 矩阵。

付费弱扩展 hub p=512 作业 `1526616` 申请 8 节点×64 核、2 小时；22:39 SGT 仍为 `Q`，`Hold_Types=n`，PBS 原因 `Insufficient amount of resource: ncpus`。若启动会申请最多 1,024 核小时。当前余额不适合再释放大批 512 核暂挂作业；继续提交前先刷新账户额度和 `qstat`。

114 项 Kokkos 免费批次的历史实际总用量估计为 **670.35 核小时**（1 节点 95.43、2 节点 202.54、4 节点 372.37）。这小于 CPU 账面总余额，但不是可直接预留的费用：当前 paid jobs 的作业申请先扣了资源时限额度；而要给 114 项设置能覆盖历史 P90/最大值的 walltime，其预留总额会更高。全量重跑在等当前作业结算前不能保证可提交，应按余额分批。
