# DSA5208 Project 3：Vanda 实验交接

**状态快照：2026-11-06 19:49 SGT**  
**截止日期：2026-11-13**  
**主运行 ID：** `20261102T092147Z`  
**仓库：** `https://github.com/rosesnack/DSA5208_PROJECT_3`，分支 `main`

这份文件给接手的组员说明哪些数据已经通过校验、哪些作业仍在 Vanda 队列、哪些设计点尚未提交，以及如何继续。PBS 状态会变化；接手时先重新运行文末的检查命令。

## 1. 当前完成度

固定图矩阵的审计结果为 **16,116/19,980 配置单元通过**。批次审计为 **384/473 个已提交批次通过**。两种数字的单位不同：一个 PBS 批次会包含许多图配置和 Allgatherv/Halo 两种通信测量。只有结果标记对应到原作业或登记的替代作业、且独立校验通过，才算完成。

| 审计范围 | 严格通过 | 目标 | 状态 |
|---|---:|---:|---|
| 固定图 Serial | 45 | 45 | 完成 |
| 单独 OpenMP（CPU） | 270 | 270 | 完成 |
| 单独 Kokkos OpenMP（CPU） | 270 | 270 | 完成 |
| 固定图 GPU 节点：Serial、OpenMP、纯 MPI、MPI+OpenMP | 1,215 | 1,215 | 完成 |
| 单独 CUDA、单独 Kokkos CUDA | 90 | 90 | 完成 |
| MPI+CUDA、MPI+Kokkos CUDA | 360 | 360 | 完成 |
| CPU 常规强扩展：纯 MPI | 1,812 | 2,160 | 缺 348 |
| CPU 常规强扩展：MPI+Kokkos OpenMP，T=1 | 1,812 | 2,160 | 缺 348 |
| CPU 常规强扩展：MPI+OpenMP | 6,342 | 7,560 | 缺 1,218 |
| CPU 常规强扩展：MPI+Kokkos OpenMP，T>1 扩展 | 3,900 | 5,400 | 缺 1,500 |
| CPU 512 核端点：纯 MPI | 0 | 90 | 未完成 |
| CPU 512 核端点：MPI+Kokkos OpenMP，T=1 | 0 | 90 | 未完成 |
| CPU 512 核端点：MPI+OpenMP | 0 | 180 | 未完成 |
| CPU 512 核端点：MPI+Kokkos OpenMP，T=4 | 0 | 90 | 未完成 |
| **合计固定图配置** | **16,116** | **19,980** | **缺 3,864** |

弱扩展是固定图审计之外的独立实验：CPU 常规三家族曲线、GPU 三家族 p=1/2 曲线、uniform 的按核配平曲线已完成。CPU 按 rank 扩到 512 的 hub/controlled 端点待补；按核配平的 hub/controlled 家族尚未提交。4/8 GPU 已明确从目标移除。

## 2. Vanda 队列快照：已完成、排队、运行、暂挂和失败

19:49 SGT 的 `qstat -w -u hongxinran` 显示 **2 个运行、10 个排队、77 个用户暂挂**。其中 88 个属于主运行的未完成批次；另有 1 个独立 GPU 代码验证作业排队。结合完成标记，主运行的 89 个未完成批次是：77 个暂挂、9 个排队、2 个运行、1 个已失败且当前不在队列。

### 正在运行或排队的主实验重跑

| PBS 作业 | 实验 | 19:49 状态 | 说明 |
|---|---|---|---|
| `1526604` | Kokkos CPU 大图 `strong_uniform`，1 节点 | 运行 | 免费 CPU 队列，6 小时上限 |
| `1526605` | 同图，2 节点 | 排队 | 免费 CPU 队列 |
| `1526606` | 同图，4 节点 | 排队 | 免费 CPU 队列 |
| `1526607` | Kokkos CPU 大图 `strong_hub`，1 节点 | 运行 | 免费 CPU 队列，6 小时上限 |
| `1526608` | 同图，2 节点 | 排队 | 免费 CPU 队列 |
| `1526609` | 同图，4 节点 | 排队 | 免费 CPU 队列 |
| `1526610` | Kokkos CPU 大图 `strong_controlled`，1 节点 | 排队 | 免费 CPU 队列 |
| `1526611` | 同图，2 节点 | 排队 | 免费 CPU 队列 |
| `1526612` | 同图，4 节点 | 排队 | 免费 CPU 队列 |
| `1526615` | CPU 弱扩展 controlled，p=512 | 排队 | 免费校验续跑；复用已存计时，不重跑计时 |
| `1526616` | CPU 弱扩展 hub，p=512 | 排队 | 付费队列，8 节点/512 rank，2 小时；需重跑实验 |

另有 `1511417` 在 GPU 队列排队，申请 2 个 GPU 节点、每节点 1 张 A40。它是独立的 GPU 运行环境/代码验证，不属于 19,980 固定图单元，也不是 4/8 GPU 扩展实验。

### 77 个用户暂挂作业

这些作业分为：

- **29 个 CPU MPI 强扩展批次：** 8 节点网格图缺口与三张大图的缺口。对应作业由 PBS 标为用户 hold。
- **44 个固定图 512 核批次：** 纯 MPI、MPI+OpenMP、MPI+Kokkos OpenMP 的 45 个图批次中，44 个仍暂挂。
- **4 个 Kokkos CPU 512 核批次：** `google`、`uniform`、`hub`、`synthetic_uniform`，均暂挂。

29 个 CPU MPI 强扩展缺口的完整图/节点清单（这些 job ID 均是 PBS 用户暂挂）：

| 图 | 节点数 | PBS 作业 ID |
|---|---:|---|
| `grid_hub_n100000_d16`、`grid_hub_n200000_d4/d8/d16`、`grid_hub_n400000_d4/d8/d16` | 8 | `1513439, 1513444, 1513449, 1513454, 1513459, 1513464, 1513469` |
| `grid_controlled_n{50000,100000,200000,400000}_d{4,8,16}` | 8 | `1513474, 1513479, 1513484, 1513489, 1513494, 1513499, 1513504, 1513509, 1513514, 1513519, 1513524, 1513529` |
| `strong_uniform` | 4, 8 | `1513533, 1513534` |
| `strong_hub` | 1, 2, 4, 8 | `1513536–1513539` |
| `strong_controlled` | 1, 2, 4, 8 | `1513541–1513544` |

44 个固定图 512 核暂挂作业的每个图与 PBS ID，可在 [`submitted_jobs.tsv`](results/updated_vanda_scaling/20261102T092147Z/submitted_jobs.tsv) 筛选 `stage=mpi_strong_512` 查看；`synthetic_uniform` 的第 45 项 `1510577` 是已失败项。

**暂挂作业不会因 Vanda 维护结束或资源变空而自动运行。** PBS 记录的 hold 类型是用户暂挂；必须由原提交账号有选择地释放，或取消后重新提交。组员的新账号不能默认管理 `hongxinran` 账号提交的作业。不要一次性释放全部 77 个：账户余额有限，512 核任务的长 walltime 会大量占用额度。

### 失败和未提交

- 固定图 `synthetic_uniform` 的 512 核批次 `1510577` 曾因 MPI TCP 地址绑定错误退出；没有通过校验的结果，也没有当前替代作业。
- 弱扩展 hub/controlled 旧作业 `1510691/1510692` 分别在约 1 小时 walltime 失败。前者已由 `1526616` 重跑，后者由 `1526615` 补验证。
- Kokkos 大图的 9 个旧批次 `1523221–1523229` 在约 2 小时 walltime 失败；相应 6 小时重跑是 `1526604–1526612`。
- Kokkos 8 节点 T>1 扩展中，已有的 4 张图（Google、uniform、hub、synthetic_uniform）通过；**其余 41 张图未提交**：`synthetic_hub`、`synthetic_controlled`、36 张网格图及三张 `strong_*` 大图。
- 固定图 Kokkos 512 核 T=4 端点目前只为上述 4 张图提交过作业且均暂挂；另外 41 张图的端点未提交。
- CPU 按核配平弱扩展的 hub、controlled 家族未提交。

### 额度和队列风险

`hpc project` 在快照时显示 `personal-hongxinran` 的 CPU 余额 **1,570.921 核小时**、GPU 余额 **978.587 GPU 小时**。当前 hub 弱扩展 p=512 作业申请 512 核、2 小时，最多占用约 **1,024 核小时**的 PBS 资源时段；真正记账以 Vanda 项目记录为准。余额不足以支持无差别释放其余 512 核批次。优先监控免费队列重跑，等待 hub/controlled 的弱扩展结果后再依据新余额与实测墙钟选择下一批。

## 3. 完整实验矩阵（目标口径）

### 图集合：45 张固定图，另加三个弱扩展家族

| 图组 | 数量 | 内容 |
|---|---:|---|
| 原仓库图 | 3 | Google、uniform、hub |
| 典型合成图 | 3 | synthetic_uniform、synthetic_hub、synthetic_controlled |
| 网格规模/度数图 | 36 | uniform/hub/controlled 三家族 × 顶点数 50k/100k/200k/400k × 平均出度 4/8/16 |
| 固定大图 | 3 | strong_uniform、strong_hub、strong_controlled |
| **固定图合计** | **45** | 每种有效方法覆盖相同图集合 |
| 弱扩展图 | 3 家族 | uniform、hub、controlled；按资源规模生成，和固定图矩阵分开统计 |

### CPU 实现与布局

记节点数 `n`、每节点 MPI rank 数 `r`、每 rank 线程数 `T`、总 rank 数 `p=n×r`、实际 CPU 核数 `C=p×T`。

| 实现 | 固定图强扩展布局 | 通信 |
|---|---|---|
| Serial | `n=1,p=1,T=1` | 不适用 |
| 单独 OpenMP、单独 Kokkos OpenMP | `n=1,p=1,T=1/2/4/8/16/32` | 不适用 |
| 纯 MPI、MPI+Kokkos OpenMP T=1 | `n=1/2/4/8`，每节点 `r=1/2/4/8/16/32`；24 个布局/实现 | Allgatherv、Halo |
| MPI+OpenMP | 上述节点/rank 组合上取 `T=1/2/4/8/16/32` 且 `r×T≤32`；84 个有效布局 | Allgatherv、Halo |
| MPI+Kokkos OpenMP T>1 | T>1 的多线程扩展，和 Kokkos T=1 基线合起来对齐 MPI+OpenMP 目标 | Allgatherv、Halo |
| 512 核补充端点 | 8 节点×64 核：纯 MPI 和 Kokkos T=1 用 `p=512,T=1`；MPI+OpenMP 增加 `p=512,T=1`、`p=128,T=4`；MPI+Kokkos 增加 `p=128,T=4` | Allgatherv、Halo |

MPI+OpenMP 的 84 个布局包含 T=1 的 24 个基础布局和其余符合 `r×T≤32` 的混合布局。MPI+Kokkos 的 T>1 扩展独立提交；T=1 结果归在 MPI+Kokkos T=1 批次中。每个 MPI 配置都对同图、同资源布局分别测两种通信。512 核点是补充端点，不应和常规每节点最多 32 核曲线混成一条曲线。

### GPU 实现与布局

Vanda GPU 配对使用 1/2 节点，每节点 1 rank、1 GPU，即 p=1/2。每张固定图均包含：

- 单独 CUDA 与 Kokkos CUDA（单 GPU 消融）。
- 同 GPU 节点上的 Serial、OpenMP、纯 MPI 及 MPI+OpenMP（T=1/2/4/8）CPU 对照。
- MPI+CUDA 与 MPI+Kokkos CUDA。
- 所有 MPI 方法在 p=1/2 分别运行 Allgatherv、Halo。

纯 MPI 和 OpenMP 在 GPU 节点上仍是 CPU 运算对照。GPU p=4/8 不在范围内。

### 弱扩展矩阵

三种图家族分别保持每 rank 50,000 顶点和 800,000 条边，随 p 增加总图规模。每个 MPI 点均做 Allgatherv、Halo。

- 纯 MPI、MPI+Kokkos OpenMP T=1：p=1/2/4/8/16/32/64/128/256，另含 p=512 端点。
- MPI+OpenMP T=4：p=1/2/4/8/16/32/64，另含 p=128,T=4 的 512 核配平端点。
- GPU 弱扩展：三家族 p=1/2，每节点一 rank、一 GPU；包括 CUDA/Kokkos CUDA、MPI+CUDA/MPI+Kokkos CUDA和 CPU 对照。
- 额外按核配平曲线：MPI+OpenMP 与 MPI+Kokkos OpenMP T=4，C=4/8/16/32/64/128/256/512，每个点两种通信；目前只 uniform 家族完成。

### 测量规则

统一 Release 构建、1 次 warmup、5 次计时、报告中位数。保存求解时间、迭代数、通信模式/字节和正确性验证；GPU 还应分别记录传输和设备计算时间。用同配置 Serial 做正确性参考。排队状态、部分输出、walltime 失败均不纳入性能结论。

## 4. 新组员接手步骤

1. **各自注册 NUS HPC 账号。**使用有效 NUS-ID 在 [NUS HPC Registration Guide](https://nusit.nus.edu.sg/services/getting-started/registration-guide/) 按提示提交注册表。注册通过后再尝试 SSH 登录；不要共享密码。
2. 登录后运行 `hpc project`，确认自己的项目名称、CPU/GPU balance 和项目成员。当前 `personal-hongxinran` 只显示 hongxinran；如需组员共用项目额度，先确认 HPC 管理员是否需要添加成员或建立组项目。不要默认组员可使用这笔个人额度。
3. 获取仓库主分支：

   ```bash
   git clone https://github.com/rosesnack/DSA5208_PROJECT_3.git
   cd DSA5208_PROJECT_3
   ```

4. **先对照现有作业和结果，不要重复提交：**

   ```bash
   python3 scripts/check_vanda_progress.py 20261102T092147Z --missing
   python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
   qstat -w -u "$USER"
   hpc project
   ```

5. 主项目路径原属 hongxinran 账号：仓库为 `/scratch/hongxinran/DSA5208_PROJECT_3`，大型输入/中间数据为 `/scratch/hongxinran/dsa5208_scaling/20261102T092147Z`。其他账号不一定能读写这两个目录；新账号需要从 GitHub 获取代码和已提交结果，并确认/重建数据及 Release 构建。检查 scratch 配额和文件保留期限，不要假设 owner 的 scratch 对组员共享。
6. 原账户的 77 个 hold 由提交账号处理。先等 `1526604–1526612`、`1526615` 和 `1526616` 出结果，再同步并更新 `retry_jobs.tsv`、PBS 用时和矩阵审计。下一批只选能由当前额度承担的缺口；不要批量释放 512 核作业。
7. 更新实验结论和最终 PDF：说明覆盖范围、失败/未完成项、计时口径、Google 图的数据结论、所有组员姓名与学号，以及 AI 使用说明。只有通过审计的结果可进入性能图表。

### 截止日期优先级

课程说明要求报告介绍算法、解释并行设计、讨论扩展性/效率、验证正确性、提供 Atlas 或 Vanda 的实际运行时间、说明真实数据结论（如使用真实数据）及 AI 使用；另需提交源代码和运行 README。课程说明没有规定必须达到 256 或 512 CPU 核，也没有规定必须跑满这 19,980 个扩展单元。固定图 512 核、所有 45 图的完整 MPI 笛卡尔积，是本组追加的高覆盖率目标。若额度/时间不允许，优先整理现有已验证的 Vanda 曲线并完成报告，明确列出未覆盖的图和布局；不要因追求矩阵全满而漏交 PDF、AI 说明、组员姓名/学号或代码运行说明。

## 5. 重要文件与运行目录

| 用途 | 路径 |
|---|---|
| 主批次清单 | [`submitted_jobs.tsv`](results/updated_vanda_scaling/20261102T092147Z/submitted_jobs.tsv) |
| 原作业/替代作业映射 | [`retry_jobs.tsv`](results/updated_vanda_scaling/20261102T092147Z/retry_jobs.tsv) |
| PBS 请求和实际用时快照 | [`pbs_job_usage.csv`](results/updated_vanda_scaling/20261102T092147Z/pbs_job_usage.csv) |
| 严格进度脚本 | [`check_vanda_progress.py`](scripts/check_vanda_progress.py) |
| 19,980 单元固定矩阵审计 | [`audit_fixed_matrix.py`](scripts/audit_fixed_matrix.py) |
| 矩阵定义全文 | [`updated_experiment_matrix_20261103.md`](updated_experiment_matrix_20261103.md) |
| 最新简明状态 | [`updated_vanda_run_status_20261106.md`](updated_vanda_run_status_20261106.md) |
| 阶段性性能结论 | [`updated_experimental_conclusions_20261105.md`](updated_experimental_conclusions_20261105.md) |

原提交账号上继续看作业可运行：

```bash
qstat -w -u hongxinran
hpc project
python3 scripts/check_vanda_progress.py 20261102T092147Z --missing
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
```
