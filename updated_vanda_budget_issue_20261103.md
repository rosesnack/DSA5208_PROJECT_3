# Vanda CPU 额度暂挂核查（2026-11-03 23:35 SGT）

项目 `personal-hongxinran` 当前 CPU Net Balance 为 **19.427 核小时**。PBS 的 `am_hook` 已把约 50 个 CPU 作业设为用户暂挂；新投的 `strong_uniform` 两个 4 小时重跑作业 `1515650/1515651` 显示 `Budgets: runjob` 等待预算。另约 52 个作业在排队，其中 512 核配置符合 `batch_cpu` 的 720 核、10 节点上限，但当前节点不足。

这不是已经花掉 9,980.573 核小时的证据。当天的 [`amgr` CPU 交易导出](results/updated_vanda_scaling/20261102T092147Z/amgr_cpu_transactions_20261103.csv) 中，**79 个已结束**的作业仍标记 `reconciled=no`，预扣合计 **8,768 核小时**。相同作业的 PBS `resources_used.ncpus × resources_used.walltime` 合计约 **2,569.9 核小时**；两者差约 **6,198.1 核小时**。后者只是按分配核心数和实际墙钟时间估算，并不声称等于 NUS 最终计费。当天已有 140 笔已对账的 CPU 返还，合计 15,175.761 核小时，最近一笔在 16:52 SGT；`hpc project-usage` 明确说明负用量代表已完成作业的额度返还。

2026-11-02 晚间出现过类似预扣：余额 11.666 核小时，次日回升到 9,782.674 核小时。因此先等待本轮对账，而不是把 19.427 误报为最终消耗或立刻申请新 CPU 额度。额度回升后，需要分批 `qrls` 释放 `am_hook` 暂挂，优先完成现有强扩展和按核配平弱扩展，再继续 Kokkos OpenMP 全图网格及 512 核端点。若下一次对账后余额仍未返还，应请 NUS HPC 核查。

可向 NUS HPC 同时提交以下 GPU 队列申请与 CPU 对账询问：

> **Subject:** Vanda DSA5208 MPI project: 8-GPU queue access and CPU credit reconciliation
>
> Hello NUS HPC Support, I use Vanda under NUS ID `hongxinran`, project `personal-hongxinran`, for a DSA5208 MPI+CUDA/Kokkos PageRank assignment due 13 November 2026. The experiment needs one rank and one A40 GPU per node at 1, 2, 4, and 8 nodes. The visible `batch_gpu` and `batch_gpux` queues cap a job at 2 GPUs and 2 nodes. Could you provide an approved Vanda queue or temporary per-job limit for 4- and 8-node GPU MPI runs under this project?
>
> The CPU Net Balance currently reads 19.427 hours and `am_hook` holds about 50 CPU jobs. The 3 November `amgr` export shows 79 finished jobs with 8,768 CPU hours of unreconciled precharges. Their PBS allocated cores multiplied by elapsed walltime total approximately 2,569.9 core-hours. We understand the unused precharge can be returned on reconciliation. Could you advise when these jobs will reconcile and how best to release the held jobs after credit returns? I can provide the transaction export and PBS job IDs.
>
> Thank you.
