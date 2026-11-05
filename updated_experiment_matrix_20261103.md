# Project 3 实验矩阵澄清（2026-11-03）

**2026-11-04 范围调整：**课程作业要求探索并行方法、扩展性与效率，未指定 4/8 GPU；Vanda 每作业最多 2 GPU/2 节点。因此当前必做 GPU 矩阵为同一环境的 p=1/2，4/8 GPU 保留为可选扩展，不计入默认覆盖目标。p=1/2 可计算强扩展效率，但只有两个资源点，报告须明确其外推限制。

## 强扩展、弱扩展和资源数量

强扩展与弱扩展由**问题规模如何随资源变化**定义，不由“是否达到 256/512 核”定义。固定一张图 G45 中的图，增加 CPU 核、MPI rank 或 GPU 数，是强扩展；同一合成家族保持每 rank 50,000 顶点、800,000 边，随 rank 数 p 增加生成 N=50,000p、M=800,000p 的图，是弱扩展。两者都需要 p=1 基线和多个资源点。强扩展显示固定任务的加速与通信瓶颈；弱扩展显示资源增加后能否处理同比增大的任务。

CPU 的 512 是额外的 **512 CPU 核**端点：8 节点×每节点 64 核。纯 MPI 用 512 rank×1 线程；MPI+OpenMP 已设计 512 rank×1 线程与 128 rank×4 线程；MPI+Kokkos OpenMP 也应补齐这两个相同布局。两种拆分的总 CPU 核数相同，专门检验 rank/线程分配的影响。它不是 GPU 的 512 卡目标；CPU 核和 GPU 卡不是可互换的资源单位。

## 有定义的方法 × 计算后端

以下是方法与后端的**有效组合**，不是五种方法机械乘以 CPU/GPU 两列。CPU 方法在 GPU 节点运行仍然只用 CPU，作为同节点对照。

| 方法 | CPU 计算 | GPU 计算 | MPI 通信模式 |
|---|---|---|---|
| Serial 基准 | C++ Serial | 无；单 GPU 由 CUDA/Kokkos CUDA 消融代表 | 不适用 |
| 纯 MPI 基准 | C++ MPI | 无；可在 GPU 节点作为 CPU 对照 | Allgatherv、Halo |
| 单独 OpenMP 消融 | OpenMP | 无 | 不适用 |
| 单独 CUDA 消融 | 无 | 原生 CUDA | 不适用 |
| 单独 Kokkos 消融 | Kokkos OpenMP | Kokkos CUDA | 不适用 |
| MPI+OpenMP | MPI+OpenMP | 无；可在 GPU 节点作为 CPU 对照 | Allgatherv、Halo |
| MPI+CUDA | 无 | MPI+原生 CUDA | Allgatherv、Halo |
| MPI+Kokkos | MPI+Kokkos OpenMP | MPI+Kokkos CUDA | Allgatherv、Halo |

Kokkos 是可选择执行后端的 C++ 并行框架，既能在 CPU 以 OpenMP 后端运行，也能在 GPU 以 CUDA 后端运行；两者分别构建和测量。OpenMP 在本项目中是 CPU 线程方法，CUDA 是 NVIDIA GPU 方法。每个 MPI 方法都对相同图、rank 数、线程数与节点布局分别运行 Allgatherv/Halo。Serial 和单独后端没有跨 rank 交换，不能附加这两个通信模式。

Allgatherv 和 Halo 是两种**通信策略**，不是通信“程度”的连续参数。Allgatherv 收集全部 rank 的贡献；Halo 只交换本 rank 更新所需的远端贡献。p=1 时没有真正的跨 rank 交换，两种模式仍可校验实现，但通信量/效率结论主要看 p≥2。纯 MPI 在 GPU 节点运行时仍只使用 CPU；GPU 计算的单卡基准是单独 CUDA 或 Kokkos CUDA，而非纯 MPI。

## 图 × 方法 × 通信 × 资源布局

### 固定图：45 张图上的完整有效组合

G45 = 原仓库的 Google、uniform、hub 3 图 + 三个家族各一张典型合成图 + 三个家族各 4 种顶点数×3 种平均出度的 36 张网格图 + 三张 12.8m 顶点的大图。固定图用于 Serial/单独后端消融和**强扩展**，每个有效方法与布局都应覆盖同一 G45。

固定图的目标是一个**受方法约束的笛卡尔积**：`G45 × 后端环境 × 有效实现 × 该实现可用的资源布局 ×（MPI 实现才有的 2 种通信策略）× 5 次计时`。Serial 是每图一个 CPU 基准，不会因 MPI 的 p、T、通信模式重复定义；单独 OpenMP/Kokkos CPU 按线程数展开，单独 CUDA/Kokkos CUDA 按单 GPU 展开。纯 MPI、MPI+OpenMP、MPI+CUDA、MPI+Kokkos 才按各自有效布局分别配对 Allgatherv/Halo。这是实验设计目标，不能把已提交作业等同于已完成结果。

对 CPU 布局，记 `n=节点数`、`r=每节点 MPI rank 数`、`T=每 rank CPU 线程数`。总进程数 `p=n×r`，**实际使用的 CPU 核数** `C=p×T=n×r×T`。因此 C 由 n/r/T 导出，不作为可任意独立取值的第四轴；额外申请但闲置的核不算计算规模。每次记录 PBS 申请的 `ncpus/node` 与实际 C，两者不得混称。

| CPU 实现 | 固定图 G45 的常规布局（每节点最多实际使用 32 核） | 8 节点 × 64 核的补充端点 |
|---|---|---|
| Serial | `n=1,p=1,T=1,C=1` | 不重复 |
| 单独 OpenMP / Kokkos OpenMP | `n=1,p=1,T=1/2/4/8/16/32` | 不重复 |
| 纯 MPI | `n=1/2/4/8; r=1/2/4/8/16/32; T=1`，共 24 个布局 | `n=8,r=64,p=512,T=1,C=512` |
| MPI+OpenMP | 同样的 n/r，各配 `T=1/2/4/8/16/32`，只取 `r×T≤32`，共 84 个布局 | `p=512,T=1` 与 `p=128,T=4`，两者 C=512 |
| MPI+Kokkos OpenMP | **目标**与 MPI+OpenMP 使用相同 84 个布局，便于同配置比较 | **目标**与 MPI+OpenMP 使用相同两种 512 核布局 |

上述 84 个布局是每种 CPU 混合实现的完整有效组合：每个 n 上有 21 组 `(r,T)`。每一组都在 G45 上配对 Allgatherv/Halo。原 Vanda CPU 作业只让 MPI+Kokkos OpenMP 取 `T=1`（24 个常规布局与一个 512 核端点）。现已另加独立的 Kokkos CPU T>1 作业脚本、结果路径和校验器，不改变排队中的原作业；它们尚未在 Vanda 完整运行，不能当作现成结果。

用相同总核数的不同布局单列对比：128 核可取 `(n,r,T)=(4,32,1)`、`(4,8,4)` 或 `(8,16,1)`，分别检验 rank/线程拆分和节点数变化；256 核可取 `(8,32,1)` 或 `(8,8,4)`。512 核的两个端点为 `(8,64,1)`、`(8,16,4)`。比较“纯 MPI 对混合方法”时分别报告同 p/n 与同 C/n 两种配对，因为同 p 的 T=4 混合方法用了四倍 CPU 核。

| 后端环境 | 强扩展资源布局 | G45 中每图运行的方法 |
|---|---|---|
| Vanda CPU | 上表中的 n/r/T 布局；常规最高 256 个实际 CPU 核，另有两个 512 核 rank/线程拆分 | Serial、单独 OpenMP/Kokkos OpenMP、纯 MPI、MPI+OpenMP、MPI+Kokkos OpenMP；MPI+Kokkos 多线程网格仍待补齐 |
| Vanda GPU 已运行 | 1/2 A40 GPU 节点，每节点 1 MPI rank、1 GPU | 同节点 Serial/纯 MPI/MPI+OpenMP CPU 对照；单独 CUDA/Kokkos CUDA；MPI+CUDA/MPI+Kokkos CUDA。GPU 节点 MPI+OpenMP 对照 T=1/2/4/8 |
| Vanda GPU 可选扩展 | 同一 A40 环境的 4/8 节点，每节点 1 rank、1 GPU | 同一 G45 的纯 MPI、MPI+OpenMP CPU 对照、MPI+CUDA、MPI+Kokkos CUDA；每个 MPI 方法逐格配对 Allgatherv/Halo。当前 Vanda GPU 队列每作业最多 2 GPU、2 节点，须先由 NUS HPC 放宽额度；不计入当前必做目标 |

同一 Vanda A40 环境中已完成的 p=1/2 可以作为后续 p=4/8 的曲线起点；新端点仍须记录具体节点型号、构建和重复口径。GPU 的资源单位是 GPU 卡数，不与 512 CPU 核直接画成同一条效率曲线。

GPU 布局记 `g=每节点 GPU 数`。当前设计固定 `g=1`、每 GPU 一个 MPI rank，所以 Vanda 的 `(n,p,GPU总数)` 必做目标为 `(1,1,1)/(2,2,2)`；`(4,4,4)/(8,8,8)` 仅是可选扩展，受队列上限阻挡，不能称为已完成。CPU 对照在同一 GPU 节点上使用相同 n/p，MPI+OpenMP 另取 T=1/2/4/8；GPU 实现的 CUDA/Kokkos kernel 不存在同含义的 OpenMP T。每节点 PBS 所申请的主机 CPU 核数固定并记录，不把它当作 GPU 并行度。不把一 GPU 共享给多个 rank 的争用运行混进这条曲线。

CPU 的 512 核端点与 GPU 1/2 卡比较回答相同类型的扩展性问题，但对应不同硬件规模；“GPU 也跑 512”意味着 512 张 GPU，绝不等于每卡开 512 个 CUDA 线程。当前 GPU p>2 仅为可选计划，不是已验证结果。Vanda 4/8 GPU 的队列限制与申请文字见 `updated_vanda_gpu_queue_limits_20261103.md`。

### 弱扩展：三个可复现合成家族

当前 CPU **按 rank 定义**的弱扩展：纯 MPI、MPI+Kokkos OpenMP T=1 在 p=1/2/4/8/16/32/64/128/256/512 跑三个家族；MPI+OpenMP T=4 目前在 p=1/2/4/8/16/32/64/128 跑三个家族。图规模为 `N=50,000p; M=800,000p`。固定 T 的每条曲线都有相同每 rank 工作量；T=1 与 T=4 的**每核**工作量不同，不能称为同一条按核数配平的弱扩展比较。已新增**按核定义**的补充脚本：复用现有 `weak_pC` 合成图，令 `N=50,000C; M=800,000C`，`C=p×4`；MPI+OpenMP 与 MPI+Kokkos OpenMP 同取 T=4、C=4/8/16/32/64/128/256/512，两种 MPI 通信模式逐格配对。C≤256 用每节点 32 核，C=512 用 8 节点×64 核。该路径已在本机小图校验，并在 Vanda 提交首个家族。GPU MPI 弱扩展在 Vanda p=1/2 跑三个家族；p=4/8 仅为受队列上限阻挡的可选扩展。所有必做 MPI 弱扩展点都有 Allgatherv/Halo 配对。

原始 Google 图不能一边保持“同一张原图”，一边让其规模随 p 增长；若复制或抽样成图，那是新数据集，必须另列而不能称为原图的弱扩展。单独后端在弱扩展图上的规模消融与 MPI 弱扩展是不同分析。当前脚本尚未让单独 Kokkos OpenMP 覆盖全部弱扩展图，这与“所有有效组合都跑”的个人目标仍有缺口。

## 统一测量与当前缺口

所有配置使用 Release、1 次预热、5 次计时和中位数，保存求解时间、迭代数、进程/线程/节点布局、通信时间与字节、Halo 预处理、GPU 传输/计算时间，以及正确性校验。强扩展应同时区分 **相对 Serial 的速度比**与**同方法 p=1 基线的强扩展加速/效率**；现有验证 CSV 的 `speedup` 是前者，最终图表还需计算后者。弱扩展报告总时间、每轮时间、迭代数及相对同方法 p=1 的效率。

Vanda p=1/2 GPU 的 G45 已全部校验；CPU 后续状态见最新运行快照。默认逐格核查目标共有 18,315 个 CPU、1,665 个 GPU 节点单元，总计 19,980。这个数只覆盖 45 张固定图上的配置，**不包含弱扩展、五次计时重复或 PBS 作业数量**；每图 444 个单元的明细和逐作业墙钟时间见 [`updated_vanda_runtime_budget_20261105.md`](updated_vanda_runtime_budget_20261105.md)。仅在选择可选 4/8 GPU 扩展时使用 `scripts/audit_fixed_matrix.py --include-vanda-gpu-extension`，额外加入 1,260 个单元，总计 21,240。最终 PDF 报告仍需根据实际完成的 Vanda 结果制作，包括 Google 真实图结论与 AI 使用说明。
