#pragma once

#include <cstdint>
#include <string>
#include <vector>

using Index = std::uint64_t;

// Store the graph in CSR (compressed sparse row) format.
struct Graph {
    std::vector<Index> original_ids;
    std::vector<Index> in_offsets;
    std::vector<Index> in_sources;
    std::vector<Index> out_degree;
    Index raw_edges = 0;
    Index self_loops = 0;
    double read_seconds = 0;
    double preprocess_seconds = 0;
    std::size_t size() const { return original_ids.size(); }
};

// Each non-comment line is exactly two IDs. An optional node file is an
// authoritative list (one ID per line), including isolated vertices.
Graph load_graph(const std::string& edge_path, const std::string& node_path = "");
