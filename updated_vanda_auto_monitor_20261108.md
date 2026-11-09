# Vanda 自动监视与缺项续投

> **Nov 9 更新：**以下 Nov 8 的 PID 和状态路径已过期。旧进程因 PBS 异常响应退出，随后恢复遇到 scratch 写满；已修复并将新监控状态迁至 `/tmp/dsa5208_xtt_ella_monitor_20261106T185006Z/`，PID 2879720。当前服务故障、过夜新增 104 项及最新查看方式统一见 [Nov 9 状态](updated_vanda_run_status_20261109.md)。不要用下方历史心跳来判断当前是否存活。

> **21:22 已恢复读取：**沙箱外直连、公钥认证及远程命令全部成功。最新监控心跳 21:20，PID 2539365，状态为 `waiting_real_credits`；余额仍为 576.128 CPUh，未新增提交或失败。当前路由和 SSH 正常，先前超时原因没有被定位，不能把连接恢复直接归因于切换沙箱权限（此前失败查询同样使用了沙箱外权限）。

> **21:16 连接复查说明：**新、旧授权账户及不复用连接的 SSH 查询均超时，无法读取最新心跳。下面 20:31 为最近成功核实的运行状态，不是 21:16 的实时保证；连接失败也不能证明后台进程已停止。没有重复启动监控或重复挂任务。

**2026-11-08 20:26 SGT 已启动并验证独立存活。** 监控运行在 Vanda 的 `xtt_ella` 账号，PID `2539365`；前一 SSH 会话关闭后，已通过新会话核对进程及更新后的心跳。它不依赖 Mac 或本次聊天保持打开。每 **300 秒**检查 PBS 作业、免费校验状态和 `hpc project` 的真实余额，再决定是否续挂。

**20:31 第二轮自动心跳已验证并下载。** 进程仍存活，当前为 `waiting_real_credits`；累计注册的性能组为 28 个已结束、1 个 Q，免费校验为 16 个已结束、2 个 R、10 个 Q、1 个依赖 H。监控没有在余额不足时重复提交。运行记录已保存到本地 `auto_monitor_status.json` 和 `auto_monitor_events.jsonl`。

## 本次即时结果

- 新增性能作业 **1533432** 和免费校验 **1533433**：controlled 100k/d16、2 节点、`p=2,T=2`、总 4 核，分别补 Allgatherv/Halo 两个配置。请求上限 30 分钟、2 CPUh。
- PBS 确认实际申请为 2 节点/4 核，与 p×T 一致。随后性能已 **Exit 0，实际 1:27**，免费校验 Q。没有提前计为独立校验通过。
- 20:26 余额 **576.128 CPUh**；已排队的 512 核任务仍需预留 512 CPUh，保留 64 CPUh 余量后只剩 **0.128 CPUh**，因此监控进入 `waiting_real_credits`，未继续透支提交。
- 最近完整矩阵审计为 **14,289/19,980**；当前任务覆盖的原矩阵缺项为 176 已测待检＋5 排队待测，另 **5,510** 未由现有任务覆盖。新增 512 核拆分 720 项另列。

## 自动执行范围

冻结计划由有效结果合并审计生成，含原矩阵当时缺失的 5,691 项，以及独立标记的新增 512 核拆分 720 项。已登记的 179 项及本轮新增项会逐配置去重，不因“尚未校验”重新提交。每轮还检查新发布的完成标记。

- 先补 32/64/128/256 核主线，再补较小总核数的布局；所有 CPU 性能任务逐配置满足 p×T=申请核数，实际 MPI 节点数等于申请节点数。
- 支持每节点 1/2/4/8/16/32/64 核，分别按实际并行度申请，不为低并行度组合统一申请整组 32 核。释放暂挂的性能作业前检查 PBS 最终资源；若系统改变节点/核数，取消未运行的性能及依赖校验并记录，避免错误布局产生性能结论。
- 付费只测性能。独立校验、汇总、发布依然使用免费队列。算法、GCC/OpenMPI、Release、预热一次、五次计时、中位数口径不变。
- 保留 64 CPUh 余量，并扣除其他 Q/H 性能请求的上限；已运行作业使用项目系统已扣除的余额口径。每轮重新查询余额，不把预计返还当成已到账余额。
- 每次最多补至 6 个未结束性能资源组；最多允许 24 个性能已完成、独立校验未结束的资源组，防止原始数据和校验无限堆积。
- 新的 512 核批次和新增 720 拆分必须等原补点的独立校验 **1532795 成功**。两类的原始数据分别位于 `cpu_core_groups` / `cpu_core_groups_extra512`，不覆盖原已测批次的硬件记录；新增 720 不并入原 19,980 分母。
- 已失败或登记不完整的任务不盲目重试；状态中的 `failed_jobs_not_retried` 记录失败，需要检查后决定补救。额度认证过期或查询失败时停止新增提交、继续定期查询；不会读取或保存密码。

提交监控截止 **2026-11-12 23:59 SGT**，为 Nov 13 的校验和报告留时间；已提交任务不会因为监控停止而被取消。Vanda 重启会终止普通后台进程，届时需要重启监控；停止后不声称仍在监控。

## 查看、停止和重启

在已登录的 Vanda 终端：

```bash
cd /scratch/xtt_ella/DSA5208_PROJECT_3_20261107
cat results/updated_vanda_scaling/20261106T185006Z/auto_monitor_status.json
tail -n 20 results/updated_vanda_scaling/20261106T185006Z/auto_monitor.log
qstat -u xtt_ella
```

状态 JSON 中的 `observed_at` 是心跳；`action=submitted` 表示本轮新增提交，`waiting_real_credits` 表示当前余额不足，`waiting_existing_jobs` 表示已有任务/校验达到本脚本设置的待处理数量，`waiting_amgr_login` 或查询错误表示需要核查查询认证。若额度认证过期，在该账号自行执行 `amgr login`，监控在下一轮重新查询后继续，不需要发密码。

停止后续提交（保留已挂作业及校验）：

```bash
touch results/updated_vanda_scaling/20261106T185006Z/STOP_AUTO_SUBMIT
```

需要重启时，先确认旧进程已经结束，移除停止文件，再启动同一命令；进程锁会阻止第二个监控同时运行：

```bash
rm -f results/updated_vanda_scaling/20261106T185006Z/STOP_AUTO_SUBMIT
nohup python3 -u scripts/watch_vanda_core_groups.py \
  20261106T185006Z personal-xtt_ella \
  results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_20261108.json \
  --dependency 1530741.stdct-mgmt-02 --interval 300 \
  --until 2026-11-12T23:59:00+08:00 \
  >> results/updated_vanda_scaling/20261106T185006Z/auto_monitor.log 2>&1 < /dev/null &
```

本地仓库中的状态文件是下载时快照，实时心跳以 Vanda 文件为准。

## 代码与验证

[监控脚本](scripts/watch_vanda_core_groups.py)、[冻结计划生成器](scripts/prepare_vanda_watch_plan.py)、[预算内提交器](scripts/submit_vanda_core_groups.py)。预算预留、已测待检及已通过结果去重、512 核校验依赖的三项测试通过；原矩阵缺项 5,691 与新增 720 的唯一性和互不重叠检查通过。新四核任务已实际成功运行。

真实提交保存在累计 `core_group_jobs.tsv`、`core_group_submission_events_*.jsonl` 以及带时分秒的单次提交 JSON；不会用零项检查覆盖上次成功提交记录。`auto_monitor_status.json`、`auto_monitor_jobs.json` 与 `auto_monitor_events.jsonl` 仅保存调度/资源信息，不保存 PBS 完整认证环境。
