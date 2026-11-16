# Remaining 512-core work

Latest operational update: 17 November 2026, 01:00 SGT. Job 1560661 is now user-held to prevent output failure while xtt_ella scratch is not writable (errno 28). Do not release it before storage recovery; see [incident details](PERFORMANCE_INVESTIGATION.md). The older scheduling snapshot below is from 16 November 14:21 SGT. No 512-core result is included
in the non-512 report, tables or figures.

The full 512 fixed target is 1,170 cells. Five previously valid cells are retained
in the result archive. The other 1,165 consist of 48 newly registered cells, five
legacy held cells and 1,112 not currently scheduled.

## Newly registered batch

| Graph | Cells | Paid performance | Free validation | Dependency |
|---|---:|---|---|---|
| grid_controlled_n50000_d4 | 16 | 1560661 | 1560662 | Successful environment check 1560492 |
| grid_uniform_n50000_d4 | 16 | 1560663 | 1560664 | afterok1560662 |
| grid_hub_n50000_d4 | 16 | 1560665 | 1560666 | afterok1560662 |

Owner: xtt_ella, project personal-xtt_ella. Each group requests eight CPU nodes,
64 cores per node, 512 total, and one hour walltime. For both MPI+OpenMP and
MPI+Kokkos OpenMP it runs p/T=256/2, 64/8, 32/16 and 16/32, each with Allgatherv
and Halo. Every layout uses p*T=512. One warm-up and five timed runs are preserved.

The maximum new walltime reservation is 1,536 CPUh, not an estimate of actual
consumption. Submission used the verified balance of 4,861.854 CPUh, reserved all
other live requests and a further 256 CPUh margin. This does not authorize
additional submissions without a fresh balance and cross-account overlap check.

The first group is Q; the others are dependency-held. The snapshot has no
available physical host meeting the 64-core/memory chunk requirement. The
controller preserves node/core/memory/walltime parameters when refreshing host
bindings. It must not substitute 16x32 or oversubscription for the required 8x64.

The scoped monitor's last recorded PID is 1301843; its deadline is 16 November
23:59 SGT. After the deadline, inspect live jobs and existing registry before
starting a controller again. Archived final PBS states were restored from saved
observations because the server purged some older completed job IDs.

## Evidence and restrictions

- [48-cell source plan](../results/updated_vanda_scaling/20261106T185006Z/endpoint512_plan_20261116.json)
- [Submission receipt and resource checks](../results/updated_vanda_scaling/20261106T185006Z/endpoint512_submission_20261116.json)
- [Monitor restart record](../results/updated_vanda_scaling/20261106T185006Z/monitor_endpoint512_20261116/restart.json)
- [Physical capacity observation](../results/updated_vanda_scaling/endpoint512_20261116/capacity_1419.json)
- [Unique full-target ownership](../results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv)

Do not release legacy job 1532794 or the old hongxinran held requests as a batch.
Their source plans predate the present ownership/deduplication records. Controlled
rank-based 512 weak results also need their existing remote evidence checked
before being classified as missing. Already validated or in-flight cells cannot
be assigned to a teammate without an explicit, recorded owner transfer.
