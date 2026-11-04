# 45 图实验代码与流水线审计（2026-11-03）

**2026-11-04 范围更新：**本文件保留 11 月 3 日按 4/8 GPU 扩展目标统计的历史审计。课程文本未要求 4/8 GPU，现改为可选；当前默认目标为 19,980 个固定图单元。实时批次和队列状态见 `updated_vanda_run_status_20261104.md`。

## 审计范围与结果

按 `updated_experiment_matrix_20261103.md` 核对 45 张固定图的 Serial、单独后端、纯 MPI、MPI+OpenMP、MPI+Kokkos OpenMP、MPI+CUDA、MPI+Kokkos CUDA，以及两种 MPI 通信策略、节点/rank/线程布局、Release 构建、正确性校验与结果汇总。45 张固定图 = 原仓库 3 + 典型合成 3 + 顶点/边密度网格 36 + 大图 3；弱扩展图另列。

**结论：固定图矩阵的代码入口与覆盖核查器已基本接齐；CPU 实际数据远未跑齐。** 11 月 3 日从 Vanda 同步的 `20261102T092147Z` 快照有 **2,046/19,980** 个当时目标内的固定图配置单元带完成标记；GPU p=1/2 固定图 **45/45** 批完成。用户随后要求 4/8 GPU 也只在 Vanda 运行，完整目标现为 **21,240** 个单元，其中新增 1,260 个 4/8 GPU MPI 单元受 Vanda 每作业最多 2 GPU/2 节点的队列限制。该数是同步时点，不代表后续实时 CPU 进度。

| 部分 | 代码与流水线 | 运行与验证现状 |
|---|---|---|
| 45 图清单与可复现生成 | `generate_scaling_graphs.py`；`list_fixed_graphs.py` 输出 45 个名字 | 本地检查数量为 45；Vanda 图是否全部保持可用需随作业复核 |
| Serial、单独 OpenMP/Kokkos OpenMP | Vanda Serial grid 作业和独立残差校验 | 本地快照中 Serial 9/45、两种单独 CPU 方法各 54/270 单元完成 |
| 纯 MPI 与 MPI+OpenMP CPU | 常规 24/84 布局；额外 512 核；每格 Allgatherv/Halo | 当前快照只有少量强扩展图完成；不能称为全 45 图结果 |
| MPI+Kokkos OpenMP CPU | 原脚本覆盖 24 个 T=1 布局；新增其余 60 个 T>1 布局脚本，合计 84 个；另补 p=128,T=4 的 512 核作业 | 本机 Release 重编译及 p=2,T=2 的两种通信模式通过独立校验；Vanda 新网格未提交/运行 |
| 单独 CUDA/Kokkos CUDA、MPI+CUDA/Kokkos CUDA | Vanda p=1/2 代码、作业、两种通信模式及校验 | 最新同步快照 45/45 个 GPU 图批次、1,665/1,665 个 GPU 单元完成；新版共享驱动的隔离双节点验证作业仍在 GPU 队列 |
| Vanda p=4/8 GPU 扩展 | 已新增每节点一 GPU/rank 的计算、独立 CPU 校验、结果汇总与覆盖核查入口 | 当前 `batch_gpu`/`batch_gpux` 上限均为 2 GPU、2 节点；无 4/8 GPU 实测，需要 NUS HPC 开放更高额度 |
| 逐格覆盖与结果汇总 | `audit_fixed_matrix.py` 枚举每格；`plot_kokkos_cpu_grid.py` 和 `plot_scaling.py` 汇总同方法 p=1 强扩展效率 | 覆盖计数与 CSV 汇总已在本机快照运行；本机无 matplotlib，尚未生成最终图 |

## 修正过的实际缺口

1. 旧 MPI+Kokkos CPU 结果路径只有 `pN`，多线程会覆盖 T=1。现以 `pN_tT` 保存 T>1，记录请求线程数和 Kokkos 实际线程数；两者不一致时作业失败。T=1 路径与旧结果兼容。
2. 原 Vanda CPU 主作业保持原工作量。Kokkos 多线程扩展另用 `submit_vanda_kokkos_cpu_grid.sh` 按图提交四种节点布局和一个 512 核端点，避免改变已排队的旧作业。
3. GPU 运行循环可按 4/8 个 Vanda A40 节点启动；独立的 `vanda_gpu_extension_compute.pbs` 与 `vanda_gpu_extension_validate.pbs` 保存新增结果和校验，不覆盖已完成的 p=1/2 报告。队列上限未改变前不提交这些作业。
4. `check_vanda_progress.py` 识别新增 Kokkos 作业类型；`audit_fixed_matrix.py` 按配置单元核查，避免以“已提交 job 数”冒充完整实验。
5. 原 `scaling.csv` 的 `speedup` 是相对 Serial 的速度比；Kokkos 与 Vanda GPU 汇总另计算同一方法 p=1 基线的强扩展速度比和效率，口径分开。

## 仍未闭环

- **Vanda CPU 实跑：**项目 CPU 额度已返还；全部 45 图的纯 MPI/MPI+OpenMP 强扩展与 512 核端点已提交，Kokkos CPU 多线程网格已开始分批提交。完成数仍须以验证标记为准。
- **Vanda 4/8 GPU 实跑：**同一作业的 GPU/节点数都受上限 2 约束。已有代码入口，但真实测量必须等 NUS HPC 放宽队列或提供合法等效队列；不能用两张 GPU 的超额进程数替代。
- **弱扩展：**现有 CPU 图按每 rank 50k 顶点/800k 边放大，MPI+OpenMP T=4 的每核工作量低于 T=1。按每核配平的 MPI+OpenMP/Kokkos OpenMP T=4 代码路径已补，并在本机 p=1/2、两种通信模式的小图上通过 12 项校验；Vanda 首个家族已提交。Vanda GPU p=4/8 弱扩展及单独 Kokkos OpenMP 全弱图消融仍未补。45 张固定图不属于弱扩展图组。
- **最终作业：**必须根据实际完成的 Vanda/Atlas 时间生成图、完成 PDF、Google 真实图结论与 AI 使用说明。尚不能宣称整套实验完成。

## 本机验证证据

- Shell 新/改脚本通过 `bash -n`；Python 新/改脚本通过 `py_compile`；`git diff --check` 无格式错误。
- MPI+Kokkos OpenMP 使用本机 Release 构建重新编译成功，Kokkos 4.5.01。
- 四顶点五边小图上，`p=2,T=2` 的 Allgatherv 与 Halo 均通过独立残差、质量、最终 rank L1 与线程数检查；两种模式分别写入 `p2_t2` 路径。本机冒烟测试不作为性能结果。
- Vanda 上次同步快照的逐格核查为 2,046/19,980；GPU p=1/2 为 1,665/1,665 单元。加入 Vanda p=4/8 目标后，核查器可用 `--include-vanda-gpu-extension` 显示 2,046/21,240；新增 1,260 个 GPU 单元目前没有结果。Kokkos CPU 汇总 CSV 读出 48 个已有 T=1 单元。
- Vanda 独立 CPU 免费队列作业 `1511433.stdct-mgmt-02` 在计算节点完成，PBS `Exit_status=0`，26 项独立校验全部通过；原始输出保存在 `results/updated_vanda_validation_20261103/cpu/`。独立 GPU 作业 `1511417.stdct-mgmt-02` 尚在排队。
