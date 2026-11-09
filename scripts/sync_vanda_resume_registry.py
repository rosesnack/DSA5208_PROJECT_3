"""Map audited continuation jobs into the project's existing progress/usage tables."""
import argparse
import csv
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run_id")
args = parser.parse_args()
root = Path("results/updated_vanda_scaling") / args.run_id


def read(name):
    with (root / name).open(newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def write(name, fields, rows):
    with (root / name).open("w", newline="") as destination:
        output = csv.DictWriter(destination, fieldnames=fields, delimiter="\t")
        output.writeheader()
        output.writerows(rows)


def key(row):
    stage, nodes = row["stage"], row["nodes"]
    if stage == "core_weak":
        stage = "cpu_core_weak_512" if nodes == "512" else "cpu_core_weak"
    stage = {"strong": "mpi_strong", "strong512": "mpi_strong_512",
             "mpi_512_fixed": "mpi_strong_512", "weak_core": "cpu_core_weak_512",
             "weak512": "mpi_weak_512", "weak_512": "mpi_weak_512",
             "kokkos_retry": "kokkos_cpu_grid", "mpi_strong_retry": "mpi_strong"}.get(stage, stage)
    if stage in ("cpu_core_weak", "cpu_core_weak_512", "mpi_strong_512", "mpi_weak_512"):
        nodes = "8"
    return stage, row["graph"], nodes


backup = root / "submitted_jobs_before_resume_20261107.tsv"
if not backup.exists():
    shutil.copyfile(root / "submitted_jobs.tsv", backup)
original = read(backup.name)
audited = read("audited_resume_jobs.tsv")
replanned = {row["old_job"].split(".")[0]: key(row)
             for row in audited if row["old_job"]}
targets, attempts, retries = {}, {}, []
for row in original:
    if row["stage"] == "serial_reference_validation":
        continue
    k = replanned.get(row["job_id"].split(".")[0], key(row))
    targets.setdefault(k, row["job_id"])
    attempts[row["job_id"]] = k
for row in audited:
    k = key(row)
    job = row["performance_job"]
    targets.setdefault(k, job)
    if row["old_job"]:
        attempts[row["old_job"].split(".")[0] + ".stdct-mgmt-02"] = k
    if job != targets[k]:
        retries.append(dict(zip(("stage", "graph", "nodes", "original_job", "replacement_job", "reason"),
                                (*k, targets[k], job, "paid_performance_with_free_validation"))))
for row in read("reused_results.tsv"):
    k = key(row)
    retries.append(dict(zip(("stage", "graph", "nodes", "original_job", "replacement_job", "reason"),
                            (*k, targets[k], row["source_job"], "reuse_after_per_host_cpu_audit"))))
for stage, job in (("data", "1527523"), ("data_512", "1527526"),
                   ("cpu_build", "1527528"), ("cpu_smoke", "1527550")):
    targets.setdefault((stage, "-", "1"), job + ".stdct-mgmt-02")
write("submitted_jobs.tsv", ("stage", "graph", "nodes", "job_id"),
      [dict(zip(("stage", "graph", "nodes", "job_id"), (*k, job)))
       for k, job in targets.items()])
write("retry_jobs.tsv", ("stage", "graph", "nodes", "original_job", "replacement_job", "reason"), retries)

known = set(targets.values()) | {row["replacement_job"] for row in retries}
failed = {
    "1527524.stdct-mgmt-02": ("cpu_build", "-", "1"),
    "1527561.stdct-mgmt-02": ("kokkos_cpu_grid", "grid_controlled_n50000_d4", "1"),
    "1527562.stdct-mgmt-02": ("kokkos_cpu_grid", "grid_controlled_n50000_d4", "2"),
}
write("failed_jobs.tsv", ("stage", "graph", "nodes", "job_id"),
      [dict(zip(("stage", "graph", "nodes", "job_id"), (*k, job)))
       for job, k in failed.items() if job not in known])
write("replaced_jobs.tsv", ("stage", "graph", "nodes", "job_id"),
      [dict(zip(("stage", "graph", "nodes", "job_id"), (*k, job)))
       for job, k in attempts.items() if job not in known and job not in failed])

auxiliary = [{"stage": "free_validation", "graph": row["graph"], "nodes": "1",
              "job_id": row["validation_job"], "role": "independent_free_validation"}
             for row in audited if not row["validation_job"].startswith("1527816.")]
for stage, graph, job in (("reference_generation", "nine_graphs", "1527560"),
                          ("reference_staging", "nine_graphs", "1527806"),
                          ("weak_baseline_staging", "three_families", "1527812"),
                          ("original_reference_pack", "45_graphs", "1527814"),
                          ("original_reference_unpack", "45_graphs", "1527875"),
                          ("free_validation", "hub_core256", "1527844"),
                          ("free_validation", "controlled_core256", "1527845")):
    auxiliary.append(dict(stage=stage, graph=graph, nodes="1", job_id=job + ".stdct-mgmt-02",
                          role="free_reference_or_postprocessing"))
write("auxiliary_jobs.tsv", ("stage", "graph", "nodes", "job_id", "role"), auxiliary)
print(f"Registered {len(targets)} submitted targets, {len(retries)} replacements/reused sources, "
      f"{len(auxiliary)} free preparation/validation jobs")
