#include <mpi.h>

#include <iostream>
#include <string>

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    char host[MPI_MAX_PROCESSOR_NAME];
    int length = 0;
    MPI_Get_processor_name(host, &length);
    std::cout << rank << ',' << std::string(host, static_cast<std::size_t>(length)) << '\n';
    MPI_Finalize();
    return 0;
}
