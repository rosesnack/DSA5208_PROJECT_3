# Vanda 实验交接（2026-11-11 复核版）

**这是当前唯一执行交接入口，状态更新至 11-11 23:53 SGT。** hongxinran 前三批 448+730+100=1,278 项均已独立校验通过并同步。 本批另转交 **64 组/306 项**，已从主账号远端真实源计划移除，跨账号实际登记与未来计划交集均为零。本批 64 组/306 项（四节点、总核数 8/16/32），实际已登记 42/64 组、174/306 项；性能状态 F=40, R=2。其中 138/306 项已独立校验并同步。

固定图严格完成 **17,321/20,700**，剩余 3,379；尚未完成归属 xtt_ella **3,211**、hongxinran **168**。这是本地已同步且独立校验的数量。未提交仍有负责人，队友不能直接领取缺项 CSV。

免费四节点准备 **1543299** 已通过，复用已有图与 Serial；没有重测 Serial 或重新构建。性能付费，准备/校验免费；全部 p×T=请求核数、同编译器、五次重复及原计时口径。当前细节见 [双账号状态](updated_vanda_two_accounts_20261111.md)。

## 1. 先分清状态与下一步

一个配置 = 图 × 实现/后端 × 节点/进程/线程布局 × 通信；五次计时重复不另乘数量。一个 PBS 资源组可包含多个配置。完整固定图目标 **20,700 = 原 19,980 + 后追加 720 个 512 核拆分**。

| 固定图状态 | 配置数 | 下一步 |
|---|---:|---|
| `validated` | **17,321** | 复用，不重跑 |
| `running` | **38** | 跟踪原作业 |
| `queued` | **86** | 等原作业，不复制提交 |
| `awaiting_validation` | **50** | 等独立校验或结果同步 |
| `performance_failed` | **66** | 原账号先查失败及部分输出 |
| `held` | **5** | 原 512 组延期 |
| `unsubmitted` | **1,974** | 按 future_owner 续投，队友接手先转交 |
| `deferred_512` | **1,160** | 原优先级延期 |
| **合计** | **20,700** | 已验证 17,321，剩余 3,379 |

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
| 纯 MPI CPU 常规 | n=1/2/4/8，r=1/2/4/8/16/32，T=1；每布局两通信 | 2,160 | 1,992 | 168 |
| MPI+OpenMP CPU 常规 | 同 n、r，T=1/2/4/8/16/32，rT≤32；每布局两通信 | 7,560 | 7,028 | 532 |
| MPI+Kokkos OpenMP CPU 常规 | 与 MPI+OpenMP 同一套布局；每布局两通信 | 7,560 | 6,046 | 1,514 |
| 原 CPU 512 核端点 | 纯 MPI p512,T1；两混合方法各 p512,T1 和 p128,T4；每布局两通信 | 450 | 5 | 445 |
| 后追加 CPU 512 核拆分 | 两混合方法各 T=2/8/16/32，p=512/T；每布局两通信 | 720 | 0 | 720 |
| GPU 节点完整配对区块 | 下表，包含真实 GPU 计算及同机 CPU 对照 | 1,665 | 1,665 | 0 |
| **固定图合计** | | **20,700** | **17,321** | **3,379** |

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

## 4. 两账号当前负责什么

| 账号 | 当前分工与登记 | 未完成固定图归属 |
|---|---|---:|
| xtt_ella | 189 个登记组；持续运行原大图；已移除新转交 306 项 | 3,211 |
| hongxinran | 原 1,278 项全部通过；本批 64 组/306 项（四节点、总核数 8/16/32），实际已登记 42/64 组、174/306 项；性能状态 F=40, R=2。其中 138/306 项已独立校验并同步。 | 168 |

监控 PID **3695677 / 3601173**，每 60 秒检查、最多六个在途性能组，截止 Nov 12 23:59 SGT。本次 306 项全部四节点、总核数 8/16/32，墙钟 45 分钟；原矩阵和 p×T=请求核数不变。转交前余额 1,234.94 CPUh，请求上限 1,092 CPUh，全额承诺后余 142.94，高于控制器 64 CPUh 余量。

后续未登记 CPU 组由调度器在 `node_pool=cpu_node:switch=ccid-10` 中选择物理主机。运行前与独立发布前均核对 Platinum 8452Y，并保存实际主机、affinity、进程与线程记录。已有运行组保持原作业。多个物理节点需同时可用，Q 不代表失败或已完成。

| 账号 | 项目目录 | 当前源计划（相对于项目根目录） |
|---|---|---|
| xtt_ella / personal-xtt_ella | `/scratch/xtt_ella/DSA5208_PROJECT_3_20261107` | `results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_xtt_ella_20261111_phase5.json` |
| hongxinran / personal-hongxinran | `/scratch/hongxinran/DSA5208_PROJECT_3_assist_20261111` | `results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261111_phase5.json` |

[实际登记的 483 个资源组及作业 ID](results/updated_vanda_scaling/git_sync_20261111/submitted_core_groups.csv) 包含付费性能与免费校验两个 job；不能重复算成两组实验。[主队列](results/updated_vanda_scaling/git_sync_20261111/queue_xtt_ella.json)、[分担队列](results/updated_vanda_scaling/git_sync_20261111/queue_hongxinran.json) 各有准确时间。

**旧 H 不能批量释放。** 原有 78 个旧 H job（主账号 8、分担 70）仍保持原延期，其中当前 512 组的 `1532794` 与依赖校验 `1532795` 对应 5 个 held 配置；其他旧请求可能已被替代或与计划重叠，不是可领取的新实验。新增免费校验的依赖 H 在性能成功后自动解除，含义不同。

失败先检查证据与部分输出，不能盲目重投。原 `1537511` 的 128 核十项与 `1538617` 的 16 核四项尚未成功。新 `1543209`、`1543315`、`1543317`因 MPI 主机信息采集卡住、持续 CPU 时间为零且无任何测量而停止以节约额度，日志及资源记录保留于各 `stalled_start_*_20261111.json`。没有把这些算成算法性能结果；后续源计划已改用已验证的 CPU 池。已登记失败仍归原账号，需明确处理旧注册后才能补跑，不由控制器自动重试。

## 5. 防重复接手流程（必须先做，再提交）

当前两个账号**已登记配置交集为零、未来源计划交集为零**；全部 3,379 个固定图缺项都有明确归属。这个结论针对快照，不能代替未来转交。

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

续投预算快照已改用 PBS 历史查询 `qstat -x`，避免小任务在 qselect 后结束导致查询报错。修正已部署两个账号，只影响调度查询，不改变五次重复、性能指标或既有结果。
