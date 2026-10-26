**PageRank 串行、OpenMP 与 MPI 实验**

C++17 同步 Pull PageRank。三个版本均依次运行 Google、Uniform 和 Hub 三张图。OpenMP 默认测试 1、2、4、8 个线程；MPI 分别启动 1、2、4、8 个进程。MPI + OpenMP 混合版尚未实现。

**项目结构**

```text
DSA5208_PROJECT_3/
├── CMakeLists.txt
├── src/
│   ├── graph_io.cpp / .hpp     # 共用图读取和稀疏存储
│   ├── utility.cpp / .hpp     # 公共配置、结果结构、输出和耗时统计
│   ├── pagerank_serial.cpp     # 串行算法和实验
│   ├── pagerank_openmp.cpp     # OpenMP 算法和线程数实验
│   └── pagerank_mpi.cpp        # MPI 图分发、求解和进程数实验
├── scripts/
│   ├── prepare_data.py        # 下载 Google，生成 Uniform 和 Hub
│   ├── validate_serial.py     # 独立检查串行结果
│   ├── validate_openmp.py     # 检查 OpenMP 并与串行比较
│   └── validate_mpi.py        # 检查 MPI 并与串行比较
├── data/
├── build/
└── results/
    ├── serial/{google,uniform,hub}/
    ├── openmp/{google,uniform,hub}/{t1,t2,t4,t8}/
    └── mpi/{google,uniform,hub}/{p1,p2,p4,p8}/
```

**运行步骤**

需要支持 OpenMP 的 C++17 编译器、MPI 开发库及运行环境、CMake、Ninja 和 Python 3.9+，Python 脚本仅使用标准库。以下命令均在项目根目录执行。Windows 使用 MS-MPI 和匹配编译器的开发库；Linux 可使用 MPICH 或 Open MPI。CMake 会查找已安装的 MPI。

**1. 准备数据**

下载 [SNAP web-Google](https://snap.stanford.edu/data/web-Google.html)，生成各含 10 万节点、100 万条边的 Uniform 和 Hub 图。已有数据时可跳过。

```text
python scripts/prepare_data.py
```

**2. 配置构建**

生成 Release 构建配置。

```text
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
```

**3. 编译程序**

可执行文件生成在 `build/`。修改 C++ 后重新执行这一步。

```text
cmake --build build
```

**4. 运行串行、OpenMP 和 MPI 实验**

```powershell
.\build\pagerank_serial.exe
```

串行运行结束后再运行 OpenMP，避免两个程序同时争用 CPU：

```powershell
.\build\pagerank_openmp.exe
```

依次运行 MPI 的四种进程配置；每条命令均运行完整的三张图：

```powershell
mpiexec -n 1 .\build\pagerank_mpi.exe
mpiexec -n 2 .\build\pagerank_mpi.exe
mpiexec -n 4 .\build\pagerank_mpi.exe
mpiexec -n 8 .\build\pagerank_mpi.exe
```

Linux 使用 `./build/pagerank_serial`、`./build/pagerank_openmp` 和 `mpiexec -n 4 ./build/pagerank_mpi` 等命令。每个程序对每张图只读取一次；串行、每个 OpenMP 线程配置和每个 MPI 进程配置均预热一次、正式运行三次；每次求解都从均匀排名重新开始。默认阻尼系数为 `0.85`，L1 更新差阈值为 `1e-8`，最多迭代 1000 次。

`solve_s` 只计迭代循环，包含每轮的排名更新和收敛判断，不包含图读取、预处理、求解器初始化、最终残差验证及文件输出。OpenMP 计入线程团队的进入/退出、任务调度、归约和迭代同步。MPI 计入每轮集合通信，以所有进程中最大的循环耗时为准；初始图分发、计时前屏障、耗时汇总、最终残差验证和最终排名收集不计入。

每张图（并行版还区分线程或进程配置）的目录保存四个文件，重新运行会覆盖同版本、同数据集的结果：

| 文件 | 内容与用途 |
|---|---|
| `timings.csv` | 三次正式运行的耗时、迭代数和正确性指标 |
| `summary.json` | 数据规模、实验配置、耗时中位数/最小值/最大值及各次运行中的最大残差和排名总和误差 |
| `ranks.csv` | 最后一次运行的节点 ID、排名、入度和出度，用于串并行比较及真实数据分析 |
| `history.csv` | 最后一次运行的 L1 更新差，用于收敛曲线 |

当前环境标记为 `local workstation`，本机结果不能替代作业要求的 Atlas/Vanda 测量。集群实验时同步修改 `src/utility.hpp` 中的环境标记，并在报告记录硬件、编译器和资源配置。OpenMP 的摘要和逐次记录会保存实际线程数；`t4` 等目录名表示请求的线程数。

**5. 验证三张图的实验结果**

先完成第 4 步，再运行：

```text
python scripts/validate_serial.py
```

脚本读取三个结果目录，检查节点 ID、排名非负性与总和、收敛历史、重复运行记录和耗时统计，并读取原始图核对每个节点的入度与出度，独立计算一次 PageRank 更新的 L1 残差。

验证面向当前无重复边的三张图，不构造稠密矩阵。独立残差需不超过收敛阈值加 `1e-12` 的舍入余量，排名总和误差需不超过 `1e-10`。检查结果写入 `results/serial/validation.json`；任一数据集未通过时，脚本以非零状态退出。

串行和 OpenMP 实验完成后，验证所有 12 个并行配置：

```text
python scripts/validate_openmp.py
```

它复用独立残差检查，按节点 ID 比较完整的串并行排名，要求 L1 误差不超过 `1e-8`。结果写入 `results/openmp/validation.json`；`scaling.csv` 保存各配置的误差、加速比和效率。加速比为串行耗时中位数除以 OpenMP 耗时中位数，效率为加速比除以实际线程数。

**OpenMP 实现**

整个迭代过程复用一个线程团队。贡献计算采用静态调度，排名更新采用 `dynamic,64` 调度，以分散 Hub 图中入边较多节点的工作。每个节点只由一个线程写入新排名；悬挂节点总排名和 L1 更新差使用归约，交换排名数组和判断停止由一个线程执行。循环末尾的隐式屏障保证线程看到相同的迭代状态。

浮点归约的加法顺序可能改变，因此串并行结果按数值误差验证，不要求逐位相同。小图上的调度和同步开销可能抵消并行收益，实际加速情况以实验记录为准。

**MPI 实现与验证**

0 号进程读取图，按连续节点 ID 均分，并用 `Scatterv` 分发各分区的入边和出度。各进程只更新本地排名；每轮 `Allgatherv` 交换贡献值，两次 `Allreduce` 分别汇总悬挂节点排名和 L1 更新差。所有进程根据同一误差停止，最终用 `Gatherv` 在 0 号进程收集排名并写文件。

这是基础 MPI 方案：各进程保留完整贡献向量，0 号进程保留完整图用于输出。均分节点不保证边数均衡，Hub 图可能出现明显负载不均；摘要中的 `min_local_edges`、`max_local_edges` 用于分析这一点。当前使用 MPI 的 `int` 计数接口，分发数组的计数和位移需能由 `int` 表示，三张实验图均满足。

完成四种进程配置后运行：

```text
python scripts/validate_mpi.py
```

脚本对 12 个配置进行独立残差检查，并按节点 ID 与串行排名比较，L1 误差阈值为 `1e-8`。验证报告与性能汇总分别保存为 `results/mpi/validation.json`、`results/mpi/scaling.csv`。加速比使用同环境串行耗时中位数作为基线，效率为加速比除以进程数。本机多进程结果不代表跨节点扩展性，正式报告仍需 Atlas/Vanda 测量。
