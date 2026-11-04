# Vanda 实验运行状态（2026-11-04 14:33 SGT）

## 22:31 SGT 最新进展

主运行已校验 **258/350** 批，较 20:09 的 254 批增加 4 批：固定图 CPU MPI 强扩展 **142/180**，Kokkos OpenMP 多线程网格 **15/16**。前次 MPI 网络端口冲突的同配置重试 `1519851` 以 PBS `Exit_status=0` 完成并通过校验；`synthetic_uniform` 的 Kokkos CPU 2/4 节点作业 `1519860/1519861` 也以 0 结束。原先 1/2 节点超时的 `strong_uniform` 重跑 `1515650/1515651` 仍在运行。PBS 当前 **2 个 R、58 个 Q、33 个 H**，CPU Net Balance **3342.378 核小时**，GPU Net Balance **978.587 GPU 小时**。8 节点 Kokkos 批次 `1519862` 和 512 核批次 `1519863` 仍在队列中；全部 512 核端点仍无有效测量。新增结果已同步，本地固定图逐格审计为 **12,072/19,980**。

## 20:09 SGT 最新进展

Vanda 已校验批次由 **243/346** 增为 **254/350**：固定图 CPU MPI 强扩展 **140/180**，Kokkos OpenMP 多线程网格 **13/16**，按核配平 T=4 弱扩展 **1/1**。分母增加 4 是后来提交的 `synthetic_uniform` Kokkos CPU 三个常规节点布局和一个 512 核端点，不是已完成批次失效。本地已同步新增校验结果；固定图逐格审计为 **11,880/19,980**。

上一批释放的 12 个作业中，11 个以 PBS `Exit_status=0` 完成并通过校验。`1513379`（`grid_uniform_n100000_d16`、8 节点）以 `Exit_status=16` 结束；[PBS 输出](results/updated_vanda_scaling/20261102T092147Z/pbs_failure_1513379.log)显示节点 `CN-108` 上 MPI TCP 端口绑定返回 `Address already in use`，随后 `MPI_Barrier` 失败。该次不计为有效测量。已用同图、同布局、同 Release/预热/重复口径重投 `1519851`；重试脚本会将失败尝试的部分 scratch 输出归档，重试原因在 `retry_jobs.tsv` 记为 `mpi_transport_bind`。

用户提供最新 CPU 余额 **4622.378 核小时**后，另释放了原先暂挂的 `strong_uniform` 重跑 `1515650/1515651` 和 4 个普通强扩展作业；提交 `synthetic_uniform` 的 4 个 Kokkos CPU 待补批次 `1519860`–`1519863`。20:09 PBS 显示 **4 个 R、60 个 Q、33 个 H**，CPU Net Balance **3854.378 核小时**，GPU 余额 **978.587 GPU 小时**。`1519851`、`1515650/1515651` 正在运行；新提交的 Kokkos 图已有一个作业运行。512 核端点仍没有完成标记。当前不继续批量释放，先等待已运行任务校验与额度对账。

## 14:42 SGT 后续进展

用户重新执行 `amgr login` 后，`hpc project` 已可查询：项目 `personal-hongxinran` 的 CPU Net Balance 为 **6218.183 核小时**，GPU Net Balance 为 **978.587 GPU 小时**。分两批调用 `scripts/release_vanda_existing_cpu.py`，共释放 **12 个现有暂挂的 CPU 作业**：强扩展 8 个、Kokkos OpenMP 网格 3 个、按核配平弱扩展 1 个。首批作业 `1513357` 已于 14:41 开始运行，其余已释放作业进入队列。运行后的 CPU 余额为 **5962.183**，减少 256 核小时，与一个 8 节点×32 核、1 小时作业的预扣一致。

14:42 再查 PBS：**63 个 Q、1 个 R、40 个 H**；已校验批次仍为 **243/346**，因为刚启动作业尚未完成。当前先让这 12 个已释放作业运行和对账，再视余额及队列进展分批释放其余暂挂任务。512 核端点仍未有校验完成结果。下方为 14:33 的初始快照。

已通过 Vanda 内网地址 `172.20.101.10` 重新连接并读取 PBS 队列与主运行 `20261102T092147Z` 的完成标记。此次登录时 `vanda.nus.edu.sg` 在本机无法解析；内网地址可连接。以下只计通过校验的批次，不能把排队作业当作运行结果。

| 实验 | 已校验批次 |
|---|---:|
| 固定图 Serial | 45/45 |
| 固定图 GPU p=1/2 | 45/45 |
| 固定图 CPU MPI 强扩展 | 133/180 |
| 固定图 CPU MPI 512 核端点 | 0/45 |
| CPU 原定义弱扩展 | 1/1；512 核补充 0/3 |
| GPU 弱扩展 p=1/2 | 1/1 |
| Kokkos OpenMP 多线程试跑 | 10/13；512 核补充 0/3 |
| CPU 按核配平 T=4 弱扩展 | 0/1；512 核补充 0/1 |

`check_vanda_progress.py` 报告 **243/346** 个批次完成，与 11 月 3 日快照相同。`qstat -u hongxinran` 有 **52 个 Q、52 个 H、0 个 R**。暂挂作业 `1513357` 的 PBS 注释是 `Job held by 'am_hook' hook on Tue Nov 3 20:48:08 2026`；排队的 512 核作业 `1510577` 注释是 `Not Running: Insufficient amount of resource: ncpus`。另有一个 GPU 免费队列作业 `1511417` 排队，PBS 注释为 `Insufficient amount of resource: node_pool`。这些状态不证明任务失败，也不提供预计启动时间。

本次远程 `hpc project` 提示先运行 `amgr login`，因此无法核实当前 CPU/GPU 余额，也不能据 11 月 3 日的余额推断是否能解除预算暂挂。不要在余额未核实前批量重新提交或释放全部 CPU 作业。

课程作业文本没有规定 4/8 GPU。Vanda 每作业最多 2 GPU/2 节点；现有 45 张固定图及弱扩展三个家族的 p=1/2 GPU 批次已经完成。4/8 GPU 改为可选扩展，不计入默认固定图覆盖目标；其脚本与队列证据保留。p=1/2 的 GPU 强扩展只有两个资源点，结论仅限于这两个点。

复核命令：

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
qstat -u hongxinran
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
```
