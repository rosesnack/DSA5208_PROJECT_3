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
