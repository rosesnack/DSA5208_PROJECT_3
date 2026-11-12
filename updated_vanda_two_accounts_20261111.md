# 两账号状态：2026-11-13 02:21 SGT

**严格完成 18,829/20,700（91.0%），剩余 1,871；本次新增同步 24 项独立校验结果。** 观察时间为 Nov 13 02:21:31/02:21:34 SGT。PBS 作业数、单独配置数和五次重复次数分别计数，不能互相替代。

| 账号 | 性能 R | 性能 Q | Nov 13 新增校验通过 | 最近 CPUh 余额 | 全矩阵未完成归属 |
|---|---:|---:|---:|---:|---:|
| xtt_ella | 1 | 11 | 4 | 5278.406 | 1,761 |
| hongxinran | 0 | 6 | 20 | 1052.818 | 110 |

主账号 `1550031` 正在计算 strong_uniform 大图，实际为 **8 个物理节点、总 8 核**；02:22 的只读核对确认八节点记录、累计 CPU 时间 26 分 32 秒、已保存两项测量。它仍在运行，尚未独立校验的测量不计完成。

主账号此前 32 核作业 `1550029` 已正常结束（22 秒）并校验通过四项。主机绑定调整后，hongxinran 五个 32 核批次依次完成，共新增通过20项。主账号今天已实际提交13组/76项，分担账号11组/88项；两边有效结束的性能请求未发现新增非零退出码。当前在途为1个运行、17个排队，不再是零启动。

剩余64/128核请求仍受指定节点可用资源限制。两个远端监控均存活，显示 waiting_existing_jobs，每60秒检查；主账号最多12组在途、留16 CPUh，分担账号最多六组、留64 CPUh，Nov 13 23:59 SGT停止新增提交。付费只测性能，处理和独立校验免费；普通缺项优先、512核继续延期。

当前逐配置状态：`{'validated': 18829, 'deferred_512': 1160, 'queued': 134, 'unsubmitted': 464, 'held': 5, 'performance_failed': 102, 'running': 6}`。两个账号的当前登记和未来计划交集均为零；原转交给hongxinran的130项中20项已完成、110项仍归该账号，不得由队友重复提交。当前真实源计划仍为 core_group_watch_plan_<账号>_20261113_refund.json。

- [唯一执行交接与完整矩阵](HANDOFF_VANDA_EXPERIMENTS_20261106.md)
- [逐配置状态及来源](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)
- [首个32核请求的主机调整](results/updated_vanda_scaling/20261106T185006Z/queue_capacity_fix_20261113.json)
- [分担账号复用32核节点的请求记录](results/updated_vanda_scaling/20261111_hongxinran_assist/aligned_32core_queue_20261113.json)
- [今天恢复续投、墙钟及失效依赖修复](updated_vanda_resumption_20261113.md)
