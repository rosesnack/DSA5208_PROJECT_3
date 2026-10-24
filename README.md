**PageRank 串行实验**

C++17 同步 Pull PageRank。程序依次运行 Google、Uniform 和 Hub 三张图；MPI/OpenMP 尚未实现。

**项目结构**

```text
DSA5208_PROJECT_3/
├── CMakeLists.txt
├── src/
│   ├── graph_io.cpp / .hpp     # 图读取和稀疏存储
│   ├── pagerank_result.hpp     # 共用的结果结构
│   └── pagerank_serial.cpp     # 参数、算法、实验和输出
├── scripts/prepare_data.py     # 下载 Google，生成 Uniform 和 Hub
├── scripts/validate_serial.py    # 读取实验输出并独立验证三张图
├── data/                      # 原始数据和合成图
├── build/                     # CMake 构建产物
└── results/serial/
    ├── google/
    ├── uniform/
    ├── hub/
    └── validation.json        # 运行验证脚本后生成
```

**运行步骤**

需要 C++17 编译器、CMake、Ninja 和 Python 3.9+，Python 脚本仅使用标准库。以下命令均在项目根目录执行。

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

**4. 运行三张图的实验**

```powershell
.\build\pagerank_serial.exe
```

Linux 使用 `./build/pagerank_serial`。每张图读取一次，预热一次，再正式运行三次；每次求解都从均匀排名重新开始。默认阻尼系数为 `0.85`，L1 更新差阈值为 `1e-8`，最多迭代 1000 次。

`solve_s` 只计迭代循环，包含每轮的排名更新和收敛判断，不包含图读取、预处理、求解器初始化、最终残差验证及文件输出。后续并行版使用相同口径，并计入迭代内的通信和同步。

每张图的目录保存四个文件，重新运行会覆盖同版本、同数据集的结果：

| 文件 | 内容与用途 |
|---|---|
| `timings.csv` | 三次正式运行的耗时、迭代数和正确性指标 |
| `summary.json` | 数据规模、实验配置、耗时中位数/最小值/最大值及各次运行中的最大残差和排名总和误差 |
| `ranks.csv` | 最后一次运行的节点 ID、排名、入度和出度，用于串并行比较及真实数据分析 |
| `history.csv` | 最后一次运行的 L1 更新差，用于收敛曲线 |

当前环境标记为 `local workstation`，本机结果不能替代作业要求的 Atlas/Vanda 测量。集群实验时同步修改文件顶部的环境标记，并在报告记录硬件、编译器和资源配置。后续并行结果按 `results/版本/数据集/资源配置/` 保存。

**5. 验证三张图的实验结果**

先完成第 4 步，再运行：

```text
python scripts/validate_serial.py
```

脚本读取三个结果目录，检查节点 ID、排名非负性与总和、收敛历史、重复运行记录和耗时统计，并读取原始图核对每个节点的入度与出度，独立计算一次 PageRank 更新的 L1 残差。

验证面向当前无重复边的三张图，不构造稠密矩阵。独立残差需不超过收敛阈值加 `1e-12` 的舍入余量，排名总和误差需不超过 `1e-10`。检查结果写入 `results/serial/validation.json`；任一数据集未通过时，脚本以非零状态退出。
