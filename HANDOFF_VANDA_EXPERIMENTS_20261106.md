# Vanda 实验交接（2026-11-13 15:32 SGT）

这是当前唯一执行交接入口。

**截至 2026-11-13 15:32 SGT，严格完成 18,997/20,700（91.8%），今天新增 192 项通过独立校验。** 两账号额度查询已恢复，主账号又自动提交三个 128 核组（1551771、1551773、1551775），覆盖 24 项缺口。新增提交不计入完成数。

| 账号 | 今天已登记组/配置 | 今天新增校验通过 | 快照中性能 R/Q | 额度显示余额（CPUh） |
|---|---:|---:|---|---:|
| xtt_ella | 51 / 442 | 118 | 0运行、35排队 | 4,715.066 |
| hongxinran | 18 / 130 | 74 | 0运行、4排队 | 635.875 |
| 合计 | 69 / 572 | **192** | **0运行、39排队** | 分属两个项目 |

这些是 15:32 的冻结快照。部分普通组约半分钟就结束，一分钟轮询可能看到运行数为零；完成结果持续增加。今天已结束的性能作业未发现新增失败。余额不是可再次提交的额度：还须扣除现有 Q/R 的预留及留量，主账号此刻仅余约 107.066 CPUh 可再预留。

排队还发现并修复了一处节点选择问题：此前按单个 NUMA vnode 判断空闲核，漏掉同一物理节点上 4+4 核可合并满足 8 核的情况。两个原有 64 核、八节点作业改绑后分别 32/29 秒退出0，各六项结果均通过独立校验。两边监控已经部署按物理节点汇总资源的修复，并实际自动改绑15次；核数、物理节点数、p/T、内存、墙钟及测量口径均保留。[修复与分配证据](updated_vanda_numa_placement_20261113.md)。

远端监控每60秒检查，至 Nov 13 23:59 SGT；主/分担账号允许在途上限64/32。现有排队请求的放置刷新在额度认证检查之前执行，认证过期仍可推进已提交任务；新增请求需认证有效且有真实余额。不重复已完成、在途或待校验配置，512核继续延期。

固定图状态为：已验证18,997、排队368、待独立校验12、历史失败102、暂挂5、延期512核1,160、未提交56，共20,700。当前已测待检及排队380项若全部成功，可达到 **19,377/20,700**；届时仍缺 **1,323**：512核1,165、历史失败102、内存前置条件阻塞12，以及尚未获额度覆盖的两个大图128核组44项。最后两组按现有墙钟共需1,056 CPUh预留，监控等待真实返还后再尝试。

两个账号当前登记与未来源计划交集均为零。上述数字是快照，队友不能把未提交清单直接当作提交许可；先按交接流程转移所有权。

## 1. 先分清状态与下一步

一个配置 = 图 × 实现/后端 × 节点/进程/线程布局 × 通信；五次计时重复不另乘数量。一个 PBS 资源组可包含多个配置。完整固定图目标 **20,700 = 原 19,980 + 后追加 720 个 512 核拆分**。

| 固定图状态 | 配置数 | 下一步 |
|---|---:|---|
| `validated` | **18,997** | 复用，不重跑 |
| `running` | **0** | 跟踪原作业 |
| `queued` | **368** | 等PBS调度，不复制提交 |
| `awaiting_validation` | **12** | 等免费校验/同步，不重测 |
| `performance_failed` | **102** | 先查失败及部分输出 |
| `held` | **5** | 原512组延期 |
| `unsubmitted` | **56** | 按future_owner和真实余额续投 |
| `deferred_512` | **1,160** | 延期，先补普通核数 |
| **合计** | **20,700** | 已验证18,997，剩余1,703 |

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
| 纯 MPI CPU 常规 | n=1/2/4/8，r=1/2/4/8/16/32，T=1；每布局两通信 | 2,160 | 2,124 | 36 |
| MPI+OpenMP CPU 常规 | 同 n、r，T=1/2/4/8/16/32，rT≤32；每布局两通信 | 7,560 | 7,450 | 110 |
| MPI+Kokkos OpenMP CPU 常规 | 与 MPI+OpenMP 同一套布局；每布局两通信 | 7,560 | 7,168 | 392 |
| 原 CPU 512 核端点 | 纯 MPI p512,T1；两混合方法各 p512,T1 和 p128,T4；每布局两通信 | 450 | 5 | 445 |
| 后追加 CPU 512 核拆分 | 两混合方法各 T=2/8/16/32，p=512/T；每布局两通信 | 720 | 0 | 720 |
| GPU 节点完整配对区块 | 下表，包含真实 GPU 计算及同机 CPU 对照 | 1,665 | 1,665 | 0 |
| **固定图合计** |  | **20,700** | 18,997 | 1,703 |

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

此表按本地可审阅摘要及独立完成标记统计。controlled 的六项状态为 `evidence_missing_verify_remote_first`，不把“未找到本地证据”写成“已经失败”或“从未提交”；核实远端已保存测量、校验和旧作业后再决定接手动作。这六项尚未分派给新队友，也独立于固定图缺项。

## 4. 当前资源、失败和分工

当前统计与余额见本文开头和[两账号快照](updated_vanda_two_accounts_20261111.md)。自动节点刷新、物理节点汇总与部署证据见[调度修复](updated_vanda_numa_placement_20261113.md)。监控启用 `--placement-hosts`；改绑只改变Q请求的host，保留p×T=C与原资源。已有Q的刷新不依赖额度认证，新增qsub仍受余额及认证约束。

以下保留此前依赖修复过程供追溯；当前在途上限和有效job以本节及最新快照为准。

主账号续投时引用了已被 PBS 清理的历史依赖 1530741，53 组/486 项请求在启动前被取消：无 stime、CPU 资源用量或 Exit_status，余额保持不变。已把这批请求及原计划单独归档，从有效注册表移出；只重新提交其从未计算的配置，不删除历史证据。新的免费输入检查 **1550012** 已通过，未重跑 Serial 性能或重新构建；提交器增加当前 PBS 依赖检查，防止再次仅凭历史缓存成功状态续投。

大图新请求墙钟按“同图成功批次最慢用时 ×3 +30 分钟，向上取整 15 分钟”：uniform **2:30**、controlled **3:45**、hub **4:30**；普通八节点组保留一小时。依据来自 49 个历史成功批次（以证据文件为准），最慢约 79 分钟。只改尚未登记的新请求，核数、节点、线程、五次重复和计时指标不变；低内存已知失败前置条件保留。

- [唯一执行 handover 与完整矩阵](HANDOFF_VANDA_EXPERIMENTS_20261106.md)
- [130 项互斥分担及预算](results/updated_vanda_scaling/account_partition_20261113_refund/account_partition.json)
- [墙钟依据与每个修改前后的上限](results/updated_vanda_scaling/account_partition_20261113_refund/walltime_evidence.json)
- [启动前取消请求的诊断、归档和恢复](results/updated_vanda_scaling/20261106T185006Z/dependency_repair_20261113.json)
- [逐配置状态、来源和归属](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)

新有效请求使用当前检查依赖，不能释放或重用已归档的旧依赖取消请求。取消前未进入计算节点的 53 组不计入下文历史 102 个性能失败配置。旧 H 保持原延期和防重复规则。输入/校验全部免费，正式性能全部付费。

原失败的 1537511（10项）、1538617（4项）以及零产出启动 1543209/1543315/1543317（共52项）没有盲目重投。新增六个大图组详见 [失败记录](results/updated_vanda_scaling/20261106T185006Z/large_graph_failures_20261112.json)：一核/节点、每节点 6GB 时 Kokkos 被 signal 9 杀死，36 个目标中有 18 项完整测量保留，尚未独立校验。内存上限为主要嫌疑，不宣称已确诊。另两个未提交的 strong_controlled/hub n8/C8 组共 12 项有明确内存验证前置条件，不能强行提交。失败和资源阻塞没有从分母剔除。

旧 H 保留原延期；其中 512 组 1532794/1532795 对应五个 held 配置，其他旧 H 可能与新计划/成功结果重叠，不能批量 qrls。新增校验依赖 H 会随性能成功自动解除，意义不同。

| 账号 | 目录 | 当前源计划 |
|---|---|---|
| xtt_ella | `/scratch/xtt_ella/DSA5208_PROJECT_3_20261107` | `results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_xtt_ella_20261113_refund.json` |
| hongxinran | `/scratch/hongxinran/DSA5208_PROJECT_3_assist_20261111` | `results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261113_refund.json` |

[实际资源组及 job ID](results/updated_vanda_scaling/git_sync_20261111/submitted_core_groups.csv)、[主账号快照](results/updated_vanda_scaling/git_sync_20261111/queue_xtt_ella.json)、[分担快照](results/updated_vanda_scaling/git_sync_20261111/queue_hongxinran.json) 有准确时间；未提交按 future_owner 分属两账号，队友须先按下文转交。

## 5. 防重复接手流程（必须先做，再提交）

当前两个账号**已登记配置交集为零、未来源计划交集为零**；全部 1,703 个固定图缺项都有明确归属。这个结论针对快照，不能代替未来转交。

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

续投查询已修正：预算快照使用 PBS 历史查询 `qstat -x`，避免小任务在 qselect 后结束导致查询报错。修正已部署两个账号，仅影响调度信息查询；五次重复、指标与原性能结果均不变。
