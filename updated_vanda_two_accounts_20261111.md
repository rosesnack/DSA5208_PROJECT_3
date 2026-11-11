# 两账号当前状态（Nov 11 20:46 SGT）

**本轮新增 562 项独立校验通过，固定图累计完成 16,103/20,700（77.8%），尚缺 4,597。** 新测量、计时、校验标记及硬件/布局记录已下载。主账号 20:46、分担账号 20:37 的查询均无 R/Q；详细矩阵、所有权及队友接手流程统一见 [Vanda handover](HANDOFF_VANDA_EXPERIMENTS_20261106.md)。

| 账号 | 当前状态 | 最近 CPU 余额 | 现有分配 |
|---|---|---:|---|
| xtt_ella | waiting_real_credits；无在途性能/校验 | 16.097 CPUh，余量 16 | 当前注册 149 组；继续负责全部 4,597 个固定图缺项 |
| hongxinran | no_eligible_unregistered_cells；无在途性能/校验 | 1,257.712 CPUh，余量 64 | 原两批 78 组、448/448 项全部通过，尚未接手新配置 |

主账号相比上次新增 66 组/566 项，其中 **65 组/562 项全部通过**。一组四项 `1538617`（controlled n100000/d16，四节点、每节点四核，总 16 核）墙钟超限 -29，实际 46:27、CPU 时间 0；尚未确定根因，未重复提交。加上此前 128 核失败组十项，共 14 项待处理。

| 固定图状态 | 配置数 |
|---|---:|
| validated | 16,103 |
| unsubmitted（仍归主账号） | 3,418 |
| performance_failed | 14 |
| held（当前 512 作业） | 5 |
| deferred_512（其他 512） | 1,160 |
| **合计** | **20,700** |

非 512 核缺 3,432（未提交 3,418＋失败 14）；全部 512 核缺 1,165，仍有五个有效完成配置。GPU 固定图全部完成：真实 GPU 450、同机 CPU 对照 1,215。弱扩展单列，controlled rank 曲线的 512 核端点六项仍须先核实远端证据。

主账号 8 个 H、hongxinran 70 个旧 H 均不是正在计算，不能批量释放。只有当前 512 性能 1532794/校验 1532795 对应完整清单的 held 五项，其余是已替代或此前延期的旧请求。

监控 PID 251391 / 155730，每 60 秒查询，提交截止 Nov 12 23:59 SGT。hongxinran 的余额已返还，但其原清单做完；若继续分担，先停止相关续投、从主账号真实源计划移除拟转交项、检查两边实时队列，再发布互斥新计划。**不能直接把未提交清单当作队友可领取任务。** 本轮仅核查、下载与更新文档，没有新增、释放或取消性能作业。

- [完整矩阵、状态及 future_owner](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)
- [当前登记的 227 个资源组及 job ID](results/updated_vanda_scaling/git_sync_20261111/submitted_core_groups.csv)
- [主账号队列及监控](results/updated_vanda_scaling/git_sync_20261111/queue_xtt_ella.json)
- [hongxinran 队列及监控](results/updated_vanda_scaling/git_sync_20261111/queue_hongxinran.json)
- [今晚新增 66 组的独立校验、退出状态与资源用时](results/updated_vanda_scaling/20261106T185006Z/monitor_recovery_20261110/account_progress_20261111.json)

余额以实时 hpc project 为准，不等同于实际用量；冻结清单不构成跨账号提交锁。
