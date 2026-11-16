# Remaining 512-core work

Latest live snapshot: **17 November 2026, 02:32 SGT**. Eight performance jobs cover
**114 distinct configurations**; two are Q, six are dependency-held, none is R.
All performance jobs use the paid batch_cpu execution queue, eight physical nodes
and 64 active cores per node. Every configuration satisfies p*T=512. Independent
validation and storage checks use auto_free; no main performance is moved there.

Five validated 512-core cells remain the only completed fixed-graph supplement.
There are 1,165 missing cells: **114 registered**, **five legacy held**, and
**1,046 deferred/unregistered**. Do not duplicate a registered cell. The main
non-512 matrix is complete and unchanged.

## xtt_ella: seven groups, 112 cells

| Graph | Cells | Paid performance | Free validation | State |
|---|---:|---|---|---|
| grid_controlled_n50000_d4 | 16 | 1569659 | 1569660 | Q |
| grid_uniform_n50000_d4 | 16 | 1569685 | 1569686 | H: after first validation |
| grid_hub_n50000_d4 | 16 | 1569687 | 1569688 | H: after first validation |
| grid_controlled_n50000_d8 | 16 | 1569690 | 1569691 | H: after first validation |
| grid_uniform_n50000_d8 | 16 | 1569692 | 1569693 | H: after first validation |
| grid_hub_n50000_d8 | 16 | 1569694 | 1569695 | H: after first validation |
| grid_controlled_n50000_d16 | 16 | 1569696 | 1569697 | H: after first validation |

Each group has one hour walltime. It tests both MPI+OpenMP and MPI+Kokkos OpenMP,
p/T=256/2, 64/8, 32/16 and 16/32, each with Allgatherv and Halo. Each measurement
retains one warm-up and five timed repeats; reports use the five-run median.
One hour covers sixteen small-graph cases, affinity probes, MPI startup and the
existing 65-second pauses after dense TCP Halo launches. It is a limit, not an
expected runtime or actual charge.

The original never-started 1560661/63/65 and their free dependents were cancelled
after replacement registrations were recorded. Their scratch output was not
writable. The new jobs run from
`/home/svu/xtt_ella/dsa5208_endpoint512_20261117/project`, with data/output under
its sibling `data` directory. Original binaries, graph inputs and historical
results stay on scratch; seven Serial references were copied and SHA-256 checked.
Free 1569596 passed the home write/fsync preflight. No source or timing kernel was
changed. The new first validator 1569660 gates the six follow-on performance jobs.
After it passes, PBS automatically releases those dependencies without a new
accounting login or another submission.

Verified fresh CPU balance: 4,749.854 CPUh. Seven one-hour jobs reserve at most
3,584 CPUh. Conservatively counting another 586.667 CPUh for untouched old held
requests and a 256 CPUh margin leaves 323.187 CPUh uncommitted. The prior verified
balance minus all subsequent maximum paid requests independently gives the same
4,749.854 lower bound. These reservations are not actual runtime charges.

## hongxinran: one group, two cells

Paid **1569700**, free validator **1569701**, free storage check **1569699**.
The storage check passed; performance is Q. Graph `grid_uniform_n50000_d16`,
MPI+OpenMP p256,T2, Allgatherv and Halo. It uses eight nodes x64 cores with a
30-minute walltime. Only two small-graph cases and one shared affinity layout
are measured, so the limit retains substantial allowance for MPI startup.

Verified balance is 325.444 CPUh; the maximum new reservation is 256 CPUh,
leaving 69.444 CPUh. Old user-held requests remain deferred and are not released.
These two canonical keys were removed from xtt_ella's revised future plan and
explicitly transferred; they do not overlap its seven registered groups.

## Monitoring and handover

Two detached controllers query PBS every 60 seconds until **18 November 23:59
SGT**. They cover only the registered jobs, adjust queued host bindings only when
previously verified Platinum 8452Y hosts satisfy the full request, and preserve
queue, nodes, cores, memory and walltime. They do not retry failed jobs. At 02:32,
no physical host had 64 free CPUs plus 444 GiB; cpu_all's largest free CPU count
was 32. The two Q jobs are waiting for sufficient resources, not running yet.
PBS rewrites each requested 64 GiB chunk to 444 GiB; capacity checks use the
actual PBS request. Do not promise an immediate start.

The original broad scratch plans and expired controllers are archival. Use the
current scoped plans and explicit ownership records before any further submission.
To stop a controller, create `STOP_AUTO_SUBMIT` in its recorded state directory.
A terminal/SSH disconnect does not cancel PBS jobs or these detached processes.

- [Submission, budgets, current job IDs and cancelled predecessors](../results/updated_vanda_scaling/endpoint512_20261117/resubmission_receipt.json)
- [hongxinran small batch](../results/updated_vanda_scaling/endpoint512_20261117/hongxinran_submission.json)
- [Updated xtt_ella future plan](../results/updated_vanda_scaling/endpoint512_20261117/future_xtt_ella_plan.json)
- [Updated hongxinran future plan](../results/updated_vanda_scaling/endpoint512_20261117/future_hongxinran_plan.json)
- [Explicit two-key transfer](../results/updated_vanda_scaling/endpoint512_20261117/ownership_transfer.json)
- [xtt_ella live snapshot](../results/updated_vanda_scaling/endpoint512_20261117/live_xtt_ella.json)
- [hongxinran live snapshot](../results/updated_vanda_scaling/endpoint512_20261117/live_hongxinran.json)
- [xtt_ella controller](../results/updated_vanda_scaling/endpoint512_20261117/monitor_xtt_ella.json)
- [hongxinran controller](../results/updated_vanda_scaling/endpoint512_20261117/monitor_hongxinran.json)

Legacy 1532794 stays system/user-held; its five cells require separate inspection.
Controlled rank-based 512 weak evidence is also separate from this fixed matrix.
