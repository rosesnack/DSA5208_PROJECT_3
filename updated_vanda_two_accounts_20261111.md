# 两账号当前状态与交接入口（Nov 11）

**03:31 SGT 实时复查：两个账号均无 R/Q。** 固定图严格完成 **15,541/20,700**，剩余 **5,159**。当前的完整矩阵、按状态清单、所有权和接手流程统一见 [Vanda handover](HANDOFF_VANDA_EXPERIMENTS_20261106.md)；本文件不再保留相互矛盾的“最新”执行说明。

| 账号 | 最新观测动作 | 本轮状态 | 未完成固定图归属 |
|---|---|---|---:|
| xtt_ella | waiting_real_credits；最近余额 16.138 CPUh | 无在途性能/校验；含历史失败 10 项、当前延期 H 5 项 | 5,159 |
| hongxinran | no_eligible_unregistered_cells；最近余额 77.677 CPUh | 两批 78 组、448/448 项已校验通过 | 0 |

主账号 8 个 H、hongxinran 70 个旧 H 均不是正在计算；不能批量释放。其中只有当前 512 性能 1532794/校验 1532795 对应完整清单的 held 5 项，其余是已替代或此前延期的旧请求。原文说“新增项正在运行”的状态已过期，详见 [归档原文](docs/history/updated_vanda_two_accounts_20261111_before_handoff_review_20261111.md)。

两个监控仍每 60 秒检查，PID 251391 / 155730，新增提交截止 Nov 12 23:59 SGT。主账号余额返还后仍可能提交 **3,984 个未提交的非 512 核缺项**；这些不是空闲可领取项。队友须先完成原监控暂停、源计划移除、实时队列核对和所有权转交，再提交互斥的新计划。当前登记与未来计划的跨账号交集均为零。

- [逐配置完整清单及 future_owner / handoff_action](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)
- [实际登记的 161 个资源组与 job ID](results/updated_vanda_scaling/git_sync_20261111/submitted_core_groups.csv)
- [主账号实时查询快照](results/updated_vanda_scaling/git_sync_20261111/queue_xtt_ella.json)
- [hongxinran 实时查询快照](results/updated_vanda_scaling/git_sync_20261111/queue_hongxinran.json)

快照是观测结果，不能作为跨账号的全局提交锁。性能用付费队列；构建、数据处理、独立校验和发布用免费。没有在本次文档审查中新增、取消或释放任何作业。
