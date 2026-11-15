# Vanda 实验交接（2026-11-15 00:56 SGT）

这是当前唯一执行交接入口。

**严格完成19,377/20,700（93.6%）。全部非512缺项都已有执行安排。** 此前44项保留原作业，本轮另将114项拆成96项付费补跑和18项免费复用校验，未重跑任何已验证配置。

| 当前安排 | 配置数 | 作业/状态（Nov15 00:56快照） |
|---|---:|---|
| 此前两个大图128核组 | 44 | 1555661、1555663，Q |
| 新增网格补跑，5组 | 66 | 1555789/1555791/1555793/1555795/1555797，Q |
| 新增低核大图补跑，8组 | 30 | 1555773…1555787的奇数ID，依赖H |
| 复用完整旧测量，6组 | 18 | 免费校验1555761…1555766，Q |
| **非512尚待通过** | **158** | 已全部登记，不可复制提交 |

8个新大图组的H是等待免费内存检查1555753成功；不是用付费额度跑校验。当前该免费检查和免费复用校验的PBS注释出现 `Budgets: runjob ... Connection refused`，平台预算服务暂时阻止启动。主监控存活、每60秒重试；qalter也暂受该服务影响。已接收的作业不需要重新qsub。没有可用新候选时，监控现已跳过无意义的额度查询，不会仅为查看这些已有任务再要求amgr登录。

固定图快照：已验证19,377，Q为110，H为35（新依赖30项加旧512核5项），待复用校验18，512核延期1,160，未提交0、当前性能失败0。旧102项失败记录已归档，改由新任务或免费复用校验接手；零当前失败不代表历史失败被计为成功。

这些158项全部计算并校验通过后，将到 **19,535/20,700**，届时固定图只剩512核1,165项。弱扩展另列：非512证据已齐，rank-512仍有6项需先核实远端证据，不能和固定图分母混算。

## 1. 先分清状态与下一步

一个配置 = 图 × 实现/后端 × 节点/进程/线程布局 × 通信；五次计时重复不另乘数量。一个 PBS 资源组可包含多个配置。完整固定图目标 **20,700 = 原 19,980 + 后追加 720 个 512 核拆分**。

| 固定图状态 | 配置数 | 下一步 |
|---|---:|---|
| validated | 19,377 | 复用，不重跑 |
| queued | 110 | 跟踪已有任务 |
| held | 35 | 新内存依赖30项等待免费预检；旧512核5项延期 |
| awaiting_validation | 18 | 等免费独立校验，不重测 |
| deferred_512 | 1,160 | 延期 |
| unsubmitted / performance_failed / running | 0 | 历史失败见归档，不计为完成 |
| **合计** | **20,700** | 严格完成19,377，尚缺1,323 |

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
| 纯 MPI CPU 常规 | n=1/2/4/8，r=1/2/4/8/16/32，T=1；每布局两通信 | 2,160 | 2,136 | 24 |
| MPI+OpenMP CPU 常规 | 同 n、r，T=1/2/4/8/16/32，rT≤32；每布局两通信 | 7,560 | 7,504 | 56 |
| MPI+Kokkos OpenMP CPU 常规 | 与 MPI+OpenMP 同一套布局；每布局两通信 | 7,560 | 7,482 | 78 |
| 原 CPU 512 核端点 | 纯 MPI p512,T1；两混合方法各 p512,T1 和 p128,T4；每布局两通信 | 450 | 5 | 445 |
| 后追加 CPU 512 核拆分 | 两混合方法各 T=2/8/16/32，p=512/T；每布局两通信 | 720 | 0 | 720 |
| GPU 节点完整配对区块 | 下表，包含真实 GPU 计算及同机 CPU 对照 | 1,665 | 1,665 | 0 |
| **固定图合计** | | **20,700** | **19,377** | **1,323** |

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

## 4. 非512补跑的实际任务、资源和版本

| 图 | 节点×每节点核数 | 只补测项数 | 性能ID | 免费校验ID | 墙钟 |
|---|---|---:|---|---|---|
| strong_controlled | 1×1 | 5 | 1555773 | 1555774 | 03:45:00 |
| strong_hub | 1×1 | 5 | 1555775 | 1555776 | 04:30:00 |
| strong_controlled | 2×1 | 2 | 1555777 | 1555778 | 03:45:00 |
| strong_hub | 2×1 | 2 | 1555779 | 1555780 | 04:30:00 |
| strong_controlled | 4×1 | 2 | 1555781 | 1555782 | 03:45:00 |
| strong_hub | 4×1 | 2 | 1555783 | 1555784 | 04:30:00 |
| strong_controlled | 8×1 | 6 | 1555785 | 1555786 | 03:45:00 |
| strong_hub | 8×1 | 6 | 1555787 | 1555788 | 04:30:00 |
| grid_controlled_n100000_d16 | 4×4 | 4 | 1555789 | 1555790 | 01:00:00 |
| grid_controlled_n400000_d16 | 4×16 | 8 | 1555791 | 1555792 | 01:00:00 |
| grid_controlled_n200000_d16 | 8×16 | 22 | 1555793 | 1555794 | 01:00:00 |
| grid_controlled_n200000_d8 | 8×16 | 22 | 1555795 | 1555796 | 01:00:00 |
| grid_controlled_n400000_d4 | 4×32 | 10 | 1555797 | 1555798 | 01:00:00 |

以上13组共96项，正式性能均为付费batch_cpu，每项p×T=请求核数，物理节点数保持原矩阵。五个网格组墙钟1小时；controlled大图3:45、hub大图4:30，沿用同图成功批次保守估计，没有缩短时间抢额度。最大墙钟预留合计587.75 CPUh，其中网格464、大图123.75；实际消耗由真实运行时间决定。

| 图 | 原布局 | 复用项数 | 原测量作业 | 新免费校验ID |
|---|---|---:|---|---|
| strong_controlled | 1节点/1核 | 1 | 1543491 | 1555761 |
| strong_hub | 1节点/1核 | 1 | 1543493 | 1555762 |
| strong_controlled | 2节点/2核 | 4 | 1543508 | 1555763 |
| strong_hub | 2节点/2核 | 4 | 1543511 | 1555764 |
| strong_controlled | 4节点/4核 | 4 | 1543579 | 1555765 |
| strong_hub | 4节点/4核 | 4 | 1543592 | 1555766 |

以上18项已保存完整五次计时、一轮预热、排名和亲和性记录，只排cpu_serial免费独立校验。原整个批次后来失败，不影响先前已完整写出的单项测量；它们只有在这次独立校验通过后才计入完成。硬链接到新的cpu_reuse_20261115目录，保留原性能job ID、原CPU型号/映射和时间；原目录不覆盖。原11个失败资源组移入retired_failed_groups_20261115档案，旧不可成功解除的依赖校验才取消，未删除测量。

低核大图此前每节点6GiB时Kokkos被signal9终止。现增加默认关闭的CMake选项MPI_DEVICE_COMPACT_SETUP：MPI分发完只释放根节点已不用的in_sources副本，保留写输出所需的ID、offset和degree，在计时循环开始前执行。新构建build-vanda-memory-repair只用于本轮低核大图MPI+Kokkos；其他方法和所有旧二进制保留，GCC13.3/OpenMPI4.1.8/Release、五次计时、一次预热及solve_s中位数不变。summary用compact_setup=true标注该版本；它是初始化内存调整，报告需说明，不能宣称整个初始化版本完全相同。

免费1555731已证明原/新实现的小图完整排名和收敛历史一致。它初次RSS仪表只记录到MPI启动器，相关内存结论已撤销并归档；实际付费依赖改为1555753，在MPI rank内部测两个大图两种通信的真实峰值，要求给6GiB配额留出余量。该检查目前Q，尚未宣称真实峰值检查已通过，低核大图性能H会等它成功后才释放。所有预检输出均明确是校验数据，不纳入性能表。

五个网格旧失败都停在record_vanda_allocation，CPU用量为零；两个耗尽45分钟，其余启动被终止。补跑选择已验证Platinum8452Y的主机并排除隔离节点，同时只对实际发生过卡住的节点/亲和性探测设120秒上限；求解器仍由保守的PBS墙钟限制。校验标准未放宽。

额度查询认证再次过期后，提交器使用00:04真实核对余额4,955.473，先减去原44项全部1,056 CPUh墙钟成本得到3,899.473保守下界，再扣除所有当前Q/H/R/E和16CPUh留量后才提交。保留balance_floor证据，未把旧余额伪称实时余额，也未预支尚未到账退款；PBS项目端仍检查实际额度。本轮所有13个性能ID都已经返回并核对过原核数/节点数。服务器runjob预算服务的Connection refused现在会阻止免费和付费请求启动，属于当前平台阻塞。

- [完整本轮提交回执](results/updated_vanda_scaling/non512_recovery_20261115/submission.json)
- [实时核对与平台错误原文](results/updated_vanda_scaling/non512_recovery_20261115/live_verification.json)
- [原始失败诊断与18项完整测量](results/updated_vanda_scaling/non512_recovery_20261115/inspection.json)
- [保守预算计算](results/updated_vanda_scaling/non512_recovery_20261115/balance_floor.json)
- [退役失败组与原注册表](results/updated_vanda_scaling/20261106T185006Z/retired_failed_groups_20261115/retired_rows.json)

所有114项继续归xtt_ella，hongxinran本轮130项已完成且无待补候选。两边当前注册表和未来计划交集为零。旧512核H维持延期，不能批量qrls。单独CUDA/KokkosCUDA及GPU节点配对和非512弱扩展不重跑。

## 5. 防重复接手流程（必须先做，再提交）

当前两个账号**已登记配置交集为零、未来源计划交集为零**；全部1,323个固定图缺项都有明确归属。这个结论针对快照，不能代替未来转交。

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

> 请接手这个仓库的 Vanda 实验。先读 HANDOFF_VANDA_EXPERIMENTS_20261106.md 和 git_sync_20261111 下完整固定图、弱扩展、资源组及 ownership 清单。先只做只读核对，向原负责人取得明确转交的 canonical_summary 配置与新源计划；当前非512缺项都已登记已有任务，unsubmitted为零；需要先读future_owner并核实已有作业，不能另开RUN_ID复制提交。严格复用已校验结果，不重跑 Serial/GPU 等完整部分；在途、待校验和 H 不重复提交；失败先查可复用部分，controlled 的 rank 弱扩展 512 端点先核实远端证据。暂停/移除原账号真实续跑计划中的拟接手项，核对实时两边队列及旧 H，确认所有权互斥后再 dry-run、提交和登记 job ID。优先非 512 核；正式性能用付费、构建处理校验用免费，p×T 等于请求核数，保持既有硬件/编译/五次重复/指标口径。不要直接套旧宽计划或新 RUN_ID 重跑全矩阵。每次更新已完成、已提交、未提交和交接归属并同步 Git。

此前堆叠的旧 handover、双账号状态及 Nov 8 提交计划已移至 [历史目录](docs/history/)。里面的旧“最新”状态、旧免费性能命令与旧提交范围只作追溯，不作为当前操作说明。

续投查询已修正：预算快照使用 PBS 历史查询 `qstat -x`，避免小任务在 qselect 后结束导致查询报错。修正已部署两个账号，仅影响调度信息查询；五次重复、指标与原性能结果均不变。
