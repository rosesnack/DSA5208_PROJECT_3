"""Report an MPI rank's actual CPU affinity for a Vanda placement check."""

import os
import socket

print(
    f"{os.environ['OMPI_COMM_WORLD_LOCAL_RANK']},"
    f"{socket.gethostname()},"
    f"{':'.join(map(str, sorted(os.sched_getaffinity(0))))}"
)
