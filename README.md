# PageRank: Serial, OpenMP, MPI, MPI+OpenMP, MPI+CUDA, and MPI+Kokkos

Latest Vanda progress and newly assigned work: [two-account status](updated_vanda_two_accounts_20261111.md).

Full fixed-graph target: **20,700 configurations** (original 19,980 plus 720 later requested 512-core splits). **Current execution and teammate handover: [Vanda handoff](HANDOFF_VANDA_EXPERIMENTS_20261106.md).** It distinguishes completed, submitted, held, failed, deferred and owner-assigned missing cells; do not submit from an old plan or a fresh RUN_ID without ownership transfer. See also [CPU split coverage](updated_cpu_layout_coverage_20261111.md).

A C++17 implementation of synchronous pull-based PageRank for DSA5208 Project 3. The fixed-graph matrix compares Serial, OpenMP, CUDA, Kokkos OpenMP/CUDA, pure MPI, MPI+OpenMP, MPI+CUDA, and MPI+Kokkos. Every MPI method implements both Allgatherv and Halo; the standalone methods have no MPI communication mode.

## Project structure

```text
DSA5208_PROJECT_3/
├── CMakeLists.txt
├── src/
│   ├── graph_io.cpp / .hpp   # Graph loading and incoming-edge CSR storage
│   ├── mpi_graph.cpp / .hpp  # Graph partitioning and distribution for MPI
│   ├── utility.cpp / .hpp    # Shared settings, results, output, and timing statistics
│   ├── pagerank_serial.cpp  # Serial implementation and experiments
│   ├── pagerank_openmp.cpp  # OpenMP implementation and experiments
│   ├── pagerank_mpi.cpp     # MPI implementation and experiments
│   ├── pagerank_hybrid.cpp  # MPI + OpenMP; Allgatherv and Halo
│   ├── pagerank_cuda.cu / pagerank_kokkos.cpp # Standalone GPU/CPU backends
│   ├── pagerank_mpi_cuda.cu / pagerank_mpi_kokkos.cpp # MPI + device backends
│   └── mpi_device_driver.hpp # Shared distributed PageRank driver
├── scripts/
│   ├── prepare_data.py     # Download Google and generate Uniform and Hub
│   ├── generate_scaling_graphs.py # Reproducible serial-grid and MPI scale graphs
│   ├── validate_serial.py  # Independent checks of saved serial results
│   ├── validate_openmp.py  # OpenMP validation and scaling analysis
│   ├── validate_mpi.py     # MPI validation and scaling analysis
│   └── validate_hybrid.py  # Hybrid validation and scaling analysis
├── data/                   # Downloaded and generated input graphs
├── build/                  # CMake build output
└── results/
    ├── serial/{google,uniform,hub}/
    ├── openmp/{google,uniform,hub}/{t1,t2,t4,t8}/
    ├── mpi/{google,uniform,hub}/{p1,p2,p4,p8}/
    └── hybrid/{google,uniform,hub}/p<P>_t<T>/
```

Refreshed experiment runs are stored separately under `results/updated_local_macos/`, `results/updated_vanda/`, `results/updated_vanda_gpu/`, and `results/updated_vanda_scaling/`; they do not overwrite the original result set. The completed 31 October local run is summarized in [`updated_experimental_conclusions_20261031.md`](updated_experimental_conclusions_20261031.md).

`P` is the number of MPI processes; `T` is the requested number of OpenMP threads per process.

## Requirements

- A C++17 compiler with OpenMP support.
- An MPI implementation with development headers and libraries, such as MPICH or Open MPI on Linux, or MS-MPI with compiler-compatible development libraries on Windows.
- CMake 3.16 or newer and Ninja.
- Python 3.9 or newer. Experiment generation and validation use the standard library; `scripts/plot_scaling.py` additionally requires Matplotlib (`python -m pip install -r requirements-plot.txt`).

## Build and run

### 1. Prepare the datasets

```bash
python scripts/prepare_data.py
```

The script downloads [SNAP web-Google](https://snap.stanford.edu/data/web-Google.html) and generates two synthetic graphs using seed `5208`.

| Dataset | Nodes | Directed edges | Description |
|---|---:|---:|---|
| Google | 875,713 | 5,105,039 | Real web-link graph |
| Uniform | 100,000 | 1,000,000 | Uniformly sampled source and destination nodes |
| Hub | 100,000 | 1,000,000 | 80% of candidate destinations are sampled from the first 1% of nodes |


### 2. Configure the build

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
```

CMake locates the installed OpenMP and MPI libraries and configures an optimized build.

### 3. Compile

```bash
cmake --build build
```

The base build writes Serial, OpenMP, MPI, and MPI+OpenMP executables to `build/`. Repeat this step after changing C++ source files.

GPU targets are optional at build time. Configure native CUDA and MPI+CUDA with `-DBUILD_CUDA=ON -DBUILD_MPI_CUDA=ON`. Configure standalone Kokkos and MPI+Kokkos with `-DBUILD_KOKKOS=ON -DBUILD_MPI_KOKKOS=ON -DCMAKE_PREFIX_PATH=<kokkos-install>`. Use separate build directories for Kokkos OpenMP and CUDA backends. Run the standalone GPU executables and validate their saved results with:

```bash
./build/pagerank_cuda
./build/pagerank_kokkos
python scripts/validate_gpu.py cuda
python scripts/validate_gpu.py kokkos Cuda  # use the execution-space name printed by the binary
```

The Kokkos validation name may be `OpenMP`, `Serial`, or `Cuda`, depending on how Kokkos was built. On a CUDA GPU host, `scripts/run_gpu_suite.sh` runs both GPU executables and their validators; set `CUDA_BUILD_DIR`, `KOKKOS_BUILD_DIR`, and `KOKKOS_BACKEND` if your build paths/backend differ.

For MPI+CUDA and MPI+Kokkos, use a shared `PAGERANK_RESULTS_ROOT` and the same graph manifest as the Serial reference. Run each communication mode with the same MPI placement:

```bash
./build-cuda/pagerank_serial
mpiexec -n 2 ./build-cuda/pagerank_mpi_cuda --communication=allgather
mpiexec -n 2 ./build-cuda/pagerank_mpi_cuda --communication=halo
mpiexec -n 2 ./build-kokkos-cuda/pagerank_mpi_kokkos --communication=allgather
mpiexec -n 2 ./build-kokkos-cuda/pagerank_mpi_kokkos --communication=halo
python3 scripts/validate_mpi_device.py mpi_cuda Cuda allgather --processes 2
python3 scripts/validate_mpi_device.py mpi_cuda Cuda halo --processes 2
python3 scripts/validate_mpi_device.py mpi_kokkos Cuda allgather --processes 2
python3 scripts/validate_mpi_device.py mpi_kokkos Cuda halo --processes 2
```

The MPI+GPU implementations stage contribution values through host memory for MPI. Halo reduces the network payload to distinct remote source contributions; device-to-host staging is timed separately. Use one GPU per rank for the multi-node comparisons.

### 4. Run the experiments

Each executable processes all three graphs. Run the commands sequentially to avoid CPU contention between experiments.

On Linux, run the serial baseline, followed by OpenMP:

```bash
./build/pagerank_serial
./build/pagerank_openmp
```

OpenMP automatically tests 1, 2, 4, and 8 threads. Run MPI with each process count:

```bash
mpiexec -n 1 ./build/pagerank_mpi
mpiexec -n 2 ./build/pagerank_mpi
mpiexec -n 4 ./build/pagerank_mpi
mpiexec -n 8 ./build/pagerank_mpi
```

The default MPI mode is the `Allgatherv` baseline. Run `./build/pagerank_mpi --communication=halo` under the same process counts to use the precomputed halo: each rank requests distinct remote source IDs once, then exchanges only those contributions per iteration. Results are saved separately under `results/mpi_halo/`.

Run the hybrid experiments with the same process counts:

```bash
mpiexec -n 1 ./build/pagerank_hybrid
mpiexec -n 2 ./build/pagerank_hybrid
mpiexec -n 4 ./build/pagerank_hybrid
mpiexec -n 8 ./build/pagerank_hybrid
```

The hybrid executable automatically tests the following combinations, with at most eight total threads:

| MPI processes | OpenMP threads per process |
|---:|---|
| 1 | 1, 2, 4, 8 |
| 2 | 1, 2, 4 |
| 4 | 1, 2 |
| 8 | 1 |

On a cluster, run within an allocated job and use the site's MPI launcher and binding settings. Allocate enough CPUs per process for the largest OpenMP team tested by that command. For example, the hybrid run with two processes needs up to four CPUs per process.

For Windows PowerShell with MS-MPI, use:

```powershell
.\build\pagerank_serial.exe
.\build\pagerank_openmp.exe

mpiexec -n 1 .\build\pagerank_mpi.exe
mpiexec -n 2 .\build\pagerank_mpi.exe
mpiexec -n 4 .\build\pagerank_mpi.exe
mpiexec -n 8 .\build\pagerank_mpi.exe

mpiexec -affinity_layout 0 -n 1 .\build\pagerank_hybrid.exe
mpiexec -affinity_layout 0 -n 2 .\build\pagerank_hybrid.exe
mpiexec -affinity_layout 0 -n 4 .\build\pagerank_hybrid.exe
mpiexec -affinity_layout 0 -n 8 .\build\pagerank_hybrid.exe
```

The MS-MPI option `-affinity_layout 0` disables process affinity so that an OpenMP team is not confined to a single core. This option is specific to MS-MPI.

### 5. Validate the results

After completing all experiment configurations, run:

```bash
python scripts/validate_serial.py
python scripts/validate_openmp.py
python scripts/validate_mpi.py
python scripts/validate_mpi.py halo
python scripts/validate_hybrid.py
```

For a deliberately partial MPI sweep, the validator accepts a process subset, e.g. `python scripts/validate_mpi.py halo --processes 1 2`. The default remains the full 1/2/4/8 sweep.

The scripts read saved outputs and original graphs. They check node IDs, degrees, nonnegative ranks, rank sums, convergence histories, repeated-run records, and timing summaries. An independent PageRank update checks the final L1 residual against the convergence threshold plus `1e-12`; rank-sum error must not exceed `1e-10`.

Parallel results are compared with validated serial ranks by node ID, with an L1 error limit of `1e-8`. Floating-point reduction order may differ, so bitwise equality is not required. The pre-existing result set covers the original three datasets; the expanded Vanda matrix has 45 fixed datasets and three synthetic weak-scaling families. Any failed check produces a nonzero exit status.

## Implementation

All versions use synchronous pull-based PageRank with incoming-edge CSR storage and uniform redistribution of dangling-node mass.

| Version | Strategy |
|---|---|
| Serial | Sequential rank updates. |
| OpenMP | One persistent thread team; static contribution loops and `dynamic,64` rank updates. |
| MPI | Contiguous node partitions; `Allgatherv` exchanges contributions and `Allreduce` combines dangling mass and convergence errors. |
| MPI halo | Precomputes each rank's distinct remote source IDs and exchanges only their contributions with `Alltoallv`. |
| MPI + OpenMP | OpenMP within each MPI partition; only the initializing thread calls MPI (`MPI_THREAD_FUNNELED`). |
| CUDA | GPU CSR pull update with block reductions for dangling mass and convergence error. |
| Kokkos | The same CSR pull formulation using the build's selected Kokkos execution space. |


## Experiment protocol and output

Each configuration starts from uniform ranks and uses damping factor `0.85`, L1 tolerance `1e-8`, and at most 1,000 iterations. The default is one warm-up and five measured runs; `PAGERANK_WARMUPS` and `PAGERANK_REPEATS` override these counts.

`solve_s` measures iteration time, including thread-team startup/shutdown, synchronization, and iterative MPI communication where applicable. MPI-based timings use the slowest process. Input loading, preprocessing, solver data initialization, graph distribution, final validation/gathering, and output are excluded.

Each configuration saves the following files. Set `PAGERANK_RESULTS_ROOT` to a run-specific directory and `PAGERANK_ENVIRONMENT` to a concise machine label so runs from separate environments do not overwrite one another. The default results root is `results/`.

| File | Contents |
|---|---|
| `timings.csv` | Per-run times, iterations, and correctness metrics |
| `summary.json` | Dataset, configuration, timing statistics, and correctness summary |
| `ranks.csv` | Final ranks and node degrees from the last run |
| `history.csv` | Per-iteration L1 differences from the last run |

**Current Vanda continuation (2026-11-11):** the previous disjoint 730-cell batch is fully validated and downloaded; the full fixed target has 16,833/20,700 validated cells. Another 38 groups / 100 missing cells are assigned to hongxinran with a 240 CPU-hour request ceiling and original 30/45-minute walltimes. Those keys were removed from the primary live plan. See the [handoff](HANDOFF_VANDA_EXPERIMENTS_20261106.md) and [current two-account state](updated_vanda_two_accounts_20261111.md). Paid jobs measure performance; preparation and independent validation use free queues. PBS chooses nodes in the verified CPU switch pool, with model and affinity checked outside solver timing.

**Complete local backup:** source, scripts and result tables are tracked here. The [full backup guide](FULL_PROJECT_BACKUP_20261109.md) links the same repository's Release containing all local graph inputs, raw rank vectors, pinned Kokkos source, checksums and restore instructions.

`scripts/run_cpu_suite.sh` runs the CPU suite and validators inside an existing PBS allocation. `scripts/vanda_cpu_job.pbs` targets Vanda's zero-charge `auto_free` queue, builds Kokkos OpenMP and the project in Release mode with GCC 13.3/Open MPI 4.1.8, then runs Serial, OpenMP, MPI Allgatherv/halo, Hybrid, and Kokkos OpenMP with the same warm-up/repeat counts and datasets. The run directory records the host, compiler, MPI, CMake, and module versions.

The earlier three-graph Vanda job, `scripts/vanda_gpu_job.pbs`, requests one A40 GPU from the `auto_free` queue and runs native CUDA and Kokkos CUDA against a Serial reference. It is separate from the 45-graph MPI+GPU matrix below. Stage the pinned Kokkos source under `third_party/kokkos` before submitting either suite:

```bash
mkdir -p third_party
git clone --depth 1 --branch 4.5.01 https://github.com/kokkos/kokkos.git third_party/kokkos
qsub scripts/vanda_gpu_job.pbs
```

The GPU job stores results separately under `results/vanda-a40-gpu/<PBS_JOBID>/`. The actual queue, resource availability, and job state should be checked with `qstat`; a submitted job is not a completed experiment.

## Updated experiment matrix and coverage

The full current target matrix and statuses are specified in the [handoff](HANDOFF_VANDA_EXPERIMENTS_20261106.md); [`updated_experiment_matrix_20261103.md`](updated_experiment_matrix_20261103.md) preserves the earlier design. It covers the three original graphs and all 42 reproducible fixed graphs, plus three separate weak-scaling graph families. The generated grid crosses 50k/100k/200k/400k vertices with average out-degree 4/8/16 for each family. The 45 fixed graphs are used for standalone comparisons and strong scaling; the weak-scaling graphs are generated separately as resource counts grow. The target matrix is larger than the currently validated result set.

The current completed/missing matrix, live-state snapshot times, ownership and teammate prompt are in the [handoff](HANDOFF_VANDA_EXPERIMENTS_20261106.md). Older dated status/conclusion/budget documents are historical observations, not current submission instructions.

- **Standalone ablations:** Serial; OpenMP with 1/2/4/8/16/32 threads; Kokkos OpenMP with the same thread counts; native CUDA and Kokkos CUDA with one A40. These methods have no MPI communication choice.
- **CPU distributed methods:** Pure MPI and MPI+Kokkos OpenMP at T=1 use 1/2/4/8 nodes crossed with 1/2/4/8/16/32 ranks per node, plus a separate 8-node × 64-rank 512-core point. MPI+OpenMP adds every T=1/2/4/8/16/32 that fits 32 CPU cores per node, plus 512×1 and 128×4 on 8 nodes with 64 cores per node. The matching MPI+Kokkos OpenMP T>1 grid is implemented as a separate extension pipeline. The later requested 512-core T=2/8/16/32 splits add 720 cells for the two hybrid methods; these remain in the full target. Each graph, rank, thread, and node layout runs **both** `--communication=allgather` and `--communication=halo`.
- **Matched GPU-node methods:** On the same allocated GPU nodes, pure MPI, MPI+OpenMP T=1/2/4/8, MPI+CUDA, and MPI+Kokkos CUDA cover p=n=1/2 with one rank and one A40 per node. Each method runs both communication modes on the same graph and layout. T=1 is a CPU control; T=2/4/8 exercises OpenMP inside each MPI rank. Serial and standalone OpenMP/CUDA/Kokkos CUDA are measured on that GPU-node environment as ablations. GPU p=4/8 is excluded from the experiment plan and will not be submitted.
- **Weak scaling (required in this project plan):** Three synthetic graph families keep 50k vertices and 800k edges per rank. Pure MPI and MPI+Kokkos OpenMP cover p=1…256 plus the p=512 endpoint; MPI+OpenMP T=4 covers p=1…64 plus p=128,T=4, paired at 512 CPU cores. Both communication modes are run at every MPI point. The p=512 graphs have 25.6m vertices and 409.6m edges each. Matched Vanda GPU-node MPI methods cover p=1/2, with MPI+OpenMP T=1/2/4/8; standalone CUDA/Kokkos CUDA also run on these weak graphs. No p=4/8 GPU extension is in scope.

The original weak curves hold work **per rank** constant. For a matched work-per-CPU-core comparison at T=4, `scripts/run_vanda_cpu_core_weak.sh` reuses the `weak_pC` graph for `C=p×4` CPU cores, so vertices and edges scale with C. It runs both MPI+OpenMP and MPI+Kokkos OpenMP, each with both communication modes, for C=4/8/16/32/64/128/256/512. All 96 of these cells have validated local evidence; reuse them. The separate weak inventory and evidence gaps are in the handoff.

The p=512 graph is already generated by the existing data pipeline; this comparison changes its rank/thread layout rather than its edges. These core-normalized curves are separate from the original rank-normalized weak curves; their 96 Vanda measurements are complete. The controlled family rank-normalized 512-core endpoint has six cells whose remote evidence must be checked before any rerun.

For strong scaling, one graph stays fixed as resources increase. For weak scaling, graph size grows in proportion to rank count. Record total solve time and iteration count in both cases; weak scaling additionally compares time per iteration against p=1. `solve_s` times the iterative solver, including its MPI waits and device transfers. Halo setup time and bytes are separate fields. Use Release builds, one warmup, five measured repeats, and the median throughout.

### Submit and monitor on Vanda

**Current campaign:** follow the ownership-transfer procedure in the [handoff](HANDOFF_VANDA_EXPERIMENTS_20261106.md) before using any submission command below. These general scripts do not coordinate ownership across accounts or a new RUN_ID. Serial, standalone methods and GPU sections are already complete; do not resubmit them.

The jobs require Kokkos 4.5.01 source at `third_party/kokkos`. Stage the repository and Kokkos on Vanda, then submit free-queue data/build/smoke jobs:

```bash
mkdir -p third_party
git clone --depth 1 --branch 4.5.01 https://github.com/kokkos/kokkos.git third_party/kokkos
bash scripts/submit_vanda_bootstrap.sh
```

After the data, builds, and CPU/GPU smoke tests pass, obtain a Vanda project name and balance with `amgr login` followed by `hpc project`. The paid project queue is required for the coursework's ≥256-core runs: the free CPU queue caps a job at 160 cores; the paid CPU queue permits up to 10 nodes and 720 cores. Submit the independent fixed-graph baselines and weak-scaling suites with:

```bash
bash scripts/submit_vanda_serial_grid.sh <run-id> <project-name>
bash scripts/submit_vanda_gpu_grid.sh <run-id> <project-name>
bash scripts/submit_vanda_cpu_weak.sh <run-id> <project-name>
MAX_NEW_GRAPHS=1 bash scripts/submit_vanda_full_experiments.sh <run-id> <project-name>
```

Submitters skip batches recorded in their own run registry. They do not deduplicate against other accounts or a fresh RUN_ID; do not use a broad plan to continue the current campaign. Use only a coordinated missing-cell plan with transferred ownership. Increase `MAX_NEW_GRAPHS` only when project CPU credits permit the additional reserved walltime. Job IDs are recorded in `results/updated_vanda_scaling/<run-id>/submitted_jobs.tsv`. The original CPU batches reach 8 nodes × 32 cores; the extra 512-core endpoint uses 8 nodes × 64 cores. The p=512 weak graphs are split by synthetic family because each has 409.6 million edges. Vanda GPU batches request two nodes × one A40 and run p=1/2. Check completed batches, active jobs, allocations, and rank placement with:

```bash
python3 scripts/check_vanda_progress.py <run-id> --qstat
python3 scripts/check_vanda_progress.py <run-id> --missing
python3 scripts/audit_fixed_matrix.py vanda results/updated_vanda_scaling/<run-id>
```

The fixed-graph audit enumerates every expected method, graph, communication mode, and resource layout. It reports completed cells against the target rather than counting submitted PBS jobs as finished experiments. The original Vanda fixed-graph target has 18,315 CPU cells and 1,665 GPU-node cells; the full target adds 720 CPU splits, giving 19,035 CPU and 1,665 GPU-node cells; the GPU-node standalone OpenMP sweep includes T=16/32 as well as T=1/2/4/8. The CPU Kokkos thread-grid extension is submitted separately after the serial baseline passes, only when project credits allow its reserved walltime:

```bash
MAX_NEW_GRAPHS=1 bash scripts/submit_vanda_kokkos_cpu_grid.sh <run-id> <project-name>
```

This submits four 32-core node-layout jobs and one 512-core endpoint per graph. The endpoint adds Kokkos OpenMP `p=128,T=4`; the original CPU job already covers Kokkos OpenMP `p=512,T=1`. Do not infer an actual 512-core result from the submission alone.

After the jobs finish, generate a tidy summary of every validated MPI+Kokkos OpenMP CPU layout and example strong-scaling figures with:

```bash
python3 scripts/plot_kokkos_cpu_grid.py results/updated_vanda_scaling/<run-id> \
  results/updated_vanda_scaling/<run-id>/figures --graphs google uniform hub
```

Each successful batch writes `complete.txt` only after all validators pass and its output is copied. The job's `environment.txt` and `mapping/*.csv` record the actual allocation. Vanda's OpenMPI stalls with `PE=` in `--map-by` on this system, so multi-threaded MPI ranks use `scripts/mpi_affinity_exec.py` to pin nonoverlapping CPU sets; `affinity_probe_mapping.csv` records the actual two-rank placement. A queued job is not an observed runtime.

For a fixed-graph MPI batch that reaches its walltime after saving partial results, submit a continuation only after checking project credits:

```bash
bash scripts/submit_vanda_mpi_strong_retry.sh <run-id> <project-name> \
  <graph-name> <node-count> <failed-job-id> resume_after_walltime 08:00:00
```

This continuation reuses only measurements with all five timed repeats, the summary, history, and rank output present in the same scratch run. It reuses complete validation reports, computes missing configurations, and writes a batch completion marker only after all validators pass. The original failed job and each replacement are retained in `retry_jobs.tsv`.

After jobs pass their independent residual, mass, history, rank comparison, and repeated timing checks, their JSON/CSV outputs are copied to `results/updated_vanda_scaling/<run-id>/`. The large per-vertex `ranks.csv` files remain in scratch only until validation finishes. `scripts/plot_scaling.py` plots the completed matrix; its plots must not be treated as evidence until all plotted rows are validated. The Vanda CUDA and Kokkos CUDA Release builds and two-node correctness tests passed on 2 November 2026. The latest dated batch snapshot is in [`updated_vanda_run_status_20261105.md`](updated_vanda_run_status_20261105.md); the validated results and current limits are indexed in [`updated_results_snapshot_20261104.md`](updated_results_snapshot_20261104.md).

Keep the existing Git-tracked `results/` runs unchanged. Synchronize the current matrix with:

```bash
bash scripts/sync_updated_vanda_scaling.sh <run-id>
```

This writes the current Vanda run to `results/updated_vanda_scaling/<run-id>/`. The older `scripts/sync_updated_vanda_results.sh` remains for the earlier two-job layout.

Validators write `results/<version>/validation.json`; parallel validators also write `scaling.csv`. **Speedup** is serial median time divided by parallel median time. **Efficiency** divides speedup by the actual thread count, process count, or total hybrid thread count.

Current results are labeled `local workstation`. The coursework report requires Atlas or Vanda measurements with the environment and resource configuration documented. Preserve each environment's results separately to avoid overwriting them.

### GPU scope

The GPU experiment scope ends at one and two A40 nodes, with one MPI rank and one GPU per node. The 4/8 GPU scripts and queue-limit notes are retained as historical implementation artifacts, but those jobs are excluded from the matrix, coverage audit, and runtime budget. Continue the required three-family weak-scaling runs at the CPU layouts and GPU p=1/2 layouts described above.

### Workstation CPU subset

The Mac CPU subset uses the same Release, one-warmup, five-repeat timing rule and independent validators. It includes the original three graphs, the three canonical synthetic graphs, and all 36 size/degree grid graphs. The three 12.8m-vertex strong-scaling graphs and the 512-core configurations require Vanda. The separate local weak-scaling subset uses three families at p=1/2/4/8. Local runs are **workstation observations**, not substitutes for the required Vanda runtime figures.

```bash
python3 scripts/generate_scaling_graphs.py --output-root data/local_matrix_20261031 --fixed-only
python3 scripts/generate_local_weak_graphs.py --output-root data/local_weak_20261031
LOCAL_BUILD_DIR=/path/to/release-build LOCAL_MPIEXEC=/path/to/mpiexec \
  bash scripts/run_local_matrix.sh
LOCAL_BUILD_DIR=/path/to/release-build LOCAL_MPIEXEC=/path/to/mpiexec \
  bash scripts/run_local_weak_matrix.sh
```

The local scripts write to `results/updated_local_macos/20261031_full_cpu_kokkos45/` and `results/updated_local_macos/20261031_weak_cpu_kokkos45/`. The first covers Serial, OpenMP, standalone Kokkos OpenMP, pure MPI, MPI+OpenMP, and MPI+Kokkos OpenMP; the latter repeats the available methods on the weak-scaling graphs. Both MPI communication modes are paired at every local MPI configuration.

See [`updated_experimental_conclusions_20261101.md`](updated_experimental_conclusions_20261101.md) for the completed 42-graph fixed and 12-graph local weak matrices, validation scope, halo communication comparison, and remaining cluster/GPU runs. The earlier [`updated_experimental_conclusions_20261031.md`](updated_experimental_conclusions_20261031.md) and [`updated_experimental_conclusions_20261030.md`](updated_experimental_conclusions_20261030.md) snapshots are retained.
