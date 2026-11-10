# 当前剩余提交范围（Nov 11 复核，沿用 Nov 8 文件名）

执行交接统一以 [HANDOFF_VANDA_EXPERIMENTS_20261106.md](HANDOFF_VANDA_EXPERIMENTS_20261106.md) 为准。原 Nov 8 请求与当时预算保存在 [历史原文](docs/history/updated_vanda_submission_plan_20261108_before_handoff_review_20261111.md)，里面的旧“正在运行”与未完成数不再适用。

| 当前固定图状态 | 配置数 | 所有权与动作 |
|---|---:|---|
| 严格完成 | 15,541 | 复用 |
| 非 512 尚无当前有效登记 | 3,984 | xtt_ella 活跃计划；转交前队友不得提交 |
| 非 512 历史失败 | 10 | xtt_ella，128 核组 1537511；先排查后补缺项 |
| 当前登记 512 暂挂 | 5 | 原性能 1532794、免费校验 1532795；延期 |
| 其他延期 512 | 1,160 | xtt_ella；含后追加 720，不自行取消目标 |
| **总计** | **20,700** | 尚缺 5,159；两账号 03:31 均无 R/Q |

hongxinran 两批 448 项全部通过，其余未完成项没有自动转交给它或新队友。主计划每 60 秒根据实际余额续投非 512，优先完成常规曲线；当前两账号余额不足以按既有余量和墙钟再提交正常请求。不得为了余额硬缩墙钟、降低并行度或把主性能搬到免费队列。

逐配置的 `canonical_summary`、状态、性能/校验 ID、`future_owner`、`future_plan` 和 `handoff_action` 见 [完整清单](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)。旧 H 与当前注册组分开记录；缺项不等于从未运行，也不等于无人负责。任何新账号接手前按 handover 完成实时去重及源计划转交。弱扩展单列，其中 controlled rank 曲线的 512 核端点六项先核实远端，不能盲目补跑。
