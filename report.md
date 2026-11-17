# Parallel PageRank on Vanda

Parallel PageRank experiments - 17 November 2026

CHEN Dedan (A0353553A); HE Xinyi (A0351082M); HONG Xinran (A0356216E)

Project repository: [https://github.com/rosesnack/DSA5208_PROJECT_3](https://github.com/rosesnack/DSA5208_PROJECT_3)

### Abstract

We study synchronous PageRank using Serial, OpenMP, MPI, MPI+OpenMP, native CUDA, and Kokkos with OpenMP and CUDA backends. The fixed-input study comprises 45 directed graphs: three original graphs and 42 reproducible extensions spanning graph size, edge density, and destination concentration. Fixed-input resource experiments ask whether additional workers solve the same graph faster; fixed-core comparisons then separate the effect of MPI process/thread decomposition. These experiments contain 19,530 configurations. A separate growing-input suite uses 27 scale-specific synthetic inputs from three graph families, with 318 resource-scaled configurations and 54 fixed-resource input-size controls. It tests whether runtime per iteration remains stable as graph size and resources grow together. Measurements use one warm-up and the median of five timed solves on NUS Vanda, with independent numerical validation. Balanced graphs benefit from distributed execution, whereas concentrated incoming edges limit useful parallelism despite equal vertex ownership. Selective Halo exchange reduces contribution traffic without consistently reducing runtime, and adding a second GPU does not guarantee acceleration.

A further 59 matched diagnostic configurations examine MPI collective selection, node boundaries, and CPU binding. These controls distinguish communication-policy effects from the graph-partition and workload mechanisms underlying the scaling curves.

## 1 Introduction to the algorithm and data

### 1.1 PageRank and its relation to PPR

PageRank assigns a probability score to each vertex of a directed graph. A random surfer follows an outgoing edge with probability alpha and otherwise jumps according to a preference vector. Personalized PageRank (PPR) uses a query-specific preference vector. Our implementation uses the uniform preference vector and uniform redistribution of dangling-vertex mass: it is standard PageRank, equivalently the uniform-preference special case of PPR. Throughout this report, PageRank denotes this uniform-preference case.

$$r_v^{(k+1)}=\frac{1-\alpha}{N}+\frac{\alpha D^{(k)}}{N}+\alpha\sum_{u:(u,v)\in\mathcal{E}}\frac{r_u^{(k)}}{d_{\mathrm{out}}(u)}.$$

Here N is the number of vertices, the directed edge set is denoted by script E, r_v is the probability score of vertex v, and d_out(u) is the number of outgoing edges from u. A dangling vertex has no outgoing edges; D is the sum of scores at these vertices and is redistributed uniformly. All scores start at 1/N. We use alpha=0.85, double precision, and synchronous old/new score buffers. Iteration stops when the sum of absolute score changes is at most epsilon=10^-8, with a cap of 1,000 iterations:

$$D^{(k)}=\sum_{u:d_{\mathrm{out}}(u)=0}r_u^{(k)},\qquad \Delta^{(k)}=\left\|\mathbf{r}^{(k+1)}-\mathbf{r}^{(k)}\right\|_1\leq\varepsilon.$$

The pull formulation stores incoming edges in compressed sparse row (CSR) form: each destination vertex has a row listing its source vertices. Updating one destination requires scanning that row. Serial work and storage are O(N+E), where E is the number of directed edges.

PageRank workers cannot proceed independently. A vertex update may need a source score owned by another process, so scores must be exchanged every iteration. The processes must also combine dangling-vertex scores and the total score change to perform the same update and stopping test. Furthermore, a vertex with 10,000 incoming edges requires a much longer row scan than one with two. Assigning equal numbers of vertices can therefore give processes very different amounts of computation. These dependencies, collective operations, and unequal row lengths make parallelization nontrivial.

### 1.2 Fixed-input graphs for resource comparisons

Fixed input means that a graph is unchanged when the hardware configuration changes. It does not mean only the three original files: all 45 graphs below are fixed inputs for the strong-scaling and fixed-core studies.

Table 1. Fixed-input graph collection. N and E count vertices and directed edges; the grid crosses mean degree with vertex count.

| Source | Graphs | Vertices N | Directed edges E | Purpose |
| --- | --- | --- | --- | --- |
| Original Google | 1 | 875,713 | 5,105,039 | Real web-link graph |
| Original uniform and hub | 2 | 100,000 each | 1,000,000 each | Original synthetic controls |
| Canonical extensions | 3 | 100,000 | 1,000,000 | One per generated family |
| Size-density grid | 36 | 50k / 100k / 200k / 400k | N x 4 / 8 / 16 | 3 families x 4 sizes x 3 densities |
| Large extensions | 3 | 12,800,000 | 204,800,000 | One per generated family |
| Total fixed graphs | 45 |  |  | 3 original + 42 extensions |

The generated families use seed 5208 and deterministic integer mixing. Uniform spreads destinations across all vertices with fixed source degree. Hub directs approximately 80% of each source's edges to the first 1% of vertices. Controlled combines the hub destination pattern with two source-degree classes: 80% lower-degree sources and 20% higher-degree sources. Integer rounding and unique arithmetic progressions determine exact counts. The original uniform/hub files are retained unchanged; they are not interchangeable with the new canonical graphs of the same size.

For the three large graphs, E/N=16. The integer rule floor(4*d_out/5) sends exactly 75.0% of Hub edges and 77.5% of Controlled edges into the first 1% of destination IDs. These exact fractions, rather than an assumed 80%, are used in the workload model below. The concentration is deliberately aligned with contiguous vertex partitions; results therefore characterize this partitioner and vertex ordering as well as graph structure.

Integer rounding also qualifies the density-grid interpretation: Controlled sends 65.0% of its edges to the hot block at mean degree 4, and 77.5% at degrees 8 and 16. Changing density therefore changes this exact structural concentration as well as E. The grid is a reproducible generator-family study, not an intervention that isolates edge count from every other graph property.

Vertex count and average out-degree are crossed systematically, not changed together in a single size parameter. The three large graphs have identical N and E but different structural concentration, making them useful for separating graph size from load imbalance. All 45 fixed graphs are reused unchanged across the full fixed-graph configuration matrix.

### 1.3 Graphs that grow with resource count

The growing-input experiments use Uniform, Hub, and Controlled graphs at nine scale factors s=1,2,4,8,16,32,64,128,256. Each input contains N=50,000s vertices and E=800,000s directed edges, giving 27 scale-specific graph identifiers. The largest scale has 12.8 million vertices and 204.8 million edges. The three large fixed-input graphs reuse these largest-scale inputs; the fixed-input and growing-input counts describe their experimental roles and should not simply be added.

In a rank-normalized experiment s equals the MPI process count p; in a core-normalized experiment s equals the active CPU core count C. The CPU suites contain 150 rank-normalized and 84 core-normalized configurations. On GPU nodes, six inputs (three families at s=1 and 2) provide 84 distributed resource-scaled configurations and 54 standalone fixed-resource controls. Thus 372 growing-input records comprise 318 resource-scaled configurations and 54 controls; the latter measure increasing input size without labeling them as resource-scaled efficiency measurements.

## 2 Methodology

### 2.1 Notation, implementations, and communication

Table 2. Symbols, terminology, and measurement units used in the experiment design.

| Symbol or term | Definition and unit |
| --- | --- |
| N; E | Numbers of vertices and directed edges (counts). Average out-degree is E/N. |
| Node; n | A physical compute machine; n is the number of participating machines (nodes). |
| MPI rank; p | An MPI rank identifies a participating process, not a PageRank score. p is the total process count; rank IDs are 0,...,p-1. Processes have separate local data. |
| r; T | r is the number of MPI processes per node. T is the number of CPU threads per process (threads/process). |
| C; G | C is active CPU parallelism (cores); G is the number of GPUs used by device computation (devices). |
| t; I | t is solve time in seconds; I is the convergence iteration count. T denotes threads, never runtime. |
| CSR; PPR | Compressed sparse row storage; personalized PageRank. We use the uniform-preference special case of PPR. |
| OMP; KK; A; H | Figure abbreviations: OpenMP; Kokkos; Allgatherv; Halo. CUDA and Kokkos CUDA denote GPU computation. |

$$p=nr,\qquad C=pT=nrT.$$

For example, four nodes with eight processes per node and four threads per process give p=32 and C=128 active CPU cores. The process count and thread count describe different levels of parallelism. On GPU nodes, distributed device methods use one process and one GPU per node, so G=p=n. Their GPU thread blocks are separate from the host CPU thread parameter T.

Table 3. Implemented compute methods, local work distribution, and applicable MPI exchange strategies.

| Implementation | Compute and work distribution | MPI exchange |
| --- | --- | --- |
| Serial | One CPU thread; incoming CSR pull | Not applicable |
| OpenMP | CPU threads; dynamic row scheduling, chunks of 64 vertices | Not applicable |
| Kokkos OpenMP | CPU threads; default static RangePolicy and reductions | Not applicable |
| CUDA / Kokkos CUDA | One GPU; incoming-row vertex kernels | Not applicable |
| MPI | Contiguous destination partitions; one CPU thread per process | Allgatherv; Halo |
| MPI+OpenMP | Threaded pull within each MPI partition | Allgatherv; Halo |
| MPI+CUDA | One GPU per MPI process; host buffers for MPI exchange | Allgatherv; Halo |
| MPI+Kokkos | Distributed driver with OpenMP or CUDA execution space | Allgatherv; Halo |

The standalone methods execute in one process and make no MPI calls; their MPI exchange setting is therefore not applicable. OpenMP threads share memory, while CUDA threads exchange device data through the kernel and memory system. MPI+OpenMP requests MPI_THREAD_FUNNELED: only the main thread calls MPI.

MPI assigns approximately equal consecutive ranges of destination vertex IDs to processes. Each process updates its own destinations and stores their incoming-edge rows. The two communication strategies differ in which source contributions they make available for those updates:

Table 4. The two exact MPI contribution-exchange strategies and the data communicated in each iteration.

| Strategy | Values exchanged each iteration | MPI operation |
| --- | --- | --- |
| Allgatherv | Every process receives the contribution value for every vertex, assembling a complete vector. This is simple but also transfers values that a process may not need. | MPI_Allgatherv |
| Halo | Each process receives only distinct remote-source values referenced by its incoming rows. Required source IDs are determined once; later iterations exchange their current values. | MPI_Alltoallv |

Both strategies calculate the same PageRank update and use MPI_Allreduce to combine dangling mass and convergence changes. Halo changes the communicated dependency set without dropping edges or approximating scores. Its request-list construction occurs before solve timing; packing and exchanging current values occur inside every timed iteration.

The counted per-iteration payload is the algorithm-level contribution-vector traffic, excluding collective implementation details, reduction traffic, and protocol overhead. Allgatherv counts 8N(p-1) aggregate bytes; Halo counts eight bytes per requested remote contribution. Payload sizes use decimal MB (one million bytes). Metadata setup is recorded separately and lies outside solve time. Fewer counted bytes therefore need not imply lower measured latency.

Local update work depends on both the number of owned vertices and their incoming edges. Global iteration progress waits for the slowest process and completion of collective operations. Equal vertex counts therefore do not imply equal computation time. The MPI timer includes packing/copies, collectives and waiting at reductions; it is not a network-only timer. Solve and phase timings take separate maxima across ranks, then separate medians across five runs. They cannot be subtracted or added to reconstruct one critical-path trace.

The distributed device implementations stage contributions through host memory; they do not use CUDA-aware MPI or overlap communication with computation. The CUDA version uses 256-thread blocks and explicit kernels. Kokkos expresses comparable operations through Views, parallel_for/parallel_reduce and execution-space fences. Kokkos OpenMP and CUDA are two backends, not interchangeable hardware measurements.

### 2.2 Hardware, software and timing protocol

All reported measurements are from NUS Vanda. CPU comparisons use Intel Xeon Platinum 8452Y hosts, GCC 13.3.0, Open MPI 4.1.8 and Release builds. GPU comparisons use NVIDIA A40 nodes with Platinum 8452Y CPUs; archived build metadata identifies CUDA toolkit 12.4.1. Driver-reported CUDA compatibility is not treated as the compiler toolkit version. Original laptop and mixed-hardware exploratory measurements are excluded.

Every configuration has one warm-up followed by five timed runs. All primary solve-time tables and figures report the median of those five timed runs. The exported statistic solve_median_s is recomputed here from the five original solve_s observations. MPI solve time is the maximum elapsed solver time across ranks. Graph input, partition distribution, backend construction and Halo setup are outside solve time; per-iteration MPI and host/device staging are inside the distributed solve. Standalone GPU setup and final rank copies are outside solve time. These are solver-time comparisons, not end-to-end application runtimes.

OpenMP creates its persistent thread team inside the timed solver, while Kokkos runtime initialization precedes solver timing. Backend-compute phases use fenced host-clock intervals, including dispatch and reduction implementation costs; they are not CUDA-event measurements of pure kernel execution. Transfer phases measure explicit staging and need not capture every internal scalar-result copy. These boundaries should be considered when comparing backends or very small graph runtimes.

The twelve MPI+Kokkos configurations with a lower-memory initialization use the same timed update and communication kernels. Their initialization variant is identified in the accompanying data; graph construction and memory preparation remain outside solve time.

### 2.3 Experimental configuration matrix

Every row below is applied to all 45 fixed-input graphs. One configuration is one graph, implementation, valid layout, and communication setting; its five timed repeats are not counted as five configurations. The design is a constrained Cartesian product: graph, implementation, valid resource layout, and communication strategy are crossed. Derived quantities are not additional independent dimensions: p=nr, C=pT, and for GPU computation G=p=n. CPU layouts satisfy rT<=32; combinations that exceed this per-node budget are excluded. Standalone methods have no MPI communication dimension.

CPU-node matrix. Q={1,2,4,8,16,32} is the tested set of per-node process and thread counts. Every listed MPI layout is measured separately with Allgatherv and Halo.

Table 5. CPU-node fixed-input matrix. Every row is crossed with all 45 graphs; Q={1,2,4,8,16,32} and the constraint rT<=32 selects valid layouts.

| Implementation | Nodes n | Ranks/node r | Processes p | Threads T | CPU cores C | MPI exchange | Configs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Serial | 1 | 1 | 1 | 1 | 1 | Not applicable | 45 |
| OpenMP | 1 | 1 | 1 | Q | T | Not applicable | 270 |
| Kokkos OpenMP | 1 | 1 | 1 | Q | T | Not applicable | 270 |
| MPI | 1,2,4,8 | Q | nr | 1 | nr | Allgatherv; Halo | 2,160 |
| MPI+OpenMP | 1,2,4,8 | Q | nr | Q; rT<=32 | nrT | Allgatherv; Halo | 7,560 |
| MPI+Kokkos OpenMP | 1,2,4,8 | Q | nr | Q; rT<=32 | nrT | Allgatherv; Halo | 7,560 |

For pure MPI, four node choices and six ranks-per-node choices give 24 layouts per graph. For each CPU hybrid method, 21 valid (r,T) pairs per node count give 84 layouts. Multiplying by 45 graphs and two communication settings yields 2,160 and 7,560 configurations, respectively. The CPU-node block contains 17,865 configurations. A standalone row uses p=1 to denote its one process, without creating an MPI communicator.

GPU-node matrix. The first four rows perform GPU computation; the last four execute on CPUs of the same GPU-node class as hardware-matched controls. G counts GPUs used for computation, so G=0 for those CPU controls.

Table 6. GPU-node fixed-input matrix, including device-computing methods and same-node-class CPU controls. G counts GPUs used for computation.

| Implementation | Nodes n | Processes p | CPU threads T | GPUs G | MPI exchange | Configs |
| --- | --- | --- | --- | --- | --- | --- |
| CUDA | 1 | 1 | 1 host | 1 | Not applicable | 45 |
| Kokkos CUDA | 1 | 1 | 1 host | 1 | Not applicable | 45 |
| MPI+CUDA | 1,2 | n | 1 host | n | Allgatherv; Halo | 180 |
| MPI+Kokkos CUDA | 1,2 | n | 1 host | n | Allgatherv; Halo | 180 |
| Serial CPU control | 1 | 1 | 1 | 0 | Not applicable | 45 |
| OpenMP CPU control | 1 | 1 | 1,2,4,8,16,32 | 0 | Not applicable | 270 |
| MPI CPU control | 1,2 | n | 1 | 0 | Allgatherv; Halo | 180 |
| MPI+OpenMP CPU control | 1,2 | n | 1,2,4,8 | 0 | Allgatherv; Halo | 720 |

The GPU-node block contains 450 device-computing configurations and 1,215 CPU controls, giving 1,665 configurations. Together with the CPU-node block, the fixed-input matrix has 19,530 configurations. No communication setting is attached to a standalone method, and no GPU-computing version is implied for Serial or ordinary OpenMP.

The principal CPU scaling line increases C=32,64,128,256 on n=1,2,4,8 nodes, keeping 32 active CPU cores per node. Pure MPI uses p=C,T=1; the plotted hybrid line uses p=C/4,T=4. At fixed C, the matrix also contains every legal split with T in Q and p=C/T. Thus one can compare increasing total parallelism separately from changing the process/thread mix at the same total core budget.

### 2.4 Scaling questions and statistical summaries

The fixed-input resource experiment asks: how much faster can the same graph be solved by adding workers? N, E, graph structure, and the convergence criterion are held fixed while C increases. The ideal is that doubling cores halves solve time. For each graph, let t_ser be its Serial solve median and t(C) the parallel solve median on C active cores. Speedup and CPU core efficiency are:

$$S(C)=\frac{t_{\mathrm{ser}}}{t(C)},\qquad \eta_{\mathrm{CPU}}(C)=\frac{S(C)}{C}.$$

Speedup is dimensionless; efficiency is reported as a percentage, with 100% representing ideal linear speedup relative to Serial. Fixed-input resource curves reveal where communication, synchronization, or insufficient local work outweighs the benefit of more workers. A different experiment holds C=256 fixed and varies p/T, asking which decomposition uses an equal core budget most effectively. This is a method comparison at fixed resources, not another increase in parallel degree.

The growing-input resource experiment asks: if graph size grows in proportion to resources, can each resource continue to handle the same nominal amount of work without increasing runtime? The graph must change in this experiment. Rank-normalized inputs use N=50,000p and E=800,000p; core-normalized inputs use N=50,000C and E=800,000C. The latter permits CPU hybrid methods with different process/thread decompositions to be compared at equal nominal work per core. Keeping vertex and edge counts per resource constant does not guarantee equal communication or balanced incoming-edge work; the growing-input experiment tests these additional costs.

Table 7. Growing-input experiment groups. Counts refer to configurations, not five-run repetitions; fixed-resource controls are kept separate.

| Growing-input block | Graph scale | Resource layouts | Configurations |
| --- | --- | --- | --- |
| Rank-normalized CPU | s=p; 3 families | MPI and MPI+Kokkos T1: p=1,...,256 in powers of 2; MPI+OpenMP T4: p=1,...,64; Allgatherv and Halo | 150 |
| Core-normalized CPU | s=C; 3 families | MPI+OpenMP and MPI+Kokkos OpenMP: T4, p=C/4; C=4,...,256 in powers of 2; Allgatherv and Halo | 84 |
| GPU-node resource scaling | s=p=1,2; 3 families | Distributed GPU methods and distributed CPU controls; n=p; Allgatherv and Halo | 84 |
| GPU-node input-size controls | s=1,2; 3 families | Standalone Serial, OpenMP, CUDA, and Kokkos CUDA retain one node while input size increases | 54 |
| Total |  | 318 resource-scaled configurations + 54 fixed-resource controls | 372 |

Graphs can require different iteration counts as they grow. We therefore define retained per-iteration efficiency using time per iteration rather than conflating communication scaling with a change in convergence length. Let I(C) be the number of iterations and C0 the smallest resource point of the same series:

$$\tau(C)=\frac{t(C)}{I(C)},\qquad \eta_{\mathrm{grow,iter}}(C)=\frac{\tau(C_0)}{\tau(C)}.$$

Ideal proportional input/resource growth has constant time per iteration and 100% efficiency; a value of 25% means each iteration takes four times as long as at the reference point. The matched CPU figure uses C0=4 for all three methods on identical growing inputs. MPI follows p=C,T1; the hybrid methods use p=C/4,T4. The separate rank-normalized source series retains its p0=1 reference in the data. This normalization changes the plotted reference, not any timing observation. Total-solve efficiency is retained as a secondary metric. CPU speedup always uses the corresponding CPU-node Serial reference; GPU-node speedup uses its own Serial control. One-to-two-GPU scaling instead divides each implementation's one-GPU time by its two-GPU time.

Two statistical levels are used. First, every individual configuration reports the median of its five timed solves after one warm-up. Second, a cross-graph comparison first divides those medians to obtain a speedup for each graph, then takes the geometric mean of the speedups:

$$\widetilde{t}_{g,a}=\operatorname{median}(t_{g,a,1},\ldots,t_{g,a,5}),\qquad s_g=\frac{\widetilde{t}_{g,a}}{\widetilde{t}_{g,b}},\qquad \overline{s}_{\mathrm{geo}}=\left(\prod_{g=1}^{m}s_g\right)^{1/m}.$$

Here g indexes the m compared graphs, a and b are matched configurations, and s_g>1 favors b. The geometric mean is applied to dimensionless ratios, not to the five timings of a configuration and not to seconds pooled across graph sizes. A 2x improvement and a 2x slowdown combine to 1x, giving equal multiplicative weight to each compared graph. Communication comparisons additionally match method, backend, nodes, processes, and threads. The 45-row best-time matrix is an overview of each method's best observed median; it is kept separate from matched-layout scaling and equal-core comparisons.

The fixed-core aggregate uses 45 ratios, one per graph. Communication aggregates instead use matched graph/layout pairs, with pair counts reported explicitly. Payload reduction is the fraction of Allgatherv contribution bytes avoided by Halo; its aggregate is the median across those matched pairs.

### 2.5 Correctness and reproducibility

The independent Python validators rebuild one PageRank update by streaming the original edge list, rather than sharing the C++ CSR traversal. Checks include vertex IDs/degrees, nonnegative finite ranks, total score within 10^-10 of one, residual within the stopping tolerance, full-vector L1 difference from Serial within 10^-8, history and repeated-run metadata. Allocation records and rank affinity maps verify the distributed layout. Raw rank vectors remain on Vanda; the repository holds summaries, timings, validation markers and provenance. The local analysis checks these saved proofs.

For the additional collective-policy controls, an independent raw-edge scan validates the Serial vector s once per graph. Every new vector x is compared in full, including IDs, degrees, probability mass and L1 error. The PageRank map is contractive in L1 with factor alpha=0.85. The new residual is therefore bounded by the reference residual plus 1.85 times the full-vector L1 difference. Requiring this bound to be at most 10^-8 independently certifies the new vector while reusing the reference scan. The distance to the unique stationary vector is at most the residual divided by 1-alpha. Timings, histories, actual threads and all five reported residuals are checked separately. These checks run on the free queue.

The accompanying data retain input identity, software version, hardware allocation, original timing observations, and independent validation records. These records support reconstruction of both the reported statistics and the configuration matched to each comparison.

### 2.6 MPI collective selection and controlled policies

The main experiment preserves Open MPI's automatic collective selection rather than prescribing one communication algorithm for all resource counts. The tuned component chooses an implementation for each collective operation according to its installed rules. On Vanda, the recorded Open MPI 4.1.8 configuration uses coll_tuned_use_dynamic_rules=false and algorithm overrides set to 0 (ignore). Automatic selection therefore follows the compiled fixed decision tree. The word fixed describes the decision rules, not a single algorithm: the selected algorithm can change with process count, and for Allgatherv also with message size. This automatic rule-based behavior is distinct from online adaptation based on measured congestion.

We retain that automatic behavior for the main scaling study, then perform matched forced-policy controls around the 64-core and 128-process selection boundaries. These controls ask whether a rule transition contributes to the measured bend, while holding the graph, binary, resource count, and allocation fixed within each comparison. Enabling coll_tuned_use_dynamic_rules=1 is the mechanism used to force an algorithm in these diagnostic runs; it was not the mode of the main matrix.

Table 8. Collective algorithms exposed by the installed Open MPI 4.1.8 tuned component. Algorithm ID 0 retains automatic selection and is not another implementation.

| MPI operation | Algorithm ID | Implementation | Applicability |
| --- | --- | --- | --- |
| Alltoallv (Halo) | 1 | basic_linear | General process counts |
| Alltoallv (Halo) | 2 | pairwise | General process counts |
| Allgatherv | 1 | GatherV followed by Bcast; parameter name default | General process counts |
| Allgatherv | 2 | Bruck | General process counts |
| Allgatherv | 3 | Ring | General process counts |
| Allgatherv | 4 | Neighbor exchange | Applicable at p=8,16,32 |
| Allgatherv | 5 | two_proc | Exactly two processes |

Thus tuned exposes two actual Alltoallv algorithms and five actual Allgatherv algorithms in this version. ID 0 (ignore) retains automatic selection and is not another implementation. Allgatherv ID 1 is named default, but explicitly forcing it selects GatherV+Bcast; it does not mean restoring the automatic decision tree [9]. Other collectives, including Allreduce, have their own algorithm lists and retain their default settings here.

Table 9. Compiled automatic Alltoallv selection rules in Open MPI 4.1.8. p is communicator process count, not CPU core count or payload size.

| Alltoallv communicator size p | Default tuned algorithm |
| --- | --- |
| p < 4 | pairwise |
| 4 <= p < 64 | basic_linear |
| 64 <= p < 128 | pairwise |
| 128 <= p < 256 | basic_linear |
| 256 <= p < 1024 | pairwise |
| p >= 1024 | basic_linear |

These are the fixed rules in Open MPI 4.1.8 [7] for communicators handled by tuned. A single-rank communicator can use the self component and has no remote Halo payload. For Alltoallv, this selector uses communicator size p, not message bytes, CPU cores or measured congestion. basic_linear starts nonblocking requests to the participating peers and waits for them; pairwise schedules rank-step exchanges [8]. Both implement the same blocking MPI_Alltoallv interface and transfer the same requested values. Their different request concurrency and message order can change latency and resource pressure. A blocking collective is not an MPI_Barrier.

Allgatherv has a separate selector using both p and average contribution bytes per rank, b=8N/p. On the large graphs N=12.8 million, the T=4 mainline changes from p=8, b=12.8 MB at 32 cores to p=16, b=6.4 MB at 64 cores. Its default Allgatherv algorithm changes from Bruck to Ring; at p=32 and 64 it remains Ring [7]. Thus a 64-core bend may involve a different collective transition from the 128-rank Halo peak.

The Allgatherv control deliberately compares the two implementations on either side of the observed rule transition: default selection, forced Bruck, and forced Ring, on both large concentrated graphs at C=32,64,128 with T=4. It is a symmetric transition test, not an exhaustive search for the fastest Allgatherv implementation. GatherV+Bcast and neighbor exchange are not part of that comparison; two_proc does not apply at its p=8,16,32. The Uniform Halo control instead compares default selection with both available Alltoallv algorithms at p=64,128,256.

Table 10. Automatic collective choices on the principal resource line. Pure MPI uses T1 and CPU hybrids T4; n is node count.

| Active cores C | Nodes | MPI p / Alltoallv | Hybrid p / Alltoallv | Hybrid Allgatherv |
| --- | --- | --- | --- | --- |
| 32 | 1 | 32 / basic_linear | 8 / basic_linear | Bruck |
| 64 | 2 | 64 / pairwise | 16 / basic_linear | Ring |
| 128 | 4 | 128 / basic_linear | 32 / basic_linear | Ring |
| 256 | 8 | 256 / pairwise | 64 / pairwise | Ring |

Hybrid columns use T=4 and both CPU hybrid implementations. To isolate a collective policy, enable coll_tuned_use_dynamic_rules=1 and force only that operation: Alltoallv algorithm 1=basic_linear or 2=pairwise; Allgatherv algorithm 2=Bruck or 3=Ring [9]. Other collectives retain their fixed-rule choices. The dynamic switch enables forced/user-rule dispatch; it is not online timing-based learning. Paired policies use the same graph, binary, allocation, p/T, CPU affinity and transport, with identical tuned/basic/libnbc/self component availability. Component probes run outside the five timed solves. Five-run medians and ranges, rather than a selected fastest repeat, quantify policy sensitivity.

Equal CPU budgets do not imply equal MPI policies. At C=256, p256/T1 uses pairwise Alltoallv, p128/T2 uses basic_linear, and p64/T4 returns to pairwise. Reducing p further to 32/16/8 uses basic_linear. Rank/thread decomposition therefore changes collective participation, local work sharing and the runtime selection regime together. The matched fixed-policy controls distinguish the contribution of a specific communication choice.

The compiled tree is a general performance heuristic. The controlled comparisons assess how well its choices suit this graph and allocation, without replacing the main automatic-selection curves with selected fastest policies. OpenMP schedule(dynamic,64), which redistributes local vertex chunks among CPU threads, is independent of this MPI setting. OMP_DYNAMIC=false fixes the OpenMP team size and does not disable dynamic row scheduling.

## 3 Results

The results follow the experimental questions in order: numerical agreement; serial input cost; more CPU resources for a fixed graph; single- and multi-GPU execution; communication policy; and proportional growth of inputs and resources. Unless explicitly labeled as a forced-policy control, every MPI result retains automatic tuned selection. Allgatherv and Halo are already present in the CPU and GPU comparisons; Section 3.5 re-expresses their matched results to isolate communication effects.

### 3.1 Numerical agreement across implementations

Table 11. Numerical consistency of the fixed-input results. L1 differences and probability-mass errors are dimensionless; 90 groups comprise 45 graphs on two node classes.

| Numerical check | Acceptance criterion | Observed outcome |
| --- | --- | --- |
| Full score vector versus Serial | L1 difference <= 10^-8 | All independently validated configurations pass |
| Final convergence residual | L1 residual <= 10^-8 | Maximum 7.520e-09 |
| Total probability mass | Absolute difference from 1 <= 10^-10 | Maximum 9.726e-12 |
| Iterations on a fixed graph and hardware class | Same stopping rule across implementations | Identical counts in all 90 graph/hardware groups |

These checks establish that the implementations compute the same uniform-preference PageRank solution within the prescribed tolerance. The performance sections therefore compare the cost of an equivalent numerical task. Each configuration contributes the median of five timed solves after one warm-up; repeated timings do not increase the configuration count.

### 3.2 Graph characteristics and serial reference costs

#### 3.2.1 Graph size, edge density, and iteration cost

The serial experiments establish the work scale before adding parallel resources. The same size-density grid is shown for Uniform, Hub, and Controlled, with vertex count on the horizontal axis and one line for each mean out-degree. Each point is one fixed graph; no process or thread count changes in this comparison.

![Figure 1. Serial solve time (s) for the 36 grid inputs: three families, four vertex counts, and mean out-degree d=4,8,16 edges/vertex. All runs use one CPU process and one thread. Points are five-run medians; both axes are logarithmic. Family panels use the same experimental design.](report_assets/figures/01_serial_grid.png)

Table 12. Density comparisons at N=100,000 vertices. Mean degree is E/N in edges/vertex; solve and per-iteration times separate convergence length from iteration cost.

| Family | Mean degree | Edges E | Iterations I | Solve time (s) | Time/iteration (ms) |
| --- | --- | --- | --- | --- | --- |
| Uniform | 4 | 400,000 | 22 | 0.042 | 1.91 |
| Uniform | 8 | 800,000 | 16 | 0.0369 | 2.3 |
| Uniform | 16 | 1,600,000 | 12 | 0.0385 | 3.21 |
| Hub | 4 | 400,000 | 23 | 0.0396 | 1.72 |
| Hub | 8 | 800,000 | 17 | 0.0387 | 2.28 |
| Hub | 16 | 1,600,000 | 14 | 0.044 | 3.14 |
| Controlled | 4 | 400,000 | 35 | 0.0647 | 1.85 |
| Controlled | 8 | 800,000 | 22 | 0.0314 | 1.43 |
| Controlled | 16 | 1,600,000 | 17 | 0.0532 | 3.13 |

More edges increase the work available to an iteration, but total solve time also depends on how many iterations the graph requires. Controlled at N=100,000 takes 35, 22, and 17 iterations as mean degree increases from 4 to 8 to 16. Its total time consequently need not increase monotonically. The density generator also changes the exact concentration of destination edges, as described in Section 1.2; the curves characterize the generated family rather than an isolated edge-count intervention.

Table 13. Serial baselines for the three original inputs and the three large inputs used in the resource curves. N and E are counts; all times are five-run medians on CPU nodes.

| Graph | Vertices N | Directed edges E | Iterations I | Serial time (s) |
| --- | --- | --- | --- | --- |
| Google | 875,713 | 5,105,039 | 90 | 1.9 |
| Original uniform | 100,000 | 1,000,000 | 15 | 0.0373 |
| Original hub | 100,000 | 1,000,000 | 16 | 0.0255 |
| Large uniform | 12,800,000 | 204,800,000 | 12 | 15.9 |
| Large hub | 12,800,000 | 204,800,000 | 14 | 23.2 |
| Large controlled | 12,800,000 | 204,800,000 | 12 | 15.9 |

#### 3.2.2 PageRank concentration in the real Google graph

The validated Google Serial vector has 136,259 dangling vertices (15.6%), so dangling-mass redistribution is essential. The highest-scoring 1% of vertices carry 27.1% of the total probability mass. Pearson correlation between PageRank and in-degree is 0.901: incoming links are strongly associated with rank, but raw in-degree is not the complete weighting rule.

Table 14. Five highest-scoring Google vertices. PageRank is a dimensionless probability score; in-degree and out-degree are edge counts.

| Node ID | PageRank | In-degree | Out-degree |
| --- | --- | --- | --- |
| 597621 | 0.0009237 | 5354 | 22 |
| 41909 | 0.0009211 | 4219 | 10 |
| 163075 | 0.0009040 | 4731 | 36 |
| 537039 | 0.0008988 | 6326 | 27 |
| 384666 | 0.0007869 | 4010 | 20 |

These anonymized vertex IDs cannot be mapped to named websites from this edge-list dataset alone. The observed rank concentration supports a structural statement about this graph; it does not identify trustworthy content or establish a causal relationship between links and importance.

### 3.3 Fixed graphs with more CPU processes and nodes

#### 3.3.1 Increasing active cores through explicit process layouts

The graph is held fixed while active CPU parallelism increases. C=4 is the first common point because the hybrid line uses four threads per process; lower-core measurements remain in the full matrix. Pure MPI starts p=C single-threaded processes. MPI+OpenMP and MPI+Kokkos OpenMP retain four CPU threads per process and start p=C/4 processes. Up to 32 cores the line uses one node; at 64, 128, and 256 cores it uses two, four, and eight nodes. Thus process count and, at the larger points, node count increase together.

Table 15. Layouts used in both fixed-graph CPU figures. Each row is measured with Allgatherv and Halo; C=pT for every method. Hybrid denotes MPI+OpenMP and MPI+Kokkos OpenMP.

| Active cores C | Nodes n | MPI processes p | MPI threads T | Hybrid processes p | Hybrid threads T |
| --- | --- | --- | --- | --- | --- |
| 4 | 1 | 4 | 1 | 1 | 4 |
| 8 | 1 | 8 | 1 | 2 | 4 |
| 16 | 1 | 16 | 1 | 4 | 4 |
| 32 | 1 | 32 | 1 | 8 | 4 |
| 64 | 2 | 64 | 1 | 16 | 4 |
| 128 | 4 | 128 | 1 | 32 | 4 |
| 256 | 8 | 256 | 1 | 64 | 4 |

The following two figures have identical organization: original inputs first, then the three large inputs; speedup above and CPU efficiency below. Across the CPU resource figures, colors identify the same methods, and solid/dashed lines identify Allgatherv/Halo. The matching CPU-node Serial median is the reference. The curves use default automatic collective selection; the fixed-algorithm tests are presented separately in Section 3.5.2.

![Figure 2. Fixed original graphs with increasing CPU resources. Top: speedup relative to each graph's Serial baseline (×). Bottom: speedup divided by C, expressed as CPU efficiency (%). Layouts are listed in the preceding table. A=Allgatherv and H=Halo; MPI uses T=1 and both hybrid methods T=4. Points are derived from five-run solve medians; matching rows share axis scales.](report_assets/figures/02_strong_original.png)

![Figure 3. The same CPU process/node experiment on the large Uniform, Hub, and Controlled graphs, each with N=12.8 million vertices and E=204.8 million directed edges. Top: Serial-relative speedup (×); bottom: CPU efficiency (%). Layout, method colors, communication line styles, and statistic match the original-graph figure.](report_assets/figures/03_strong_large.png)

The large balanced Uniform graph reaches 28.6× Serial speedup with MPI Halo at 256 cores, corresponding to 11.2% CPU efficiency. Google behaves differently: its best pure-MPI point is one node with 32 processes and Halo, at 0.149 s, whereas eight nodes and 256 processes take 1.462 s. The added communication and synchronization are not offset by enough useful work on this smaller input. Hub and Controlled also obtain less benefit from more processes despite having the same size as large Uniform.

Incoming-edge work explains the structural distinction. Each process receives approximately the same number of destination vertices, but these vertices can own very different numbers of incoming edges. The next figure measures the resulting maximum-to-mean edge load as process count increases; one indicates perfect edge balance.

![Figure 4. Incoming-edge workload imbalance for the three equal-size large graphs. The horizontal axis is MPI process count p; the vertical axis is maximum/mean incoming-edge count (dimensionless). Equal consecutive vertex partitions are used for all families. These are partition statistics, not timing ratios.](report_assets/figures/13_rank_workload.png)

$$B_E=\frac{\max_i E_i}{E/p},\qquad p_{\mathrm{edge}}=\frac{E}{\max_i E_i}=\frac{p}{B_E}.$$

Table 16. Work concentration at 256 processes. B_E is dimensionless. The equal-work process proxy assumes equal edge-scanning rates and describes load balance; it is not an observed speedup or the number of processes launched.

| Large graph, p=256 | Max/mean edge load | Busiest process edge share (%) | Equal-work process proxy |
| --- | --- | --- | --- |
| Large uniform | 1.002 | 0.39% | 255 |
| Large hub | 75.002 | 29.30% | 3.41 |
| Large controlled | 77.508 | 30.28% | 3.3 |

All 256 processes are launched, but one process owns about 29%-30% of all edges on Hub and Controlled. The iteration must wait for that process, even when the others finish early. The edge-only load corresponds to roughly 3.4 or 3.3 perfectly balanced processes under an equal-rate model. Uniform remains nearly balanced. The generator places 75.0% and 77.5% of edges into the first 1% of destination IDs; contiguous ownership preserves that concentration. The hot block stays inside one process while p<=100 and first crosses process boundaries at higher counts. Halo changes exchanged values while leaving this ownership unchanged.

Table 17. One-node scheduling comparison on the same large graphs. Each method uses one process and 32 CPU threads; times are five-run solve medians. The static-block share is an analytical workload proxy.

| Large graph; T=32 | OpenMP time (s) | Kokkos OpenMP time (s) | Kokkos/OpenMP (×) | Largest static block edge share (%) |
| --- | --- | --- | --- | --- |
| Large uniform | 0.54 | 0.542 | 1 | 3.1% |
| Large hub | 0.704 | 16 | 22.8 | 75.5% |
| Large controlled | 0.537 | 11.8 | 22 | 78.0% |

The same issue can occur within one process. OpenMP dynamically distributes destination chunks of 64 vertices. The compiled Kokkos RangePolicy uses static ranges by default [6]. A contiguous 32-way split leaves about 75.5%-78.0% of the concentrated graphs' edges in one block. The methods have similar Uniform times but differ by about 22× on Hub and Controlled. This associates the performance gap with their implemented scheduling policies and workload ordering, rather than assigning the entire gap to framework overhead.

#### 3.3.2 Fixed 256-core budget: changing the process/thread split

This experiment holds the total resource count fixed instead of increasing it. Every configuration uses eight nodes and 256 CPU cores; p decreases as T increases. Both CPU hybrid implementations use the same six splits and both communication strategies. Each plotted ratio compares a graph's five-run median with the same method and exchange at p=256,T=1, before aggregating over the 45 graphs.

Table 18. Equal-core process/thread comparison. Values are geometric means of 45 paired speedups, each based on five-run median times. All rows satisfy pT=256; A=Allgatherv, H=Halo. The reference is the corresponding method's T=1 row, not Serial.

| Processes p | Threads/process T | MPI+OMP A (×) | MPI+OMP H (×) | MPI+KK A (×) | MPI+KK H (×) |
| --- | --- | --- | --- | --- | --- |
| 256 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| 128 | 2 | 1.26 | 5.02 | 1.28 | 5.22 |
| 64 | 4 | 2.42 | 3.65 | 2.42 | 3.63 |
| 32 | 8 | 2.50 | 11.67 | 2.37 | 10.24 |
| 16 | 16 | 3.04 | 13.12 | 2.76 | 11.35 |
| 8 | 32 | 3.40 | 12.41 | 3.20 | 10.53 |

![Figure 5. Changing process/thread decomposition at a fixed eight-node, 256-core budget. Horizontal axis: threads per process T, with p=256/T. Vertical axis: geometric-mean speedup relative to the same method/exchange at T=1 (×), over 45 graphs. Method colors and Allgatherv/Halo line styles match the preceding figures.](report_assets/figures/04_fixed_256_splits.png)

With Allgatherv, T=32,p=8 improves the aggregate time ratio by 3.40× for MPI+OpenMP and 3.20× for MPI+Kokkos relative to their T=1 configurations. The best aggregate Halo splits use T=16 and T=16, with 13.12× and 11.35× improvements. Fewer processes reduce collective participation and allow more local sharing of hot rows. The optimum remains graph-dependent; these aggregate ratios do not imply that every graph favors the same split.

### 3.4 Standalone methods and one-to-two-GPU execution

#### 3.4.1 Standalone CPU/GPU baselines and MPI overhead

Table 19. Standalone baselines on the same six representative graphs. CPU methods use one node; device methods use one A40. All values are five-run solve medians in seconds. CPU-node and GPU-node Serial references are kept separate.

| Graph | CPU Serial (s) | OpenMP T32 (s) | KK OpenMP T32 (s) | GPU-node Serial (s) | CUDA (s) | KK CUDA (s) |
| --- | --- | --- | --- | --- | --- | --- |
| Google | 1.9 | 0.125 | 0.104 | 1.86 | 0.115 | 0.0936 |
| Original uniform | 0.0373 | 0.00267 | 0.00225 | 0.0288 | 0.00136 | 0.000999 |
| Original hub | 0.0255 | 0.00239 | 0.0101 | 0.0285 | 0.00616 | 0.00851 |
| Large uniform | 15.9 | 0.54 | 0.542 | 15.9 | 0.531 | 0.478 |
| Large hub | 23.2 | 0.704 | 16 | 17.1 | 0.755 | 2.03 |
| Large controlled | 15.9 | 0.537 | 11.8 | 12.9 | 0.594 | 1.77 |

Standalone device methods and MPI device methods differ even at one GPU. The distributed driver stages source contributions through host memory every iteration. On Google, standalone CUDA and Kokkos CUDA take 0.115 and 0.094 s, compared with approximately 0.243 and 0.383 s for their MPI Allgatherv p=1 versions. The difference is part of the distributed solve path, not the one-time graph loading or backend initialization.

#### 3.4.2 One versus two GPUs on fixed inputs

The distributed device comparison keeps each graph fixed and changes n=p=G from one to two, with one MPI process and one A40 per node. Allgatherv and Halo are each measured under automatic tuned selection. CPU-only MPI and MPI+OpenMP T=1 on the same node class provide layout-matched controls. Each curve is normalized to its own one-node time.

![Figure 6. Fixed-graph one-to-two-node comparison on the three large inputs. Device methods use one GPU per MPI process and node; CPU controls use T=1 and no device computation. Vertical axis: each method/exchange's one-node time divided by its n-node time (×). One-node reference is 1×. Colors, communication line styles, and panel axes are consistent across graphs; all source times are five-run medians.](report_assets/figures/06_gpu_node_scaling.png)

Table 20. Allgatherv GPU comparisons, presented identically for all three large graphs and both backends. Each ratio divides the p1 median by the p2 median; values above 1× favor two GPUs. The edge share is a partition statistic.

| Large graph | GPU method | Busiest p2 edge share (%) | Compute p1/p2 (×) | Solve p1/p2 (×) |
| --- | --- | --- | --- | --- |
| Large uniform | MPI+CUDA | 50.0% | 2 | 1.12 |
| Large uniform | MPI+Kokkos CUDA | 50.0% | 1.99 | 1.22 |
| Large hub | MPI+CUDA | 87.4% | 1.11 | 0.909 |
| Large hub | MPI+Kokkos CUDA | 87.4% | 1.88 | 1.46 |
| Large controlled | MPI+CUDA | 88.6% | 1.1 | 0.882 |
| Large controlled | MPI+Kokkos CUDA | 88.6% | 1.89 | 1.46 |

![Figure 7. Five-run phase medians per solve (s) for the same Allgatherv cases on all three large graphs. CU=CUDA, KK=Kokkos CUDA; suffix 1/2 is GPU and process count. Dots show total solve, device computation, host staging, and MPI exchange/waiting. Panels share a logarithmic time scale. Separately reduced and summarized phases are not additive pieces of one median execution.](report_assets/figures/08_gpu_phases.png)

Uniform divides incoming-edge work approximately in half: both backends obtain about 2× computation acceleration, but increased MPI cost limits end-to-end improvement. Hub and Controlled leave roughly 87%-89% of all edges on one GPU, so native CUDA computation improves only about 1.1× while communication rises. Kokkos improves more on those graphs, indicating additional effects from kernel mapping, vertex reductions, and memory locality. The edge-only workload proxy describes one mechanism, rather than a universal runtime bound.

### 3.5 Communication strategy and MPI implementation choice

Communication appears in all preceding MPI results. This section separates two different questions. Section 3.5.1 compares which contribution values are exchanged: the complete Allgatherv vector or the exact Halo dependency set. Section 3.5.2 holds that strategy fixed and changes how Open MPI schedules the collective. The first comparison reuses main-matrix measurements; the second uses separately matched diagnostic allocations. No standalone method acquires an MPI exchange parameter.

#### 3.5.1 Allgatherv versus exact Halo exchange

![Figure 8. Matched communication comparisons on all 45 fixed graphs. Left: geometric-mean Allgatherv/Halo solve-time ratio (×); above 1× favors Halo. Right: median reduction in logical contribution payload (%), with measured zero labeled explicitly. Each pair matches graph, method, nodes, processes, and threads; p=1 is excluded. CPU-node and GPU-node populations have different layout ranges, so their aggregate bars are not a hardware-only comparison.](report_assets/figures/05_halo_pairs.png)

Table 21. Populations and statistics behind the communication bars. Speedup is the geometric mean of paired five-run-median ratios. Payload reduction and the fraction of pairs favoring Halo are percentages; they are different statistics.

| Node class | Family | Matched pairs | Halo speedup (×) | Payload reduction (%) | Halo faster (%) |
| --- | --- | --- | --- | --- | --- |
| cpu node | Google | 179 | 1.89 | 58.6% | 87.2% |
| cpu node | Uniform | 2685 | 1.23 | 28.6% | 62.9% |
| cpu node | Hub | 2685 | 1.19 | 70.1% | 69.1% |
| cpu node | Controlled | 2506 | 1.19 | 71.8% | 68.8% |
| gpu node | Google | 7 | 0.969 | 27.7% | 14.3% |
| gpu node | Uniform | 105 | 0.922 | 0.0% | 16.2% |
| gpu node | Hub | 105 | 0.962 | 11.6% | 24.8% |
| gpu node | Controlled | 98 | 0.975 | 14.8% | 32.7% |

![Figure 9. Payload reduction (%) versus process count on the same fixed graphs. Each point is the family median across graphs for pure MPI with T=1; layouts use n=max(1,p/32) nodes. Only p changes the dependency partition, and each communication comparison holds that layout fixed. This view separates process-count effects from the different populations in the aggregate bars; byte counts exclude reduction and protocol traffic.](report_assets/figures/15_payload_by_process.png)

GPU-node Uniform has a measured median reduction of 0.0%, not an absent GPU result. Of its 105 matched pairs, 91 have zero contribution-payload savings. At p=2, most Uniform partitions require all source contributions owned by the other process, making the Halo contribution payload equal to Allgatherv. For large Uniform the aggregate payload is 102.4 MB per iteration with either strategy. These dependency counts are properties of the graph and partition, not of GPU arithmetic.

On CPU nodes the Google aggregate favors Halo by about 1.89× with a 58.6% median payload reduction. The synthetic families have aggregate gains near 1.19-1.23×, but many individual configurations still favor Allgatherv. Saving bytes does not remove packing, collective latency, global reductions, or waiting for imbalanced work. On device paths it also does not remove host staging. One-time Halo setup is outside solve timing and therefore cannot explain a timed-iteration slowdown.

Table 22. Paired Allgatherv/Halo time ratios on the same six inputs at eight nodes and 256 CPU cores. Each cell holds method, p, and T fixed; ratios above 1× favor Halo. The three columns need not use the same process count.

| Graph; C=256 | MPI p256/T1 (×) | MPI+OMP p64/T4 (×) | MPI+KK p64/T4 (×) |
| --- | --- | --- | --- |
| Google | 0.547 | 3.33 | 3.57 |
| Original uniform | 0.396 | 0.473 | 0.575 |
| Original hub | 0.274 | 0.539 | 0.701 |
| Large uniform | 1.9 | 0.798 | 0.905 |
| Large hub | 0.943 | 1.1 | 0.966 |
| Large controlled | 0.959 | 1.11 | 0.98 |

#### 3.5.2 Default tuned selection versus fixed collective algorithms

The preceding resource and exchange comparisons use Open MPI's default automatic selection. The diagnostic controls below isolate implementation choices within a fixed graph, process layout, binary, affinity map, and allocation. Default means the compiled selection tree with coll_tuned_use_dynamic_rules=0. Forced-policy runs set that parameter to 1 and override only the named collective; this is forced dispatch, not online performance learning.

Table 23. Primary matched-policy matrix: nine Alltoallv configurations and eighteen Allgatherv configurations. Uniform uses pure MPI; Hub and Controlled use MPI+OpenMP. Every row compares three policies within one allocation and satisfies C=pT=32n. Each configuration has one warm-up and five timed solves.

| Graph | Nodes n | Cores C | Processes p | Threads T | Exchange | MPI implementations | Configs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Large uniform | 2 | 64 | 64 | 1 | Halo | Automatic; basic_linear; pairwise | 3 |
| Large uniform | 4 | 128 | 128 | 1 | Halo | Automatic; basic_linear; pairwise | 3 |
| Large uniform | 8 | 256 | 256 | 1 | Halo | Automatic; basic_linear; pairwise | 3 |
| Large hub | 1 | 32 | 8 | 4 | Allgatherv | Automatic; Bruck; Ring | 3 |
| Large hub | 2 | 64 | 16 | 4 | Allgatherv | Automatic; Bruck; Ring | 3 |
| Large hub | 4 | 128 | 32 | 4 | Allgatherv | Automatic; Bruck; Ring | 3 |
| Large controlled | 1 | 32 | 8 | 4 | Allgatherv | Automatic; Bruck; Ring | 3 |
| Large controlled | 2 | 64 | 16 | 4 | Allgatherv | Automatic; Bruck; Ring | 3 |
| Large controlled | 4 | 128 | 32 | 4 | Allgatherv | Automatic; Bruck; Ring | 3 |

The 27 policy-comparison configurations are complemented by 30 automatic-selection context configurations and two binding configurations, giving 59 unique diagnostic settings. The full node-boundary context has 36 settings: both exchanges for MPI and the two CPU hybrid methods on both concentrated graphs at C=32,64,128. Six automatic Allgatherv settings are already in the primary matrix and are counted once. The binding comparison holds n=8,p=256,T=1 and pairwise fixed. These context and binding results follow the two policy comparisons below.

Alltoallv exposes two actual algorithms in this Open MPI version, and both are tested. The Allgatherv comparison targets Bruck and Ring because automatic selection crosses between them at p=8-to-16 for these large inputs; it is not an exhaustive search over its five available algorithms. GatherV+Bcast and neighbor exchange are outside that targeted contrast, and the two-process implementation does not apply at p=8,16,32. Section 2.6 lists the complete menus and the separate meaning of algorithm ID 0.

![Figure 10. Large Uniform with Halo: automatic Alltoallv selection versus forced basic_linear and pairwise. Every point is a five-run solve median (s); error bars span the five observed times and are not confidence intervals. Each process count shares one allocation across policies, while different counts use different allocations. Markers are slightly offset horizontally for visibility; the process axis is logarithmic.](report_assets/figures/11_collective_policies.png)

Table 24. Alltoallv comparison on the same graph and layout within each row. Each value is a five-run median; all policies produce independently validated PageRank vectors.

| Processes p = cores C | Automatic (s) | basic_linear (s) | pairwise (s) | Automatic/pairwise (×) |
| --- | --- | --- | --- | --- |
| 64 | 1.22 | 1.38 | 1.17 | 1.04 |
| 128 | 4.13 | 4.13 | 0.886 | 4.66 |
| 256 | 3.59 | 6.63 | 3.56 | 1.01 |

At p=128, automatic selection takes 4.134 s and forced basic_linear 4.129 s. Pairwise takes 0.886 s, a 4.66× improvement over automatic selection. The default range is 3.740-4.331 s and the pairwise range 0.873-0.965 s. Communication/waiting falls from 3.949 to 0.694 s while convergence remains 12 iterations. This directly demonstrates a policy effect in the MPI path.

The default Alltoallv rule changes pairwise-to-basic_linear-to-pairwise across p=64,128,256. The controller uses process count rather than graph payload or congestion; different request concurrency, buffering, and MPI progress can therefore produce different performance at the boundary. The same 128-process communication peak appears on the separate growing Uniform series. Its mean logical peer payload differs from the fixed-input case, supporting a scheduling explanation beyond one average-message-size threshold. TCP eager/rendezvous behavior and shared-resource contention may interact with that schedule.

![Figure 11. Large Hub and Controlled with MPI+OpenMP Allgatherv: automatic selection versus forced Bruck and Ring. Both panels use n=1/2/4, C=32/64/128, T=4, and p=C/4, with a common time scale. Points are five-run solve medians (s); error bars show observed minima and maxima. Policies share an allocation within a resource point; markers are slightly offset for visibility.](report_assets/figures/12_allgatherv_policies.png)

Table 25. Allgatherv transition controls, presented symmetrically for both graphs and all three resource points. T=4 throughout; only the selected collective implementation changes within a row.

| Graph | C / p | Automatic (s) | Bruck (s) | Ring (s) | Bruck/Ring (×) |
| --- | --- | --- | --- | --- | --- |
| Large hub | 32 / 8 | 4.96 | 4.98 | 4.96 | 1 |
| Large hub | 64 / 16 | 5.02 | 5.55 | 5.01 | 1.11 |
| Large hub | 128 / 32 | 6.35 | 7.21 | 6.38 | 1.13 |
| Large controlled | 32 / 8 | 3.82 | 3.83 | 3.85 | 0.994 |
| Large controlled | 64 / 16 | 3.89 | 4.29 | 3.88 | 1.11 |
| Large controlled | 128 / 32 | 4.79 | 5.57 | 4.66 | 1.19 |

At 64 cores, Hub takes 5.022 s under automatic selection, 5.010 s with Ring, and 5.550 s with Bruck. Controlled takes 3.886, 3.884, and 4.294 s, respectively. The default therefore agrees with Ring, while restoring Bruck does not improve this point. Unlike the Uniform 128-process Alltoallv case, this transition is not evidence that the default chose the slower of the two tested algorithms. At C=32, the default agrees with Bruck; the two transitions are evaluated using their own operation-specific algorithm menus.

Table 26. Default-policy node-boundary context from the same diagnostic matrix. Each ratio compares two nodes/64 cores with one node/32 cores. MPI uses T1 and hybrids T4; graph structure and the policy setting are unchanged.

| Method | Exchange | Hub: time64/time32 (×) | Controlled: time64/time32 (×) |
| --- | --- | --- | --- |
| MPI | Allgatherv | 1.019 | 1.008 |
| MPI | Halo | 1.031 | 0.927 |
| MPI+OMP | Allgatherv | 1.013 | 1.019 |
| MPI+OMP | Halo | 0.989 | 0.981 |
| MPI+KK | Allgatherv | 1.022 | 1.035 |
| MPI+KK | Halo | 1.021 | 1.023 |

Across these twelve method/exchange/graph lines, time64/time32 lies near 0.93-1.04. The hot destination block still belongs to one hybrid process: its Hub edge share changes only from 77.90% to 76.33%, and Controlled from 80.11% to 78.69%. Extra processes mostly subdivide cold work, while crossing to two nodes adds inter-node progress and synchronization. This combination explains an approximately flat resource curve more naturally than an assumption that every algorithm transition must be harmful.

Table 27. Launch-binding comparison within one eight-node, 256-core allocation. The graph and Alltoallv policy are fixed, and post-initialization affinity confirms one distinct CPU per process for both launchers.

| Binding at p256, fixed pairwise | Solve median (s) | Five-run range (s) | MPI/wait median (s) |
| --- | --- | --- | --- |
| Native core binding | 2.97 | 2.928-3.039 | 2.91 |
| Explicit CPU mask | 3.11 | 2.979-4.509 | 3.05 |

The launchers produce medians of 2.975 and 3.111 s, with overlapping five-run ranges. Their modest difference does not account for the larger variation between allocations. In the policy-control allocation, p256 pairwise takes 3.563 s; in the binding allocation both launchers remain near 3 s. Host/NUMA placement, shared-fabric contention, and peer progress are plausible contributors. These matched controls quantify within-allocation changes and remain separate from the main resource curves; their values are not pooled or substituted into those curves.

### 3.6 Growing graph size together with resources

#### 3.6.1 Constant nominal work per CPU core

This experiment changes the graph as CPU resources grow. At C=4,8,16,32,64,128,256, every method receives the same family input with N=50,000C vertices and E=800,000C edges. MPI uses p=C,T=1; the two hybrid methods use p=C/4,T=4. The principal comparison uses a common C=4 reference for all methods, so the graph sizes and efficiency definitions are directly comparable. This is a common reference definition applied to the saved per-iteration measurements. The separate rank-based p=1 reference series is retained in the accompanying data.

Table 28. Common growing-input CPU matrix. All three families and both Allgatherv/Halo settings use every row. Node count follows n=max(1,C/32); the per-core vertex and edge counts remain fixed.

| Active cores C | Vertices N | Directed edges E | MPI p / T | Hybrid p / T |
| --- | --- | --- | --- | --- |
| 4 | 200,000 | 3,200,000 | 4 / 1 | 1 / 4 |
| 8 | 400,000 | 6,400,000 | 8 / 1 | 2 / 4 |
| 16 | 800,000 | 12,800,000 | 16 / 1 | 4 / 4 |
| 32 | 1,600,000 | 25,600,000 | 32 / 1 | 8 / 4 |
| 64 | 3,200,000 | 51,200,000 | 64 / 1 | 16 / 4 |
| 128 | 6,400,000 | 102,400,000 | 128 / 1 | 32 / 4 |
| 256 | 12,800,000 | 204,800,000 | 256 / 1 | 64 / 4 |

![Figure 12. Graph size grows with CPU resources at fixed nominal vertices and edges per core. Top: per-iteration solve time (ms/iteration). Bottom: retained efficiency (%) relative to each method/exchange at C=4 on the same family. MPI uses T1 and hybrids T4. Solid/dashed lines are Allgatherv/Halo; all panels use the same layouts and matching axis scales. Ideal proportional scaling retains a flat iteration time and 100% efficiency.](report_assets/figures/07_core_weak.png)

Table 29. Retained per-iteration efficiency at 256 CPU cores, using the common C=4 reference of the preceding figure. Each percentage divides its C4 iteration time by its C256 iteration time; no Serial baseline enters this metric.

| Family | Method | C256 Allgatherv (%) | C256 Halo (%) |
| --- | --- | --- | --- |
| Uniform | MPI | 1.93% | 5.16% |
| Uniform | MPI+OpenMP | 4.18% | 3.80% |
| Uniform | MPI+Kokkos OpenMP | 3.63% | 3.66% |
| Hub | MPI | 0.63% | 0.58% |
| Hub | MPI+OpenMP | 0.79% | 0.97% |
| Hub | MPI+Kokkos OpenMP | 1.41% | 1.21% |
| Controlled | MPI | 0.56% | 0.55% |
| Controlled | MPI+OpenMP | 0.66% | 0.86% |
| Controlled | MPI+Kokkos OpenMP | 1.09% | 0.83% |

The common reference fixes the graph and core budget, but each method retains its own reference time. A higher retained percentage therefore need not mean a shorter absolute iteration; the two rows of the figure should be read together. Iteration cost increases even though nominal work per core is constant. On Uniform, retained efficiency at 256 cores is about 1.9%-5.2% depending on method and exchange; the concentrated families are lower. Allgatherv makes every process receive a contribution vector that grows with the global graph. With N proportional to p, its per-process contribution traffic is proportional to p and aggregate traffic to p squared. Equal vertex counts also fail to preserve equal incoming-edge work on Hub and Controlled.

![Figure 13. Pure-MPI growing Uniform inputs. Left: logical contribution payload (MB/rank/iteration); right: communication plus waiting (ms/iteration), each as a function of process count. N=50,000p and E=800,000p, T=1. Time points are the five-run median communication duration divided by iteration count. Both axes are logarithmic; byte counts exclude reductions and transport overhead.](report_assets/figures/14_growing_communication.png)

Table 30. Matched contribution volume and communication duration for growing Uniform. Rows compare the two exchanges at the same graph and process count; these are per-iteration quantities, not total job traffic.

| Processes p | Exchange | Payload (MB/rank/iteration) | MPI + waiting (ms/iteration) |
| --- | --- | --- | --- |
| 16 | Allgatherv | 6.00 | 2.56 |
| 16 | Halo | 4.40 | 3.25 |
| 64 | Allgatherv | 25.20 | 14.89 |
| 64 | Halo | 6.30 | 17.28 |
| 256 | Allgatherv | 102.00 | 85.76 |
| 256 | Halo | 6.37 | 38.07 |

Halo bounds Uniform payload near 6.4 MB per process per iteration, in contrast with Allgatherv's 102.0 MB at p=256. Nevertheless, Halo communication/waiting increases from 17.28 to 38.07 ms per iteration between p=64 and 256 while payload remains almost unchanged. More participating peers, collective/reduction latency, packing, and resource contention therefore matter in addition to contribution bytes. Concentrated inputs add waiting for heavily loaded processes to the same costs.

#### 3.6.2 Constant nominal work per GPU or MPI process

On GPU nodes, the growing-input comparison uses one and two nodes, with N=50,000p and E=800,000p. Device methods use one GPU per process; CPU controls use T=1 here to preserve the same host layout. Each method/exchange uses its own p=1 per-iteration time as reference. These percentages describe this one-to-two-resource experiment and are not compared numerically with the CPU C4-to-C256 percentages.

Table 31. Per-iteration efficiency retained when both graph size and GPU-node process count double. A=Allgatherv, H=Halo; reference p1 and measured p2 each use five-run median time per iteration. CPU controls do not compute on GPUs.

| GPU-node method | Uniform A (%) | Uniform H (%) | Hub A (%) | Hub H (%) | Controlled A (%) | Controlled H (%) |
| --- | --- | --- | --- | --- | --- | --- |
| MPI | 71.3% | 62.2% | 59.0% | 55.9% | 54.6% | 50.0% |
| MPI+OpenMP | 76.5% | 72.9% | 56.7% | 53.2% | 59.8% | 52.1% |
| MPI+CUDA | 40.3% | 38.8% | 59.6% | 57.8% | 59.8% | 54.6% |
| MPI+Kokkos CUDA | 44.8% | 41.6% | 58.1% | 57.6% | 64.0% | 55.1% |

The corresponding standalone runs on both graph sizes retain one node or device. They are fixed-resource input-size controls and are not assigned a resource-scaling efficiency. The complete growing-input inventory retains these 54 controls alongside the 318 resource-scaled configurations, with their layouts and original reference definitions.

### 3.7 Complete fixed-input summary and additional high-core example

The following matrices summarize all 45 fixed graphs. Every cell is the best observed five-run median for that method over its legal configurations; selected layouts are retained in the accompanying data. The resource budget can differ between cells. These overview matrices complement, rather than replace, the fixed-layout and equal-core comparisons above.

Table 32. CPU-node best observed solve medians (s), one row per fixed graph. KK=Kokkos; original/canonical are abbreviated o./s.; U/H/C identify generated families, followed by vertex count and mean out-degree.

| Graph | CPU Serial | OpenMP | KK OpenMP | MPI | MPI+OMP | MPI+KK |
| --- | --- | --- | --- | --- | --- | --- |
| Google | 1.9 | 0.125 | 0.104 | 0.149 | 0.146 | 0.146 |
| o. hub | 0.0255 | 0.00239 | 0.00935 | 0.0173 | 0.00418 | 0.015 |
| o. uniform | 0.0373 | 0.00267 | 0.00225 | 0.00426 | 0.00416 | 0.00453 |
| s. controlled | 0.0497 | 0.00373 | 0.0119 | 0.0186 | 0.0054 | 0.0196 |
| s. hub | 0.0396 | 0.00301 | 0.00937 | 0.0172 | 0.0044 | 0.0162 |
| s. uniform | 0.0349 | 0.00244 | 0.0018 | 0.00422 | 0.00362 | 0.00433 |
| C 100k/16 | 0.0532 | 0.00302 | 0.0155 | 0.0266 | 0.00473 | 0.0205 |
| C 100k/4 | 0.0647 | 0.00555 | 0.00919 | 0.0184 | 0.00906 | 0.0194 |
| C 100k/8 | 0.0314 | 0.00321 | 0.0103 | 0.0137 | 0.00504 | 0.0147 |
| C 200k/16 | 0.146 | 0.00837 | 0.0428 | 0.0611 | 0.0108 | 0.0433 |
| C 200k/4 | 0.129 | 0.0119 | 0.0209 | 0.0396 | 0.0174 | 0.0333 |
| C 200k/8 | 0.0712 | 0.00742 | 0.0265 | 0.0439 | 0.0122 | 0.0406 |
| C 400k/16 | 0.206 | 0.0174 | 0.124 | 0.159 | 0.0234 | 0.099 |
| C 400k/4 | 0.274 | 0.0219 | 0.0539 | 0.0768 | 0.0271 | 0.0861 |
| C 400k/8 | 0.242 | 0.0188 | 0.0797 | 0.107 | 0.0248 | 0.0845 |
| C 50k/16 | 0.0242 | 0.00212 | 0.00718 | 0.013 | 0.00286 | 0.0108 |
| C 50k/4 | 0.0297 | 0.0033 | 0.00415 | 0.00855 | 0.00457 | 0.0093 |
| C 50k/8 | 0.0151 | 0.00175 | 0.00489 | 0.0101 | 0.00518 | 0.0106 |
| H 100k/16 | 0.044 | 0.00254 | 0.0128 | 0.0215 | 0.00399 | 0.0187 |
| H 100k/4 | 0.0396 | 0.00376 | 0.0067 | 0.00908 | 0.0052 | 0.0101 |
| H 100k/8 | 0.0387 | 0.00279 | 0.0111 | 0.0103 | 0.00398 | 0.0112 |
| H 200k/16 | 0.0942 | 0.00673 | 0.0296 | 0.0525 | 0.00888 | 0.0339 |
| H 200k/4 | 0.0843 | 0.00843 | 0.0163 | 0.0297 | 0.0122 | 0.0284 |
| H 200k/8 | 0.0844 | 0.00804 | 0.0198 | 0.0306 | 0.00979 | 0.0294 |
| H 400k/16 | 0.242 | 0.0173 | 0.15 | 0.157 | 0.0208 | 0.0897 |
| H 400k/4 | 0.198 | 0.018 | 0.0577 | 0.0893 | 0.023 | 0.0685 |
| H 400k/8 | 0.214 | 0.0134 | 0.085 | 0.0993 | 0.0201 | 0.0703 |
| H 50k/16 | 0.0206 | 0.00292 | 0.00566 | 0.00987 | 0.0023 | 0.00971 |
| H 50k/4 | 0.019 | 0.0021 | 0.00328 | 0.00621 | 0.00311 | 0.00658 |
| H 50k/8 | 0.0189 | 0.00155 | 0.00415 | 0.0075 | 0.00253 | 0.00765 |
| U 100k/16 | 0.0385 | 0.00222 | 0.00181 | 0.00434 | 0.00345 | 0.0047 |
| U 100k/4 | 0.042 | 0.00372 | 0.00245 | 0.0024 | 0.00253 | 0.00258 |
| U 100k/8 | 0.0369 | 0.00307 | 0.00222 | 0.0044 | 0.00439 | 0.00461 |
| U 200k/16 | 0.0782 | 0.00449 | 0.00444 | 0.00868 | 0.00663 | 0.0118 |
| U 200k/4 | 0.0868 | 0.00763 | 0.00494 | 0.00692 | 0.00704 | 0.00744 |
| U 200k/8 | 0.0754 | 0.00505 | 0.00362 | 0.00698 | 0.00705 | 0.00783 |
| U 400k/16 | 0.208 | 0.0135 | 0.0116 | 0.0236 | 0.0158 | 0.0216 |
| U 400k/4 | 0.118 | 0.0123 | 0.00679 | 0.0115 | 0.0117 | 0.0133 |
| U 400k/8 | 0.121 | 0.00992 | 0.00643 | 0.0141 | 0.0142 | 0.0185 |
| U 50k/16 | 0.0178 | 0.00122 | 0.00104 | 0.00137 | 0.00152 | 0.00153 |
| U 50k/4 | 0.0206 | 0.00221 | 0.00135 | 0.0014 | 0.00159 | 0.00159 |
| U 50k/8 | 0.0181 | 0.00171 | 0.00112 | 0.00137 | 0.00156 | 0.00155 |
| 12.8M controlled | 15.9 | 0.537 | 10.7 | 6.6 | 0.642 | 5.36 |
| 12.8M hub | 23.2 | 0.704 | 16 | 8.93 | 0.808 | 8.2 |
| 12.8M uniform | 15.9 | 0.54 | 0.542 | 0.554 | 0.519 | 0.574 |

Table 33. GPU-node best observed solve medians (s) for the same 45 graphs. The distributed device methods select over one/two GPUs and Allgatherv/Halo. The Serial column is measured on this node class.

| Graph | GPU-node Serial | CUDA | KK CUDA | MPI+CUDA | MPI+KK CUDA |
| --- | --- | --- | --- | --- | --- |
| Google | 1.86 | 0.115 | 0.0936 | 0.243 | 0.381 |
| o. hub | 0.0285 | 0.00616 | 0.00851 | 0.0101 | 0.0148 |
| o. uniform | 0.0288 | 0.00136 | 0.000999 | 0.00514 | 0.00753 |
| s. controlled | 0.0358 | 0.00689 | 0.00931 | 0.0123 | 0.0182 |
| s. hub | 0.0398 | 0.00608 | 0.00844 | 0.0109 | 0.0171 |
| s. uniform | 0.037 | 0.00133 | 0.00102 | 0.00875 | 0.0121 |
| C 100k/16 | 0.053 | 0.00807 | 0.0114 | 0.0128 | 0.0175 |
| C 100k/4 | 0.0634 | 0.00554 | 0.00667 | 0.0156 | 0.0252 |
| C 100k/8 | 0.0496 | 0.00622 | 0.00834 | 0.0127 | 0.0192 |
| C 200k/16 | 0.117 | 0.0101 | 0.0269 | 0.0256 | 0.0487 |
| C 200k/4 | 0.129 | 0.00736 | 0.0136 | 0.0241 | 0.047 |
| C 200k/8 | 0.109 | 0.00816 | 0.0189 | 0.0189 | 0.0373 |
| C 400k/16 | 0.286 | 0.0135 | 0.0601 | 0.0264 | 0.0659 |
| C 400k/4 | 0.179 | 0.0114 | 0.0276 | 0.0359 | 0.0802 |
| C 400k/8 | 0.169 | 0.0111 | 0.0397 | 0.0315 | 0.0761 |
| C 50k/16 | 0.0245 | 0.00626 | 0.00626 | 0.00839 | 0.0098 |
| C 50k/4 | 0.0302 | 0.00412 | 0.00401 | 0.00964 | 0.0123 |
| C 50k/8 | 0.0246 | 0.00475 | 0.00458 | 0.00824 | 0.00982 |
| H 100k/16 | 0.0312 | 0.00723 | 0.0104 | 0.0108 | 0.0171 |
| H 100k/4 | 0.0399 | 0.0044 | 0.00556 | 0.011 | 0.0176 |
| H 100k/8 | 0.0246 | 0.00514 | 0.00706 | 0.00929 | 0.0144 |
| H 200k/16 | 0.0741 | 0.00885 | 0.0239 | 0.0149 | 0.0314 |
| H 200k/4 | 0.0848 | 0.00573 | 0.0111 | 0.0169 | 0.0347 |
| H 200k/8 | 0.0553 | 0.00655 | 0.0152 | 0.0136 | 0.0302 |
| H 400k/16 | 0.226 | 0.0116 | 0.0505 | 0.0226 | 0.0578 |
| H 400k/4 | 0.136 | 0.00829 | 0.0215 | 0.0254 | 0.058 |
| H 400k/8 | 0.212 | 0.00877 | 0.03 | 0.0242 | 0.0556 |
| H 50k/16 | 0.0124 | 0.00527 | 0.00512 | 0.00703 | 0.00772 |
| H 50k/4 | 0.0192 | 0.00327 | 0.00316 | 0.00686 | 0.00862 |
| H 50k/8 | 0.0139 | 0.00382 | 0.00371 | 0.00617 | 0.00712 |
| U 100k/16 | 0.0359 | 0.00134 | 0.00106 | 0.00482 | 0.00717 |
| U 100k/4 | 0.0266 | 0.0016 | 0.0011 | 0.00693 | 0.0103 |
| U 100k/8 | 0.0232 | 0.00133 | 0.000972 | 0.00537 | 0.0076 |
| U 200k/16 | 0.0495 | 0.00251 | 0.00184 | 0.00754 | 0.0121 |
| U 200k/4 | 0.0551 | 0.00286 | 0.00156 | 0.0121 | 0.0201 |
| U 200k/8 | 0.0759 | 0.00248 | 0.00146 | 0.0104 | 0.0188 |
| U 400k/16 | 0.176 | 0.00586 | 0.00436 | 0.0149 | 0.023 |
| U 400k/4 | 0.179 | 0.00582 | 0.00269 | 0.026 | 0.0463 |
| U 400k/8 | 0.125 | 0.00518 | 0.00301 | 0.0173 | 0.0277 |
| U 50k/16 | 0.0182 | 0.000753 | 0.000704 | 0.00428 | 0.00535 |
| U 50k/4 | 0.0129 | 0.00104 | 0.000852 | 0.00389 | 0.00506 |
| U 50k/8 | 0.0115 | 0.000776 | 0.000674 | 0.00287 | 0.00368 |
| 12.8M controlled | 12.9 | 0.594 | 1.77 | 0.851 | 1.85 |
| 12.8M hub | 17.1 | 0.755 | 2.03 | 1.03 | 2.13 |
| 12.8M uniform | 15.9 | 0.531 | 0.478 | 0.705 | 1.13 |

![Figure 14. Best observed speedups (×) on all 45 graphs, each using its own node-class Serial reference. CPU and GPU-node blocks are separated. Color is logarithmic and clipped at 1/16× and 64×; the exact median seconds appear in the two tables. Different cells may use different resource budgets.](report_assets/figures/09_runtime_matrix.png)

#### 3.7.1 Additional 512-core example

Five configurations on Controlled N=50,000 and E=200,000 use eight nodes with 64 active cores per node, giving 512 cores. This small-graph example is reported separately from the resource curves and aggregate method comparisons.

Table 34. Additional 512-core measurements. Every row satisfies pT=512 and uses one warm-up plus five timed solves; speedup uses this graph's CPU-node Serial median. The rows are not a complete 512-core scaling curve.

| Method | Processes p | Threads T | Exchange | Solve time (s) | Speedup (×) | CPU efficiency (%) |
| --- | --- | --- | --- | --- | --- | --- |
| MPI | 512 | 1 | Allgatherv | 0.131 | 0.227 | 0.044% |
| MPI+Kokkos OpenMP | 512 | 1 | Allgatherv | 0.13 | 0.229 | 0.045% |
| MPI+OpenMP | 512 | 1 | Allgatherv | 0.142 | 0.21 | 0.041% |
| MPI+OpenMP | 128 | 4 | Allgatherv | 0.12 | 0.247 | 0.048% |
| MPI | 512 | 1 | Halo | 1.6 | 0.0185 | 0.004% |

All five configurations are slower than Serial on this graph, and the p512 Halo configuration is particularly costly. Distributing a small amount of graph work across many participants amplifies synchronization and exchange overhead. The example therefore illustrates a workload-size constraint rather than a general high-core ranking.

## 4 Conclusions and insights

### 4.1 What the experiments establish

Standalone OpenMP or Kokkos OpenMP gives the lowest observed CPU-node runtime on 42/45 graphs; only 2 winning configurations use multiple MPI ranks. Standalone CUDA or Kokkos CUDA wins all 45 device-only comparisons, but including GPU-node CPU controls changes the winners to OpenMP on 18 graphs, native CUDA on 11, and Kokkos CUDA on 16. These best-observed comparisons screen implementations across budgets. The matched resource curves establish the separate scaling result: additional participants help large balanced inputs, while smaller or concentrated inputs often favor fewer processes and more threads per process.

The underlying constraint is the distribution of edge work, not graph size alone. Equal vertex ownership leaves roughly 29%-30% of the concentrated graphs’ edges on one process at p=256. Local scheduling and the process/thread split therefore determine how effectively the allocated cores can contribute. Exact Halo exchange changes communication dependencies but leaves this ownership imbalance intact.

Reduced contribution traffic is not equivalent to reduced solve time. Collective scheduling, packing, synchronization, and host/device staging also matter. Matched controls show that a fixed pairwise Alltoallv improves the p=128 Uniform solve by 4.66× relative to automatic selection; they do not establish a universally optimal collective. Similarly, faster device computation does not guarantee a benefit from a second GPU. The practical choices below follow from these workload-dependent effects.

### 4.2 Design implications supported by the experiments

The results suggest different priorities for different workloads. More resources, fewer contribution bytes, and a portable execution interface address different costs; none alone determines runtime. The following decisions follow from the matched resource, exchange, and workload comparisons rather than from a universal ranking of programming models.

Table 35. Practical implications of the measured cases. These are workload-dependent design choices, not claims that one backend or communication implementation is universally optimal.

| Workload or decision | Evidence-based implication | Basis in the results |
| --- | --- | --- |
| Small or moderate fixed graph | Evaluate a single-node backend before increasing MPI participation. | Standalone OpenMP/Kokkos OpenMP is fastest in 42 of 45 CPU-node best-observed comparisons. |
| Large, balanced graph | Consider distributed execution and compare both exact exchanges at the target layout. | Large Uniform benefits from MPI resources; the selected 256-core Halo point reaches 28.6× Serial speedup. |
| Concentrated incoming-edge work | Prioritize ownership balance and local scheduling; compare p/T at equal cores. | One process owns roughly 29%-30% of edges at p256. Changing the fixed-core split improves aggregate Halo ratios by over an order of magnitude. |
| Collective-selection boundary | Retain the automatic baseline and test candidate implementations within matched allocations. | At p128 pairwise improves Uniform by 4.66×; at 64 cores Ring already matches or improves on Bruck for the tested concentrated graphs. |
| Adding a second GPU | Measure end-to-end solve and staging/MPI costs alongside device computation. | Uniform obtains about 2× computation acceleration, while concentrated inputs leave most edge work on one GPU. |
| Graph size grows with resources | Track iteration time and contribution volume separately from nominal vertices/edges per worker. | Allgatherv contribution traffic grows with the global vector; Halo bounds Uniform bytes but does not eliminate peer and synchronization costs. |

The Google output provides a complementary data conclusion: score mass is concentrated and strongly associated with incoming links, while in-degree is not the full weighting rule. Numerical agreement across implementations preserves that graph-level conclusion; hardware and communication choices change the cost of obtaining it.

### 4.3 Scope and reproducibility

The study combines fixed-input scaling, equal-core method comparisons, growing-input comparisons, and matched collective-policy controls. Each configuration uses five timed repeats within an allocation, with CPU models and process/core maps retained. Placement, NUMA regions, and execution dates vary across shared-cluster allocations. Solve time includes iterative computation, communication, and device staging; job startup and graph input are excluded. GPU comparisons use one or two A40 devices.

The repository [5] provides source code, reproducible input-generation parameters, original timing summaries, independent validation records, and measurement-selection rules. Report tables and figures can be regenerated from these records without repeating the performance experiments.

### 4.4 References

[1] Page, L., Brin, S., Motwani, R. and Winograd, T. The PageRank Citation Ranking: Bringing Order to the Web. Stanford, 1999. http://ilpubs.stanford.edu:8090/422/

[2] Stanford SNAP. Google web graph dataset. https://snap.stanford.edu/data/web-Google.html

[3] MPI Forum. MPI standard and collective communication. https://www.mpi-forum.org/docs/

[4] Kokkos documentation. RangePolicy and execution policies. https://kokkos.org/kokkos-core-wiki/API/core/policies/RangePolicy.html

[5] Project source and Vanda result records, report data snapshot compiled 17 November 2026. https://github.com/rosesnack/DSA5208_PROJECT_3

[6] Kokkos 4.5.01 source, commit 175257a51ff29a0059ec48bcd233ee096b2c0438: traits/Kokkos_ScheduleTrait.hpp and OpenMP/Kokkos_OpenMP_Parallel_Reduce.hpp. https://github.com/kokkos/kokkos/tree/4.5.01/core/src

[7] Open MPI v4.1.8. Fixed Alltoallv and Allgatherv algorithm selection, coll_tuned_decision_fixed.c. https://github.com/open-mpi/ompi/blob/v4.1.8/ompi/mca/coll/tuned/coll_tuned_decision_fixed.c

[8] Open MPI v4.1.8. Pairwise and basic-linear implementations, coll_base_alltoallv.c. https://github.com/open-mpi/ompi/blob/v4.1.8/ompi/mca/coll/base/coll_base_alltoallv.c

[9] Open MPI v4.1.8. Forced collective algorithm parameters, coll_tuned_alltoallv_decision.c and coll_tuned_allgatherv_decision.c. https://github.com/open-mpi/ompi/tree/v4.1.8/ompi/mca/coll/tuned

### AI usage

AI assistance supported adaptation of the existing implementation, experiment design, job scripts, debugging, result verification, visualization, and report drafting. All performance values were measured by compiled programs on NUS Vanda. Numerical results were checked independently against Serial and residual criteria; tables and figures were generated from stored measurements. The authors are responsible for reviewing the code, experimental choices, interpretation, and final text.
