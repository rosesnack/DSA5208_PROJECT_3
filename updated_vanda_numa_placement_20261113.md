# Vanda 物理节点放置修复（2026-11-13）

此前节点选择按单个 NUMA vnode 的空闲 CPU 判断是否能容纳请求，遗漏了同一物理主机多个 vnode 可共同承载一个 PBS chunk 的情况。例如同一主机两个 vnode 各空闲4核，合计能满足每节点8核。固定在原主机上的部分排队请求因此没有利用其他符合条件的主机资源。这是调度辅助代码的问题，已修复。

## 两个原有请求的实际验证

没有为验证增加新的付费性能任务。只对两个原有Q请求更换 `host=`，保留八个物理节点、总64核、每节点8核、总440GB内存、原墙钟、MPI进程数及线程数。PBS实际把同一主机的请求分配到多个NUMA vnode。

| 账号 | 原性能作业 | PBS批次墙钟 | 退出码 | 独立校验 |
|---|---|---:|---:|---:|
| xtt_ella | 1550033.stdct-mgmt-02 | 32秒 | 0 | 6/6配置通过 |
| hongxinran | 1550244.stdct-mgmt-02 | 29秒 | 0 | 6/6配置通过 |

这些是整个PBS批次的用时，包含启动及探测，不能作为算法性能图中的单次 `solve_s`。算法性能继续使用原有一次预热、五次计时、中位数口径。

- [主账号实际分配、CPU型号及校验证据](results/updated_vanda_scaling/20261106T185006Z/aggregate_placement_validation_20261113.json)
- [分担账号实际分配、CPU型号及校验证据](results/updated_vanda_scaling/20261111_hongxinran_assist/aggregate_placement_validation_20261113.json)

两份证据保留PBS `exec_host`、`exec_vnode`、资源请求与运行节点CPU型号。实际各为八台物理主机，全部Platinum 8452Y；多个vnode记录不代表增加了物理节点。

## 已部署的自动接续

新增 `scripts/refresh_vanda_cpu_placement.py`，在同一物理主机内汇总可用CPU和内存，并按兼容资源池选择主机。两账号控制器通过 `--placement-hosts <RUN>/validated_8452y_hosts_20261113.json` 启用，主机名单来自已有CPU探测证据，剔除隔离节点，共95台已验证Platinum 8452Y主机。

每轮只考虑仍为Q的 `batch_cpu`、零GPU请求。当前可用绑定保持原样；需要调整时只改主机绑定并核对CPU核数、物理节点数、内存、墙钟、GPU数、MPI进程数和place不变。不调整R、H或超过当前256/128核续跑上限的512核请求。同一次选择在内存中扣除已选资源，避免给多个请求重复推荐同一批空位；实际调度仍由PBS决定。

`scripts/watch_vanda_core_groups.py` 在额度认证检查前执行这一步，因此额度查询过期不会阻止刷新已有Q请求；新增qsub仍要求有效认证与真实余额。两监控每60秒检查，允许在途上限64/32，运行至Nov13 23:59 SGT。标准重启记录 `refund_restart_20261113.json` 已包含新参数，不应按旧参数手动另启重复监控。

截至15:31同步的事件记录，主账号自动改绑7次、分担账号8次。这些是放置更新次数，不是新增实验数，也不是完成数：

- [主账号自动改绑前后资源](results/updated_vanda_scaling/20261106T185006Z/placement_refresh_events.jsonl)
- [分担账号自动改绑前后资源](results/updated_vanda_scaling/20261111_hongxinran_assist/placement_refresh_events.jsonl)

源计划 `requested_hosts` 保留初始意向；后续放置以事件日志、实际PBS分配及 `cpu_hosts.jsonl` 为准。物理CPU型号保持一致，但NUMA分配仍可能不同，分析时应保留实际亲和性和拓扑记录；不能宣称所有作业的内存拓扑完全相同。

## 验证和当前范围

26项Vanda调度测试与3项固定目标测试通过，包括同物理主机4+4核聚合、未验证主机排除、资源保持、运行/暂挂/512请求保持，以及认证缺失时仍刷新已有排队请求。两个真实原作业均成功并通过原独立校验。

没有修改MPI/C++计算、通信算法、编译选项、图、指标、计时重复或实验矩阵。固定目标仍为20,700；截至15:32已严格完成18,997，今天新增192。当前排队及待检380项若全部成功，可到19,377；仍需另外处理512核1,165项、历史失败102项、内存前置条件阻塞12项，以及尚未获额度覆盖的两个大图128核组44项。当前执行与转交以[唯一交接文档](HANDOFF_VANDA_EXPERIMENTS_20261106.md)为准。
