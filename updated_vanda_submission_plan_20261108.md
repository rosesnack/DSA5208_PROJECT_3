# 当前剩余提交范围（Nov 11 复核，沿用 Nov 8 文件名）

执行交接统一以 [HANDOFF_VANDA_EXPERIMENTS_20261106.md](HANDOFF_VANDA_EXPERIMENTS_20261106.md) 为准。原 Nov 8 请求与当时预算保存在 [历史原文](docs/history/updated_vanda_submission_plan_20261108_before_handoff_review_20261111.md)，里面的旧“正在运行”与未完成数不再适用。

| 当前固定图状态 | 配置数 | 所有权与动作 |
|---|---:|---|
| 严格完成 | 16,103 | 复用 |
| 非 512 尚无当前有效登记 | 3,418 | xtt_ella 活跃计划；转交前队友不得提交 |
| 非 512 失败 | 14 | xtt_ella，128 核组 1537511＋16 核组 1538617；先排查后补缺项 |
| 当前登记 512 暂挂 | 5 | 原性能 1532794、免费校验 1532795；延期 |
| 其他延期 512 | 1,160 | xtt_ella；含后追加 720，不自行取消目标 |
| **总计** | **20,700** | 尚缺 4,597；两账号 20:46 均无 R/Q |

hongxinran 两批 448 项全部通过，其余未完成项没有自动转交给它或新队友。主计划每 60 秒根据实际余额续投非 512，优先完成常规曲线；主账号余额仅 16.097 CPUh，留余量后无法再提交正常请求。hongxinran 已返还到 1,257.712 CPUh，但原 448 项分配已做完，尚未接手新的互斥清单。不得为了余额硬缩墙钟、降低并行度或把主性能搬到免费队列。

逐配置的 `canonical_summary`、状态、性能/校验 ID、`future_owner`、`future_plan` 和 `handoff_action` 见 [完整清单](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)。旧 H 与当前注册组分开记录；缺项不等于从未运行，也不等于无人负责。任何新账号接手前按 handover 完成实时去重及源计划转交。弱扩展单列，其中 controlled rank 曲线的 512 核端点六项先核实远端，不能盲目补跑。
