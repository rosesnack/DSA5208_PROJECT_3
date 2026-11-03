# Vanda 4/8 GPU 扩展的队列限制（2026-11-03）

用户要求所有实验只在 Vanda 运行。现有 45 张固定图的 Vanda A40 `p=1/2` GPU 配置已完成并通过校验；`p=4/8` 要求每节点一张 GPU、一个 MPI rank，分别在 4/8 个节点上运行同一图和两种通信策略。

Vanda 登录节点实时 `qstat -Qf` 显示；原始输出保存在 `results/updated_vanda_scaling/20261102T092147Z/vanda_gpu_queue_limits_20261103.txt`：

| GPU 队列 | 每作业最多 GPU | 每作业最多节点 | 说明 |
|---|---:|---:|---|
| `batch_gpu`（项目 `auto` 路由） | 2 | 2 | 当前项目作业使用的付费队列 |
| `batch_gpux`（`autox` 路由） | 2 | 2 | 也是 2/2 上限 |
| `interactive_gpu` | 2 | 2 | 交互队列 |
| `gpu`（免费路由） | 2 | 未单列；总 GPU 上限仍为 2 | 免费队列 |

因此当前个人项目即使有 GPU 时数余额，也不能提交真正的 4/8 GPU、4/8 节点 MPI 作业。4/8 个 rank 共享两张 GPU 只测到资源争用，不是所要求的 4/8 GPU 强扩展；跨两个 PBS 作业偷用节点也不作为有效方案。

已备好 `scripts/vanda_gpu_extension_compute.pbs`、`scripts/vanda_gpu_extension_validate.pbs`、`scripts/submit_vanda_gpu_extension.sh`：当 NUS HPC 放宽同一项目作业的 GPU 与节点上限后，按每节点 1 GPU、1 rank 补跑 G45 的 `p=4/8`。沿用 Vanda A40、相同 Release 二进制、1 次预热、5 次计时；CPU 免费队列只做结果校验，不采集性能时间。独立保存 `scaling_p4_p8.csv` 和 `validation_p4_p8.json`，不覆盖已有 `p=1/2` 报告。`scripts/audit_fixed_matrix.py --include-vanda-gpu-extension` 把新增 1,260 个 GPU MPI 单元计入覆盖目标，总固定图目标为 21,240 个单元。**目前没有任何 4/8 GPU 实测结果。**

三种合成图家族的弱扩展也已备好 `scripts/vanda_gpu_weak_extension_compute.pbs`、`scripts/vanda_gpu_weak_extension_validate.pbs`、`scripts/submit_vanda_gpu_weak_extension.sh`。它在每节点 1 GPU、1 rank 的 `p=4/8` 布局上运行，沿用现有弱扩展图与同一计时规则，并把新验证报告另存为 `_p4_p8`。这部分同样等待 Vanda 队列上限调整。

需要用户向 NUS HPC 申请：为 `personal-hongxinran` 提供同一 PBS 作业至少 8 张 A40 GPU、8 个 GPU 节点的合法队列额度，或告知课程项目可使用的等效 Vanda 队列。该申请尚未发送。可直接使用以下文字：

> Subject: Request for 8-node / 8-GPU Vanda MPI scaling job for DSA5208 project
>
> Hello NUS HPC Support, I am using Vanda under NUS ID hongxinran and project personal-hongxinran for a DSA5208 MPI+CUDA/Kokkos PageRank assignment. My experiment needs one MPI rank and one A40 GPU per node at 1, 2, 4, and 8 nodes, with both Allgatherv and Halo communication. The current batch_gpu and batch_gpux queues report resources_max.ngpus=2 and resources_max.nodect=2, so I cannot submit the 4- and 8-GPU points. Could you advise whether an approved Vanda queue or temporary project limit allows one 4-node/4-GPU and one 8-node/8-GPU job at a time? The jobs use the existing project GPU-hours allocation. Thank you.
