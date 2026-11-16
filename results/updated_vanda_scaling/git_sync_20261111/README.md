# Experiment handover inventory (latest update 2026-11-17)

Nov17 02:32 SGT: 19,535 validated; 114 registered 512-core cells across eight current performance jobs, five legacy held cells and 1,046 deferred cells. Two jobs Q, six dependency H, none R. Current future plans are the scoped/ownership-adjusted files under `../endpoint512_20261117/`; the old three primary 512 job IDs were cancelled. See the operating handoff before using older commands below.

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
  --main-plan results/updated_vanda_scaling/20261106T185006Z/core_group_watch_plan_xtt_ella_20261113_refund.json \
  --assist-plan results/updated_vanda_scaling/20261111_hongxinran_assist/core_group_watch_plan_hongxinran_20261113_refund.json \
  --snapshots results/updated_vanda_scaling/git_sync_20261111 \
  --output results/updated_vanda_scaling/git_sync_20261111
```

Both commands are local audits; neither submits, releases or cancels jobs. Add new transferred-account roots and ownership records before using this inventory for later handovers. A successful export checks unique future ownership and consistency with current registered assignments; it does not certify that an old local snapshot equals the live remote queues.

The 2026-11-12 validation reroute preserves performance job IDs and records replaced free validation jobs in `../20261106T185006Z/free_validation_reroute_20261112.json`. Follow the registry's current validation ID; cancelled old validation IDs do not grant permission to remeasure a performance cell.

Nov 13 current source plans are disjoint. The primary archived 53 scheduler requests cancelled before start because their dependency was purged; those archives are not active assignments. Only never-computed cells were registered again against the fresh successful input check. Current assignments remain unique. See dependency_repair_20261113.json for exact PBS evidence.

Nov 13 15:32 SGT frozen export: 18,997 validated fixed cells. Queued physical CPU host bindings can now be refreshed by the live controllers. `requested_hosts` in source/group plans records the initial request; consult each RUN's `placement_refresh_events.jsonl` for later changes and PBS `exec_vnode` plus `cpu_hosts.jsonl` for actual allocation. `aggregate_placement_validation_20261113.json` preserves the two successful eight-physical-node trials. NUMA vnode count is not physical node count.

Nov 14 01:46 SGT: 19,111 validated cells are downloaded and audited. PBS queries on both accounts fail with Connection refused. Unfinished PBS states retain their last successful observations; they are NOT current queue confirmations. See queue_query_available=False and queue_status_note in handoff_summary.json. Both remote monitors are alive again, with the unchanged plans and limits, until Nov14 23:59 SGT.

Nov14 23:57 SGT service/queue queries recovered. Both accounts had zero performance R/Q. The previous 28 queued128 jobs finished, and 266 newly validated cells were downloaded and audited on Nov15: 19,377/20,700 complete. Source plans and assignment ownership remain disjoint. The final44 ordinary candidates remain owned by xtt_ella and need renewed accounting authentication plus budget checks; the primary monitor now continues until Nov15 23:59. Earlier service-unavailable notices describe earlier snapshots.

Nov15 00:46 SGT: all114 reviewed non512 error/missing targets now have unique registrations:96 paid measurements and18 free saved-cell checks. Eleven failed registrations are archived rather than duplicated. held includes30 new memory-dependent cells and5 old512 cells; awaiting_validation includes18 intact measurements from failed batches. Actual runjob is currently blocked by the platform budget service, even on free jobs. See current handoff and non512_recovery_20261115/submission.json.

Nov16 01:14: validated19,461. Saved19 partial measurements remain under primary free validation; only55 missing performance cells move to hongxinran. The old74 assignments are archived, current/future ownership remains disjoint. Formal vectors are retained without compression/deletion; the receiving scratch had281G free. All new performance waits for receiving-account free6GiB check1560516.
