# Performance anomaly investigation

Evidence checked on 16 November 2026. This investigation is additional to the
completed non-512 matrix. No historical measurement is overwritten, deleted or
reclassified as a newly validated reproduction. Numerical correctness does not
by itself establish that a performance result is free of placement or timing issues.

## Findings and confidence

| Observation | Supported finding | Still unresolved |
|---|---|---|
| Google OpenMP/Kokkos, 16 to 32 threads | Both backends slow in every saved repeat. PBS job 1510598 allocated 32 CPUs on Platinum 8452Y; OpenMP reports 32 actual threads. It is not a median arithmetic error or a single outlier. | Original standalone script did not explicitly control binding/wait policy or save each thread's affinity. A 32-thread team does not prove 32 distinct physical cores were used. NUMA, thread runtime and interference remain hypotheses. |
| Large Uniform MPI Halo, 128 ranks | Five times are 3.669-3.730 s. Median communication timing is 3.508 s versus solve 3.696 s; median per-run ratio is 94.9%. Max/mean incoming edges is approximately 1.002. Major partition imbalance does not explain this spike. | Collective waiting, runtime/transport selection, placement and other-job interference cannot be separated using the saved aggregate timers. Do not claim measured network congestion. |
| Uniform weak scaling, 256 MPI ranks | Balanced edges: max/mean 1.002. Allgatherv is 1.141 s with 1.029 s communication median; Halo is 0.531 s with 0.457 s communication median. | Independent allocations are needed to quantify environmental variability. |
| Hub/Controlled weak scaling | Max/mean edge work is 75.00/77.51. Equal vertex partitions are severely unequal in edge traversal work. | Aggregate communication timers include ranks waiting for slow computation; they do not isolate a network bottleneck. |
| Fixed 256 cores, different p/T | Existing analysis pairs the same graph, method, nodes and communication. Ratio direction and geometric averaging were checked. Reducing ranks changes collective participants and local work. | Large paired ratios are observations, not proof that all gains arise solely from fewer messages. |

The solver review found synchronous old/new rank buffers, global convergence,
correct source-contribution exchange and maximum-rank solve timing. Independent
saved rank/residual checks and recomputed five-run medians pass. No algorithmic
correctness bug was identified in the reviewed paths. This is not a proof that
all performance or runtime configuration bugs are absent, nor evidence of a
mistake introduced by the user's manual actions.

## Mechanisms established from code and metadata

Allgatherv sends a full contribution vector to every rank. In the rank-normalized
Uniform weak series, total vertices grow with p while owned edges per rank stay
approximately constant. At p=256, the logical aggregate payload per iteration is
26.112 GB for Allgatherv and 1.632 GB for Halo. These are algorithm-level bytes,
not measured network-wire traffic. Halo still uses an all-rank Alltoallv, packing
and two global reductions per iteration. Keeping local edge count constant does
not keep communication or synchronization constant.

The generator concentrates destination vertices in a contiguous low-ID hub
region, while MPI divides contiguous destination IDs. This directly creates the
measured edge imbalance. OpenMP uses dynamic chunks of 64 vertices; Kokkos uses
a RangePolicy without an explicit dynamic schedule. Their behavior on skewed
rows is therefore an implementation design comparison, not evidence that Kokkos
or OpenMP must inherently be faster.

A communication timer includes local packing/copies and time waiting inside MPI.
Solve time and communication time use separate maxima across ranks. Their ratios
are useful diagnostics but cannot be decomposed into additive critical-path
percentages or pure network utilization.

## Targeted independent reproduction

Existing Release binaries are reused and their SHA-256 values recorded. Every
case retains one warm-up and five timed runs, original tolerance and iteration
cap. Serial reference vectors are reused; no Serial performance rerun is added.

| Scope | Paid performance | Layout / walltime | Free independent validation |
|---|---|---|---|
| Google thread anomaly | 1567277 | 1 node, 32 CPUs, 30 minutes | 1567278, afterok performance |
| Uniform Halo anomaly | 1567279 | 4 nodes, 32 CPUs/node, 128 ranks, 45 minutes | 1567280, afterok performance |

Maximum new paid reservation: 112 CPUh. Balance before submission: 4,861.854 CPUh.
The Google job tests explicitly unbound/default waiting and spread binding with
ACTIVE/PASSIVE waiting, for OpenMP and Kokkos at 16/32 threads. The unbound
OpenMP case also keeps the original 1/2/4/8/16/32 order to test thread-team history.
This reconstructs known settings; the original inherited environment is unknown.
OMP display output records runtime settings and affinity outside the solve clock.
The MPI job records 128 distinct one-core rank affinities on four hosts and
repeats the same p128 Halo layout. Hardware is checked against Platinum 8452Y.
All result files use a separate investigation directory and remain outside the
main report until independently validated and reviewed.

At 21:17 SGT both performance jobs were Q and both validators dependency-held.
The placement check found zero eligible known hosts with 32 free CPUs and the
scheduler-required memory. It made no layout changes. PBS increased the submitted
64 GB/node request to 222 GB/node; therefore the displayed memory reservation is
not solely the script's explicit request. No reproduction has finished yet.
Do not interpret the queued investigations as confirmation of a root cause.

## How to inspect and reproduce the evidence

- [Historical timings and derived diagnostics](../results/updated_vanda_scaling/performance_investigation_20261116/historical_evidence.json)
- [Submission receipt](../results/updated_vanda_scaling/performance_investigation_20261116/submission.json)
- [Queue snapshot](../results/updated_vanda_scaling/performance_investigation_20261116/queue.json)
- [Placement capacity check](../results/updated_vanda_scaling/performance_investigation_20261116/placement.json)
- [Evidence analysis script](../scripts/audit_performance_anomalies.py)
- [Compute/validate driver](../scripts/investigate_performance.py)

Run `python3 scripts/audit_performance_anomalies.py` locally to recompute the saved
evidence without submitting a benchmark. On Vanda, check `qstat -u xtt_ella` and
the receipt's destination paths. `compute_complete.txt` is only a measurement
completion marker; `validate_complete.txt` is written only after the independent
validators pass. A reproduction's interpretation must also review its hardware,
thread/rank affinity and five timing observations before using it in conclusions.

## Two-account update, 21:34 SGT

Google performance 1567277 and independent free validation 1567278 both finished
with Exit 0. Performance walltime was 67 seconds, allocated 32 CPUs (about
0.596 allocated CPUh). All 16 result configurations were downloaded with timings,
histories, numerical reports, environment, binary hashes and affinity output.
Local recomputation confirms every five-run median and numerical bound.

| Thread policy | OpenMP T16 / T32 seconds | Kokkos T16 / T32 seconds |
|---|---|---|
| Unbound, default waiting | 0.188906 / 0.124646 | 0.180557 / 0.103958 |
| Spread, active waiting | 0.176530 / 0.120280 | 0.153480 / 0.086686 |
| Spread, passive waiting | 0.177041 / 0.142752 | 0.166063 / 0.115531 |

The old 32-thread cliff did not reproduce, even in the unbound case. This
weakens an explanation based on an inevitable graph/algorithm scaling limit.
It does not establish binding as the sole cause: host, allocation and execution
time also changed. Preserve the old records as environment-sensitive observations;
do not silently replace the full matrix with the fastest reproduction.

- [Downloaded Google evidence](../results/updated_vanda_scaling/performance_investigation_20261116/google/)
- [Reproduction medians](../results/updated_vanda_scaling/performance_investigation_20261116/google/reproduction_summary.json)

The four-node p128 Uniform reproduction remains Q on xtt_ella. On hongxinran,
three additional eight-node, 256-core diagnostic groups are now registered:

| Graph | Paid performance | Free validation | Cases | Walltime |
|---|---|---|---:|---|
| Large Uniform | 1567383 | 1567384 | 14 | 1 hour |
| Large Hub | 1567385 | 1567386 | 2 | 45 minutes |
| Large Controlled | 1567387 | 1567388 | 2 | 45 minutes |

Every group includes pure MPI p256,T1 with both communication modes. Uniform
also tests MPI+OpenMP and MPI+Kokkos OpenMP with p/T=256/1,16/16,8/32, each with
both modes. All cases use exactly 256 active CPU cores on eight nodes, keeping
32 cores/node. This independently checks the large-input endpoint mechanisms and
selected fixed-core decomposition gains. Historical weak baselines are reused;
these strong-graph labels are not added as new points in the weak suite.

The added reservation is at most 640 CPUh against the verified hongxinran balance
of 1,061.444 CPUh. The existing xtt_ella diagnostic reservation was at most 112
CPUh. Neither number is actual consumption. All new validators use auto_free.
At 21:34 all three hongxinran performance jobs were Q, validators dependency-held;
node-placement checks made no changes. No old held batch was released and no
completed main-matrix configuration was scheduled as a missing cell.

- [hongxinran submission and owners](../results/updated_vanda_scaling/performance_investigation_20261116/submission_hongxinran.json)
- [hongxinran queue snapshot](../results/updated_vanda_scaling/performance_investigation_20261116/queue_hongxinran_latest.json)
- [xtt_ella queue snapshot](../results/updated_vanda_scaling/performance_investigation_20261116/queue_xtt_ella_latest.json)
- [256-core diagnostic driver](../scripts/investigate_256.py)

## Same-queue placement control, 22:38 SGT

The user explicitly requested resource/host adjustments without changing queues.
Both accounts now run a bounded host-placement controller every 60 seconds until
17 November 06:00 SGT. It handles only the four unfinished diagnostic performance
groups, keeps batch_cpu, all rank/thread/core/node counts, memory, walltime and
communication cases, and selects only previously verified Platinum 8452Y hosts.
The completed Google job and dependent validators are not resubmitted. Existing
512-core work remains under its separate controller and was not changed here.

The 22:37 physical-host check summed NUMA vnodes rather than treating every vnode
as a separate machine. In cpu_all no physical host had 32 free CPUs; the maximum
was 20. In gpu_all no host had 32 free CPUs either. Hence no immediate compatible
host rebinding was possible, and no resource mutation was made. Lowering memory
alone would not solve this CPU shortage. A PBS `free` state denotes a schedulable
vnode, not an entirely idle physical host.

Both controller startup checks succeeded. Their status and bounded scope are in
[xtt_ella](../results/updated_vanda_scaling/performance_investigation_20261116/placement_watch_xtt_ella.json)
and [hongxinran](../results/updated_vanda_scaling/performance_investigation_20261116/placement_watch_hongxinran.json).
These are login-node controllers only: they query PBS and update queued host
bindings, never execute PageRank kernels or consume a performance allocation.
For an early stop, create `STOP` in the account's
`results/updated_vanda_scaling/performance_investigation_20261116/placement_watch/`.
The controller will also exit when all its registered performance jobs finish.

The paid queue permits at most 720 running CPUs per user. Thus the three new
hongxinran groups, 256 CPUs each, cannot all run simultaneously under that limit;
at most two can run together. At the current zero-running snapshot, that limit
is not the immediate reason they are queued.

## Overnight measurements and storage incident, 17 November 01:00 SGT

All three hongxinran performance jobs completed with Exit 0. Uniform 1567383
used 17m54s; Hub 1567385 used 5m47s; Controlled 1567387 used 4m43s. Hub validation
1567386 and Controlled validation 1567388 also completed with Exit 0. Uniform
validation 1567384 is still running. Eighteen measurement sets, their five-run
timings, mappings and existing validator outputs have been downloaded. Local
median and numerical-summary checks pass; the 14 Uniform sets are not yet counted
as independently complete. The node-placement controller exited after all its
registered performance jobs ended. These jobs stayed in batch_cpu; some physical
hosts were allocated using portions of both NUMA vnodes.

Pure MPI p256 reproductions: Uniform Allgatherv/Halo 1.053/0.554 s (validation
pending), Hub 8.932/9.469 s, Controlled 6.598/6.879 s. These are independent
observations; no historical report table has been silently replaced.

xtt_ella's p128 job 1567279 started at 23:42 and exited 1 after 1m54s. All five
solve observations were saved (median 3.165987798 s), and the rank vector ends at
vertex 12,799,999. History and the original summary were not saved. Single-byte
write probes in both scratch project/result directories returned errno 28,
`No space left on device`. This is an output/storage failure, not a walltime
termination. Its dependent validation did not run. The measurement is retained
as incomplete evidence and is excluded from full-completion counts.

Free recovery validator 1569085 reads the existing vector and timings, independently
checks degrees/residual/Serial agreement from the edge list, and writes to the
writable home filesystem. It never invents the missing convergence history.
Even a passing numerical recovery report will explicitly retain the missing
history flag; it is not the ordinary complete validation marker.

A bounded relocation attempt copied one already validated new Google vector
(29,913,145 bytes) to home and verified its SHA-256 before removing the scratch
copy. Scratch then refused the replacement symlink with errno 28. The bytes are
retained in home; the original path has not yet been restored. No additional
vector was moved and historical result/reference vectors were untouched. The
alternate path and digest are in the incident receipt. This attempt did not
restore scratch writability. Do not repeat broad cleanup or delete old vectors.

To prevent another output failure, pending 512 job 1560661 was explicitly
user-held; its two follow-on jobs remain dependency-held. Restore writable output
storage and inspect the original assignment before releasing that user hold.
No running performance job was killed, no queue was changed, and no paid
recomputation was submitted for the p128 failure.

- [hongxinran measurements and proofs](../results/updated_vanda_scaling/performance_investigation_20261116/hongxinran/)
- [hongxinran completion snapshot](../results/updated_vanda_scaling/performance_investigation_20261116/completion_hongxinran_latest.json)
- [Storage incident, retained alternate path and checksum](../results/updated_vanda_scaling/performance_investigation_20261116/space_incident_20261117.json)
- [Free recovery submission](../results/updated_vanda_scaling/performance_investigation_20261116/recovery_submission_20261117.json)


## Final independent test and report snapshot, 17 November 02:01 SGT

The storage-affected xtt_ella p128 recovery validator 1569085 exited 0 and found
zero L1 rank error, but the original summary/history remain missing. Its receipt
explicitly marks canonical_validation_complete false. This incomplete observation
is preserved as evidence and is not selected into the scientific report.

At the user's request, the final p128 test used hongxinran home output after a
free 1 GiB write/fsync preflight (1569194, Exit 0). Paid batch_cpu performance
1569195 used four Platinum 8452Y nodes with 32 cores each, p128,T1,Halo, and
finished in 2m07s. Free independent validator 1569196 finished in 20m06s, Exit 0.
Original summary, history, all five timings and validation proof are complete.
Median solve is 4.296756030 s, communication median 4.122365467 s, independent
residual 1.4262839174e-9, rank-sum error 2.22e-16 and full-vector Serial L1 error
zero. The summary communication_max_s stores the last measured run (4.160842671 s),
not its five-run median; report phase statistics are recomputed from timings.csv.
The slower point remains a valid final observation; timing localizes a
communication/synchronization bottleneck without uniquely proving network
congestion, affinity or an implementation defect. No further paid test was added.

The Uniform 256-core validation driver needed an explicit --threads argument
for threaded MPI+Kokkos cases. This only changes validation dispatch, not solver
or performance measurements. Five completed independent reports were reused.
Sequential validators were retired and nine remaining cases were validated in
parallel on auto_free (1569272 through 1569280), all Exit 0; free aggregator
1569281 checked all 14 reports and wrote the complete marker. Hub and Controlled
remain independently complete. No additional paid computation was needed.

The selected report sources are deterministic: Google uses unbound_default
OpenMP T1..32 and Kokkos T16/32; the 18 complete hongxinran diagnostic cases and
this final p128 observation replace matching main-table sources. The 27 selected
cells retain source and validation job identifiers. Selection does not choose
between runtime policies by speed. All tables, ratios and figures are regenerated
from the selected five-run medians. The paper presents the final measurements
without a troubleshooting chronology; source records and this operational log
retain provenance. Five historical valid 512-core cells are a separate incomplete
supplement, excluded from main-matrix aggregates. At 02:01 the remaining new
512 jobs were H(u)/H(d)/H(d); storage recovery is still required.

- [Final p128 submission](../results/updated_vanda_scaling/performance_investigation_20261116/final128_submission_20261117.json)
- [Final p128 measurements and validation](../results/updated_vanda_scaling/performance_investigation_20261116/final128/results/)
- [Parallel free validation receipt](../results/updated_vanda_scaling/performance_investigation_20261116/validation_parallel_20261117.json)
- [Final completion snapshot](../results/updated_vanda_scaling/performance_investigation_20261116/report_validation_status_latest.json)
- [Remaining 512 holds](../results/updated_vanda_scaling/performance_investigation_20261116/remaining_512_status_20261117.json)
