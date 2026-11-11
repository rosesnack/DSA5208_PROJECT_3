# Vanda 实验交接（2026-11-11 复核版）

**这是当前唯一的执行交接入口。文件名沿用 Nov 6，当前归属已更新至 Nov 11 22:07 SGT。** 已把 **136 组/730 个尚缺配置**从 xtt_ella 的真实源计划移除，交给 hongxinran；现有有效结果没有重跑。首次免费预检只因多检查了未使用的辅助程序失败，修正后的免费预检 **1542434** 已 Exit 0；没有重测 Serial。

新计划总请求上限 **932 CPUh**，沿用单节点 20 分钟、两节点 30 分钟；只测付费性能，独立校验用免费。当前新登记 **52 组/246 项**，其中性能 R=3、Q=0、H=0、F=49；其余分担配置由后台监控分批续投。实际作业 ID、请求和观测时间见清单。

**未提交不代表无人负责。** 当前未完成固定图归属为 xtt_ella **3,867** 项、hongxinran **702** 项；队友仍须按下面流程完成所有权转交，不能从缺项 CSV 直接 qsub。两边未来计划和已登记配置均无交集。

## 1. 先分清状态与下一步

一个配置 = 图 × 实现/后端 × 节点/进程/线程布局 × 通信；五次计时重复不另乘数量。一个 PBS 资源组可包含多个配置。完整固定图目标 **20,700 = 原 19,980 + 后追加 720 个 512 核拆分**。

| 固定图状态 | 配置数 | 队友怎么处理 |
|---|---:|---|
| `validated` | **16,131** | 已校验，直接复用 |
| `running` | **10** | 跟踪原作业，不重复提交 |
| `queued` | **0** | 跟踪原作业，不重复提交 |
| `awaiting_validation` | **208** | 原测量结束，等校验或结果同步，不重复测量 |
| `performance_failed` | **14** | 由原账号检查失败及可复用部分 |
| `held` | **5** | 当前原 512 核组延期，不复制提交 |
| `unsubmitted` | **3,172** | 仍有明确 future_owner，先转交再提交 |
| `deferred_512` | **1,160** | 按原优先级延期 |
| **合计** | **20,700** | 已验证 16,131；其余 4,569 |

[全部 20,700 行状态及来源](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv) 是固定图逐配置依据。另有按状态拆出的 [完成](results/updated_vanda_scaling/git_sync_20261111/cells_validated.csv)、[未提交](results/updated_vanda_scaling/git_sync_20261111/cells_unsubmitted.csv)、[失败](results/updated_vanda_scaling/git_sync_20261111/cells_performance_failed.csv)、[暂挂](results/updated_vanda_scaling/git_sync_20261111/cells_held.csv)、[延期 512](results/updated_vanda_scaling/git_sync_20261111/cells_deferred_512.csv) 清单；均不能直接当提交计划。

CSV 中 `canonical_summary` 是跨账号匹配同一配置的唯一键。`assigned_account` 只表示当前注册表中已有作业的归属；旧完成结果可能为空，**不能据此判为未完成**。`future_owner` / `future_plan` 标出未完成配置的继续执行归属；`handoff_action` 给出动作；`submission_allowed_from_snapshot` 全部为 False。PBS 的 F/Exit 0 只代表作业退出，独立校验标记与摘要齐全才计入完成。

## 2. 完整固定图矩阵及完成情况

所有行都覆盖同一批 **45 张固定图**：原仓库 Google/uniform/hub 三图；uniform/hub/controlled 三张典型合成图；三个家族 × 顶点数 50k/100k/200k/400k × 平均出度 4/8/16 的 36 张网格图；三个家族各一张 12.8m 顶点大图。每张图本身固定、改变资源做强扩展。

记 n=节点数，r=每节点 ranks，p=n×r，T=每 rank 线程。CPU 性能每个配置 **C=p×T=请求 CPU 核数**。常规单节点最多 32 核，512 端点用 8×64 核。

| 实验 | 每张图的布局及通信 | 目标 | 已完成 | 尚缺 |
|---|---|---:|---:|---:|
| Serial CPU | n=1,p=1,T=1；无通信 | 45 | 45 | 0 |
| 单独 OpenMP CPU | n=1,p=1,T=1/2/4/8/16/32；无通信 | 270 | 270 | 0 |
| 单独 Kokkos OpenMP CPU | 同上，OpenMP 后端；无通信 | 270 | 270 | 0 |
| 纯 MPI CPU 常规 | n=1/2/4/8，r=1/2/4/8/16/32，T=1；每布局两通信 | 2,160 | 1,966 | 194 |
| MPI+OpenMP CPU 常规 | 同 n、r，T=1/2/4/8/16/32，rT≤32；每布局两通信 | 7,560 | 6,966 | 594 |
| MPI+Kokkos OpenMP CPU 常规 | 与 MPI+OpenMP 同一套布局；每布局两通信 | 7,560 | 4,944 | 2,616 |
| 原 CPU 512 核端点 | 纯 MPI p512,T1；两混合方法各 p512,T1 和 p128,T4；每布局两通信 | 450 | 5 | 445 |
| 后追加 CPU 512 核拆分 | 两混合方法各 T=2/8/16/32，p=512/T；每布局两通信 | 720 | 0 | 720 |
| GPU 节点完整配对区块 | 下表，包含真实 GPU 计算及同机 CPU 对照 | 1,665 | 1,665 | 0 |
| **固定图合计** | | **20,700** | **16,131** | **4,597** |

两通信是 Allgatherv（参数 `allgather`）与 Halo。单独方法没有 MPI，不扩展通信维度。

| GPU 节点区块 | 配置（45 图各自都跑） | 目标/完成 |
|---|---|---:|
| 单独 CUDA / Kokkos CUDA | n=1，1 A40；各 45 | 90/90 |
| MPI+CUDA / MPI+Kokkos CUDA | n=p=1/2，每节点 1 rank、1 A40；各布局两通信 | 360/360 |
| 同 GPU 节点的 Serial / OpenMP CPU 对照 | Serial 1 核；OpenMP T=1/2/4/8/16/32 | 315/315 |
| 同 GPU 节点的纯 MPI / MPI+OpenMP CPU 对照 | n=p=1/2，纯 MPI T1，混合 T=1/2/4/8；两通信 | 900/900 |

真实 GPU 计算共 **450/450**，GPU 节点 CPU 对照 **1,215/1,215**；CPU 对照不称为“纯 MPI GPU 计算”。4/8 GPU 已取消，不在缺项内。Kokkos 按 OpenMP/CUDA 两个后端分别计数。线程范围不含 T64。

固定总核数主线：C=32/64/128/256 分别用 n=1/2/4/8；C512 用 n8。混合方法每个 C 都有 T=1/2/4/8/16/32、p=C/T 的六拆分，纯 MPI p=C,T1；1/2/4/8/16 核只取满足 p≥n、p 可均分到节点的合法拆分。原矩阵还包含同 C 的其他节点布局。[逐核心主线覆盖](results/updated_vanda_scaling/git_sync_20261111/cpu_core_layouts.csv) 与 [范围解释](updated_cpu_layout_coverage_20261111.md) 可直接核对。

## 3. 弱扩展另列，不能遗漏或照旧指令重跑

弱扩展使用三个合成家族，独立于 45 张固定图；不计入 20,700 分母。保持每 rank 或每 CPU 核的顶点/边量，随资源增加图规模。[逐项弱扩展证据清单](results/updated_vanda_scaling/git_sync_20261111/weak_experiment_manifest.csv) 单列结果根目录和校验标记。

| 弱扩展实验 | 布局与图规模规则 | 本地已验证证据/目标 | 交接动作 |
|---|---|---:|---|
| CPU 按 rank 常规曲线 | 每 rank 50k 顶点、800k 边；纯 MPI/Kokkos T1 p=1…256 的 2 次幂；Hybrid T4 p=1…64；两通信 | 150/150 | 复用 |
| CPU 按 rank 512 核端点 | 纯 MPI/Kokkos T1 p512；Hybrid p128,T4；三个家族、两通信 | 12/18 | uniform、hub 已齐；controlled 六项先查远端与旧 H，不能直接认定从未运行 |
| CPU 按核归一曲线 | 同 C 使用 weak_pC 图；Hybrid/Kokkos OpenMP 均 T4,p=C/4，C=4…512 的 2 次幂；两通信 | 96/96 | 复用 |
| GPU 节点弱扩展 | n=p=1/2、两通信及同机消融/CPU 对照 | 138/138 | 复用；其中真实 GPU 36 项 |

此表按本地可审阅摘要及独立完成标记统计。controlled 的六项状态为 `evidence_missing_verify_remote_first`，不把“未找到本地证据”写成“已经失败”或“从未提交”；核实远端已保存测量、校验和旧作业后再决定接手动作。这六项尚未分派给新队友，也不在固定图 4,597 缺项里。

## 4. 两账号当前负责什么

| 账号 | 当前登记和动作 | 继续负责的固定图缺项 |
|---|---|---:|
| xtt_ella | 149 组；wait_real_credits；已移除这次转交的 730 项 | 3,867 |
| hongxinran | 原 78 组/448 项全部完成；新增登记 52 组/246 项；新计划共 136 组/730 项 | 702 |

两个监控每 60 秒查询，新 PID **765730 / 765579**，截止 Nov 12 23:59 SGT。最多六个在途性能组；主账号最高 256 核、分担账号上限 128 核，本次实际申请为 1/2 节点、总 1–32 核，每个配置 p×T 等于请求核数。原 20/30 分钟墙钟不缩短。本批总预留 932 CPUh，按交接前余额 1,257.712 CPUh 计算仍保留 325.712；监控另留 64 CPUh，实际可提交量以实时余额为准。

当前剩余任务已取消固定主机绑定，交由 PBS 在 `node_pool=cpu_node, switch=ccid-10` 内分配；核数、线程、内存和墙钟不变。免费两节点预检 **1542730** 使用与性能任务相同的 TCP/OpenMPI 配置成功，计算前与独立发布前均检查 Platinum 8452Y。详见 [本次排队修复](updated_vanda_queue_recovery_20261111.md)。 新的主机分配由调度器决定，实际节点仍由 cpu_hosts 和 affinity 记录，不把 Q 当作测量结果。

| 账号 | 项目目录 | 当前源计划（相对于项目根目录） |
|---|---|---|
| xtt_ella / personal-xtt_ella | `/scratch/xtt_ella/DSA5208_PROJECT_3_20261107` | `results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_xtt_ella_20261111_phase3.json` |
| hongxinran / personal-hongxinran | `/scratch/hongxinran/DSA5208_PROJECT_3_assist_20261111` | `results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261111_phase3.json` |

[实际登记的 279 个资源组及作业 ID](results/updated_vanda_scaling/git_sync_20261111/submitted_core_groups.csv) 与 [主队列快照](results/updated_vanda_scaling/git_sync_20261111/queue_xtt_ella.json)、[分担队列快照](results/updated_vanda_scaling/git_sync_20261111/queue_hongxinran.json) 分开列出“注册组”和“PBS 作业”。一个资源组的性能、免费校验是两个 job，不能重复当两组实验。

**旧 H 不能直接释放。** 两边原有 78 个旧 H job：主账号 8、hongxinran 70。其中只有当前 512 组的性能 `1532794` 与依赖校验 `1532795` 对应上表 `held` 的 5 项；主账号另 6 个是已被成功补跑替代的旧性能/校验。hongxinran 的 70 个是此前延期的旧请求，可能与新计划或缺项重叠，不能称它们“70 个待领取实验”，也不能称为“全部完成”。继续保留旧请求暂挂；本批转交时已核对目标并保持旧请求延期，禁止批量 qrls。新增免费校验的依赖 H 会在相应性能成功后自动解除，不等同于这些旧 H。`u` 是用户暂挂，`s` 是系统暂挂，`d` 是依赖暂挂；H 不会自动等同于 Q。

尚未补成功的常规失败组之一为 `1537511`：controlled n400000/d4，n4×32=128 核，Kokkos T=2/4/8/16/32 × 两通信，共 10 项。原 45 分钟、上限 96 CPUh，退出 -29，日志停在 MPI 分配信息采集、CPU 时间为零；先排查启动与部分输出，不据此缩短墙钟或认定算法很慢。

新增失败组 `1538617`：controlled n100000/d16，n4×4=16 核，Kokkos OpenMP 四项；45 分钟墙钟超限 -29，实际 46:27、CPU 时间 0。实际节点 CN-148/151/153/154。尚未定位原因，未盲目重投。这四项与原 128 核十项合计 14 项，不计完成。

此前 66 组新结果中 562 项已通过并同步。本次新增的 730 项只改变后续执行归属，已完成结果仍复用；新完成项以摘要和独立校验标记同步后再纳入严格审计。

## 5. 防重复接手流程（必须先做，再提交）

当前两个账号**已登记配置交集为零、未来源计划交集为零**；全部 4,597 个固定图缺项都有明确归属。这个结论针对快照，不能代替未来转交。

1. 队友先读取本文件与完整 CSV，只拟定要接手的 `canonical_summary` 集合；不从历史 handover、旧宽计划或剩余 CSV 直接 qsub。已验证、R/Q、待检、H、延期和失败各按上文处理。
2. 由原账号负责人协调暂停相关自动续投：在对应 `monitor_recovery_20261110/` 或 `monitor_assist_20261111/` **状态目录**创建 `STOP_AUTO_SUBMIT`，等待监控退出，并核对是否已有正在执行的提交。它只停止后续提交，不取消 PBS 作业。不要在队友目录创建一个 STOP 就以为停掉了原账号。
3. 两个原账号刷新 qstat、注册表、独立校验标记和源计划。对拟转交配置检查完整结果、已保存部分测量及旧 H。已完成直接复用；已在途或等待校验继续原作业。已 H 的同目标请求先由原负责人明确处理，不能留着以后又意外释放。
4. 从**原账号真实源计划**移除拟转交配置，保存原/新计划与转交记录；生成队友只含这些剩余配置的新计划。按 `canonical_summary` 断言新计划与原账号未来计划及未结束作业均无交集，并记录新 owner、项目、RUN_ID、交接时间。仅修改本地 CSV 不会阻止远端监控。
5. 新账号免费完成必要的构建/环境验证，复用有效图与 Serial 参考；不重做已有 Serial 性能。跨账号目录权限不同，按授权复制必要数据或免费重建，不能假设可直接访问他人 scratch。配置 paid 项目及足够余额，保持同硬件、编译器、计时和布局口径。
6. 新计划先 dry-run，核对每个配置 p×T=申请核数、去重、预算、墙钟及免费校验依赖后再正式提交，立即记录 job ID。把队友结果根目录纳入合并审计，更新本交接文档与 Git；最后恢复不重叠的原监控。

**提交器的去重只读取本 RUN_ID 注册表/完成标记，不是跨账号全局锁。** 新建 RUN_ID 后直接运行旧宽计划，会重复跑已完成或别人的配置。冻结的缺项 CSV、分区脚本或这份 Git 提交本身都不构成原子领取。不要同时启两个相同计划的监控。

付费队列只测核心性能；构建、图处理、独立校验、汇总与发布用免费队列。正式 CPU 对照保持 Platinum 8452Y；GPU 保持 A40；Release、GCC 13.3/OpenMPI 4.1.8、1 次预热/5 次计时/中位数及原 `solve_s` 等指标。不能把已剔除的免费混合硬件或错误布局结果重新加入性能表。保留原始 Git 旧结果，不覆盖原口径。

## 6. 只读检查与重新导出

在各账号自己的 Vanda 登录窗口运行（不会提交/释放作业）：

```bash
qstat -u "$USER"
hpc project
# 若额度查询提示先认证，运行 amgr login；密码只在终端输入。
```

主账号在其项目目录查看 `results/updated_vanda_scaling/20261106T185006Z/monitor_recovery_20261110/auto_monitor_status.json`；分担账号查看 `results/updated_vanda_scaling/20261111_hongxinran_assist/monitor_assist_20261111/auto_monitor_status.json`。状态中的 `eligible_unregistered_cells` 是自己计划的缺口，不是全项目完成数。

在已同步三个结果根目录的本地仓库可只读复核固定图目标：

```bash
python3 scripts/audit_fixed_matrix.py vanda \
  results/updated_vanda_scaling/20261106T185006Z \
  --reuse-root results/updated_vanda_scaling/20261102T092147Z \
  --reuse-root results/updated_vanda_scaling/20261111_hongxinran_assist \
  --include-additional-512
```

完整导出命令见 [快照再生成说明](results/updated_vanda_scaling/git_sync_20261111/README.md)。不带 `--include-additional-512` 时审计是原 19,980 口径；不能漏掉新增 720。本地审计不包含尚未同步的远端新完成结果。

## 7. 可以直接给队友的参考 prompt

> 请接手这个仓库的 Vanda 实验。先读 HANDOFF_VANDA_EXPERIMENTS_20261106.md 和 git_sync_20261111 下完整固定图、弱扩展、资源组及 ownership 清单。先只做只读核对，向原负责人取得明确转交的 canonical_summary 配置与新源计划；当前 unsubmitted 分属 xtt_ella 与 hongxinran 的互斥自动续跑计划，必须先读 future_owner，不能直接提交。严格复用已校验结果，不重跑 Serial/GPU 等完整部分；在途、待校验和 H 不重复提交；失败先查可复用部分，controlled 的 rank 弱扩展 512 端点先核实远端证据。暂停/移除原账号真实续跑计划中的拟接手项，核对实时两边队列及旧 H，确认所有权互斥后再 dry-run、提交和登记 job ID。优先非 512 核；正式性能用付费、构建处理校验用免费，p×T 等于请求核数，保持既有硬件/编译/五次重复/指标口径。不要直接套旧宽计划或新 RUN_ID 重跑全矩阵。每次更新已完成、已提交、未提交和交接归属并同步 Git。

此前堆叠的旧 handover、双账号状态及 Nov 8 提交计划已移至 [历史目录](docs/history/)。里面的旧“最新”状态、旧免费性能命令与旧提交范围只作追溯，不作为当前操作说明。
