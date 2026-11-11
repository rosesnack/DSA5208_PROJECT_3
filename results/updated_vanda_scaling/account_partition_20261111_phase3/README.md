# Phase 3 ownership transfer (2026-11-11)

The actual active source plans are linked from HANDOFF_VANDA_EXPERIMENTS_20261106.md. This directory records the coordinated transfer; frozen snapshots are audit evidence, not runnable current plans.

- `account_partition.json`: the actual transferred 136 groups/730 cells, CPU-hour ceiling, new owner, source removal, preparation dependency and submission snapshot.
- `primary_plan.json`: the primary remainder at transfer time.
- `combined_hongxinran_plan.json`: current combined scope, including the old completed 448 and the new 730.
- `new_hongxinran_plan.json`: only the newly transferred scope; use the active controller and registry, not a second submitter.
- `*_frozen.json`: plans, source hashes, registered keys and held jobs before source-plan removal, while both monitor locks were free. Historical only.
- `*_submission_snapshot.json`: actual registry and PBS/monitor observations, each with a timestamp. Performance jobs and dependent free checks are different jobs, not duplicate experiments.

No configuration in a frozen snapshot grants permission for a fresh RUN_ID or another account to submit it. New work is owned by hongxinran; the source plan no longer contains its keys. The scheduler may keep Q jobs waiting for matching hosts; no queued request is a runtime result.
