# Project 3 更新实验矩阵（2026-10-31；Vanda 队列修订 2026-11-02）

这份文件写的是**已实现的实验设计与运行中的作业**。原仓库结果保留；只有实际完成、校验通过的新测量才写入 `results/updated_vanda_scaling/<run-id>/` 并用于新结论。本机 42 张固定图与 12 张弱扩展图的 CPU 矩阵已通过 2160 项校验。Vanda 的 CPU/CUDA/Kokkos CUDA Release 构建和双节点 GPU 正确性试跑均已通过；其余性能批次的实时状态见 `updated_vanda_run_status_20261102.md`。

## 为什么这样设计

算法是同步 pull PageRank。每轮先用上一轮 rank 和出度形成贡献值，再按入边求和，最后计算全局悬挂质量与 L1 收敛误差。跨 MPI rank 的源顶点贡献值必须传递，因此通信是实际瓶颈之一。

- **Allgatherv**：每轮收集所有顶点贡献值，通信量约为 `8N(p−1)` 字节（全体 rank 的总量）。
- **Halo**：预先找到本 rank 入边所需的不同远端源顶点，每轮只交换这些贡献值；另计预处理时间和索引字节。两种方式都必须进行悬挂质量和收敛误差的 `Allreduce`。
- 单独的 Serial、OpenMP、CUDA、Kokkos 没有 MPI 进程间交换，因此没有 Allgatherv/Halo 参数。

## 图与方法

固定图 **G45**：原仓库的 `google`、`uniform`、`hub` 三图原样保留；新生成三张同为 100k 顶点、1m 边的 `synthetic_uniform/hub/controlled`；三个家族各有 `N={50k,100k,200k,400k} × 平均出度={4,8,16}` 的 36 张格点图；三个家族各有一张 12.8m 顶点、204.8m 边的大图。种子固定为 5208。新 uniform 家族是每个源顶点固定出度、以种子化起点和互素步长排列目标；hub 家族让约 80% 的目标落在前 1% 顶点；controlled 家族再加入 80/20 源端出度倾斜。生成器不把这种 uniform 图称作独立随机边抽样。

弱扩展另有三个合成家族，在每个 `p={1,2,4,8,16,32,64,128,256,512}` 生成 `N=50,000p`、`M=800,000p` 的图。p=512 每张图为 25.6m 顶点、409.6m 边。原始 Google 图保持固定，只能用于强扩展；不把复制得到的图冒充原图弱扩展。

| 方法 | 固定图 G45 的消融或强扩展 | 弱扩展 | 通信 |
|---|---|---|---|
| Serial | 每图一次，1 CPU 核 | GPU 弱扩展批次给每图同环境参考 | 无 |
| OpenMP | 每图 T=1/2/4/8/16/32；GPU 节点再做同图消融 | GPU 弱扩展图也做单节点消融 | 无 |
| Native CUDA | 每图 1 A40 | GPU 弱扩展图的单 GPU 消融 | 无 |
| Kokkos OpenMP | 每图 T=1/2/4/8/16/32 | 不单列 | 无 |
| Kokkos CUDA | 每图 1 A40 | GPU 弱扩展图的单 GPU 消融 | 无 |
| 纯 MPI | CPU 原有 24 个布局，加 8 节点×64 rank 的 512 核点；Vanda GPU 节点另跑 p=n=1/2 | CPU p=1…512；Vanda GPU p=1/2 | 每个配置两种 |
| MPI+OpenMP | CPU 原有 84 个布局，加 512×1、128×4 两个 512 核点；Vanda GPU 节点 T=1/2/4/8、p=n=1/2 | CPU T=4、p=1…128；Vanda GPU T=1/2/4/8、p=1/2 | 每个配置两种 |
| MPI+CUDA | Vanda GPU 节点 p=n=1/2，每节点 1 rank/1 A40 | Vanda GPU p=1/2 | 每个配置两种 |
| MPI+Kokkos OpenMP | CPU 原有 24 个节点/rank 布局，加 512×1 | CPU p=1…512 | 每个配置两种 |
| MPI+Kokkos CUDA | Vanda GPU 节点 p=n=1/2，每节点 1 rank/1 A40 | Vanda GPU p=1/2 | 每个配置两种 |

CPU 原有 24 个布局是 `节点数={1,2,4,8} × 每节点 rank={1,2,4,8,16,32}`，最高 8×32=256 CPU 核。MPI+OpenMP 在这些布局上取 `T={1,2,4,8,16,32}` 中满足每节点 `rank×T≤32` 的配置，共 84 个。另加独立的 8 节点×64 核的 512 核端点：纯 MPI 和 MPI+Kokkos OpenMP 用 p=512，MPI+OpenMP 用 p=512/T=1 和 p=128/T=4。它与 p=256 的 8 节点×32 核配置同节点数、不同每节点核数，分析时明确区分。强扩展固定图 G45 不变；弱扩展只为 p=512 新增图。比较 Allgatherv/Halo 时，图、p、T、节点数、每节点 rank 数、编译设置、预热次数和重复次数完全一致。Vanda GPU 批次在**同一批两 GPU 节点**上配对纯 MPI、MPI+OpenMP T=1/2/4/8、MPI+CUDA、MPI+Kokkos CUDA。T=1 的 MPI+OpenMP 只作为匹配 CPU 核数的控制组；T≥2 才体现节点内 OpenMP 线程并行。CUDA/Kokkos 的 GPU 线程与 OpenMP 的 T 不是同一种资源，跨后端只固定图、MPI 进程数、节点布局和每节点 GPU 数，不声称“相同 T”。

Lecture 12 第 37 页的“scaling to at least 256 CPU cores”要求 **MPI 扩展曲线的最大规模达到或超过 256 核**，并同时展示较小规模的强、弱扩展点；不要求每次运行都至少用 256 核。纯 MPI 的强扩展和弱扩展都包含 `p=1,2,4,8,16,32,64,128,256,512`，512 是高于要求的额外端点。MPI+OpenMP 等 MPI+X 分析另有评分项。

每个 GPU 节点分配 1 GPU 和 1 MPI rank 是有效的多 GPU 分布式布局：p=1 是单 GPU 基线，p=2 时两个 rank 各用自己的 GPU 并通过 MPI 交换。Vanda 当前免费和项目 GPU 队列的每作业上限均为 2 GPU，因此 p=4/8 一 GPU 一 rank 的曲线不能在这些队列上跑；若要保留此额外扩展，需另用 Google Cloud 等具有足够 GPU 节点的环境，并单独报告环境差异。

## 强扩展与弱扩展

- **强扩展**：固定同一张图，例如 Google，先用 1 rank，再用 2、4、8… rank；问同一份工作是否做得更快。`S_p=T_1/T_p`，`E_p=S_p/p`。对 GPU 多节点曲线，`T_1` 是**同一个方法的一张 GPU**时间；CPU 对 Serial 的速度比另外列出。
- **弱扩展**：固定每 rank 50k 顶点、800k 边；p 从 1 到 2 时，整图从 50k/800k 变成 100k/1.6m。理想情况每轮耗时不变。由于 PageRank 的收敛迭代数也可能变化，同时报告总时间、迭代数、每轮时间和 `p=1 每轮时间 / p>1 每轮时间`。

所有方法沿用 Release、1 次预热、5 次计时、求解循环中位数。`solve_s` 包含迭代中的 MPI 等待和 GPU 主机传输；不含读图、CSR、Halo 计划和最终校验。另报通信时间、通信字节、Halo 设置时间和字节、GPU/后端计算时间、传输时间。正确性使用独立 Python 残差、rank 总质量、每轮收敛历史、原始边和度数、重复时间记录以及与同环境 Serial 的 rank L1 对照；弱扩展再直接比对 Allgatherv/Halo 的最终 rank。

CPU 构建统一使用 Vanda 的 GCC 13/Open MPI；CUDA 代码必须由 NVCC 编译，Kokkos CUDA 使用 `nvcc_wrapper`，它们仍使用同一 GCC 主机编译环境。跨后端不能声称“完全相同编译器”，因此记录各自的 CMake 构建类型、编译器、CUDA 版本和 Kokkos commit，并在同一 GPU 节点上测纯 MPI 与混合方法。MPI+GPU 当前使用主机内存暂存通信数据；Halo 节省的是 MPI 网络负载，GPU 到主机的传输另列。

## 作业与完成状态

`scripts/submit_vanda_bootstrap.sh` 在免费队列安排数据、CPU/GPU Release 构建与正确性试跑。试跑通过后，`submit_vanda_serial_grid.sh` 和 `submit_vanda_gpu_grid.sh` 分别提交 45 张固定图的单节点消融与两节点 GPU 批次；`submit_vanda_cpu_weak.sh` 提交 CPU 弱扩展及三个按家族拆分的 512 核弱扩展批次；`submit_vanda_full_experiments.sh` 按额度分批提交 45×5 个 CPU 强扩展批次（第五批为独立 512 核端点）。Vanda 免费 CPU 队列每作业最多 160 核，项目 CPU 队列最多 10 节点/720 核；≥256 核需要有效项目与额度。弱扩展 p=512 的每张合成图有 4.096 亿边，按家族拆分以便独立计算和校验。作业 ID 写入 `submitted_jobs.tsv`。每批保留环境、rank 所在主机、原始重复时间、校验 JSON 和汇总 CSV。Kokkos 4.5.01 源码需先放到 `third_party/kokkos`。Vanda 的 OpenMPI 在 `PE=` 映射下会卡住，因此混合方法使用 `mpi_affinity_exec.py` 对同一节点的 rank 分配互不重叠的 CPU 集；实际映射已由小作业验证。

目前**不能**把上述 Vanda 矩阵称为已完成实验。本机 CPU 矩阵 2160 项校验、零失败，具体结果见 `updated_experimental_conclusions_20261101.md`。截至 2026-11-02 22:43 SGT，Vanda 运行的 133 个已登记批次中有 22 个通过完成标记；45 张图的 Serial 与 GPU 矩阵均已提交，原始三图和三张典型合成图的 CPU 强扩展已提交，CPU/GPU 弱扩展已提交。其余 39 张固定图 CPU 强扩展及 PDF 报告仍待完成，实时细节见 `updated_vanda_run_status_20261102.md`。
