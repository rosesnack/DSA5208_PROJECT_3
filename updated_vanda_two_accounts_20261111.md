# 两账号续跑：Nov 11 22:07 SGT

当前剩余任务已取消固定主机绑定，交由 PBS 在 `node_pool=cpu_node, switch=ccid-10` 内分配；核数、线程、内存和墙钟不变。免费两节点预检 **1542730** 使用与性能任务相同的 TCP/OpenMPI 配置成功，计算前与独立发布前均检查 Platinum 8452Y。详见 [本次排队修复](updated_vanda_queue_recovery_20261111.md)。

**已正式给 hongxinran 新分配 136 组/730 个缺项，总请求上限 932 CPUh。** 主账号已移除相同配置；已完成的 16,131 项固定图结果不重跑。当前执行以 [handover](HANDOFF_VANDA_EXPERIMENTS_20261106.md) 和 [逐配置归属清单](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv) 为准。

| 项目 | 当前安排 |
|---|---|
| 新工作量 | 33 张网格图，uniform/hub/controlled 三家族，136 组/730 项 |
| 布局 | 1/2 节点，总 1–32 核；每个配置 p×T=申请核数 |
| 通信和方法 | 按原矩阵只补缺项，不重跑已完成部分；MPI 方法仍分别有 Allgatherv/Halo |
| 墙钟 | 单节点 20 分钟、两节点 30 分钟，沿用原值 |
| 正式性能 | personal-hongxinran，付费 batch_cpu |
| 准备/独立校验 | 免费 auto_free；修正后的准备 1542434 已成功，未重测 Serial |
| 后台监控 | 主账号 PID 765730，分担 PID 765579；每 60 秒查余额和状态，最多六个在途性能组 |
| 截止 | Nov 12 23:59 SGT 后不新增提交 |

本次快照已登记 **52 组/246 个新配置**：性能 R=3、Q=0、H=0、F=49。首批性能 ID 为 1542438/1542440/1542442/1542444/1542446/1542448，每个均有免费校验依赖。剩余计划由监控继续分批提交；**计划 730 项不代表 730 项已经 qsub，更不代表已完成。**

此前固定主机调整仅供追溯，记录见 [记录](results/updated_vanda_scaling/20261111_hongxinran_assist/phase3_host_adjustment_20261111.json)；原 CN-051 已满。只调整未启动作业的主机选择，不改进程/线程、总核数、通信、计时口径或墙钟。

当前固定图未完成归属：xtt_ella **3,867**、hongxinran **702**。未来计划和当前登记配置的跨账号交集均为零。主账号两个既有失败组共 14 项及 512 核延期范围没有转交给本批；旧 H 继续保持延期，禁止批量释放。

- [转交与预算凭据](results/updated_vanda_scaling/account_partition_20261111_phase3/account_partition.json)
- [主账号当前源计划](results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_xtt_ella_20261111_phase3.json)
- [hongxinran 当前源计划，含原 448 项和新 730 项](results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261111_phase3.json)
- [实际注册组和 job ID](results/updated_vanda_scaling/git_sync_20261111/submitted_core_groups.csv)
- [hongxinran 作业快照](results/updated_vanda_scaling/account_partition_20261111_phase3/hongxinran_submission_snapshot.json)

准备作业第一遍误查了当前流水线不用的 mpi_rank_hosts，免费失败后已修正；第二遍免费准备一秒成功，所有新性能均依赖它，没有因此产生失败的付费测量。
