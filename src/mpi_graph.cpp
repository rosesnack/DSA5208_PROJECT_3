#include "mpi_graph.hpp"
#include <mpi.h>

#include <algorithm>
#include <unordered_map>

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

HaloPlan build_halo_plan(const Partition& local) {
    const double setup_start = MPI_Wtime();
    HaloPlan plan;
    const int count = local.counts[local.rank];
    const int begin = local.displacements[local.rank];
    std::vector<std::vector<Index>> requested_by_owner(local.processes);

    // The graph is stored by destination row, while rank values are owned by
    // the same contiguous node partition. Find the distinct remote source IDs
    // needed by this rank and group them by their owning rank.
    for (const Index source : local.in_sources) {
        const auto owner_it = std::upper_bound(local.displacements.begin(),
                                               local.displacements.end(),
                                               static_cast<int>(source));
        const int owner = static_cast<int>(owner_it - local.displacements.begin()) - 1;
        if (owner != local.rank) requested_by_owner[owner].push_back(source);
    }

    plan.request_counts.resize(local.processes);
    plan.request_displacements.resize(local.processes);
    int request_total = 0;
    for (int owner = 0; owner < local.processes; ++owner) {
        auto& ids = requested_by_owner[owner];
        std::sort(ids.begin(), ids.end());
        ids.erase(std::unique(ids.begin(), ids.end()), ids.end());
        plan.request_displacements[owner] = request_total;
        plan.request_counts[owner] = static_cast<int>(ids.size());
        request_total += plan.request_counts[owner];
        plan.requested_global_ids.insert(plan.requested_global_ids.end(), ids.begin(), ids.end());
    }
    plan.local_halo_size = static_cast<Index>(request_total);

    plan.serve_counts.resize(local.processes);
    plan.serve_displacements.resize(local.processes);
    MPI_Alltoall(plan.request_counts.data(), 1, MPI_INT,
                 plan.serve_counts.data(), 1, MPI_INT, MPI_COMM_WORLD);
    int serve_total = 0;
    for (int requester = 0; requester < local.processes; ++requester) {
        plan.serve_displacements[requester] = serve_total;
        serve_total += plan.serve_counts[requester];
    }

    std::vector<Index> served_global_ids(serve_total);
    MPI_Alltoallv(plan.requested_global_ids.data(), plan.request_counts.data(),
                  plan.request_displacements.data(), MPI_UINT64_T,
                  served_global_ids.data(), plan.serve_counts.data(),
                  plan.serve_displacements.data(), MPI_UINT64_T, MPI_COMM_WORLD);
    plan.served_local_indices.reserve(serve_total);
    for (const Index id : served_global_ids) {
        plan.served_local_indices.push_back(static_cast<int>(id) - begin);
    }

    std::unordered_map<Index, Index> remote_slot;
    remote_slot.reserve(plan.requested_global_ids.size());
    for (int i = 0; i < request_total; ++i)
        remote_slot.emplace(plan.requested_global_ids[i], static_cast<Index>(count + i));

    plan.edge_source_slots.reserve(local.in_sources.size());
    for (const Index source : local.in_sources) {
        if (source >= static_cast<Index>(begin) && source < static_cast<Index>(begin + count)) {
            plan.edge_source_slots.push_back(source - static_cast<Index>(begin));
        } else {
            plan.edge_source_slots.push_back(remote_slot.at(source));
        }
    }

    const unsigned long long local_halo = static_cast<unsigned long long>(request_total);
    MPI_Allreduce(&local_halo, &plan.global_halo_size, 1, MPI_UNSIGNED_LONG_LONG,
                  MPI_SUM, MPI_COMM_WORLD);
    const double local_setup_seconds = MPI_Wtime() - setup_start;
    MPI_Allreduce(&local_setup_seconds, &plan.setup_seconds, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
    return plan;
}

