# Vanda CPU-hour accounting issue — 2 November 2026

Account: `hongxinran`

Project: `personal-hongxinran`

Experiment run: `20261102T092147Z`

At approximately 23:38 SGT, `hpc project` showed 11.666 CPU hours left from 10,000, and 880 GPU hours left from 1,000. CPU jobs are held by PBS `am_hook` or wait with `Budgets: runjob: Required budget is not available`. Releasing one 32-core serial job moved it back to budget waiting; PBS also rejected a request to shorten its walltime.

The [amgr transaction export](results/updated_vanda_scaling/20261102T092147Z/amgr_cpu_transactions_20261102.csv) contains 35 positive CPU debits totaling **9,988.334 CPU hours**. Every CPU transaction in the export says `reconciled=no`; there are no CPU credit entries. The [PBS comparison](results/updated_vanda_scaling/20261102T092147Z/amgr_cpu_reconciliation_evidence.csv) calculates **217.326 core-hours** as allocated CPU cores multiplied by PBS's `resources_used.walltime` for those same 35 jobs. This is an estimate of time used, not a claim about NUS's final billing formula.

Examples:

| PBS job | Reserved CPU hours | PBS elapsed time | Allocated cores | Estimated core-hours | Exit |
|---|---:|---:|---:|---:|---:|
| `1509223` | 3,072 | 37 s | 128 | 1.316 | 1 |
| `1509222` | 1,536 | 5 s | 64 | 0.089 | 1 |
| `1509209` | 768 | 1 s | 32 | 0.009 | 127 |
| `1509220` | 768 | 53 s | 32 | 0.471 | 0 |
| `1510576` | 256 | 24 min 54 s | 256 | 106.240 | 0 |

The 24-hour walltime requests for the first pilot jobs were overly large. Those requests, including failed jobs, were charged in full at launch and have not been reconciled in the project ledger. Subsequent scripts use shorter walltimes and batch submission. No new paid CPU jobs should be submitted until the balance is corrected or the accounting policy is clarified. Existing GPU jobs may continue against the separate GPU balance.

The Vanda command `hpc project-usage personal-hongxinran 2026-11-02 2026-11-02` states that negative used hours indicate credit back from completed jobs and that usage can fluctuate because of reconciliation of unused job credits. At 23:46 SGT, the same-day usage report still showed zero reported jobs and the CPU balance remained 11.666. This confirms that credit-back is a supported mechanism, but does not establish when the outstanding transactions will reconcile. Recheck the balance after the next accounting update; if it remains unchanged, send the support request below. A new CPU allocation request is not the first step.

## Draft for NUS HPC Enquiries

**Subject:** Vanda CPU-hour precharges still unreconciled after PBS jobs finish

Hello NUS HPC Support,

I am using Vanda with project `personal-hongxinran` under NUS ID `hongxinran`. My CPU Net Balance is now 11.666 out of 10,000 CPU hours, and my CPU jobs are held by the `am_hook` budget check.

I exported my `amgr report project` transactions for 2 November. The 35 positive CPU debits total 9,988.334 CPU hours, all marked `reconciled=no`, with no CPU credits. The same jobs used approximately 217.326 core-hours when estimated from PBS allocated cores and `resources_used.walltime`. For example, job `1509223.stdct-mgmt-02` reserved 3,072 CPU hours for a 24-hour request but exited after 37 seconds; job `1509220.stdct-mgmt-02` reserved 768 CPU hours but completed in 53 seconds.

The `hpc project-usage` command says unused job credits can be returned during reconciliation, but the same-day usage report currently lists zero jobs. Could you please check when these completed and failed jobs will reconcile, restore any unused precharged CPU hours if the process is stuck, and advise how to release the `am_hook` holds safely? I can provide the transaction export and per-job PBS comparison.

Thank you.
