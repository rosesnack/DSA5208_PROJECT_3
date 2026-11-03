# Updated experimental conclusions (1 November 2026)

This is the 1 November local-result snapshot. For the later Vanda submission state, see [the 2 November run status](updated_vanda_run_status_20261102.md).

This snapshot extends the [31 October local report](updated_experimental_conclusions_20261031.md) without replacing its earlier three-graph results. The new Release run covers **42 fixed graphs** on the Mac and **12 local weak-scaling graphs**. The three 12.8-million-vertex fixed graphs, 256/512-core scaling, CUDA, and Vanda runtimes remain unmeasured in this snapshot. The required Atlas/Vanda figures therefore cannot yet be drawn from these local results.

## Reproducible local protocol and validation

- Apple M5 MacBook Air: 10 cores (4 performance, 6 efficiency), 16 GB RAM, Darwin 25.6.0. Clang 23.1.4, MPICH 5.0.2 with `FI_PROVIDER=sockets`, Kokkos 4.5.01, CMake Release build.
- Same PageRank algorithm, graph generator seed 5208, one warm-up, five measured solves, and median solve time for all methods. MPI graph loading, distribution, and Halo setup are excluded from `solve_s`; Halo setup is recorded separately.
- Fixed graphs: original `google`, `uniform`, `hub`; three canonical synthetic graphs; three synthetic families × four vertex counts × three mean degrees. Local weak graphs: three families × p=1/2/4/8, with 50,000 vertices and 800,000 edges per rank.
- Both MPI modes use the same graph, process/thread count, build, and repetition rule. Independent Python validation checks raw-edge degrees and PageRank residuals, rank mass, history and timing records, and complete rank-vector agreement with same-environment Serial. Weak runs additionally compare Allgatherv and Halo ranks directly.

| Local run | Validation checks | Failures |
|---|---:|---:|
| Fixed Serial, OpenMP, Kokkos OpenMP | 378 | 0 |
| Fixed pure MPI and MPI+Kokkos OpenMP, both modes | 672 | 0 |
| Fixed MPI+OpenMP Hybrid, both modes | 840 | 0 |
| Weak Serial, OpenMP, Kokkos OpenMP | 108 | 0 |
| Weak pure MPI, MPI+Kokkos OpenMP, and Hybrid, including paired mode checks | 162 | 0 |
| **Total** | **2160** | **0** |

The full local results and machine metadata are in [`results/updated_local_macos/20261031_full_cpu_kokkos45/`](results/updated_local_macos/20261031_full_cpu_kokkos45/) and [`results/updated_local_macos/20261031_weak_cpu_kokkos45/`](results/updated_local_macos/20261031_weak_cpu_kokkos45/). Each result has five raw timing rows. The large per-vertex rank CSVs remain on disk for reproducibility but are ignored by Git.

## What the local measurements show

Across the 42 fixed graphs, the median speedup relative to same-build Serial is 1.90× at OpenMP T=2, 3.12× at T=4, and 3.10× at T=8. Standalone Kokkos OpenMP gives 1.53×, 1.96×, and 2.31× at those thread counts. For MPI+OpenMP on one rank, changing T=1 to T=4 gives a median 2.44× improvement across the fixed graphs; at p=4, changing T=1 to T=2 gives only 1.01×. More local threads help most when MPI communication is small.

Halo reduces the **median counted iterative MPI payload** across the fixed graphs by 6.6% at p=2, 34.0% at p=4, and 58.5% at p=8. For pure MPI, Halo is faster on 21/42, 29/42, and 23/42 fixed graphs at those p values; for MPI+Kokkos OpenMP, on 23/42, 26/42, and 32/42. At p=1 there is no remote payload, and Halo is usually slower because its setup has no communication to save. The Google p=8 pure-MPI example has 49.0 MB/iteration and 19.70 s with Allgatherv, versus 20.3 MB/iteration, 5.74 s, and 0.21 s setup with Halo. These are local observations only.

The weak graphs show why payload savings and time gains must be reported separately. Across the three weak families, Halo saves a median 0.0% of counted bytes at p=2, 10.3% at p=4, and 43.3% at p=8. At p=8 its median Allgatherv/Halo solve-time ratio is 1.95× for pure MPI and 1.65× for MPI+Kokkos OpenMP; at p=4 both methods' median ratio is below 1. The per-iteration weak efficiency relative to p=1 is about 0.006 for pure MPI Allgatherv at p=8 and 0.012 for Halo. This is **single-Mac process scaling**, not evidence of Vanda weak-scaling efficiency.

Local MPI timing variability is substantial. For the 42 fixed graphs at p=8, 22 pure-MPI Halo configurations have a maximum/minimum ratio above 2 across their five measured repeats; one ratio reaches 47.9. MPI+Kokkos Halo has 19 such configurations. The median remains the specified estimator, but p=8 performance differences are not stable enough to support a broad cluster conclusion. The original raw timing rows are retained so these cases can be inspected rather than hidden.

## Remaining required experiments

The Vanda scripts now add a separate **16-node × 32-core = 512-core** CPU endpoint after the original 1–8-node matrix. Fixed G45 graphs stay identical to the 256-core strong-scaling inputs. Pure MPI and MPI+Kokkos OpenMP use p=512/T=1; MPI+OpenMP tests p=512/T=1 and p=128/T=4. Weak scaling adds three p=512 graphs, each with 25.6 million vertices and 409.6 million edges; the three families have separate 24-hour jobs. Hybrid T=4 extends to p=128. All these MPI configurations run both Allgatherv and Halo. The 512-core point exceeds the lecture's “at least 256 CPU cores” target; it is not a minimum required for every run.

The 512-core scripts have passed shell/Python syntax checks but have **not** been submitted or measured on Vanda. The 45-graph Vanda CPU/GPU matrix, CUDA and Kokkos CUDA builds, multi-node runtimes, required Atlas/Vanda figures, and final PDF report remain pending. The original Git results and the previous updated snapshot are preserved. AI assistance was used for code changes, experiment orchestration, validation, and interpretation; disclose this in the final report after student review.
