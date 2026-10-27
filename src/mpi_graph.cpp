#include "mpi_graph.hpp"
#include <mpi.h>

#include <algorithm>

Partition distribute_graph(const Graph& graph) {
    Partition local;
    MPI_Comm_rank(MPI_COMM_WORLD, &local.rank);
    MPI_Comm_size(MPI_COMM_WORLD, &local.processes);
    local.total_nodes = local.rank == 0 ? static_cast<int>(graph.size()) : 0;
    MPI_Bcast(&local.total_nodes, 1, MPI_INT, 0, MPI_COMM_WORLD);

    // Split consecutive dense IDs evenly; the first processes get any remainder.
    local.counts.resize(local.processes);
    local.displacements.resize(local.processes);
    int begin = 0;
    for (int p = 0; p < local.processes; ++p) {
        local.counts[p] = local.total_nodes / local.processes + (p < local.total_nodes % local.processes);
        local.displacements[p] = begin;
        begin += local.counts[p];
    }

    std::vector<int> edge_counts(local.processes), edge_displacements(local.processes);
    if (local.rank == 0) {
        for (int p = 0; p < local.processes; ++p) {
            const auto first = graph.in_offsets[local.displacements[p]];
            const auto last = graph.in_offsets[local.displacements[p] + local.counts[p]];
            edge_counts[p] = static_cast<int>(last - first);
            edge_displacements[p] = static_cast<int>(first);
        }
        local.min_edges = *std::min_element(edge_counts.begin(), edge_counts.end());
        local.max_edges = *std::max_element(edge_counts.begin(), edge_counts.end());
    }

    const int count = local.counts[local.rank];
    int edge_count = 0;
    MPI_Scatter(edge_counts.data(), 1, MPI_INT, &edge_count, 1, MPI_INT, 0, MPI_COMM_WORLD);
    local.in_offsets.resize(count + 1);
    local.in_sources.resize(edge_count);
    local.out_degree.resize(count);

    // Send row starts without overlapping boundary entries; append the final offset locally.
    MPI_Scatterv(graph.in_offsets.data(), local.counts.data(), local.displacements.data(), MPI_UINT64_T,
                local.in_offsets.data(), count, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    MPI_Scatterv(graph.in_sources.data(), edge_counts.data(), edge_displacements.data(), MPI_UINT64_T,
                local.in_sources.data(), edge_count, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    MPI_Scatterv(graph.out_degree.data(), local.counts.data(), local.displacements.data(), MPI_UINT64_T,
                local.out_degree.data(), count, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    const Index first = local.in_offsets.front();
    for (int v = 0; v < count; ++v) local.in_offsets[v] -= first;
    local.in_offsets[count] = edge_count;
    return local;
}

