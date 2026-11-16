# Vanda status

Snapshot: **17 November 2026, 02:32 SGT**. Read live PBS before any change.

All **19,530/19,530 non-512 fixed-graph configurations** and the **372 non-512
weak-suite entries/controls** have complete measurement and independent-validation
evidence. No non-512 configuration needs another performance submission.

The additional diagnostic measurements are also complete: Google 16 cases and
hongxinran 256-core Uniform/Hub/Controlled 18 cases. The final independent 128-core
Uniform MPI Halo performance job **1569195** and free validator **1569196** both
finished with Exit 0. Median solve time is **4.296756030 s** from five timed runs;
communication median is **4.122365467 s**. Independent rank L1 difference from
Serial is zero; residual is 1.4263e-9. All 14 Uniform 256-core case validations
passed; free finalizer **1569281** completed successfully.

The report uses the complete main matrix plus **five validated 512-core cases**
in a separate partial table and matrix column. Missing cells display `-`.
Every primary solve time is the median of five timed runs after one warm-up.
[Measurement selection](../reports/non512/measurement_selection.json) maps 27
final measurement sources to their original timings and validation evidence;
all other main records retain their existing sources. Raw provenance is retained.

| Remaining fixed-graph work | Configurations | Current action |
|---|---:|---|
| xtt_ella seven new/replaced groups | 112 | First Q; six depend on its successful free validation |
| hongxinran small Hybrid group | 2 | 1569700 Q; free 1569701 validates it |
| Legacy 512-core group | 5 | 1532794 system/user-held; do not release blindly |
| Other deferred 512-core targets | 1,046 | Not scheduled |
| Total remaining | 1,165 | All are 512-core fixed-graph targets |

The eight performance jobs are registered once; no performance is running at
02:32. Two scoped controllers check host availability every minute until
18 November 23:59 SGT. New home output bypasses unwritable xtt_ella scratch;
old 1560661/63/65 and their dependents were cancelled after replacement records.
All performance remains paid and uses actual 8x64-core requests. See the
[full 512 table, budget and controller records](VANDA_512.md). Registered jobs
must not be submitted again by a teammate. Follow-on dependencies release
automatically after the first group's independent validation passes.

Controlled rank-based 512 weak evidence still needs separate inspection. It is
outside the complete non-512 scope and the 20,700 fixed-graph denominator.

See the [report](../reports/non512/README.md),
[handoff](../HANDOFF_VANDA_EXPERIMENTS_20261106.md),
[512 plan](VANDA_512.md), and
[operational evidence](PERFORMANCE_INVESTIGATION.md).
