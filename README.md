# PageRank: Serial, OpenMP, MPI, and Hybrid

A C++17 implementation of synchronous pull-based PageRank for DSA5208 Project 3. The project compares serial, OpenMP, MPI, and MPI + OpenMP implementations on three directed graphs. It explores irregular graph workloads, load balancing, synchronization, and communication overhead.

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
│   └── pagerank_hybrid.cpp  # MPI + OpenMP implementation and experiments
├── scripts/
│   ├── prepare_data.py     # Download Google and generate Uniform and Hub
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

Refreshed experiment runs are stored separately under `results/updated_local_macos/`, `results/updated_vanda/`, and `results/updated_vanda_gpu/`; they do not overwrite the original result set. The completed 31 October local run is summarized in [`updated_experimental_conclusions_20261031.md`](updated_experimental_conclusions_20261031.md).

`P` is the number of MPI processes; `T` is the requested number of OpenMP threads per process.

## Requirements

- A C++17 compiler with OpenMP support.
- An MPI implementation with development headers and libraries, such as MPICH or Open MPI on Linux, or MS-MPI with compiler-compatible development libraries on Windows.
- CMake 3.16 or newer and Ninja.
- Python 3.9 or newer. The scripts use only the standard library.

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

All four executables are written to `build/`. Repeat this step after changing C++ source files.

GPU targets are optional. Configure native CUDA with `-DBUILD_CUDA=ON`. Configure Kokkos with `-DBUILD_KOKKOS=ON -DCMAKE_PREFIX_PATH=<kokkos-install>`. Use separate build directories for different Kokkos backends; the target uses the execution space selected by the Kokkos build. Run the GPU executables and validate their saved results with:

```bash
./build/pagerank_cuda
./build/pagerank_kokkos
python scripts/validate_gpu.py cuda
python scripts/validate_gpu.py kokkos Cuda  # use the execution-space name printed by the binary
```

The Kokkos validation name may be `OpenMP`, `Serial`, or `Cuda`, depending on how Kokkos was built. On a CUDA GPU host, `scripts/run_gpu_suite.sh` runs both GPU executables and their validators; set `CUDA_BUILD_DIR`, `KOKKOS_BUILD_DIR`, and `KOKKOS_BACKEND` if your build paths/backend differ.

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

Parallel results are also compared with validated serial ranks by node ID, with an L1 error limit of `1e-8`. Floating-point reduction order may differ, so bitwise equality is not required. The validators cover the current three duplicate-free datasets: 3 serial results, 12 OpenMP configurations, 12 MPI configurations, and 30 hybrid configurations. Any failed check produces a nonzero exit status.

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

`scripts/run_cpu_suite.sh` runs the CPU suite and validators inside an existing PBS allocation. `scripts/vanda_cpu_job.pbs` targets Vanda's zero-charge `auto_free` queue, builds Kokkos OpenMP and the project in Release mode with GCC 13.3/Open MPI 4.1.8, then runs Serial, OpenMP, MPI Allgatherv/halo, Hybrid, and Kokkos OpenMP with the same warm-up/repeat counts and datasets. The run directory records the host, compiler, MPI, CMake, and module versions.

On Vanda, `scripts/vanda_gpu_job.pbs` requests one A40 GPU from the `auto_free` queue, builds the native CUDA target and a CUDA-enabled Kokkos 4.5.01 backend with the same GCC 13.3 host compiler, then runs both GPU implementations against a Serial reference. It records GCC, NVCC, CMake, GPU, and module details. Stage the pinned Kokkos source under `third_party/kokkos` before submission:

```bash
mkdir -p third_party
git clone --depth 1 --branch 4.5.01 https://github.com/kokkos/kokkos.git third_party/kokkos
qsub scripts/vanda_gpu_job.pbs
```

The GPU job stores results separately under `results/vanda-a40-gpu/<PBS_JOBID>/`. The actual queue, resource availability, and job state should be checked with `qstat`; a submitted job is not a completed experiment.

Keep the existing Git-tracked `results/` runs unchanged. After both Vanda jobs finish and validate, copy the new measurements into separate `updated_*` directories with:

```bash
bash scripts/sync_updated_vanda_results.sh <CPU_PBS_JOBID> <GPU_PBS_JOBID>
```

This writes the CPU suite to `results/updated_vanda/<CPU_PBS_JOBID>/` and CUDA/Kokkos-CUDA results to `results/updated_vanda_gpu/<GPU_PBS_JOBID>/`.

Validators write `results/<version>/validation.json`; parallel validators also write `scaling.csv`. **Speedup** is serial median time divided by parallel median time. **Efficiency** divides speedup by the actual thread count, process count, or total hybrid thread count.

Current results are labeled `local workstation`. The coursework report requires Atlas or Vanda measurements with the environment and resource configuration documented. Preserve each environment's results separately to avoid overwriting them.

See [`updated_experimental_conclusions_20261031.md`](updated_experimental_conclusions_20261031.md) for the latest refreshed local results, validation scope, halo communication comparison, and outstanding cluster/GPU runs. The earlier [`updated_experimental_conclusions_20261030.md`](updated_experimental_conclusions_20261030.md) is retained as the previous snapshot.
