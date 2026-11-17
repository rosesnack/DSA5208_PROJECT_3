# Vanda 实验交接（2026-11-17）

这是当前唯一执行交接入口。

原固定矩阵与512注册表快照：**2026-11-17 02:32 SGT**。

新增归因研究：[57项集体通信策略／节点边界对照](docs/COLLECTIVE_CONTROLS_20261117.md) **57/57均完成并通过独立校验**，不属于下表缺项，不要重复提交。32/64/128/256核性能作业1576293/1576291/1576289/1576295及对应免费校验均Exit 0。另追加 **2项256核启动绑定配对**，已登记在hongxinran性能1577398、免费校验1577399中，17日17:46快照为Q/依赖H；也不要重复提交。原57行清单和追加2行清单分开保存，见研究说明；额外诊断不改变固定图分母。

- **非512固定图19,530/19,530项全部完成并通过独立校验**；非512弱扩展372项/对照也已齐。无需接手任何非512缺项。
- 额外诊断Google16项、256核Uniform/Hub/Controlled共18项全部完成校验。最后128核测试1569195与免费校验1569196均Exit0：五次计时中位数4.296756030秒，通信中位数4.122365467秒，Serial向量L1差为0。
- 报告按四部分组织，主矩阵完整；512只纳入5项已验证结果，单列512列和明细表，缺测用`-`。报告计时统一为**1次预热+5次正式计时的中位数**。
- **512仍缺1,165项：114项已登记在8个性能作业中，旧H5项保持延期，另1,046项尚未安排。** xtt_ella首组1569659 Q、后六组依赖1569660校验；hongxinran小组1569700 Q。当前2Q、6依赖H、0R；8个性能作业各有免费校验。
- 旧1560661/63/65及其依赖已取消，替换作业改用可写home输出；不再释放这些旧号。真实性能仍走付费batch_cpu，8节点×64核，p×T=512。两账号交接键无重叠。
- 两个限定范围监控每60秒检查已登记任务的主机绑定，截止**11月18日23:59 SGT**。没有无限监控或自动重试失败作业的承诺。新版未来源计划和两个键的归属转移见512说明。

[当前状态](docs/VANDA_STATUS.md)、[512限制与已登记计划](docs/VANDA_512.md)、[诊断与存储证据](docs/PERFORMANCE_INVESTIGATION.md)、[最终报告及数据](reports/non512/README.md)。原始记录保留；报告数据选择见`reports/non512/measurement_selection.json`，避免把同一配置的不同观测重复计数。

## 1. 先分清状态与下一步

一个配置 = 图 × 实现/后端 × 节点/进程/线程布局 × 通信；五次计时重复不另乘数量。一个 PBS 资源组可包含多个配置。完整固定图目标 **20,700 = 原 19,980 + 后追加 720 个 512 核拆分**。

| 固定图状态 | 配置数 | 下一步 |
|---|---:|---|
| validated | 19,535 | 含全部非512的19,530项；复用，不重跑 |
| awaiting_validation / running / unsubmitted / performance_failed | 0 | 非512已全部完成 |
| queued | 18 | xtt_ella首组16项+hongxinran两项 |
| held | 101 | xtt_ella后六组96项+旧512延期5项 |
| deferred_512 | 1,046 | 尚未安排 |
| **合计** | **20,700** | 尚缺1,165，全是512核 |

[全部 20,700 行状态及来源](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv) 是固定图逐配置依据。另有按状态拆出的 [完成](results/updated_vanda_scaling/git_sync_20261111/cells_validated.csv)、[未提交](results/updated_vanda_scaling/git_sync_20261111/cells_unsubmitted.csv)、[失败](results/updated_vanda_scaling/git_sync_20261111/cells_performance_failed.csv)、[暂挂](results/updated_vanda_scaling/git_sync_20261111/cells_held.csv)、[延期 512](results/updated_vanda_scaling/git_sync_20261111/cells_deferred_512.csv) 清单；均不能直接当提交计划。

CSV 中 `canonical_summary` 是跨账号匹配同一配置的唯一键。`assigned_account` 只表示当前注册表中已有作业的归属；旧完成结果可能为空，**不能据此判为未完成**。`future_owner` / `future_plan` 标出未完成配置的继续执行归属；`handoff_action` 给出动作；`submission_allowed_from_snapshot` 全部为 False。PBS 的 F/Exit 0 只代表作业退出，独立校验标记与摘要齐全才计入完成。

## 2. 完整固定图矩阵及完成情况

所有行都覆盖同一批 **45 张固定图**：原仓库 Google/uniform/hub 三图；uniform/hub/controlled 三张典型合成图；三个家族 × 顶点数 50k/100k/200k/400k × 平均出度 4/8/16 的 36 张网格图；三个家族各一张 12.8m 顶点大图。每张图本身固定、改变资源做强扩展。

记 n=节点数，r=每节点 ranks，p=n×r，T=每 rank 线程。CPU 活跃并行度定义为 **C=p×T**。新性能提交要求请求核数与此相等；历史批次中较大的预留资源不计作更高并行度。常规单节点最多 32 核，512 端点用 8×64 核。

| 实验 | 每张图的布局及通信 | 目标 | 已完成 | 尚缺 |
|---|---|---:|---:|---:|
| Serial CPU | n=1,p=1,T=1；无通信 | 45 | 45 | 0 |
| 单独 OpenMP CPU | n=1,p=1,T=1/2/4/8/16/32；无通信 | 270 | 270 | 0 |
| 单独 Kokkos OpenMP CPU | 同上，OpenMP 后端；无通信 | 270 | 270 | 0 |
| 纯 MPI CPU 常规 | n=1/2/4/8，r=1/2/4/8/16/32，T=1；每布局两通信 | 2,160 | 2,160 | 0 |
| MPI+OpenMP CPU 常规 | 同 n、r，T=1/2/4/8/16/32，rT≤32；每布局两通信 | 7,560 | 7,560 | 0 |
| MPI+Kokkos OpenMP CPU 常规 | 与 MPI+OpenMP 同一套布局；每布局两通信 | 7,560 | 7,560 | 0 |
| 原 CPU 512 核端点 | 纯 MPI p512,T1；两混合方法各 p512,T1 和 p128,T4；每布局两通信 | 450 | 5 | 445 |
| 后追加 CPU 512 核拆分 | 两混合方法各 T=2/8/16/32，p=512/T；每布局两通信 | 720 | 0 | 720 |
| GPU 节点完整配对区块 | 下表，包含真实 GPU 计算及同机 CPU 对照 | 1,665 | 1,665 | 0 |
| **固定图合计** | | **20,700** | **19,535** | **1,165** |

两通信是 Allgatherv（参数 `allgather`）与 Halo。单独方法没有 MPI，不扩展通信维度。

| GPU 节点区块 | 配置（45 图各自都跑） | 目标/完成 |
|---|---|---:|
| 单独 CUDA / Kokkos CUDA | n=1，1 A40；各 45 | 90/90 |
| MPI+CUDA / MPI+Kokkos CUDA | n=p=1/2，每节点 1 rank、1 A40；各布局两通信 | 360/360 |
| 同 GPU 节点的 Serial / OpenMP CPU 对照 | Serial 1 核；OpenMP T=1/2/4/8/16/32 | 315/315 |
| 同 GPU 节点的纯 MPI / MPI+OpenMP CPU 对照 | n=p=1/2，纯 MPI T1，混合 T=1/2/4/8；两通信 | 900/900 |

真实 GPU 计算共 **450/450**，GPU 节点 CPU 对照 **1,215/1,215**；CPU 对照不称为“纯 MPI GPU 计算”。4/8 GPU 已取消，不在缺项内。Kokkos 按 OpenMP/CUDA 两个后端分别计数。线程范围不含 T64。

固定总核数主线：C=32/64/128/256 分别用 n=1/2/4/8；C512 用 n8。混合方法每个 C 都有 T=1/2/4/8/16/32、p=C/T 的六拆分，纯 MPI p=C,T1；1/2/4/8/16 核只取满足 p≥n、p 可均分到节点的合法拆分。原矩阵还包含同 C 的其他节点布局。[逐核心主线覆盖](results/updated_vanda_scaling/git_sync_20261111/cpu_core_layouts.csv) 与 [报告方法](reports/non512/report.md) 可直接核对。

## 3. 弱扩展另列，不能遗漏或照旧指令重跑

弱扩展使用三个合成家族，独立于 45 张固定图；不计入 20,700 分母。保持每 rank 或每 CPU 核的顶点/边量，随资源增加图规模。[逐项弱扩展证据清单](results/updated_vanda_scaling/git_sync_20261111/weak_experiment_manifest.csv) 单列结果根目录和校验标记。

| 弱扩展实验 | 布局与图规模规则 | 本地已验证证据/目标 | 交接动作 |
|---|---|---:|---|
| CPU 按 rank 常规曲线 | 每 rank 50k 顶点、800k 边；纯 MPI/Kokkos T1 p=1…256 的 2 次幂；Hybrid T4 p=1…64；两通信 | 150/150 | 复用 |
| CPU 按 rank 512 核端点 | 纯 MPI/Kokkos T1 p512；Hybrid p128,T4；三个家族、两通信 | 12/18 | uniform、hub 已齐；controlled 六项先查远端与旧 H，不能直接认定从未运行 |
| CPU 按核归一曲线 | 同 C 使用 weak_pC 图；Hybrid/Kokkos OpenMP 均 T4,p=C/4，C=4…512 的 2 次幂；两通信 | 96/96 | 复用 |
| GPU 节点弱扩展 | n=p=1/2、两通信及同机消融/CPU 对照 | 138/138 | 复用；其中真实 GPU 36 项 |

此表按本地可审阅摘要及独立完成标记统计。controlled 的六项状态为 `evidence_missing_verify_remote_first`，不把“未找到本地证据”写成“已经失败”或“从未提交”；核实远端已保存测量、校验和旧作业后再决定接手动作。这六项尚未分派给新队友，也独立于固定图缺项。

## 4. 当前剩余执行范围与结果复用

**非512固定图已全部结束，没有需要队友补跑的非512项。** 原测量复用、内存修复补测与独立免费校验均已收齐；细节保留在机器凭证中，不再把旧提交计划当作当前待办。

| 剩余任务 | 归属与状态（17日02:32快照） | 接手限制 |
|---|---|---|
| 八个512新/替换组，共114项 | xtt_ella七组112项；hongxinran一组2项；2Q+6依赖H | 已登记，不重复提交；作业号及免费校验见512说明 |
| 旧512组5项 | 1532794仍H | 先处理旧所有权、已保存测量与暂挂原因，不能直接释放或另投 |
| 其他512固定图1,046项 | 当前延期、未安排 | 取得明确逐项转交后才可接手 |
| controlled按rank弱扩展512端点6项 | 本地证据缺失 | 先查旧远端结果及旧H；不直接判定需要新跑 |

本轮114项均保持8节点×每节点64核，每项p×T=512。xtt_ella每组16项设墙钟1小时，hongxinran两项组设30分钟；保留MPI启动与亲和性检查的裕量。只用付费任务测核心性能，免费任务做存储验证、独立校验和数据处理。不更换队列，不把8×64改成另一布局或超额订阅。当前真实空闲量不足以立即分配64核/节点，所以仍在等待调度。详细预算、替换记录、依赖、归属和监控截止时间见 [512执行说明](docs/VANDA_512.md)。

可复用的普通结果保留原二进制、编译器、计时和校验凭证。12个低核MPI+Kokkos配置使用初始化内存修复版本：只释放分发后的冗余根边及已被Halo替代的源ID存储，测量循环不变，导出数据以compact_setup标记。该修复不是需要重跑所有旧结果的算法变化。

- [最后55项性能补测及任务ID](results/updated_vanda_scaling/storage_recovery_20261116/assist_transfer.json)
- [19项已保存测量复用](results/updated_vanda_scaling/storage_recovery_20261116/main_transfer.json)
- [非512报告、完整结果与审计](reports/non512/README.md)
- [512实时检查的保存凭证](results/updated_vanda_scaling/endpoint512_20261116/live_check.json)

## 5. 防重复接手流程（必须先做，再提交）

当前快照中的两账号已登记配置及未来计划互不重叠。仅剩1,165个固定图512缺项；48项在途、5项旧H、1,112项延期。这个结论不能代替未来转交时的实时去重。

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

> 请接手这个仓库的剩余Vanda实验。先读HANDOFF_VANDA_EXPERIMENTS_20261106.md、docs/VANDA_512.md及git_sync_20261111/experiment_manifest_20700.csv。非512固定图19,530项已全部完成独立校验，非512弱扩展372项及对照也齐全，全部复用，禁止重跑。固定图只剩1,165项512核目标：48项已登记在xtt_ella的1560661/63/65，5项在旧H，1,112项延期；这些数字是Nov16 14:21快照，先刷新两账号qstat、注册表与完成标记。controlled按rank弱扩展512的六项须先查远端证据。向原负责人取得明确canonical_summary集合和新源计划；暂停相关自动续投，移除原真实计划中的转交项，确认新计划与所有在途、已完成及其他未来计划无交集后再提交。正式性能用付费、构建处理校验用免费；保留Platinum8452Y、GCC13.3/OpenMPI4.1.8/Release、1次预热5次计时、原solve_s口径。512必须8节点×64核且p×T=512，依照已完成同类任务设置留有余量的墙钟，不为缩短排队改变节点布局或超额订阅。先dry-run、检查余额和最大墙钟预留，再提交登记ID。不得直接复制旧宽计划或另开RUN_ID重跑矩阵。更新完成/在途/缺项、所有权和Git。

旧日更Markdown已合并清理；历史解释可通过Git历史查阅，旧“最新状态”和旧提交命令不是当前操作依据。原始结果、脚本、机器计划和校验凭证全部保留。续投查询使用PBS历史查询qstat -x，避免短作业结束后查询消失；该修正只影响调度信息，不影响性能测量。
