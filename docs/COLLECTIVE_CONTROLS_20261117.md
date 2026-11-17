# 集体通信策略与64核节点边界：独立配对实验

本轮主性能矩阵仍为 **19,530个非512固定图配置**，另有372项弱套件和5项有效512固定图补充。本轮补充 **57个独立诊断配置，均已完成并通过校验**，追加的2项256核启动绑定配对也均已通过校验（合计59/59）；不加入这些分母，不覆盖原始记录。每项1次预热、5次计时，报告中位数及五次范围。

## 回答的问题与组合

| 组 | 图 | 布局 | 策略或方法 | 配置数 |
|---|---|---|---|---:|
| Alltoallv策略 | 大Uniform | p=C=64/128/256；T=1；n=2/4/8 | 纯MPI Halo，默认固定规则、强制basic_linear、强制pairwise | 9 |
| 节点边界配对 | 大Hub、Controlled | C=32/64/128；n=1/2/4；每节点32活跃核 | MPI p=C,T=1；MPI+OpenMP / MPI+Kokkos OpenMP p=C/4,T=4；各跑Allgatherv/Halo，默认策略 | 36 |
| Allgatherv策略 | 大Hub、Controlled | C=32/64/128；n=1/2/4；p=C/4,T=4 | MPI+OpenMP Allgatherv，另各强制Bruck、Ring；默认对照已经计入上一行 | 12 |
| 合计 | | 所有布局p×T=C=n×32 | 39个匹配默认对照，18个强制策略配置；共285次计时 | **57** |

采用对称的邻近配置，而非仅测异常端点。两个账号的MPI、Hybrid、MPI+Kokkos CPU二进制SHA-256一致，输入和既有Serial参考直接复用。原数学内核、停止准则和精度不改动。

## 已提交的任务与预算

| 账号 | 核数 / 节点 | 配置数 | 性能作业，付费batch_cpu | 免费完整校验依赖 | 墙钟上限 |
|---|---|---:|---|---|---|
| xtt_ella | 32 / 1 | 16 | 1576293 | 1576294 | 1小时 |
| hongxinran | 64 / 2 | 19 | 1576291 | 1576292 | 1小时30分 |
| hongxinran | 128 / 4 | 19 | 1576289 | 1576290 | 1小时 |
| xtt_ella | 256 / 8 | 3 | 1576295 | 1576296 | 30分 |

原57项最大预留合计 **384 CPU小时**；四个付费性能作业均Exit 0，PBS实际墙钟分别为35分42秒（32核）、40分13秒（64核）、46分06秒（128核）、6分15秒（256核），按申请核数×实际墙钟合计约 **186.95 CPU小时**。这是资源使用估算，最终扣款以HPC对账为准。墙钟包含读图、MPI启动和写结果，不能只用solve时间设置时限。所有组均在上限内完成，没有因时限中断。

两个账号的免费预检 **1576277 / 1576279** 均Exit 0：64MiB落盘、安装参数、原生组件与五种受控策略的通信正确性通过。早期128核Uniform三策略另用免费作业 **1576353** 提前校验，不等待同组其余16项完成，也不增加性能配置。三项均已通过：相对Serial完整向量L1差为0，独立残差上界1.4263e-9。64核三策略另用免费作业 **1576456** 提前复用同一参考证书。

- [逐配置清单及状态，57行](../results/updated_vanda_scaling/collective_controls_20261117/case_manifest_57.csv)
- [xtt_ella提交及预算回执](../results/updated_vanda_scaling/collective_controls_20261117/submission_xtt_ella.json)
- [hongxinran提交及预算回执](../results/updated_vanda_scaling/collective_controls_20261117/submission_hongxinran.json)
- [实际作业墙钟与CPU小时](../results/updated_vanda_scaling/collective_controls_20261117/runtime_accounting.csv)
- [xtt_ella最新PBS快照](../results/updated_vanda_scaling/collective_controls_20261117/live_xtt_ella.json)
- [hongxinran最新PBS快照](../results/updated_vanda_scaling/collective_controls_20261117/live_hongxinran.json)

**这57项均已完成校验，请勿按清单重新提交。** 清单中的 `scheduled` 只表示该项尚未留下完成标记，其资源组已经有PBS作业。

本轮输出在各账号的 `~/dsa5208_collective_controls_20261117/results/c{32,64,128,256}/`。输入和构建只读复用scratch；输出写HOME，避开xtt_ella此前的scratch写入配额问题。未动既有512排队作业或队列。

## 已验证的主要结果（2026-11-17 17:46 SGT快照：57/57项）

四个性能作业及四个免费独立校验均Exit 0。57项、285次正式计时已保存并全部进入独立诊断表；不替换主矩阵。
| Uniform纯MPI Halo | 默认规则中位数s | 强制basic_linear s | 强制pairwise s | 默认/pairwise |
|---|---:|---:|---:|---:|
| p=64，2节点 | 1.215321067 | 1.376504149 | 1.172472765 | 1.04× |
| p=128，4节点 | 4.134223439 | 4.128567044 | 0.886278612 | 4.66× |
| p=256，8节点 | 3.593359900 | 6.630521315 | 3.562751166 | 1.01× |

128核三策略在同一分配内、同图同二进制同绑定，完整向量相对Serial的L1差均为0；改变通信实现明显改善这一点。它不改变PPR数值、图的分区方式或弱扩展的通信增长规律。

64核Allgatherv的两图对照均是默认≈强制Ring，Bruck更慢：Hub为5.022/5.010/5.550秒，Controlled为3.886/3.884/4.294秒（默认/Ring/Bruck）。因此，64核不属于“换回Bruck就能改善”的情况。两图×三方法×两通信的12条节点主线中，C64/C32的时间比为0.93–1.04，整体接近平台；热点仍集中在同一个MPI rank，额外进程主要分担冷区，是主要结构性解释。NUMA/缓存局部性、跨节点进展和共享资源可能影响细小差别。

57项最大完整向量L1差为8.82e-17，最大独立残差证书上界1.68e-9，均通过原有1e-8准则。没有改写PPR内核或把未校验结果并入报告。

## 256核启动绑定补充：2项已完成校验，不重复提交

本轮256核pairwise中位数为3.563秒，而主矩阵选用的另一分配测量为0.554秒。二进制SHA-256、图、进程数、节点数及付费队列一致；物理节点、NUMA分布及启动绑定方法不同。因此保留两批原始观测，不用旧快值替换新控制实验。报告按本次分配内的配对效应解释策略收益，并分析节点/NUMA局部性、共享网络与MPI进展可能带来的分配差异。

追加同一分配内的两个配置：大Uniform，纯MPI Halo，强制pairwise，8节点×32核，p256,T1；只改变启动绑定：Open MPI原生`--bind-to core`，或Python显式CPU掩码。计时外记录MPI_Init之后的每个rank CPU掩码，免费校验确认256个互不重叠的活跃核及数值结果。

| 账号 | 性能任务 | 免费校验 | 免费预检 | 配置数 | 墙钟 | 18:07完成快照 |
|---|---|---|---|---:|---|---|
| hongxinran | 1577398 | 1577399 | 1577397，Exit 0 | 2 | 30分 | 性能及校验均Exit 0 |

原生core绑定与显式CPU掩码的五次中位数分别为2.974793788秒、3.110986186秒；两者五次范围重叠，且MPI初始化后的256个CPU绑定均通过独立校验。性能作业实际墙钟3分35秒，约15.29 CPU小时；连同原57项，五个付费性能作业按申请核数×实际墙钟合计约202.24 CPU小时。实际扣款以HPC对账为准。59项均已完成，本机同步进程已按完成条件结束，无须重新提交或恢复本轮监控。

追加最大预留128 CPU小时，连同原57项总上限 **512 CPU小时**（这是预算单位，不是512核实验）。提交时余额647.755 CPU小时；保留旧512作业256 CPU小时和128 CPU小时余量后，仍剩135.755 CPU小时。只有这2项获准新增，没有重跑其他有效结果。

- [追加2项清单及状态](../results/updated_vanda_scaling/collective_controls_20261117/case_manifest_launcher_2.csv)
- [提交、依赖和预算回执](../results/updated_vanda_scaling/collective_controls_20261117/launcher_submission.json)
- [已校验的绑定结果表](../reports/non512/data/launcher_controls.csv)；两项均已独立校验并进入报告。

## tuned规则与控制变量

安装探测两边均为 `coll_tuned_use_dynamic_rules=false`，Alltoallv/Allgatherv算法覆盖均为`ignore`，自定义规则文件为空。主实验脚本没有请求动态规则。**OpenMP的dynamic行调度和MPI的dynamic规则开关是不同参数。**

Open MPI v4.1.8默认tuned Alltoallv固定选择：

| MPI communicator进程数p | 算法 |
|---|---|
| p<4 | pairwise |
| 4≤p<64 | basic_linear |
| 64≤p<128 | pairwise |
| 128≤p<256 | basic_linear |
| 256≤p<1024 | pairwise |
| p≥1024 | basic_linear |

**该Alltoallv规则只看p，不看载荷字节、CPU核心数，也不在线测量拥堵或学习最优策略。** Allgatherv另看每rank平均贡献量 `b=8N/p`。大图T=4主线的C=32/64/128对应p=8/16/32、b=12.8/6.4/3.2MB；默认Allgatherv为Bruck/Ring/Ring，Halo的Alltoallv在这三点均为basic_linear。

受控默认设置：

```bash
OMPI_MCA_coll=tuned,basic,libnbc,self
OMPI_MCA_coll_tuned_use_dynamic_rules=0
OMPI_MCA_coll_tuned_alltoallv_algorithm=0
OMPI_MCA_coll_tuned_allgatherv_algorithm=0
```

强制某个操作时设 `coll_tuned_use_dynamic_rules=1`，仅覆盖该操作：Alltoallv的1/2为basic_linear/pairwise；Allgatherv的2/3为Bruck/Ring。其他操作保留默认规则。动态开关在这里用于强制分派，不等于在线自适应，也不改变阻塞MPI接口。所有策略使用同一组件集合及`ob1 + self,vader,tcp`传输。libnbc为MPI初始化及非阻塞集体操作提供必需的后备支持；免费预检已验证这套完整组件集合。

免费拓扑检查 **1577092**（CN-118，Exit 0）确认该8452Y计算节点为2插槽×36物理核心、每核心1硬件线程，共72个物理核心。32核请求是32个活跃物理核，512补充是每节点64活跃核；p×T口径没有把SMT线程冒充物理核。证据见 `results/updated_vanda_scaling/collective_controls_20261117/cpu_topology_proof.json`。

每种p/T/策略先在计时外执行组件探测；实际性能计时不启用verbose。每种布局保存CPU型号、二进制哈希、所有rank的CPU映射和MCA设置。所有rank的CPU集合互不重叠，每节点恰好32个活跃CPU。

规则来源：[固定选择器](https://github.com/open-mpi/ompi/blob/v4.1.8/ompi/mca/coll/tuned/coll_tuned_decision_fixed.c)、[Alltoallv参数](https://github.com/open-mpi/ompi/blob/v4.1.8/ompi/mca/coll/tuned/coll_tuned_alltoallv_decision.c)、[Allgatherv参数](https://github.com/open-mpi/ompi/blob/v4.1.8/ompi/mca/coll/tuned/coll_tuned_allgatherv_decision.c)。

## 数值校验与结果准入

校验全部在免费队列。复用一个独立遍历原始边表验证的Serial向量s，逐元素核对每个新向量x的ID、入出度、非负性、质量及L1差。PageRank含悬挂点均匀再分配后的映射F是L1下的alpha压缩映射，因此

`||x-F(x)||₁ ≤ ||s-F(s)||₁ + (1+alpha)||x-s||₁`。

要求该独立残差上界不超过1e-8（另有1e-12舍入容差），并检查每项5次计时、原始中位数、历史、迭代数、真实线程数和所有自报残差。Serial参考的原始边扫描每图只做一次，锁定SHA-256后复用；**没有重新运行Serial性能实验**。测试覆盖含悬挂点的图、错误向量拒绝和错误中位数拒绝。

只有存在成功校验证书及逐项完成标记的配置才进入 [报告控制实验表](../reports/non512/data/collective_controls.csv)。已计时但尚在校验的记录保留在独立raw目录，不进入正式性能结论。默认／强制算法的五次范围用于描述本次分配内的一致性，不据此虚构跨作业统计显著性。

## 自动监控、同步与复现

两个账号各有 `watch_collective_controls.py` 后台进程，每60秒检查**仅本研究注册的五个性能作业及对应校验**，截止2026-11-19 23:59 SGT。只在保持queue、ncpus、nodes、mem、walltime、进程数不变的前提下，给排队作业刷新经过8452Y验证的物理主机绑定；不新增任务、不释放历史暂挂任务、不自动重试失败。

本机同步及报告入口：

```bash
python3 scripts/sync_collective_controls.py
python3 scripts/analyze_collective_controls.py
python3 scripts/build_non512_report.py --pdftoppm /path/to/pdftoppm
```

持续同步可使用 `--watch --interval 120 --until 2026-11-19T23:59:00+08:00 --rebuild`。本机必须保持运行且能访问校园网；远端已提交的PBS任务不依赖本机SSH保持连接。同步只下载计时、设置、校验证书、组件／映射和小型日志，完整rank向量仍留Vanda。报告生成器自动加入**已校验且配对完整**的策略比较表和SVG图；不拿最快策略覆盖主矩阵，也不把等待中的结果写成已完成。

报告只保留 `output/pdf/pagerank_non512_report.pdf` 这一整合版本，根目录的队友旧PDF按要求删除。正文保持四大部分；原先的待验证清单已改为证据与可能机制的论述。

独立复现的PBS入口为 `scripts/vanda_collective_control_job.pbs` 和 `scripts/vanda_collective_control_validation.pbs`，设置 `CONTROL_PLAN`，按组覆盖select/墙钟，并给免费校验添加 `afterok` 依赖。现有57项和追加2项均已完成校验，不要重复执行这些提交操作。校验器测试：`python3 scripts/check_collective_certificate.py`。
