#pragma once

#include "graph_io.hpp"

struct Partition {
    int rank, processes, total_nodes;
    std::vector<int> counts, displacements;
    std::vector<Index> in_offsets, in_sources, out_degree;
    int min_edges = 0, max_edges = 0;
};

Partition distribute_graph(const Graph& graph);
