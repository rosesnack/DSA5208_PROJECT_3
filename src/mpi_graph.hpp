#pragma once

#include "graph_io.hpp"
#include <vector>

struct Partition {
    int rank, processes, total_nodes;
    std::vector<int> counts, displacements;
    std::vector<Index> in_offsets, in_sources, out_degree;
    int min_edges = 0, max_edges = 0;
};

Partition distribute_graph(const Graph& graph);

// A static pull halo: each rank requests the distinct remote source vertices
// referenced by its local incoming-edge rows once, then exchanges only their
// PageRank contributions on each iteration.
struct HaloPlan {
    std::vector<int> request_counts, request_displacements;
    std::vector<int> serve_counts, serve_displacements;
    std::vector<Index> requested_global_ids;
    std::vector<int> served_local_indices;
    // For every local CSR edge, index into [local contributions | halo values].
    std::vector<Index> edge_source_slots;
    Index local_halo_size = 0;
    unsigned long long global_halo_size = 0;
    double setup_seconds = 0;
};

HaloPlan build_halo_plan(const Partition& local);
