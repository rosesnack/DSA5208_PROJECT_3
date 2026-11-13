> 本文是较早时刻的操作记录；当前15:32状态与新增结果见[两账号状态](updated_vanda_two_accounts_20261111.md)，物理节点放置修复见[修复记录](updated_vanda_numa_placement_20261113.md)。

# Vanda Nov 13 续跑记录（01:18 SGT）

> 本文件保留01:18恢复过程；最新队列及完成数见 [最新状态](updated_vanda_two_accounts_20261111.md) 和 [唯一handover](HANDOFF_VANDA_EXPERIMENTS_20261106.md)。

**已恢复 Nov 13 续投；严格完成仍为 18,805/20,700（90.8%），剩余 1,895。** 已完成结果沿用 Nov 12 22:10 SGT 同步证据，不因提交新请求增加完成数。当前队列快照是 Nov 13 01:18:01/01:18:05 SGT。

| 账号 | 当前登记资源组 | 付费性能 | 免费校验 R | 最近 CPUh 余额 | 固定图未完成归属 |
|---|---:|---|---:|---:|---:|
| xtt_ella | 293 | R=0，Q=12 | 0 | 5330.406 | 1,765 |
| hongxinran | 372 | R=0，Q=6 | 0 | 1212.818 | 130 |

额度已返还并可查询。两个原监控按 Nov 12 截止正常退出，现已恢复至 **Nov 13 23:59 SGT**，每 60 秒检查。主账号最多 12 个在途性能组、留 16 CPUh、先跑 ≤256 核；分担账号最多六组、留 64 CPUh、最大 128 核。付费只测核心性能，输入检查、构建处理和独立校验免费。

今天从主账号真实源计划互斥转交 **18 组/130 项**给 hongxinran，预留上限 **1,120 CPUh**；首批已提交六组/60项，其余 70 项仍由该账号自动续投。原分担的 1,810 项全部有效完成；不是把已完成范围拿来重跑。主账号首批有效提交 **12 组/70 项**。合计 **18 个有效性能作业、130 项配置排队，当前 R=0**；PBS 提示指定节点资源不足，不能把排队描述为已运行。免费校验依赖 H 在性能成功后自动解除。

当前未完成状态：`{'validated': 18805, 'deferred_512': 1160, 'queued': 130, 'unsubmitted': 498, 'held': 5, 'performance_failed': 102}`。未完成归属为 `xtt_ella=1,765`、`hongxinran=130`；两账号当前登记配置交集及未来计划交集均为零。新真实源计划为 `core_group_watch_plan_<账号>_20261113_refund.json`。普通缺项优先，512 核继续延期；旧 H 不批量释放，失败先查可复用部分。

主账号续投时引用了已被 PBS 清理的历史依赖 1530741，53 组/486 项请求在启动前被取消：无 stime、CPU 资源用量或 Exit_status，余额保持不变。已把这批请求及原计划单独归档，从有效注册表移出；只重新提交其从未计算的配置，不删除历史证据。新的免费输入检查 **1550012** 已通过，未重跑 Serial 性能或重新构建；提交器增加当前 PBS 依赖检查，防止再次仅凭历史缓存成功状态续投。

大图新请求墙钟按“同图成功批次最慢用时 ×3 +30 分钟，向上取整 15 分钟”：uniform **2:30**、controlled **3:45**、hub **4:30**；普通八节点组保留一小时。依据来自 49 个历史成功批次（以证据文件为准），最慢约 79 分钟。只改尚未登记的新请求，核数、节点、线程、五次重复和计时指标不变；低内存已知失败前置条件保留。

- [唯一执行 handover 与完整矩阵](HANDOFF_VANDA_EXPERIMENTS_20261106.md)
- [130 项互斥分担及预算](results/updated_vanda_scaling/account_partition_20261113_refund/account_partition.json)
- [墙钟依据与每个修改前后的上限](results/updated_vanda_scaling/account_partition_20261113_refund/walltime_evidence.json)
- [启动前取消请求的诊断、归档和恢复](results/updated_vanda_scaling/20261106T185006Z/dependency_repair_20261113.json)
- [逐配置状态、来源和归属](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)

有效性能注册表仍是各 RUN_ID 的 core_group_jobs.tsv。dependency_cancelled_jobs_20261113.tsv、dependency_registry_before_repair_20261113.tsv 和 dependency_cancelled_plans_20261113/ 只保留启动前取消记录，不是当前有效分派，不计新增实验或完成数。53 个请求均通过 PBS 历史逐项确认未启动后才允许恢复其缺项。初次主账号免费输入检查缺少部署脚本，耗时一秒、费用为零；补齐脚本后的新预检退出 0。

当前空闲的已验证 CPU 节点不足以同时满足八个物理节点，保留完整节点与核数请求排队，没有换混合硬件、降低并行度或借用免费队列跑性能。正式 CPU 型号仍为 Platinum 8452Y；真实主机与 affinity 在计算开始后留档。
