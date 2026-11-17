/* Untimed component-selection, post-init affinity and correctness probe. */
#define _GNU_SOURCE
#include <mpi.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    int *counts = malloc(size * sizeof(int));
    int *offsets = malloc(size * sizeof(int));
    double *send = malloc(size * sizeof(double));
    double *recv = malloc(size * sizeof(double));
    for (int i = 0; i < size; ++i) {
        counts[i] = 1;
        offsets[i] = i;
        send[i] = rank * size + i;
    }
    MPI_Alltoallv(send, counts, offsets, MPI_DOUBLE,
                  recv, counts, offsets, MPI_DOUBLE, MPI_COMM_WORLD);
    int errors = 0;
    for (int i = 0; i < size; ++i) errors += recv[i] != i * size + rank;
    double value = rank;
    MPI_Allgatherv(&value, 1, MPI_DOUBLE, recv, counts, offsets,
                   MPI_DOUBLE, MPI_COMM_WORLD);
    for (int i = 0; i < size; ++i) errors += recv[i] != i;
    int total;
    MPI_Allreduce(&errors, &total, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
    if (rank == 0) printf("collective_probe ranks=%d errors=%d\n", size, total);
    cpu_set_t allowed;
    sched_getaffinity(0, sizeof(allowed), &allowed);
    char host[MPI_MAX_PROCESSOR_NAME], row[16384];
    int length;
    MPI_Get_processor_name(host, &length);
    int written = snprintf(row, sizeof(row), "affinity_after_init {\"rank\":%d,\"host\":\"%s\",\"cpus\":[", rank, host);
    int first = 1;
    for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) if (CPU_ISSET(cpu, &allowed)) {
        written += snprintf(row + written, sizeof(row) - written, "%s%d", first ? "" : ",", cpu);
        first = 0;
    }
    snprintf(row + written, sizeof(row) - written, "]}\n");
    fputs(row, stdout);
    fflush(stdout);
    free(counts); free(offsets); free(send); free(recv);
    MPI_Finalize();
    return total ? 1 : 0;
}
