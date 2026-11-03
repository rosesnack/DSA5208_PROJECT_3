# Vanda run status — 2 November 2026, 23:43 SGT

Run ID: `20261102T092147Z`. Remote repository: `/scratch/hongxinran/DSA5208_PROJECT_3`. PBS project: `personal-hongxinran`. The authoritative live status is `python3 scripts/check_vanda_progress.py 20261102T092147Z --qstat` on Vanda.

| Stage | Validated batches | Submitted batches |
|---|---:|---:|
| Data, Release builds, CPU/GPU smoke, MPI layout, CPU affinity | 8 | 8 |
| Fixed-graph Serial/OpenMP/Kokkos OpenMP | 9 | 45 |
| Six fixed graphs (original three plus three canonical synthetic graphs) CPU strong scaling | 4 | 24 |
| Six fixed graphs, 512-core extension | 0 | 6 |
| Fixed-graph CUDA/MPI+CUDA/Kokkos CUDA matrix | 26 | 45 |
| CPU weak scaling through 256 ranks | 0 | 1 |
| CPU weak 512-core extension, three families | 0 | 3 |
| GPU weak scaling | 0 | 1 |
| **Total** | **47** | **133** |

The CPU 1/2/4/8-node `synthetic_uniform` pilot batches and twenty-six GPU fixed-graph batches have passed their validators. The 8-node/512-core CPU pilot is still waiting on the project budget. The remaining 39 fixed-graph CPU strong-scaling batches, including their 512-core points, have not yet been submitted. This is a dated snapshot; submitted or running jobs are not runtime results.

The Vanda OpenMPI launch needed `/opt/pbs/lib` on the library path. Its `--map-by ...:PE=` option then stalled for multi-threaded ranks. The current scripts map ranks by node and use `scripts/mpi_affinity_exec.py` to assign each local rank a disjoint slice of the PBS CPU set. Two small probes passed: one placed ranks on two separate nodes, and another recorded local ranks 0 and 1 on the same node with CPU sets `20:26` and `28:32`. Superseded PBS jobs are recorded in `failed_jobs.tsv` and `replaced_jobs.tsv`; their partial outputs are excluded from validated results.

At 23:43 SGT, PBS showed 3 running, 17 queued, and 66 held. The `am_hook` budget check held the CPU jobs; releasing one 32-core serial batch moved it back to budget waiting, and PBS rejected even a shorter walltime request for insufficient budget. No active job had finished without its validation marker at the preceding check. `hpc project` showed only 11.666 CPU hours left. The [budget investigation](updated_vanda_budget_issue_20261102.md) found 9,988.334 CPU hours precharged for completed or cancelled jobs, all unreconciled, versus approximately 217.326 core-hours estimated from their PBS elapsed times. Vanda's `hpc project-usage` confirms that unused job credits can return through reconciliation; if the balance does not recover after its next update, NUS HPC should check the accounting. The original Git result set is preserved separately from this `updated_vanda_scaling` run.
