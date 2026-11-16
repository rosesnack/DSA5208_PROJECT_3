# Repository guide

The old daily `updated_*.md` notes were removed after their useful information was
consolidated. Their history remains in Git. This cleanup does not remove source
code, original benchmark results, refreshed results, independent validation
evidence, source plans, registries or allocation records.

Use these entry points:

| Purpose | Entry |
|---|---|
| Build and run source code | [README](../README.md) |
| Completed non-512 report and reproducible analysis | [Report guide](../reports/non512/README.md) |
| Current validated dataset and scope | [Vanda status](VANDA_STATUS.md) |
| Full target matrix and teammate ownership | [Experiment handoff](../HANDOFF_VANDA_EXPERIMENTS_20261106.md) |
| Remaining 512-core batch | [512 status](VANDA_512.md) |
| Per-configuration authoritative inventory | [20,700-row manifest](../results/updated_vanda_scaling/git_sync_20261111/experiment_manifest_20700.csv) |
| Full-core layout coverage | [CPU layout table](../results/updated_vanda_scaling/git_sync_20261111/cpu_core_layouts.csv) |

The report contains 19,530 validated non-512 fixed-graph configurations across 45
graphs, plus a separate 372-entry non-512 weak suite including fixed-resource
controls. A repeated timing observation is not a new configuration. PBS jobs can
contain several configurations and should not be counted as configurations.

The full fixed target is still 20,700, including the 1,170 CPU 512-core targets.
Five 512-core cells were validated previously; these remain archived but are
excluded from the report. Missing 512-core work must not be inferred from a
non-512-only table.
