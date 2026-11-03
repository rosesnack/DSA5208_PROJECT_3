# Vanda / Cloud 代码与环境实测（2026-11-03）

## Vanda 隔离验证

Mac 当前通过 NUS VPN DNS 将 `vanda.nus.edu.sg` 解析为内网地址，并能用现有 SSH 密钥免交互登录 `stdct-login-01`。远端主项目及 Kokkos OpenMP/CUDA 安装存在。没有修改主项目目录或已排队作业；当前源码、小图和 PBS 脚本复制到独立目录 `/scratch/hongxinran/proj3_validation_20261103/`。

- CPU 免费队列作业 `1511433.stdct-mgmt-02`：一个计算节点、8 CPU 核；Release 编译并运行 Serial、单独 OpenMP/Kokkos OpenMP、纯 MPI、MPI+OpenMP、MPI+Kokkos OpenMP T=1/2，后四种 MPI 配置各跑 Allgatherv/Halo，并做独立残差和最终 rank 校验。
- GPU 免费队列作业 `1511417.stdct-mgmt-02`：两个 GPU 节点、每节点一张 A40；Release 编译原生 CUDA、Kokkos CUDA、MPI+CUDA、MPI+Kokkos CUDA，并运行 p=1/2 两种 MPI 通信策略和 CPU 对照；还单独验证 MPI+Kokkos OpenMP T=2。

CPU 作业已在 `IN-002` 完成，PBS 历史记录为 `Exit_status=0`、`resources_used.walltime=00:01:02`；隔离结果目录写入 `complete.txt`，11 份验证报告共 26 项检查、零失败，原始结果已同步至 `results/updated_vanda_validation_20261103/cpu/`。另在免费 CPU 计算节点提交了 CUDA 编译作业 `1511456.stdct-mgmt-02`：原生 CUDA、MPI+CUDA、Kokkos CUDA、MPI+Kokkos CUDA 的新版源码全部 Release 编译成功，PBS `Exit_status=0`、耗时 `00:01:07`，证据同步至 `results/updated_vanda_validation_20261103/cuda_compile/`。双节点 GPU **运行**验证作业 `1511417.stdct-mgmt-02` 仍排队，调度器说明 GPU 节点资源不足，尚无新版共享驱动的 GPU 运行结果。主实验最后三张大图的原作业因 2 小时 walltime 超时，PBS `Exit_status=-29`；逐格续跑 `1511591/1511593/1511595` 和后续 CPU 校验 `1511592/1511594/1511596` 均以 `Exit_status=0` 完成。三张图各有 37/37 个格子和 11 份零失败报告，主实验 GPU 固定图现为 **45/45 批、1,665/1,665 单元**，已同步到本地 updated 目录。主项目 `personal-hongxinran` 上次可读的 CPU Net Balance 约 11.666 CPU 小时、GPU Net Balance 800 GPU 小时；多项原 CPU 作业处于 PBS `H`，隔离的代码验证作业走免费队列，续跑大图使用 GPU 项目额度。

## Google Cloud

本机存在 `gcloud` 且已配置项目 `dsa5208p`，项目状态为 `ACTIVE`。只读 `gcloud compute instances list` 返回项目**未启用 billing**，因此目前不能在该项目启动 GPU VM。后续只读 gcloud 调用又因 OAuth token 刷新 TLS 错误失败；没有执行任何创建实例、启用 billing 或修改项目操作。Cloud 8 节点验证仍受项目 billing、可用 GPU 配额、实例/网络和共享文件系统约束。`scripts/build_cloud_gpu_matrix.sh` 与 `scripts/run_cloud_gpu_matrix.sh` 已就绪，但没有 Cloud 实测数据。

## 本机已通过

macOS Release 构建的 MPI+Kokkos OpenMP，在四顶点五边图上以 `p=2,T=2` 实跑 Allgatherv/Halo；两者的独立正确性校验和实际线程数校验均通过。Shell `bash -n`、Python `py_compile` 和 `git diff --check` 通过。此本机小图只验证代码路径，不作为 Vanda/Cloud 性能数据。
