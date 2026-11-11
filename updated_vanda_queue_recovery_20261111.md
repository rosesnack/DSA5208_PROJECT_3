# Vanda 排队恢复：2026-11-11

21:51 检查发现六个新性能 Q 占满控制器在途上限：五个 16 核单节点作业固定在余量不足的 CN-053；另一个两节点作业受固定主机与 placement-set 条件限制。当时已有 36 个本批性能作业结束，并非整批未运行。

22:04 已取消这六个 **尚未启动** 作业的固定 host 条件，保留原 job ID；逐项核对 **ncpus、nodect、mem、walltime** 与修改前一致。新提交的剩余配置使用 `node_pool=cpu_node:switch=ccid-10`，由 PBS 选取节点，不再只等两台物理机。既有 R/F 测量没有取消或重测。主账号计划、实验矩阵、算法与 solve_s 计时范围未变。

先运行了免费的两节点探针 **1542730**，采用与正式性能相同的 OpenMPI TCP/ob1 设置；在 CN-135/CN-136 上六秒完成，两个 CPU 均为 Platinum 8452Y。随后才调整付费作业。CPU 型号检查也提前到求解前；独立免费发布仍再次验证型号、实际节点数和 p×T/affinity，避免异硬件进入性能表。

**22:07 SGT 快照：**新批已登记 **52 组/246 个配置**，性能 F=49、R=3、Q=0；监控继续工作。F 只表示性能退出；严格完成还需独立校验与结果同步。当前共享清单仍以最后下载的 16,131 项作为严格完成数，其余已测待校验/待同步单列，禁止重复测量。

- [六个原 Q 作业的修改前后请求](results/updated_vanda_scaling/20261111_hongxinran_assist/cpu_pool_queue_repair_20261111.json)
- [免费同交换机、同 MPI 传输探针](results/updated_vanda_scaling/20261111_hongxinran_assist/cpu_pool_ccid10_probe_status_20261111.json)
- [当前双账号状态](updated_vanda_two_accounts_20261111.md)
- [当前主机选择的源计划](results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261111_phase3.json)
- [实际登记的作业与状态](results/updated_vanda_scaling/account_partition_20261111_phase3/hongxinran_submission_snapshot.json)

回归检查覆盖 CPU-pool 选择时保持节点数/核数、原固定主机配置兼容、余额与去重规则、完整矩阵和跨账号归属。付费仍只跑性能；本次探针与独立校验均用免费队列。
