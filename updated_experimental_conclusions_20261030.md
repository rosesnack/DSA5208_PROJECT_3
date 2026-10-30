# Updated experimental conclusions (30 October 2026)

This is an update to the existing PageRank project results and README, not a replacement for the final coursework report. It records the changes made to the existing implementation and the measurements that were actually completed. The matched Release measurements below are preliminary ARM64 laptop results; the Vanda CPU and GPU jobs have been submitted but are still queued.

## Experimental setup

- Platform: Apple Silicon MacBook Air, ARM64; Release (`-O3 -DNDEBUG`); local MPICH 5.0.2. Serial/OpenMP/MPI used AppleClang 21. The Kokkos OpenMP build used Clang 23 to match the installed Kokkos/libc++ package.
- Data: the real Google web graph (875,713 nodes and 5,105,039 directed edges), plus the existing 100,000-node/1,000,000-edge Uniform and Hub synthetic graphs.
- PageRank: damping factor 0.85, L1 convergence tolerance `1e-8`, uniform initial ranks, dangling-mass redistribution, and convergence-based stopping. Timings use one warm-up and five measured runs, with the median reported.
- The results are stored under `results/local_macos/`; existing `results/` files were left intact. Build/run labels and full per-run output are retained in each result folder.
- Compiler, MPI, CPU/GPU, and Release build details are recorded as provenance, not treated as extra performance metrics. The refreshed Vanda CPU methods now use the same GCC 13.3 Release build and repeat protocol; CUDA uses NVCC 12.4 with GCC 13.3 as its host compiler.

## What changed in the existing code

- Added an optional MPI halo mode while retaining Allgatherv as the comparison baseline. Each rank precomputes its unique remote source-node IDs and edge lookup slots. Iterations exchange only those remote source contributions with `MPI_Alltoallv`; dangling mass and convergence still use global reductions.
- Added an optional native CUDA CSR-pull implementation with device-side reductions and host-side independent residual validation.
- Added an optional Kokkos implementation using the configured default execution space.
- Added communication/setup byte and time fields, build/environment labels, configurable output roots and repeat counts, MPI-subset validation, GPU validation, and Vanda CPU/GPU PBS scripts.

## Real-data result

The validated Google PageRank output contains 875,713 vertices and 5,105,039 directed edges, for a mean in/out degree of 5.83. The maximum in-degree is 6,326, showing a strongly skewed graph rather than a uniform workload. The highest-ranked vertex (ID 597621) has PageRank 9.24e-4, about 809 times the uniform mean rank; the top ten vertices together hold 0.806% of total rank mass. Their in-degrees range from 3,908 to 6,326, while their out-degrees range from 6 to 36. This is consistent with PageRank favoring destinations with many incoming links, while the iterative update still weights links by the source's rank. These figures describe this SNAP graph and this PageRank configuration; they do not identify real-world entities because the dataset uses numeric vertex IDs.

## Correctness validation completed

| Implementation and scope | Result |
|---|---:|
| Serial, all three graphs | 3/3 pass |
| OpenMP, 1/2/4/8 threads on all three graphs | 12/12 pass |
| MPI Allgatherv, 1/2/4 processes on all three graphs | 9/9 pass |
| MPI halo, 1/2/4 processes on all three graphs | 9/9 pass |
| Kokkos OpenMP, all three graphs | 3/3 pass |

The original repository outputs under `results/` also pass their current validators: Serial 3/3, OpenMP 12/12, MPI Allgatherv 12/12 (including p=8), and hybrid 30/30. Those are legacy local runs with three repeats and no compiler/build-type metadata, so they support correctness coverage but are not mixed into the matched Release scaling tables below.

The checks independently recompute the PageRank residual from the raw edge files, verify node IDs/degrees/rank mass/history/timings, and compare the complete saved rank vector with Serial. The maximum allowed full-vector L1 difference is `1e-8`. Observed cross-implementation differences were around `1e-15` or zero. Final residuals were approximately `7.52e-9` (Google), `1.54e-9` (Uniform), and `2.01e-9` (Hub), all within the configured stopping tolerance. Detailed reports are saved in `results/local_macos/{serial,openmp,mpi,mpi_halo,kokkos/OpenMP}/validation.json`.

## Local runtime and scaling

### OpenMP

| Graph | Serial (s) | 1 thread (s) | 2 threads (s) | 4 threads (s) | 8 threads (s) | Best measured speedup |
|---|---:|---:|---:|---:|---:|---:|
| Google | 0.689 | 0.652 | 0.377 | 0.270 | 0.203 | 3.39x at 8 threads |
| Uniform | 0.0133 | 0.0127 | 0.00698 | 0.00417 | 0.00459 | 3.18x at 4 threads |
| Hub | 0.0149 | 0.0157 | 0.00834 | 0.00463 | 0.00507 | 3.22x at 4 threads |

The Google graph continues to benefit from 8 threads, although efficiency is about 42%. The much smaller synthetic graphs peak at 4 threads and slow down at 8 threads, consistent with scheduling and synchronization costs becoming significant relative to useful work. These results are specific to this laptop and are not the required cluster scaling results.

### Kokkos OpenMP

| Graph | Kokkos median (s) | Rank-vector L1 error |
|---|---:|---:|---:|
| Google | 0.161 | `5.20e-15` |
| Uniform | 0.00352 | `5.85e-17` |
| Hub | 0.00867 | `5.11e-17` |

Kokkos ran with `OMP_NUM_THREADS=8`, one warm-up, and five measured runs. Its local wall times are not used to claim a speedup because the Serial baseline was built with AppleClang 21 while Kokkos was built with Clang 23 to match its conda-forge runtime. The independent PageRank residual check passed for all three graphs; the queued Vanda run will provide a matched GCC comparison.

### MPI Allgatherv and halo comparison

Google graph medians from the same five-run Release protocol:

| MPI processes | Allgatherv (s) | Allgatherv speedup | Halo (s) | Halo speedup | Payload bytes/iteration, Allgatherv → halo |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.825 | 0.84x | 0.712 | 0.97x | 0 → 0 |
| 2 | 0.660 | 1.04x | 0.593 | 1.16x | 7,005,704 → 5,062,024 |
| 4 | 3.727 | 0.18x | 5.768 | 0.12x | 21,017,112 → 12,129,848 |

For the two-process Google run, halo lowers counted iterative payload by 27.7%; the request-ID setup payload is 5,062,024 bytes once at startup. At p=4, payload falls from 21,017,112 to 12,129,848 bytes (42.3%). On the synthetic graphs at p=2, payload falls from 800,000 to 794,728 bytes on Uniform and from 800,000 to 653,224 bytes on Hub; at p=4 it falls from 2,400,000 to 2,203,912 bytes on Uniform and to 1,309,504 bytes on Hub. These payload counts exclude MPI collective/reduction traffic and protocol overhead. Equal-node-count contiguous partitioning leaves Google edge counts 12.2% apart at p=2 (2.41M vs 2.70M) and 19.7% apart at p=4 (1.20M vs 1.44M), so node balance does not imply work balance. On Google p=2, halo is faster than the Allgatherv run, but the local timings vary enough that this single-node result is preliminary. At p=4, halo sends fewer bytes but is slower than Allgatherv; reduced volume alone does not guarantee lower elapsed time. At p=4, local MPI is dramatically slower than Serial on every graph measured; this laptop result reflects process-launch, memory, and communication behavior and must not be generalized to Atlas/Vanda.

The refreshed matched Release local Allgatherv p=8 run did not finish in a reasonable time and was interrupted; its p=8 timing is omitted from the Release comparison. The legacy `results/mpi` p=8 result remains validated for correctness, but its timing is not comparable because its build metadata is absent and it used three measured runs. After reducing halo memory use, the refreshed halo p=1/2/4 sweep was rerun with five measured repeats and independently validated.

## GPU and cluster status

- CUDA source is present, but the local machine has no NVIDIA compiler/runtime/device, so it has not been compiled or run here.
- Kokkos Release configuration, compilation, execution, and correctness validation succeeded with the OpenMP execution space. LLDB traced the first build's startup crash to initialization of a global `const std::string` (`build_type`) under the mixed AppleClang/conda libc++ toolchain. Configuration values and the dataset list now use function-local static initialization; Kokkos was rebuilt with the Clang 23 toolchain matching its runtime. Kokkos-CUDA has not been built or measured.
- Vanda SSH access is now confirmed with the NUS-ID account `hongxinran`; the account was initialized on first login. CPU job `1508497` was replaced while still queued by synchronized job `1508586`, which builds Kokkos OpenMP and all CPU targets with GCC 13.3/Open MPI 4.1.8 in Release mode, then runs one warm-up and five measured runs for each configuration. GPU job `1508503` was replaced while still queued by job `1508612`; it runs native CUDA and Kokkos-CUDA on one A40 GPU, with the Kokkos-CUDA client compiled by `nvcc_wrapper` using GCC 13.3 as the host compiler. The environment log records GCC, NVCC, CMake, GPU, and module details. Both active submissions are in zero-charge queues (`cpu_parallel` and `gpu`, respectively) with `queue_charge_rate=0`; both remain queued and have not produced measurements. After they finish and validate, `scripts/sync_updated_vanda_results.sh` will place their outputs in local `results/updated_vanda/<jobid>/` and `results/updated_vanda_gpu/<jobid>/`, leaving the old Git-tracked result folders intact. The login banner announced a cluster access stop on 31 October at 06:00 and service restoration on 2 November at 17:00; queued/running work may therefore be interrupted around that maintenance window. No Atlas/Vanda timings are included until the PBS jobs complete and their outputs validate.
- The configured Google Cloud project `dsa5208p` has zero L4 quota in `asia-southeast1`, but the region has one P4 quota and a P4 accelerator type. I attempted to start a separate preemptible P4 VM using the current CUDA 12.9 Deep Learning image; Google rejected VM creation because the project's billing account is on the Free Tier, which does not permit non-TPU accelerators. The earlier one-L4 quota request (`pagerank-l4-asia-southeast1`) was also granted value zero. A follow-up instance listing confirmed that no P4 VM exists; no GPU compute charge was incurred.

## Current conclusion and remaining report work

The existing Serial/OpenMP/MPI implementations, new halo mode, and Kokkos OpenMP backend produce numerically correct PageRank results on all tested local configurations. OpenMP shows useful local speedups, especially on the larger real graph; no local Kokkos speedup is claimed because it used a different compiler from the Serial baseline. The halo extension reduces iterative communication volume, but p=4 local timings remain much slower than Serial and do not demonstrate cluster scaling. The project's MPI scaling conclusion therefore remains open until the matched suite is run on Vanda. Native CUDA and Kokkos-CUDA still lack successful GPU correctness/performance runs.

For the final coursework report, replace or supplement the laptop figures with the submitted Vanda Release CPU and GPU runs once they finish, including p=1/2/4/8, both MPI communication modes, the hybrid sweep, Kokkos OpenMP, and machine/compiler/MPI/resource details. The current CPU PBS request uses one compute node, so describe its MPI results as single-node scaling; a multi-node MPI run would strengthen network-scaling claims if the queue permits, but is not required to report these measurements honestly. The Vanda GPU job is set to build and validate native CUDA and Kokkos-CUDA against the same Serial reference, recording solve, device, and transfer timings. Preserve the successful validation JSON and CSV files with the submission, then assemble these conclusions and the measured tables into the required PDF.

## AI use disclosure

AI assistance was used to inspect and modify the existing project, implement the halo/CUDA/Kokkos paths and experiment scripts, debug the local build/runtime setup, and interpret the measurements. The submitted report and source should be reviewed by the student, and this disclosure should be edited to match the actual extent of assistance used by the group.
