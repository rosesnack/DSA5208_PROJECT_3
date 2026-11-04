# Vanda 实验严格完成清单与阶段性结论（2026-11-05 02:21 SGT）

主运行 `20261102T092147Z`。只计 `complete.txt` 对应原作业或记录在 `retry_jobs.tsv` 的替代作业，且所有独立校验通过的批次；排队、运行中、失败和 scratch 部分输出均不计。所有下述性能结果来自 Vanda Release 构建、1 次预热、5 次计时的中位数；原仓库旧口径与本地 Mac 结果不并入。已提交批次 **262/350** 完成，但 350 不包括尚未提交的全部 Kokkos CPU 图；默认固定图矩阵已验证 **12,300/19,980** 个配置单元。主运行目录有 **2336 份** `validation.json`，全部 `failed=0`。

## 已严格完成

| 实验 | 已完成的图和布局 |
|---|---|
| Vanda CPU 单独方法 | 45/45 固定图：Serial、OpenMP T=1/2/4/8/16/32、Kokkos OpenMP T=1/2/4/8/16/32 |
| Vanda GPU 节点配对 | 45/45 固定图：同节点 Serial/OpenMP/纯 MPI/MPI+OpenMP 对照、单独 CUDA/Kokkos CUDA、MPI+CUDA/MPI+Kokkos CUDA；MPI 方法 p=1/2，各有 Allgatherv 与 Halo；MPI+OpenMP T=1/2/4/8 |
| Vanda CPU 常规 MPI 强扩展 | 145/180 图×节点批次：19 张图完成 1/2/4/8 节点，23 张图完成 1/2/4 节点；每个完成批次包含纯 MPI、MPI+OpenMP、MPI+Kokkos OpenMP T=1 的该节点全部有效 rank/线程布局与两种通信方式 |
| MPI+Kokkos OpenMP T>1 | 4 张图（google、uniform、hub、synthetic_uniform）×1/2/4/8 节点，16/16 个已提交常规节点批次校验通过；在 45 图目标中为 16/180 图×节点批次 |
| CPU 按 rank 弱扩展 | 3 个合成家族，纯 MPI 与 MPI+Kokkos OpenMP T=1 的 p=1…256；MPI+OpenMP T=4 的 p=1…64，均有两种通信策略 |
| CPU 按核配平弱扩展 | uniform 家族，MPI+OpenMP 与 MPI+Kokkos OpenMP T=4、C=4…256，两种通信策略 |
| GPU 弱扩展 | 3 个合成家族，p=1/2 的单独 CUDA/Kokkos CUDA 及相应 MPI+GPU 方法，并有同 GPU 节点 CPU 对照与两种通信策略 |

常规 CPU 强扩展的 19 张全节点图为原仓库 3 张、典型合成图 3 张、uniform 网格 12 张及 `grid_hub_n50000_d4`。另 23 张 hub/controlled 网格图只有 1/2/4 节点完整批次。三张 `strong_uniform/strong_hub/strong_controlled` 特大图没有完整的 CPU MPI 节点批次。

## 仍未完成

| 缺口 | 当前状态 |
|---|---|
| CPU 常规强扩展 | 35/180 批：23 张普通图的 8 节点点，以及 3 张特大图各 1/2/4/8 节点。`strong_uniform` 的 1/2 节点续跑正在运行，部分 scratch 测量不计完成 |
| 512 CPU 核固定图端点 | 纯 MPI、MPI+OpenMP、MPI+Kokkos OpenMP T=1/T=4 均无通过校验的完整批次；首个 512 核作业因 MPI TCP 地址绑定失败，另一个仍在运行，其余排队作业暂挂待排查 |
| Kokkos CPU T>1 全图网格 | 41 张固定图的常规节点批次尚未提交；全部 45 图的 Kokkos T=4、512 核端点均未通过校验 |
| CPU 弱扩展补充 | 按 rank 的 p=512 三家族未完成；MPI+OpenMP T=4 的 p=128 未完成；按核配平的 hub/controlled 家族未提交，uniform 的 C=512 未完成 |
| GPU 4/8 卡 | 未运行；课程文本没有规定该卡数，现列为可选扩展，默认覆盖目标不计入 |

## 目前能支持的结论

下列都是**同一图逐图计算比值，再取图间中位数**；强扩展效率按同方法、同图的资源倍数计算。比值 `Allgatherv 时间 / Halo 时间` 小于 1 表示 Halo 更慢。

| 对比 | 严格完成子集的观察 |
|---|---|
| GPU 节点单独 CUDA / 同节点 Serial | 45 图中位加速 **15.225×**，45/45 更快 |
| GPU 节点单独 Kokkos CUDA / 同节点 Serial | 45 图中位加速 **7.181×**，45/45 更快；与原生 CUDA 的逐图相对时间有差异，不能仅据两个中位数声称每图均更慢 |
| GPU MPI+CUDA / MPI+Kokkos CUDA，p=1→2，Allgatherv | 45 图中位强扩展效率分别 **0.326 / 0.430**；跨节点通信与额外资源开销限制两卡加速 |
| GPU MPI+CUDA，p=2，Allgatherv / Halo | 45 图时间比中位 **0.935**，Halo 仅在 11/45 图较快；Halo 每迭代字节比中位 **0.962** |
| CPU 单独 OpenMP T=32 / Serial | 45 图中位加速 **12.199×**；Google 图仅 **1.005×**，图结构会显著改变线程加速表现 |
| CPU 纯 MPI Allgatherv，1→8 节点、每节点 1 rank | 19 张全节点图的中位强扩展效率 **0.158** |
| CPU 纯 MPI Allgatherv，1→8 节点、每节点 32 ranks（p=32→256） | 同 19 图中位强扩展效率 **0.0129**，说明这一批小/中图在高进程数下通信开销严重 |
| CPU 纯 MPI，8 节点 p=256，Allgatherv / Halo | 同 19 图的 Halo 字节量为 Allgatherv 的中位 **0.0312**，但时间比中位 **0.340**，19/19 图的 Halo 都较慢；字节减少尚未转化为运行时间收益 |

这 19 张图在 p=256 的 Allgatherv/Halo 成对比较中迭代数完全相同，排除了提前停止轮数不同造成的时间差。它们主要覆盖原仓库和 uniform 网格，缺少大部分 hub/controlled 网格及三张特大图；高进程数与 Halo 的结论不能外推至所有 45 图。GPU 只有 p=1/2 两个强扩展资源点，不能推断 4/8 GPU 效率。CPU p=512 无有效结果，不能用已排队或失败的尝试补出 512 核结论。弱扩展图按资源重新生成、部分家族的迭代数会变化，最终报告需同时展示每轮时间与迭代数。最终 PDF 报告及真实 Google 图的数据结论仍待整理。

复核：

```bash
python3 scripts/check_vanda_progress.py 20261102T092147Z
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
```
