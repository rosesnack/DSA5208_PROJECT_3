"""Release one authorized held job when credits cover it and all queued requests."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("job")
parser.add_argument("project")
parser.add_argument("--state-file", type=Path, required=True)
parser.add_argument("--margin", type=float, default=128)
parser.add_argument("--interval", type=int, default=600)
args = parser.parse_args()


def command(*parts):
    return subprocess.check_output(parts, text=True, stderr=subprocess.STDOUT)


def reservation(job):
    resources = job["Resource_List"]
    hours, minutes, seconds = map(int, resources["walltime"].split(":"))
    return int(resources["ncpus"]) * (hours + minutes / 60 + seconds / 3600)


while True:
    try:
        target_id, target = next(iter(json.loads(command(
            "qstat", "-fx", "-F", "json", args.job))["Jobs"].items()))
        if target["job_state"] != "H":
            print(f'{target_id}: state {target["job_state"]}; no release needed', flush=True)
            break
        assert target["project"] == args.project
        ids = command("qselect", "-u", os.environ["USER"]).split()
        jobs = json.loads(command("qstat", "-f", "-F", "json", *ids))["Jobs"]
        balance_text = command("hpc", "project")
        balance_rows = [line for line in balance_text.splitlines()
                        if line.strip().startswith(args.project + " ")]
        if not balance_rows:
            print('No project balance available; waiting for amgr session refresh', flush=True)
        else:
            balance = float(balance_rows[0].split("|")[2])
            pending = sum(reservation(job) for job_id, job in jobs.items()
                          if job_id != target_id and job.get("project") == args.project
                          and job["queue"] in ("auto", "batch_cpu")
                          and job["job_state"] in ("Q", "H"))
            needed = reservation(target)
            state = {"observed_at": datetime.now(timezone.utc).isoformat(),
                     "job": target_id, "balance": balance, "other_queued_cpu_hours": pending,
                     "needed_cpu_hours": needed, "margin": args.margin,
                     "released": balance - pending >= needed + args.margin}
            if state["released"]:
                command("qrls", args.job)
            args.state_file.write_text(json.dumps(state, indent=2) + "\n")
            print(json.dumps(state), flush=True)
            if state["released"]:
                break
    except subprocess.CalledProcessError as error:
        print(f'Queue/budget query unavailable (exit {error.returncode}); retrying', flush=True)
    time.sleep(args.interval)
