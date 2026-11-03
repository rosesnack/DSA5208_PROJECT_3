"""Pin one MPI rank to its assigned CPU cores, then run the requested program."""

import os
import sys

threads = int(sys.argv[1])
local_rank = int(os.environ["OMPI_COMM_WORLD_LOCAL_RANK"])
allowed_cpus = sorted(os.sched_getaffinity(0))
first = local_rank * threads
os.sched_setaffinity(0, allowed_cpus[first:first + threads])
os.execvp(sys.argv[2], sys.argv[2:])
