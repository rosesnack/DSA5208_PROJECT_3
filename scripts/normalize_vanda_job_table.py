"""Normalize a run's PBS job table to LF after CSV updates."""
import sys
from pathlib import Path


root = Path("results/updated_vanda_scaling") / sys.argv[1]
for name in ("submitted_jobs.tsv", "free_cpu_archived_submissions.tsv"):
    path = root / name
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
