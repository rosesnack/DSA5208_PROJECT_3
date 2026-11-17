# Vanda report and evidence

The report has four main sections: algorithm and data; methodology; results;
conclusions and insights. It covers the complete 19,530-configuration main matrix
on 45 fixed graphs, 372 separate weak-suite entries/controls, and a clearly labeled
five-configuration 512-core supplement. The existing directory and PDF filename
are retained for stable repository links.

- [PDF report](../../output/pdf/pagerank_non512_report.pdf)
- [Editable report](report.md)
- [45-graph runtime matrix](data/runtime_matrix_45.csv)
- [Complete main records](data/fixed_results_19530.csv)
- [Partial 512-core records](data/supplement_512.csv)
- [Separate weak-suite records](data/weak_results_372.csv)
- [Numerical and timing audit](data/audit.json)
- [Measurement selection and provenance](measurement_selection.json)
- [Review of the teammate draft and evidence changes](REVIEW_NOTES.md)
- [Rank workload diagnostics](data/rank_work_diagnostics.csv)
- [Thread-policy diagnostics](data/thread_policy_diagnostics.csv)
- [Version-specific MPI selector consistency](data/mpi_selector_consistency.csv)
- [Pinned source and CPU-layout checks](data/source_mechanism_checks.json)
- [Weak-scaling payload and phase diagnostics](data/weak_traffic_diagnostics.csv)
- [GPU work-distribution diagnostics](data/gpu_work_diagnostics.csv)
- [Three precisely scoped optimum counts](data/method_optima.json)
- [Ten vector figures and PNG exports](figures/)

The 45 fixed graphs contain three original graphs and 42 extensions. Weak-suite
standalone GPU runs on growing inputs are fixed-resource controls, not weak
resource-efficiency curves. CPU and GPU-node speedups use their own Serial
references. Best-observed matrix cells may use different resource budgets;
fixed-core and matched-layout comparisons are presented separately.

Each configuration uses one warm-up and five timed runs. Primary solve-time
tables and figures report the median of the five timed runs.

The 512 supplement has only five validated cases, on one 50k-vertex graph. It is
not a complete method comparison or a complete scaling curve. A hyphen (`-`)
marks missing matrix cells. Its records are excluded from main-matrix aggregates.
The 45-row CPU matrix keeps this partial column; the separate GPU matrix includes
its own Serial reference. The root-level teammate PDF is a preserved input, while
`output/pdf/pagerank_non512_report.pdf` is the current generated deliverable.

## Build the report without running a benchmark

Use Python 3.9+ and install `requirements-report.txt`:

```bash
python3 scripts/select_report_measurements.py
python3 scripts/analyze_report_results.py
python3 scripts/build_non512_report.py --pdftoppm /path/to/pdftoppm
```

Only complete, independently validated measurements can enter the selection.
Selection is deterministic and uses predefined runtime settings, never the
fastest repeat or fastest observed runtime policy. Every selected cell retains
its source summary, original five timings and independent validator evidence.
All tables, geometric aggregates, speedups and efficiencies are recalculated.
Input-inventory and selection hashes are recorded in `data/audit.json`.

None of these commands submits a cluster job. Omit `--pdftoppm` to build only the PDF and
vector figures. PNG exports support the editable Markdown report. ReportLab
Graphics produces the scientific plots; data tables retain unrounded values.

Google graph insights use the validated Serial rank vector. Aggregate statistics,
its hash and the top ten vertices are retained in `data/google_insights.json`
and `data/google_top10.csv`. To recompute, place that vector at
`/tmp/dsa5208_google_refreshed_ranks.csv` before analysis. The full temporary vector
is not an extra Git upload. Existing insight files are used when it is absent.

## Submission preparation

Group names and student IDs in `authors.json` are transcribed from the supplied
teammate draft. Verify that transcription, review the AI disclosure and scientific
interpretations, and confirm the current submission deadline. The author file is
a list of objects with `name` and `student_id`.
Prepare the Canvas source package without operational logs or terminal output.

The local report audit checks saved independent validation evidence, settings,
five timings, medians, numerical bounds and recorded layouts. It does not execute
new graph solvers or recompute all full-vector residuals locally. Original raw
records are preserved for provenance. Current execution details and incomplete
work are in the [operational handoff](../../HANDOFF_VANDA_EXPERIMENTS_20261106.md).
