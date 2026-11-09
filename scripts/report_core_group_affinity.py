"""Record the CPU cores assigned to one MPI rank, outside solver timing."""
import json
import os
import socket

print(json.dumps({"rank": int(os.environ["OMPI_COMM_WORLD_RANK"]),
                  "host": socket.gethostname(),
                  "cpus": sorted(os.sched_getaffinity(0))}), flush=True)
