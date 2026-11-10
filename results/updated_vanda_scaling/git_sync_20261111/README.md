# Frozen experiment handover inventory (2026-11-11)

The current operating instructions are [HANDOFF_VANDA_EXPERIMENTS_20261106.md](../../../HANDOFF_VANDA_EXPERIMENTS_20261106.md). This directory is a frozen audit, not a submission plan or a cross-account reservation service.

- `experiment_manifest_20700.csv`: every fixed-graph target, completion state, actual registered jobs, future owner/plan, and handover action. `canonical_summary` is the cross-account configuration key.
- `cells_<status>.csv`: the same rows split by state for review. `unsubmitted` means no effective current registered job; it does **not** mean never attempted or available for another account to claim.
- `submitted_core_groups.csv`: actual current resource-group registries, including performance and free validation job IDs. A plan without a job ID is not a submitted experiment.
- `cpu_core_layouts.csv`: fixed-core mainline coverage; other original node layouts remain in the full manifest.
- `weak_experiment_manifest.csv`: separate weak curves, not part of the 20,700 denominator. Missing local evidence requires checking remote results and legacy jobs before considering a rerun.
- `queue_<account>.json`: whitelisted PBS snapshots, known jobs, monitor state and exact observation times. Old held jobs are recorded but are not all active assignments in the current per-cell registry.
- `handoff_summary.json`: totals, ownership assertions, future-plan paths and snapshot times.

Every row has `submission_allowed_from_snapshot=False`. Completed cells are reused. Registered/held/awaiting-validation cells are tracked through existing jobs. Unsubmitted cells still belong to `future_owner`; coordinate stopping the source monitor, removing transferred keys from its **live source plan**, checking both queues and old held requests, and recording the new owner before submitting a teammate-only plan. Local RUN_ID deduplication does not provide cross-account locking.

Rebuild the fixed audit after syncing approved result roots:

```bash
python3 scripts/audit_fixed_matrix.py vanda \
  results/updated_vanda_scaling/20261106T185006Z \
  --reuse-root results/updated_vanda_scaling/20261102T092147Z \
  --reuse-root results/updated_vanda_scaling/20261111_hongxinran_assist \
  --include-additional-512 \
  --csv results/updated_vanda_scaling/git_sync_20261111/fixed_matrix_audit_20700.csv
```

After refreshing the whitelisted queue snapshots and synchronizing the actual controller plans, export the handover:

```bash
python3 scripts/export_vanda_handoff.py \
  --audit results/updated_vanda_scaling/git_sync_20261111/fixed_matrix_audit_20700.csv \
  --main-root results/updated_vanda_scaling/20261106T185006Z \
  --assist-root results/updated_vanda_scaling/20261111_hongxinran_assist \
  --main-plan results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_xtt_ella_20261111_phase2_small_balance.json \
  --assist-plan results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261111_phase2.json \
  --snapshots results/updated_vanda_scaling/git_sync_20261111 \
  --output results/updated_vanda_scaling/git_sync_20261111
```

Both commands are local audits; neither submits, releases or cancels jobs. Add new transferred-account roots and ownership records before using this inventory for later handovers. A successful export checks unique future ownership and consistency with current registered assignments; it does not certify that an old local snapshot equals the live remote queues.
