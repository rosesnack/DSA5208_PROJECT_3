# Updated experimental conclusions (31 October 2026)

This update records the refreshed local CPU experiments completed on 31 October. It preserves the repository's original `results/` data and keeps this local run separate from the Vanda measurements, which are still queued. Full CSVs, validation JSON, raw timing records, and machine/build metadata are in [`results/updated_local_macos/20261031_clang23/`](results/updated_local_macos/20261031_clang23/).

## Refreshed local protocol

- Apple M5 MacBook Air, 10 physical/logical cores, ARM64 macOS 25.6.
- Release build, Clang 23.1.4 through local MPICH 5.0.2, CMake 4.4.4. The same compiler/build was used for Serial, OpenMP, MPI, Hybrid, and Kokkos OpenMP in this run.
- One warm-up and five measured runs per configuration; median solve time is reported.
- PageRank damping factor 0.85, L1 convergence tolerance `1e-8`, uniform initial ranks, and dangling-mass redistribution.
- Datasets: SNAP web-Google (875,713 vertices, 5,105,039 directed edges), plus the existing 100,000-vertex/1,000,000-edge Uniform and Hub graphs.
- MPI and Hybrid process counts were 1, 2, and 4 on this single workstation. OpenMP used 1, 2, 4, and 8 threads. The Vanda job includes p=8 and is the source of the required cluster measurements once it runs.
- Timings measure the iterative solve as described in the README; graph loading, MPI graph distribution, and output are excluded.

## Validation

| Implementation | Configurations checked | Result |
|---|---:|---:|
| Serial | 3 datasets | 3/3 pass |
| OpenMP | 1/2/4/8 threads × 3 datasets | 12/12 pass |
| MPI Allgatherv | p=1/2/4 × 3 datasets | 9/9 pass |
| MPI halo | p=1/2/4 × 3 datasets | 9/9 pass |
| MPI + OpenMP Hybrid | (p,t)=(1,1/2/4/8),(2,1/2/4),(4,1/2) × 3 datasets | 27/27 pass |
| Kokkos OpenMP | 3 datasets | 3/3 pass |

Independent residual checks pass for every result, and full rank-vector L1 differences from the refreshed Serial output are below `5.3e-15` for the measured parallel implementations. The Google graph converged in 90 iterations (residual `7.52e-9`); Uniform in 15 (`1.54e-9`); Hub in 16 (`2.01e-9`). The JSON validation files contain per-configuration checks.

## OpenMP and Kokkos OpenMP

| Dataset | Serial (s) | OpenMP 1/2/4/8 threads (s) | Best OpenMP speedup | Kokkos OpenMP (s) | Kokkos speedup vs same Serial |
|---|---:|---|---:|---:|---:|
| Google | 0.6771 | 0.6470 / 0.3403 / 0.1991 / 0.1568 | 4.32× at 8 threads | 0.2151 | 3.15× |
| Uniform | 0.01218 | 0.01293 / 0.00702 / 0.00415 / 0.00453 | 2.94× at 4 threads | 0.00355 | 3.43× |
| Hub | 0.01510 | 0.01447 / 0.00738 / 0.00450 / 0.00502 | 3.36× at 4 threads | 0.00903 | 1.67× |

Using one compiler/build for this run makes these local comparisons internally consistent, including the Kokkos OpenMP baseline. The larger Google graph benefits from 8 threads, while the smaller synthetic graphs peak at 4 threads; at 8 threads, thread scheduling and synchronization costs reduce their gains. On Google, the 8-thread OpenMP efficiency is about 54% (speedup divided by 8). These are workstation measurements, not Vanda scaling claims.

## MPI communication choice

Google graph measurements:

| MPI processes | Allgatherv (s) | Halo (s) | Allgatherv payload / iteration (bytes) | Halo payload / iteration (bytes) | Halo setup bytes |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.7123 | 0.7120 | 0 | 0 | 0 |
| 2 | 0.6329 | 0.6074 | 7,005,704 | 5,062,024 | 5,062,024 |
| 4 | 3.8195 | 4.3010 | 21,017,112 | 12,129,848 | 12,129,848 |

Halo lowers the counted iterative payload by 27.7% at p=2 and 42.3% at p=4 for Google. Its setup sends the distinct remote source IDs once; the table's iterative payload excludes that setup. MPI collectives also reduce dangling mass and convergence error, so payload bytes alone do not account for all communication. Despite reducing bytes, halo is slower at p=4 on this workstation. Both MPI methods are much slower than Serial at p=4 here, including on the smaller graphs. This shows the cost of running multiple MPI processes on this single-node laptop and should not be generalized to a multi-node cluster. At p=2 on Google, both methods have modest speedup (1.07× Allgatherv; 1.11× halo). Full per-dataset MPI timings are in the two `scaling.csv` files.

## Hybrid MPI + OpenMP

On the Google graph, the best measured Hybrid result is one MPI process with four OpenMP threads: 0.2828 s, 2.39× speedup, and 60% efficiency by total threads. One process/eight threads takes 0.2263 s (2.99×, 37% efficiency). Two MPI processes do not improve this result on the workstation, and p=4 configurations are particularly slow. The synthetic graphs are small and show limited benefit from combining process and thread parallelism. These results document the tested configurations; the Vanda run will determine cluster behavior with p=8 included.

## Data and current interpretation

The Google graph is substantially larger than either synthetic graph, and its 90 PageRank iterations make parallel work more visible than on the 15–16 iteration synthetic runs. OpenMP gives the clearest local scaling result. MPI tests the intended distributed decomposition and communication strategies, but this single-node laptop is not a suitable basis for claims about inter-node performance. Halo demonstrates the intended reduction in iterative payload, while its setup and communication latency prevent a runtime win at p=4 here. Kokkos OpenMP is now compared against a Serial implementation built with the same compiler configuration; its speedups are local reference measurements and still need comparison with the Vanda GCC build.

## Vanda and remaining experiments

The full CPU and A40 GPU jobs are submitted and were still queued at the latest check (31 October, 02:14 +08): CPU `1508586.stdct-mgmt-02`, GPU `1508612.stdct-mgmt-02`. Vanda's login banner announced a maintenance window beginning 31 October at 18:00 +08, with access restoration on 2 November at 17:00 +08. Therefore this update contains no Atlas/Vanda runtime figures yet. The Vanda CPU job runs Serial, OpenMP, MPI Allgatherv/halo and Hybrid at p=1/2/4/8, and Kokkos OpenMP with GCC 13.3/Open MPI 4.1.8, Release, one warm-up, and five repeats. The A40 job runs native CUDA and Kokkos-CUDA against a same-build Serial reference. After completion, synchronize their outputs into `results/updated_vanda/<jobid>/` and `results/updated_vanda_gpu/<jobid>/`, then validate and add those separate cluster/GPU tables to the final report.

The original Git-tracked `results/` runs remain unchanged. Legacy three-repeat results, this refreshed Clang 23 workstation run, and the future Vanda GCC run must remain separate in performance comparisons because their platforms and compiler builds differ.

## AI use disclosure

AI assistance was used to inspect and modify the existing project, implement the halo/CUDA/Kokkos paths and experiment scripts, configure builds, run and validate experiments, and interpret results. The student should review the submitted source and report and ensure this disclosure accurately describes the group's use of AI.
