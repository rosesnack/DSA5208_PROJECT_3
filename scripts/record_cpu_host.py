"""Emit the CPU model on one allocated MPI host for benchmark provenance."""
import json
import os
from pathlib import Path
import socket

model = next(line.split(":", 1)[1].strip()
             for line in Path("/proc/cpuinfo").read_text().splitlines()
             if line.startswith("model name"))
print(json.dumps({"host": socket.gethostname(), "cpu_model": model,
                  "logical_cpus": os.cpu_count(),
                  "affinity_cpus": len(os.sched_getaffinity(0)),
                  "tcp_ephemeral_port_range": Path('/proc/sys/net/ipv4/ip_local_port_range').read_text().strip(),
                  "tcp_tw_reuse": Path('/proc/sys/net/ipv4/tcp_tw_reuse').read_text().strip()}), flush=True)
