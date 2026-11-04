# 已校验结果快照（2026-11-04 整理）

**Vanda 数据截点：2026-11-03 23:35 SGT。** 主运行 ID 为 `20261102T092147Z`。11 月 4 日整理时无法连接 Vanda，故本快照没有推断或补造新的完成结果。原仓库旧结果仍在原目录；以下新结果使用 Release 构建、1 次预热、5 次计时，性能统计取 5 次中位数。45 张固定图、3 个弱扩展图家族及两种 MPI 通信方式的定义见 [`updated_experiment_matrix_20261103.md`](updated_experiment_matrix_20261103.md)。

## 覆盖与校验

| Vanda 实验 | 已校验批次 | 状态 |
|---|---:|---|
| Serial/OpenMP/单独 Kokkos OpenMP，45 张固定图 | 45/45 | 完成 |
| 单独 CUDA/Kokkos CUDA 与 GPU 节点 MPI 配对，45 张固定图，p=1/2 | 45/45 | 完成 |
| 纯 MPI、MPI+OpenMP、MPI+Kokkos OpenMP T=1 固定图强扩展 | 133/180 | 1/2/4/8 节点仍有缺口 |
| CPU 原定义弱扩展 p=1…256 | 1/1 | 完成；512 核端点未完成 |
| GPU 弱扩展 p=1/2 | 1/1 | 完成；p=4/8 未运行 |
| MPI+Kokkos OpenMP T>1 固定图试跑 | 10/13 | 已提交的四张图只有部分布局完成；其余图尚未提交 |
| CPU 512 核 | 0 | 不能列为实测；GPU 4/8 是可选扩展，不计入默认目标 |

[`audit_fixed_matrix.py`](scripts/audit_fixed_matrix.py) 在本快照报告 **11,328/19,980** 个预期固定图配置已具备 `summary.json` 和对应批次完成标记。主运行目录（排除不同 CPU 型号的 `free_cpu_archive`）有 **2,184 份** `validation.json`，全部 `failed=0`；另存的 Vanda 独立烟雾验证有 11 份报告，全部通过。本地 Mac 两组结果也分别保留在 `results/updated_local_macos/`，只作为本机观察，不混入 Vanda 性能曲线。完成标记、构建与节点环境、MPI 进程布局、单次计时、收敛历史、汇总和校验报告均在 [`results/updated_vanda_scaling/20261102T092147Z/`](results/updated_vanda_scaling/20261102T092147Z/) 下。逐顶点 rank 文件和个人账户交易导出体积大或与论文性能分析无关，未纳入 Git 快照；独立校验已在 Vanda 原始运行中完成。

## 当前可支持的阶段性结论

以下均是 45 张固定图的**逐图比值中位数**，不是先平均时间再相除；硬件、图与配置须按表述配对。

| 比较 | 观察 |
|---|---:|
| 同一 Vanda GPU 节点上的单独 CUDA / Serial | 中位加速 **15.225×**；45/45 张图更快 |
| 同一 Vanda GPU 节点上的单独 Kokkos CUDA / Serial | 中位加速 **7.181×**；45/45 张图更快 |
| 同一固定图 MPI+CUDA，Allgatherv，p=1→2 | 中位强扩展效率 **0.326** |
| 同一固定图 MPI+Kokkos CUDA，Allgatherv，p=1→2 | 中位强扩展效率 **0.430** |
| 同一固定图 MPI+CUDA，p=2，Allgatherv 时间 / Halo 时间 | 中位 **0.935**；Halo 在 11/45 张图较快 |
| 同一固定图 p=2，Halo 每迭代通信字节 / Allgatherv | 中位 **0.962** |
| 45 张图 CPU OpenMP T=32 / Serial | 中位加速 **12.199×**；Google 图单独只有 **1.005×** |

Halo 在 p=2 减少的通信数据通常不多，额外的建立/交换开销可能抵消收益；上述结果不能外推为所有进程数下 Halo 都较慢。CPU 8 节点和 512 核大部分尚未完成，不能据此下完整强扩展结论。Vanda GPU 队列仍限制单作业 2 GPU/2 节点，故没有真实 p=4/8 GPU 端点；课程文本未要求 4/8 GPU，这部分现为可选扩展。最新队列状态见 [`updated_vanda_run_status_20261104.md`](updated_vanda_run_status_20261104.md)，旧预算对账见 [`updated_vanda_budget_issue_20261103.md`](updated_vanda_budget_issue_20261103.md)。

复核命令：

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
```
