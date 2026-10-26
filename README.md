**PageRank 串行与 OpenMP 实验**

C++17 同步 Pull PageRank。两个版本均依次运行 Google、Uniform 和 Hub 三张图。OpenMP 默认测试 1、2、4、8 个线程；MPI 尚未实现。

**项目结构**

```text
DSA5208_PROJECT_3/
├── CMakeLists.txt
├── src/
│   ├── graph_io.cpp / .hpp     # 共用图读取和稀疏存储
│   ├── utility.cpp / .hpp     # 公共配置、结果结构、输出和耗时统计
│   ├── pagerank_serial.cpp     # 串行算法和实验
│   └── pagerank_openmp.cpp     # OpenMP 算法和线程数实验
├── scripts/
│   ├── prepare_data.py        # 下载 Google，生成 Uniform 和 Hub
│   ├── validate_serial.py     # 独立检查串行结果
│   └── validate_openmp.py     # 独立检查并与串行结果比较
├── data/
├── build/
└── results/
    ├── serial/{google,uniform,hub}/
    └── openmp/{google,uniform,hub}/{t1,t2,t4,t8}/
```

**运行步骤**

需要支持 OpenMP 的 C++17 编译器、CMake、Ninja 和 Python 3.9+，Python 脚本仅使用标准库。以下命令均在项目根目录执行。

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

**4. 运行串行和 OpenMP 实验**

```powershell
.\build\pagerank_serial.exe
```

串行运行结束后再运行 OpenMP，避免两个程序同时争用 CPU：

```powershell
.\build\pagerank_openmp.exe
```

Linux 使用 `./build/pagerank_serial` 和 `./build/pagerank_openmp`。每个程序对每张图只读取一次；串行配置和每个 OpenMP 线程配置均预热一次、正式运行三次；每次求解都从均匀排名重新开始。默认阻尼系数为 `0.85`，L1 更新差阈值为 `1e-8`，最多迭代 1000 次。

`solve_s` 只计迭代循环，包含每轮的排名更新和收敛判断，不包含图读取、预处理、求解器初始化、最终残差验证及文件输出。OpenMP 计入线程团队的进入/退出、任务调度、归约和迭代同步。

每张图（OpenMP 还区分线程配置）的目录保存四个文件，重新运行会覆盖同版本、同数据集的结果：

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
