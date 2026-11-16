# Vanda status

Snapshot: 16 November 2026, 14:19-14:21 SGT. Query live PBS before changing an
assignment; this file does not replace the scheduler.

All **19,530 non-512 fixed-graph configurations** have completed performance runs
and independent validation. The result summaries, original five-run timings,
validation markers, hardware/mapping and source-job evidence are downloaded.
There are no outstanding non-512 fixed-graph performance or validation jobs.

The full fixed-graph audit is **19,535/20,700**, including five valid historical
512-core cells. The report deliberately uses only the 19,530 non-512 cells.

| Remaining fixed-graph work | Configurations | Action |
|---|---:|---|
| New 512-core first group | 16 | Job 1560661 queued |
| New 512-core follow-on groups | 32 | Jobs 1560663/1560665 depend on free validation 1560662 |
| Legacy 512-core group | 5 | Job 1532794 remains user/system-held; do not release blindly |
| Other deferred 512-core targets | 1,112 | Not currently scheduled |
| Total remaining | 1,165 | All are 512-core targets |

The first new 512 job is queued for an eight-node, 64-core-per-node allocation.
At the snapshot, the CPU pool had no physical host with both 64 available cores
and the required memory; the largest free CPU count was 36. The queue comment
reports a placement-set/switch resource constraint. There is no evidence here of
a budget rejection or a reason to change the target layout silently.

The two-account monitors were alive. The hongxinran controller had no eligible
unregistered non-512 work. The scoped xtt_ella 512 controller checks every minute
until 16 November 23:59 SGT. The two follow-on jobs are governed by PBS dependencies
and cannot start before the first new free validation succeeds.

The separate non-512 weak inventory is complete: 150 rank-CPU, 84 core-CPU and 138
GPU-node entries/controls. Controlled rank-based 512 weak evidence still requires
inspection before any rerun; it is outside the report and fixed-graph count.

See the [report](../reports/non512/README.md), [handoff](../HANDOFF_VANDA_EXPERIMENTS_20261106.md),
[512 batch](VANDA_512.md), and [saved queue/capacity evidence](../results/updated_vanda_scaling/endpoint512_20261116/).
