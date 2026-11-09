# DSA5208 Project 3：Vanda 实验交接

> **Nov 9 15:02 新优先级：**先完成非 512 核。服务器监控已启用 `max_total_cores=256`（PID 3040469）；PBS 恢复后将未启动的 512 核补点加用户暂挂，并在确认暂挂后才释放它的预算预留。目前服务仍异常，尚未执行该暂挂。非 512 核剩余 **5,142**（72 已测待检、5,070 待安排）；原 512 核剩余 445，新增 720 拆分暂缓。512 核已有固定图 5 项、独立弱扩展 24 项成功。见[完整缺项、成功记录及运行策略](updated_non512_priority_and_remaining_20261109.md)。

> **Nov 9 最新：**新增 104 项独立校验通过并下载，合并审计 **14,393/19,980**；controlled 大图 32/64/128/256 核满核主线已齐。当前 PBS 拒绝连接、amgr 返回 HTTP 500，实时队列和余额未知，无法新增提交。旧监控因 PBS 异常字段退出，首次恢复又遇到 scratch ENOSPC；两处已修复，14:42 在独立 `/tmp` 状态目录启动 PID 2879720，14:46 已通过另一 SSH 会话核实持续存活、代码哈希一致。**新实时状态位置见 [Nov 9 状态与监控恢复](updated_vanda_run_status_20261109.md)**，下方旧 PID、旧状态路径及 Nov 8 队列均为历史。原矩阵尚余 5,587，其中 77 已登记、5,510 未安排；新增 720 仍单列。

> **Nov 8 21:22 恢复查询：**沙箱外独立 SSH 已通过公钥认证并成功执行命令。当前 VPN 路由、TCP 22 和 SSH 握手正常；先前多次超时的具体根因未确定。监控 PID 2539365 的最新心跳为 21:20，状态 `waiting_real_credits`，余额 576.128 CPUh。性能 28 组结束、512 核 1 组 Q；免费校验 2 R、10 Q、1 等待性能依赖 H，累计已结束 16 组。没有新增失败或重复投递。

> **Nov 8 21:16 复查未取得实时状态：**Vanda DNS 仍解析为 172.20.101.10，但新账号独立 SSH、复用连接及旧账号交叉查询均超时，未读到新心跳/队列/余额。因此最新成功核实的监控心跳仍为 20:31，严格通过数最近完整审计仍为 14,289；不能据此断言服务器故障或后台监控已停止。本次没有重启监控、重复提交或取消作业。

> **Nov 8 20:26 自动监控已启动：**Vanda 后台进程 PID 2539365 每五分钟查真实余额并去重续投，已用新 SSH 会话验证进程与心跳。本次又补了 4 核/2 节点的两个配置，性能 1533432 已 Exit 0（1:27），免费 1533433 等校验。目前余额 576.128，扣除既有 Q 的 512 CPUh 和 64 余量后进入等真实返还状态。详见[自动续挂规则、实时日志和停止方法](updated_vanda_auto_monitor_20261108.md)。本地文档是快照，实时记录在 Vanda。

> **Nov 8 20:12 续投已测完：**刚追加的六组均 Exit 0，60 项完整测量已保存；单组实际 37–70 秒，六个免费校验均 Q。严格通过数仍以 14,289 为最近完整审计，不能提前加上这 60。原矩阵现有任务覆盖 179 个缺项（174 已测待检＋5 排队待测），另 5,512 未覆盖。见[续投监测结果](updated_vanda_evening_submission_20261108.md)。

> **Nov 8 20:11 已追加：**新挂六个付费性能作业 1533366–1533376（偶数）及六个免费校验（对应奇数），补 hub 200k/400k × d4/8/16 的 60 个 Kokkos 满 32 核配置。六个性能均已 R；每组 20 分钟，请求上限共 64 CPUh。在真实余额 642.130 中保留既有 Q 的 512 CPUh 后，仍留 66.130。见[晚间续投及配置](updated_vanda_evening_submission_20261108.md)。未覆盖原矩阵缺项降至 5,512，新增 720 项仍单列未投。

> **Nov 8 19:44 最新：**本轮八个性能作业已成功结束，无失败；512 核 1532794 仍因 ncpus 资源不足排队。免费校验 2 R、3 Q、1 等待性能依赖，另 3 个已通过。固定矩阵严格完成 **14,289/19,980**；尚余 114 个已测量待校验、5 个排队待测量、5,572 个未由当前作业覆盖。新增 720 项仍单列未投。详见[最新状态与逐作业墙钟](updated_vanda_run_status_20261108.md)。

> **Nov 8 16:37 缺口分类快照：**原矩阵剩余 5,701 个配置中，1,250 未见正式提交记录，2,742 因旧结果不合格需补跑，1,634 已有提交/部分输出但无完整有效测量，75 已保存完整新测量待独立校验。新增 512 核拆分 720 项全部首次运行，单列。见[分类统计与逐配置清单](updated_remaining_experiments_classification_20261108.md)。各类按当前处理动作互斥，已通过的 14,279 项不在其中。

> **Nov 8 16:24 最新进度：**本轮九组为 4 运行、2 排队、3 性能成功结束；新增 20 配置已通过免费校验，累计 **14,279/19,980**。原矩阵尚余 5,701，129 已挂、5,572 未挂；新增 512 核四拆分的 720 项仍单列未挂。请求上限 3,434.667 CPUh，按本轮开始余额留 130.130 余量。[逐任务提交与墙钟依据](updated_vanda_submission_plan_20261108.md)。

> **Nov 8 16:04 已续投：**按用户新确认 3,564.797 CPUh，新增 9 个性能作业＋9 个免费校验，149 个缺项，请求上限 3,434.667 CPUh，余 130.130。性能 ID 为 `1532794–1532810` 偶数，16:04 为 6 运行、3 排队。controlled 大图补 64/128/256 核主线，512 核只补 5 个缺项。详细范围、墙钟依据及剩余任务见[本轮续投](updated_vanda_submission_plan_20261108.md)。下方“性能队列为空”为此前 15:32 的历史状态。

> **Nov 8 最新：**昨晚 13 组性能和 13 个免费校验全部通过，新增 178 配置；四个 512 核弱扩展补点也全部通过。固定图 512 核试跑因 TCP 地址绑定冲突退出，免费补检已保留其中 5 项，仅该批余 3 项需续跑。固定矩阵现为 **14,259/19,980**；本账号性能队列已跑空，但剩余缺项尚未全投。详见[Nov 8 状态](updated_vanda_run_status_20261108.md)，下方 Nov 7 排队/运行说明保留为历史记录。

> **Nov 7 22:45 队列更新：**本轮 64/128/256 核任务已全部完成并校验通过；剩余性能运行项是两个 32 核大图。五个 512 核性能作业因 ncpus 资源不足排队。uniform 大图性能完成、免费校验进行中。详见[实时状态](updated_vanda_run_status_20261107.md)。

> **Nov 7 22:25 后同步：**新批次已取得 30 个配置的免费独立校验完成标记，合并审计 **14,106/19,980**；22:25 性能快照为 6 运行、4 排队、3 已成功结束。注册表、逐图缺口和预算均已同步本地。完整状态见[Nov 7 续跑状态](updated_vanda_run_status_20261107.md)。

> **Nov 7 22:20 已续挂并启动：**新增 13 个满配性能作业（178 个缺项）＋13 个免费校验，性能 ID `1530742–1530766` 偶数，6 运行、7 排队。免费重验 `1530741` 已通过。每次测量 p×T=申请核数；注册表 `core_group_jobs.tsv`，详见[Nov 7 续跑状态](updated_vanda_run_status_20261107.md)。下方早先“未实施”是历史状态；更小核数分组和 512 核新增 720 项仍未投递。

> **按核数组织分析（Nov 7 新要求）：**优先 32/64/128/256/512 核扩展主线，同核数比较 p×T 拆分。32–256 核的六种拆分已在旧矩阵；512 核还需补 T=2/8/16/32 的 720 项（尚未提交）。原 19,980 配置审计继续保留，补充目标另记。详见[满配核数主线与覆盖审计](updated_full_core_experiment_plan_20261107.md)。

> **2026-11-07 21:33 SGT 核对：**固定矩阵为 **14,076/19,980**；新账号五个 512 核性能作业仍为 Q，五个免费校验等待依赖。课程明确要求、CPU/GPU 实际并行参数、当前结果及旧单独 Kokkos 线程元数据缺口，见[课程与配置核对](updated_coursework_configuration_audit_20261107.md)。下方 05:42 和 Nov 6 数字均保留为历史快照。

**最新本地合并审计：2026-11-09，14,393/19,980；当前续跑账号：xtt_ella。以下 Nov 6 队列表仅作历史记录。**
**截止日期：2026-11-13**
**已完成结果来源：** `20261102T092147Z`；**当前续跑 ID：** `20261106T185006Z`
**仓库：** `https://github.com/rosesnack/DSA5208_PROJECT_3`，分支 `main`

> **历史操作（2026-11-06 22:39 SGT）：** 最近一次全队列查询（21:21）为0个运行、1个排队、70个用户暂挂。22:39 复查确认付费弱扩展 `1526616` 仍为 `Q`、`Hold_Types=n`，PBS 注释仍为 `Insufficient amount of resource: ncpus`；当前资源不足以同时满足8节点/512核申请。18个免费队列未完成主实验均已取消，补充校验 `1526615` 已完成。`1527001` 已同步并通过校验。`1527002` 于21:11以 Exit 0 结束，实际34:41；结果现已同步，67项独立校验通过，但 PBS 分配混有3台 CN 与5台 GN-A40 主机，CPU 型号目前只记录了 leader CN-003 的 Platinum 型号。待逐节点核实 CPU 型号前，此结果不打严格完成标记、不纳入同硬件曲线。上一余额查询为 CPU 1,144.255 核小时、GPU 978.587 GPU 小时。清理后的矩阵为12,762/19,980配置单元、271/475批次。最新状态与删除清单见[运行状态](updated_vanda_run_status_20261106.md)和[排除清单](results/updated_vanda_scaling/20261102T092147Z/excluded_invalid_performance_results_20261106.tsv)。
>
> **免费队列结果已清理：** Kokkos CPU 网格清理前的130个完成批次中，114个由免费 `cpu_parallel` 完成、16个由付费 `batch_cpu` 完成。114个免费性能结果已删除；16个付费结果保留。节点文件证明免费结果是68个 IN-only、46个 CN-161 Platinum + IN 混合，无一项多节点结果全为 Platinum。uniform 弱扩展 `p=512` 作业 `1521114` 实际只有1节点/32核，其错误布局输出也已删除。所有删除条目在[`排除清单`](results/updated_vanda_scaling/20261102T092147Z/excluded_invalid_performance_results_20261106.tsv)中保留 job ID 和原因。免费的 `1526615` 只用于校验付费计时，验证记录保留。详见[CPU硬件审计](updated_vanda_cpu_hardware_audit_20261106.md)。

## 当前接手入口（2026-11-07）

当前严格完成 **13,986/19,980 个固定图配置**。完整现状见[新账号续跑记录](updated_vanda_new_account_run_20261107.md)，每个未完成图批次见[剩余固定图批次](results/updated_vanda_scaling/20261106T185006Z/remaining_fixed_batches_20261107.tsv)，本轮新旧 job 对照见[续跑注册表](results/updated_vanda_scaling/20261106T185006Z/audited_resume_jobs.tsv)。旧结果通过 `audit_fixed_matrix.py --reuse-root` 复用，不整套重跑。

- `1527002` 的 67 项旧正确性检查通过，现已核实原来的八台主机均为 Platinum 8452Y，恢复复用 66 个配置，停止重复作业 `1527815`。
- Kokkos 首批单/双节点作业及其免费校验均已结束；当前累计完成数包含随后完成的普通 Kokkos 和 MPI 图批次，以全矩阵审计为准。
- `1527535/1527538` 各有完整 28 个五次重复弱扩展计时。停止其付费校验阶段，改由免费 `1527844/1527845` 检查；56 个配置已通过，计算数据保留。
- 八个剩余常规 MPI 图批次、Kokkos 四个节点布局、固定图 512 核试跑及缺少的弱扩展端点已按缺口续挂；hub 的 rank 弱扩展 512 端点 `1527856` 因预算暂留用户暂挂。依赖等待与预算暂挂要区分，不能批量删除。
- 45 张图的原始 Serial rank 文件已完整转移，免费 `1527875` 核对 SHA-256 并解包。原来的 Serial 五次重复性能计时继续复用。

当前账号的检查命令：

```bash
ssh -o ProxyCommand=none -o ProxyJump=none xtt_ella@vanda.nus.edu.sg
cd /scratch/xtt_ella/DSA5208_PROJECT_3_20261107
qstat -u xtt_ella
hpc project
```

若 Codex 沙箱内出现 DNS 失败，应先使用已授权的网络执行权限重试；本次沙箱外 SSH 可以连接，不能直接据此判断用户校园网断开。

## 队列和重跑规则（2026-11-07 更新）

- 图生成、编译、正确性校验、文件整理和汇总全部使用免费 `auto_free`。45 张图的原始 Serial rank 文件已找到，后续直接转移复用；原有 Serial 性能结果不重跑。
- 付费 `batch_cpu` 只提交严格审计确认缺失或无效的性能测量。提交每个暂挂作业前，先按图、算法、节点数、MPI 进程数、线程数和通信方式核对现有结果；已有有效结果不重跑。
- 九图的参考路径已由免费 `1527806` 修复并通过；只补 rank 文件，原付费五次重复的计时元数据保持原值。新付费任务设 `PAGERANK_DEFER_VALIDATION=1`，由免费 [`vanda_finalize_cpu_job.pbs`](scripts/vanda_finalize_cpu_job.pbs) 接续检查、汇总和同步。不能把单次免费参考的计时作为 Serial 加速比基准。
- `1527529`、`1527530–1527533`、`1527561–1527562` 没有产生有效性能数据；重跑前确认对应配置仍缺结果。
- 4/8 GPU 扩展不在目标内。GPU 已有有效结果可复用。
- 此交接中的 PBS 状态是历史记录。恢复操作前先在 `xtt_ella` 账号刷新 `qstat -u xtt_ella`、作业历史和 `hpc project`；DNS 不通时不可把旧状态当成实时状态。

下方原有 PBS 队列表是 Nov 6 的历史快照。当前队列以新账号记录和 PBS 实时查询为准；旧账号的用户暂挂作业不会自动转移到新账号。

这份文件给接手的组员说明哪些数据已经通过校验、哪些作业仍在 Vanda 队列、哪些设计点尚未提交，以及如何继续。PBS 状态会变化；接手时先重新运行文末的检查命令。

## 1. 当前完成度

Nov 7 合并审计为 **13,986/19,980 配置单元通过**，含旧 `1527002` 核实后恢复的 66 项和新 Kokkos 单节点的 30 项。旧“271/475”来自历史提交注册表，不代表完整矩阵批次数。只有结果、原性能 job 来源、正确性检查和实际硬件/布局都满足要求，才计严格完成。

| 审计范围 | 严格通过 | 目标 | 状态 |
|---|---:|---:|---|
| 固定图 Serial | 45 | 45 | 完成 |
| 单独 OpenMP（CPU） | 270 | 270 | 完成 |
| 单独 Kokkos OpenMP（CPU） | 270 | 270 | 完成 |
| 固定图 GPU 节点：Serial、OpenMP、纯 MPI、MPI+OpenMP | 1,215 | 1,215 | 完成 |
| 单独 CUDA、单独 Kokkos CUDA | 90 | 90 | 完成 |
| MPI+CUDA、MPI+Kokkos CUDA | 360 | 360 | 完成 |
| CPU 常规强扩展：纯 MPI | 1,932 | 2,160 | 缺 228 |
| CPU 常规强扩展：MPI+Kokkos OpenMP，T=1 | 1,932 | 2,160 | 缺 228 |
| CPU 常规强扩展：MPI+OpenMP | 6,762 | 7,560 | 缺 798 |
| CPU 常规强扩展：MPI+Kokkos OpenMP，T>1 扩展 | 1,110 | 5,400 | 缺 4,290 |
| CPU 512 核端点：纯 MPI | 0 | 90 | 未完成 |
| CPU 512 核端点：MPI+Kokkos OpenMP，T=1 | 0 | 90 | 未完成 |
| CPU 512 核端点：MPI+OpenMP | 0 | 180 | 未完成 |
| CPU 512 核端点：MPI+Kokkos OpenMP，T=4 | 0 | 90 | 未完成 |
| **合计固定图配置** | **13,986** | **19,980** | **缺 5,994** |

弱扩展是固定图审计之外的独立实验：GPU 三家族 p=1/2 曲线已完成；CPU 的有效常规点和端点需按下方状态表分别判断。uniform 的 `p=512` 完成标记实际只对应 1 节点/32 核，必须排除并重跑；hub 的 `p=512` 正在付费队列排队；controlled 的 `p=512` 付费计时已通过补充校验。按核配平 hub/controlled 4–256 核的 56 项计时已保存，正在免费校验；其 512 核端点在前者校验通过后继续；另已补挂 20 个普通单节点 Kokkos 批次（600 配置）。4/8 GPU 已明确从目标移除。

### Nov 6 历史状态矩阵：完成、待跑、排队、暂挂

下表是交接时的执行口径。完成项可以复用；待跑项不能用排队、部分输出或 PBS Exit 0 直接代替校验。

| 实验组 | 目标布局/通信 | 已完成 | 还需跑或处理 | 当前状态 |
|---|---|---|---|---|
| 固定图集合 | 45 张：3 原图 + 3 典型合成图 + 36 张规模/度数网格 + 3 大图 | 图集及生成配置已固定 | 无 | 完成 |
| Serial | 45 图，单进程单线程 | 45/45 | 无 | 完成 |
| 单独 OpenMP、单独 Kokkos OpenMP | 45 图 × T=1/2/4/8/16/32 | 各 270/270 | 无 | 完成 |
| 单独 CUDA、单独 Kokkos CUDA | 45 图 | 各 45/45 | 无 | 完成 |
| GPU 节点 CPU 对照 | Serial、OpenMP、纯 MPI、MPI+OpenMP | 1,215/1,215 | 无 | 完成 |
| MPI+CUDA、MPI+Kokkos CUDA | 45 图 × 1/2 GPU 节点 × Allgatherv/Halo | 各 180/180 | 无 | 完成 |
| CPU 纯 MPI 常规强扩展 | 45 图 × 24 个布局 × 2 通信 | 1,824/2,160 | 336 配置单元 | 部分完成；缺项在原账户暂挂/未完成 |
| CPU MPI+Kokkos OpenMP，T=1 | 同纯 MPI 的 24 布局、两通信 | 1,824/2,160 | 336 配置单元 | 部分完成；该条目只计通过审计的有效 MPI 批次 |
| CPU MPI+OpenMP | 45 图 × 84 布局 × 2 通信 | 6,384/7,560 | 1,176 配置单元 | 部分完成；缺项在原账户暂挂/未完成 |
| CPU 512 核固定图端点 | 纯 MPI p=512；MPI+OpenMP p=512,T=1 和 p=128,T=4；MPI+Kokkos p=512,T=1 和 p=128,T=4；均两通信 | 0/450 配置单元 | 全部 450 配置单元；现有 70 个暂挂作业需逐项处理，未提交项另补 | 当前账号不宜批量释放；交接优先项 |
| CPU 弱扩展，三家族 | MPI/Kokkos T=1 的 p 扩展；含 p=512 端点 | 常规点已有；controlled p=512 的付费计时通过校验 | uniform p=512 重跑；hub p=512 等待 `1526616` | uniform 错布局；hub排队；controlled完成 |
| CPU 按核配平弱扩展 | MPI+OpenMP 与 MPI+Kokkos T=4，C=4…512，两通信 | uniform 家族 | hub、controlled 家族 | 还未完成；取消的免费任务不能计入 |
| GPU 弱扩展 | 三家族、1/2 节点、每节点1 rank/1 GPU | 全部目标点 | 无；4/8 GPU 不属于目标 | 完成 |
| 8 节点新补跑 | `grid_hub_n100000_d16`、`grid_controlled_n50000_d4` 的 MPI / 混合实现 | `1527001` 已同步且通过校验 | `1527002` 结果已同步、67项校验通过；核对3台 CN + 5台 GN-A40 的逐节点 CPU 型号 | `1527002` 暂不计严格同硬件完成数 |

**免费队列误跑的处理结论：**uniform 弱扩展 `p=512` 作业 `1521114` 的错误布局计时已删除，需以付费8节点/512核重跑；免费验证作业 `1526615` 只验证付费 controlled 计时，验证记录保留。Kokkos CPU 网格114个免费批次的性能文件已删除，需在付费 CPU 节点补跑。另有7个 MPI 和9个 Kokkos 免费恢复作业已取消，没有完整结果，需按矩阵补跑。

**队友接手判断：**当前实时队列 0 运行、1 排队、70 暂挂，付费账户 CPU 余额约 1,144 核小时。`1526616` 需要一次申请 8×64=512 核，PBS 当前注释是 `Insufficient amount of resource: ncpus`，属于资源暂时不足，不是用户 hold；它何时开始取决于调度器何时凑齐资源。若该作业启动，最多会预留约 1,024 核小时。全矩阵缺口和 114 批 Kokkos 同硬件重跑远超这点余量，建议组员注册并获得自己的 HPC 项目额度后接手；新账号不能管理原账号的 70 个用户暂挂作业。交接时从结果文件和作业记录继续，不要重复跑已通过项。

## 2. Vanda 队列快照：已完成、排队、运行、暂挂和失败

20:02 SGT 的 `qstat -w -u hongxinran` 显示 **2 个运行、10 个排队、77 个用户暂挂**。其中 88 个属于主运行的未完成批次；另有 1 个独立 GPU 代码验证作业排队。结合完成标记，主运行的 89 个未完成批次是：77 个暂挂、9 个排队、2 个运行、1 个已失败且当前不在队列。

### 正在运行或排队的主实验重跑

| PBS 作业 | 实验 | 20:02 状态 | 说明 |
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

### 免费队列可补的工作

`auto_free` 当前可用的 CPU 队列单作业上限为 160 核。主实验剩余项中，可从付费队列缺口转为免费队列重跑的有 7 个 1/2/4 节点 MPI 强扩展批次：`strong_uniform` 节点 4；`strong_hub` 和 `strong_controlled` 节点 1/2/4。8 节点 256 核和 512 核批次不能放进该免费 CPU 队列。已排队/运行的 9 个 Kokkos 作业已经是免费队列配置。

按核配平弱扩展 hub、controlled 家族还可先在免费队列补 C=4/8/16/32/64/128（最多 128 核）；C=256/512 点仍需另行安排。对应提交脚本已准备为 `scripts/submit_vanda_free_mpi_recovery.sh` 和 `scripts/submit_vanda_free_core_weak.sh`，会记录替代作业 ID，避免覆盖完整矩阵的完成标记。**截至本文件时间戳，这 7+2 个新增批次还没有获得 PBS 作业号。**

20:02 SGT 刷新过队列；之后 SSH 返回 `Timeout, server vanda.nus.edu.sg not responding`，所以暂时无法把这 9 项真正提交。恢复连接后先重查队列/完成标记，再运行提交脚本；别重复提交已经在运行的工作。

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
6. 原账户当前有 70 个用户暂挂作业，由 hongxinran 账号逐项处理；新组员不能直接释放这些 hold。已取消的 `1526604–1526612` 不会再出结果；`1526615` 是已完成的验证；`1526616` 是正常排队、当前因 512 核资源不足未启动。组员使用自己的获批项目额度补跑缺项时，应先登记新 job ID、申请布局和运行时，再逐批提交并同步结果。
7. 更新实验结论和最终 PDF：说明覆盖范围、失败/未完成项、计时口径、Google 图的数据结论、所有组员姓名与学号，以及 AI 使用说明。只有通过审计的结果可进入性能图表。

### 可直接发给组员的接手 Prompt

```text
请接手 NUS DSA5208 Project 3 的 Vanda 实验。先阅读仓库里的
HANDOFF_VANDA_EXPERIMENTS_20261106.md、updated_vanda_run_status_20261106.md、
updated_experiment_matrix_20261103.md 和 updated_vanda_cpu_hardware_audit_20261106.md，
再用 scripts/check_vanda_progress.py 与 scripts/audit_fixed_matrix.py 核对现有结果。

目标不是从头重跑，而是只补缺项。实验矩阵为：45 张固定图（3 原图、3 典型合成图、
36 张规模/度数网格、3 张大图）；Serial、单独 OpenMP/Kokkos OpenMP、纯 MPI、
MPI+OpenMP、MPI+Kokkos OpenMP、单独 CUDA/Kokkos CUDA、MPI+CUDA、MPI+Kokkos CUDA；
MPI 配置分别跑 Allgatherv 和 Halo。CPU 常规强扩展用 1/2/4/8 节点及文档列出的 rank/thread
布局；另有 512 核端点。GPU 对照用 1/2 节点、每节点 1 rank/1 GPU；不做 4/8 GPU。
弱扩展覆盖 uniform、hub、controlled 三家族。

必须优先处理的缺项：
1. uniform 弱扩展 p=512：旧免费作业 1521114 实际只有 1 节点/32 核，不能用；正确地用付费
   CPU 节点池提交 8 节点×64核，并跑 Allgatherv/Halo。
2. 固定图 512 核端点：审计目前为 0/450 配置单元，先核对旧账户的 70 个 hold 哪些确实对应
   缺项；不要重复已经通过校验的结果，也不要一次性释放所有 hold。
3. Kokkos CPU：若要形成同型号 Platinum CPU 曲线，114 个免费队列完成批次需要付费重跑；
   16 个付费完成批次保留。其余 9 个已取消大图 Kokkos 批次没有完整结果，若仍保留目标需补跑。
4. MPI 强扩展有未完成图/布局；7 个免费恢复作业已取消，没有结果。按矩阵审计逐项补跑。
5. 按核配平弱扩展 hub/controlled 尚缺；GPU 弱扩展已完成，不要重复。

所有主 CPU 性能作业用 Vanda 付费 CPU 队列/Platinum 节点，不能把 cpu_parallel 免费池结果混进
同硬件扩展曲线。先查自己的 hpc project 余额和项目资格，确认可用额度；每次只提交额度能覆盖的
小批次，walltime 参考已有同规模实测，并记录 job ID、队列、节点、实际 CPU 型号、编译器、
Release 构建、计时重复、正确性校验和 PBS 实际用时。PBS Exit 0 仍需同步结果并跑矩阵审计后
才能标记完成。不要共享密码，也不要尝试管理 hongxinran 账号的用户 hold 作业。

先给我一份准备提交的缺项/job 清单和额度估算；每批结束后同步数据、更新 retry_jobs.tsv、
pbs_job_usage.csv、进度文档，并重新运行两项审计。报告里只使用通过校验且布局/硬件记录一致的数据。
```

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
| 最新简明状态 | [`updated_vanda_new_account_run_20261107.md`](updated_vanda_new_account_run_20261107.md) |
| 阶段性性能结论 | [`updated_experimental_conclusions_20261105.md`](updated_experimental_conclusions_20261105.md) |

原提交账号上继续看作业可运行：

```bash
qstat -w -u hongxinran
hpc project
python3 scripts/check_vanda_progress.py 20261102T092147Z --missing
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/20261102T092147Z
```
