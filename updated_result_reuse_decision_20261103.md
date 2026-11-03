# 更新代码后的结果复用判定（2026-11-03）

## 判定规则

扩大实验矩阵不自动废除已完成测量。只有图、PageRank 数值实现、计时边界、编译类型、硬件环境、预热/重复次数或正确性条件改变，受影响的结果才需重跑。新增布局与新增图没有旧结果可复用，必须新跑。不同环境的强扩展曲线分别计算，Vanda p=1/2 不与 Cloud p=4/8 拼接。

## 实际核对

本机当前源码与 Vanda 主项目逐文件 SHA-256 比对：`pagerank_serial.cpp`、`pagerank_openmp.cpp`、`pagerank_mpi.cpp`、`pagerank_hybrid.cpp`、`pagerank_mpi_cuda.cu`、`mpi_graph.cpp`、`utility.cpp`、`utility.hpp` 完全一致。`pagerank_mpi_kokkos.cpp` 与 `mpi_device_driver.hpp` 的变化仅添加线程数采集、T>1 结果目录后缀和元数据字段，迭代计算、MPI 交换、PageRank 更新和计时区域未改。新增的 T=1 结果目录仍为原来的 `pN`。

首次同步的 Vanda `20261102T092147Z` 快照有 1,935 个已完成固定图配置单元；逐格读取汇总显示：381 个 CPU 单元与 1,554 个 GPU 节点单元均为 Release、1 次预热、5 次测量，`alpha=0.85`、L1 容差 `1e-8`、最大迭代 1000，固定迭代数为 0。651 份 `validation.json` 中零份报告失败。三张 GPU 大图续跑并校验后，2026-11-03 再次同步的快照增至 **2,046/19,980** 个有效固定图单元，其中 GPU **1,665/1,665**。故**这些已完成的更新口径 Vanda 结果保留并复用**，不因补充 Kokkos T>1 或 Cloud 脚本而全量重跑。

| 结果组 | 决定 | 理由 |
|---|---|---|
| 原 Git 仓库三次重复、缺构建信息的旧结果 | 保留为历史版本，不进入新性能表 | 计时重复数与构建记录口径不同 |
| 本机五次重复 Release CPU 结果 | 可保留为本地观察 | Mac 与 Vanda 硬件不同，不替代课程要求的 Vanda/Atlas 运行图 |
| 已通过校验的 Vanda Serial、OpenMP、纯 MPI、MPI+OpenMP、Kokkos T=1、CUDA/Kokkos CUDA | 复用已有格子 | 源码数值部分相同，运行与验证口径一致 |
| 原已提交但处于 PBS `H`/`Q`、无 `complete.txt` 的 CPU 作业 | 继续等待或在额度恢复后重提，不称为已完成 | 尚无有效时间与校验结果 |
| 新 MPI+Kokkos OpenMP T>1、p=128/T=4 的 512 核配对 | 新跑 | 原矩阵没有这些布局 |
| CPU 按核配平弱扩展、Vanda A40 4/8 GPU | 新跑 | 新图/新资源布局；CPU 首个家族已提交，GPU 4/8 受 Vanda 每作业最多 2 GPU/2 节点的队列限制 |

主实验最后三张 `strong_uniform`、`strong_hub`、`strong_controlled` 的原作业因 2 小时 walltime 超时（`Exit_status=-29`）；其 scratch 输出分别已有 26/37、31/37、36/37 个格子保留五次计时与最终 rank。续跑作业 `1511591/1511593/1511595` 只补缺失格子，均以 `Exit_status=0` 完成；依赖的 CPU 正确性验证作业 `1511592/1511594/1511596` 也均以 `Exit_status=0` 完成。三张图现在各有 **37/37** 个格子与 **11 份零失败的校验报告**。`check_vanda_progress.py` 已识别原作业超时、后继作业校验完成的情况：GPU 固定图 **45/45** 批，全部作业 **67/133** 批。Vanda 隔离 CPU 小图验证 `1511433.stdct-mgmt-02` 已 `Exit_status=0`；新版 CUDA/Kokkos CUDA 编译验证 `1511456.stdct-mgmt-02` 已 `Exit_status=0`；新版共享驱动的双节点 GPU 运行验证 `1511417.stdct-mgmt-02` 仍在等待节点。
