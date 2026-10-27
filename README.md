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
python scripts/validate_hybrid.py
```

The scripts read saved outputs and original graphs. They check node IDs, degrees, nonnegative ranks, rank sums, convergence histories, repeated-run records, and timing summaries. An independent PageRank update checks the final L1 residual against the convergence threshold plus `1e-12`; rank-sum error must not exceed `1e-10`.

Parallel results are also compared with validated serial ranks by node ID, with an L1 error limit of `1e-8`. Floating-point reduction order may differ, so bitwise equality is not required. The validators cover the current three duplicate-free datasets: 3 serial results, 12 OpenMP configurations, 12 MPI configurations, and 30 hybrid configurations. Any failed check produces a nonzero exit status.

## Implementation

All versions use synchronous pull-based PageRank with incoming-edge CSR storage and uniform redistribution of dangling-node mass.

| Version | Strategy |
|---|---|
| Serial | Sequential rank updates. |
| OpenMP | One persistent thread team; static contribution loops and `dynamic,64` rank updates. |
| MPI | Contiguous node partitions; `Allgatherv` exchanges contributions and `Allreduce` combines dangling mass and convergence errors. |
| MPI + OpenMP | OpenMP within each MPI partition; only the initializing thread calls MPI (`MPI_THREAD_FUNNELED`). |


## Experiment protocol and output

Each configuration starts from uniform ranks and uses damping factor `0.85`, L1 tolerance `1e-8`, and at most 1,000 iterations, with one warm-up and three measured runs.

`solve_s` measures iteration time, including thread-team startup/shutdown, synchronization, and iterative MPI communication where applicable. MPI-based timings use the slowest process. Input loading, preprocessing, solver data initialization, graph distribution, final validation/gathering, and output are excluded.

Each configuration saves the following files; rerunning it overwrites existing results.

| File | Contents |
|---|---|
| `timings.csv` | Per-run times, iterations, and correctness metrics |
| `summary.json` | Dataset, configuration, timing statistics, and correctness summary |
| `ranks.csv` | Final ranks and node degrees from the last run |
| `history.csv` | Per-iteration L1 differences from the last run |

Validators write `results/<version>/validation.json`; parallel validators also write `scaling.csv`. **Speedup** is serial median time divided by parallel median time. **Efficiency** divides speedup by the actual thread count, process count, or total hybrid thread count.

Current results are labeled `local workstation`. The coursework report requires Atlas or Vanda measurements with the environment and resource configuration documented. Preserve each environment's results separately to avoid overwriting them.
