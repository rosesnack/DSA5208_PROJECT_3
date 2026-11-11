# 其他核心数是否需要追加拆分，以及本次 Git 同步范围

当前执行与队友接手统一见 [handover](HANDOFF_VANDA_EXPERIMENTS_20261106.md)。逐配置清单已补 `future_owner`、`future_plan` 和 `handoff_action`：前批 730 项及随后 100 项已通过，本批 306 项已转交 hongxinran 并从主账号移除；其余缺项按 future_owner 各自续跑，队友不能直接套缺项清单提交。

## 核对结论

**在已确认的每进程线程范围 T=1/2/4/8/16/32、常规每节点最多使用 32 核的规则内，其他核心数不需要再追加同类任务。** 原网格已覆盖这些合法的 p/T 拆分；尚缺结果应按现有目标补跑。512 核原来只列 T=1、4，因此后续才增加 T=2、8、16、32 的 720 项。

下面是固定图强扩展主线。每个 C 的节点数明确固定；同 C 的其他合法节点布局仍保留在原网格中。

| 总核数 C | 主线节点数 | MPI+OpenMP / MPI+Kokkos OpenMP 的 p×T |
|---|---:|---|
| 32 | 1 | 32×1、16×2、8×4、4×8、2×16、1×32 |
| 64 | 2 | 64×1、32×2、16×4、8×8、4×16、2×32 |
| 128 | 4 | 128×1、64×2、32×4、16×8、8×16、4×32 |
| 256 | 8 | 256×1、128×2、64×4、32×8、16×16、8×32 |
| 512 | 8 | 512×1、256×2、128×4、64×8、32×16、16×32 |

每行的两种混合实现、六种拆分、45 张图、两种通信，加上纯 MPI 的 C×1，两种通信，目标数是 **(2×6+1)×45×2=1,170**。32/64/128/256 的各 1,170 项全部已在原 19,980 中。512 的 1,170 项由原有 450 加后追加 720 构成。

1/2/4/8/16 核也已有全部合法线程拆分，例如 4 核的 4×1、2×2、1×4；跨节点时还须满足 p 至少等于节点数、p 可均分到各节点。审计逐一检查了这些条件下的主线目标，没有发现 512 之外的“设计漏项”。**设计已覆盖不代表结果已全部跑完。**

T=64 或把常规其他布局也扩到每节点 64 核，会增加此前未确认的实验维度，本次没有自行扩大该范围。

## 统一的完整目标

- 原矩阵：19,980，包含 450 个 512 核配置。
- 后续确认的 512 核拆分：720，属于待完成任务。
- **完整固定图目标：20,700；当前严格通过 17,611，尚缺 3,089。**

弱扩展独立统计。4/8 GPU 按已确认决定不在目标中。

## 当前安排与结果

截至 2026-11-12 03:41 SGT，固定图严格完成 **17,611/20,700**，尚缺 3,089。逐状态：`{"validated": 17611, "deferred_512": 1160, "unsubmitted": 1486, "awaiting_validation": 336, "held": 5, "performance_failed": 102}`。未完成全部归 xtt_ella；hongxinran 的 1,584 项已完成。登记和未来计划仍互斥。

原九个八节点任务的 110 项均已通过独立校验并同步；另外六个大图低内存失败组保留 18 项完整测量，尚未计通过。剩余相同内存设置有明确前置条件，不能盲目提交。资源和校验修复详见 [当前状态](updated_vanda_two_accounts_20261111.md) 与 [恢复记录](updated_vanda_validation_recovery_20261112.md)。没有新增矩阵维度，进程×线程=请求核数、原五次计时和指标均保持。

## 审阅入口

- [完整 20,700 项状态与任务 ID](results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)
- [542 个当前资源组及性能/免费校验作业 ID](results/updated_vanda_scaling/git_sync_20261111/submitted_core_groups.csv)
- [各核心数主线的逐配置覆盖](results/updated_vanda_scaling/git_sync_20261111/cpu_core_layouts.csv)
- [覆盖汇总及快照时间](results/updated_vanda_scaling/git_sync_20261111/handoff_summary.json)
- [主账号 PBS 快照](results/updated_vanda_scaling/git_sync_20261111/queue_xtt_ella.json)
- [分担账号 PBS 快照](results/updated_vanda_scaling/git_sync_20261111/queue_hongxinran.json)

复核完整目标的命令：

```bash
python3 scripts/audit_fixed_matrix.py vanda \
  results/updated_vanda_scaling/20261106T185006Z \
  --reuse-root results/updated_vanda_scaling/20261102T092147Z \
  --reuse-root results/updated_vanda_scaling/20261111_hongxinran_assist \
  --include-additional-512
```

不带新增参数仍输出原 19,980 口径，便于追溯。新增参数只扩展审计范围，不会提交性能作业或改写计时。
