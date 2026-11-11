# 两账号状态：Nov 11 22:52 SGT

**上一批 hongxinran 的 136 组/730 项已全部通过独立校验并下载；本轮又补了 38 组/100 项。** 已从主账号实际源计划移除新转交项，跨账号登记和未来计划均无交集。固定图严格完成 **16,833/20,700（81.3%）**，剩余 3,867。

| 账号 | 当前情况 |
|---|---|
| hongxinran | 之前 448+730=1,178 项全部通过；新批已登记 30/38 组、84/100 项；性能 R=6、Q=0、F=24 |
| xtt_ella | 仍等实际额度，最近余额约 16.097 CPUh；本轮已移除 100 项，继续负责 3,767 个未完成目标 |

新批转交前余额 **325.713 CPUh**，完整请求上限 **240 CPUh**，请求全部承诺后仍留 **85.713 CPUh**，高于控制器 64 CPUh 余量。请求上限不等同于实际花费；返还到账前不提前使用。

| 新批配置 | 组数 | 配置数 | 总核数 | 原墙钟 |
|---|---:|---:|---|---|
| 两节点，synthetic_controlled / synthetic_hub 的已有缺项 | 8 | 40 | 4/8/16/32 | 00:30:00 |
| 四节点，每节点两核，原网格中的缺项 | 30 | 60 | 8，p=4,T=2 | 00:45:00 |
| **合计** | **38** | **100** | 每配置 p×T=请求核数 | 未缩短 |

免费准备 **1543003** 已成功：复用 32 张已有图及 Serial 参考，四节点 MPI 使用相同 TCP/ob1 配置，实际 CN-135/136/140/142，每节点两核且均为 Platinum 8452Y。没有重跑 Serial 性能或重新构建。付费只测性能，校验继续免费。

监控 PID **2632870 / 2632859**，每 60 秒检查，最多六个在途性能组；截止 Nov 12 23:59 SGT。采用同一 CPU 分区 `cpu_node/ccid-10` 的调度器分配，不再固定主机。主账号原 14 项失败和旧 H 保持原归属，512 核仍延期。

- [唯一执行 handover 与完整矩阵](HANDOFF_VANDA_EXPERIMENTS_20261106.md)
- [本轮 100 项转交/预算记录](results/updated_vanda_scaling/account_partition_20261111_phase4/account_partition.json)
- [主账号当前源计划](results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_xtt_ella_20261111_phase4.json)
- [hongxinran 当前源计划](results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261111_phase4.json)
- [免费四节点准备结果](results/updated_vanda_scaling/20261111_hongxinran_assist/phase4_prepare_status_20261111.json)
- [上一批 730 项全部完成并下载的记录](results/updated_vanda_scaling/account_partition_20261111_phase4/previous_completed_snapshot.json)
- [本轮实际 job ID 与状态](results/updated_vanda_scaling/account_partition_20261111_phase4/hongxinran_submission_snapshot.json)

计划、实际提交和严格完成分别记录。已有完整有效部分复用，R/Q、待校验/待同步均不重复提交。队友先读 future_owner，再转交所有权，不能直接领取缺项 CSV。
