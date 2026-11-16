# Non-512 report and evidence

This is the report entry point for the completed Vanda experiments. The report has
exactly four main sections: algorithm and data, methodology, results, and
conclusions and insights.

The [performance investigation](../../docs/PERFORMANCE_INVESTIGATION.md) records
open attribution questions for the Google 32-thread and Uniform MPI p128 points.
Saved numerical validation has passed; independent performance reproduction is
still pending. Interpret those points as observed measurements, not established
causal scaling behavior.

- [PDF report](../../output/pdf/pagerank_non512_report.pdf)
- [Editable report](report.md)
- [45-graph runtime matrix](data/runtime_matrix_45.csv)
- [All 19,530 fixed-graph records](data/fixed_results_19530.csv)
- [372 separate weak-suite records and controls](data/weak_results_372.csv)
- [Numerical and timing audit](data/audit.json)
- [Nine vector figures and PNG exports](figures/)

All 512-core results are excluded from every report comparison. The five valid
legacy 512-core records and their provenance remain in the underlying results
archive. The unfinished 512 work is described only in the operational handoff.
The original Git result folders are preserved; none is silently pooled with the
refreshed Vanda measurements.

The 45 fixed graphs consist of three original graphs and 42 extensions. The weak
suite is separate from the fixed-graph denominator. GPU weak-suite standalone
runs on successively larger graphs are fixed-resource controls, not weak-scaling
efficiency measurements. CPU and GPU-node speedups use their own Serial controls.
The best-observed runtime matrix permits different configurations per cell;
fixed-core comparisons are presented separately in the report.

## Rebuild without running benchmarks

Use Python 3.9+ and install `requirements-report.txt`. Neither command below
submits a cluster job or reruns a solver:

```bash
python3 scripts/analyze_report_results.py
python3 scripts/build_non512_report.py --pdftoppm /path/to/pdftoppm
```

Omit `--pdftoppm` to build only the PDF and vector figures. Poppler generates the
PNG figure exports used by the editable report. ReportLab Graphics is used for
the scientific plots; the source CSVs retain unrounded values and provenance.

Google data insights were computed locally from the refreshed, independently
validated Serial vector fetched from Vanda. The vector hash, aggregate statistics
and top ten vertices are saved in `data/google_insights.json` and
`data/google_top10.csv`. The large temporary vector is not an extra Git upload.
To recompute these insights, put that validated vector at
`/tmp/dsa5208_google_refreshed_ranks.csv` before running the analysis. Existing
insight files are reused by the report builder when no vector is available.

## Before submission

The PDF is an initial draft, not a claim that the whole coursework submission is
finished. Add actual group names and student IDs, review the AI disclosure and
interpretations, and check the submission deadline with the instructor. To add
the author block, create `reports/non512/authors.json` containing objects with
`name` and `student_id`, then rebuild. Do not use invented identity information.

Raw full-vector checks were performed by the independent Vanda validators. The
local report audit verifies saved completion evidence, solver settings, five
timings, summary medians, numerical bounds and recorded process/thread layouts;
it does not rerun all original edge-list/rank comparisons.

The source-manifest hash in `data/audit.json` identifies the input snapshot. The
raw experiment summaries, timings, mappings and validation markers remain the
authoritative measurements. Tables and figures are derived artifacts.
