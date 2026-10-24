#include "graph_io.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <fstream>
#include <stdexcept>
#include <string_view>
#include <unordered_map>
#include <utility>

namespace {
using Clock = std::chrono::steady_clock;
bool space(char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n'; }

// Remove the UTF-8 file marker, comments, and surrounding whitespace.
std::string_view content(std::string& line, std::size_t number) {
    std::string_view s(line);
    if (number == 1 && s.substr(0, 3) == "\xef\xbb\xbf") s.remove_prefix(3);
    s = s.substr(0, s.find('#'));
    while (!s.empty() && space(s.front())) s.remove_prefix(1);
    while (!s.empty() && space(s.back())) s.remove_suffix(1);
    return s;
}

// Read one node ID, then move the view to the next token.
Index read_id(std::string_view& s) {
    while (!s.empty() && space(s.front())) s.remove_prefix(1);
    const auto end = s.find_first_of(" \t\r\n");
    const auto token = s.substr(0, end);
    Index value = 0;
    std::from_chars(token.data(), token.data() + token.size(), value);
    s.remove_prefix(token.size());
    while (!s.empty() && space(s.front())) s.remove_prefix(1);
    return value;
}
} // namespace

Graph load_graph(const std::string& edge_path, const std::string& node_path) {
    const auto start = Clock::now();
    Graph g;
    std::vector<std::pair<Index, Index>> edges;  // (destination, source)
    std::ifstream input(edge_path);
    if (!input) throw std::runtime_error("Cannot open edge file: " + edge_path);
    std::string line;
    std::size_t number = 0;
    while (std::getline(input, line)) {
        auto s = content(line, ++number);
        if (s.empty()) continue;
        const auto source = read_id(s);
        const auto destination = read_id(s);
        edges.emplace_back(destination, source);
        if (node_path.empty()) {
            g.original_ids.push_back(source);
            g.original_ids.push_back(destination);
        }
    }
    g.raw_edges = static_cast<Index>(edges.size());

    if (!node_path.empty()) {
        std::ifstream nodes(node_path);
        if (!nodes) throw std::runtime_error("Cannot open node file: " + node_path);
        number = 0;
        while (std::getline(nodes, line)) {
            auto s = content(line, ++number);
            if (s.empty()) continue;
            g.original_ids.push_back(read_id(s));
        }
    }
    const auto read_end = Clock::now();
    g.read_seconds = std::chrono::duration<double>(read_end - start).count();

    // Sort and deduplicate the original IDs and edges.
    std::sort(g.original_ids.begin(), g.original_ids.end());
    g.original_ids.erase(std::unique(g.original_ids.begin(), g.original_ids.end()), g.original_ids.end());
    std::sort(edges.begin(), edges.end());
    edges.erase(std::unique(edges.begin(), edges.end()), edges.end());

    // Map original IDs, which may have gaps, to array positions 0 ... N - 1.
    std::unordered_map<Index, Index> dense;
    dense.reserve(g.size());
    for (std::size_t i = 0; i < g.size(); ++i) dense.emplace(g.original_ids[i], static_cast<Index>(i));

    // Build the CSR representation of incoming edges and the out-degree array.
    g.in_offsets.assign(g.size() + 1, 0);
    g.out_degree.assign(g.size(), 0);
    g.in_sources.reserve(edges.size());
    for (const auto& edge : edges) {
        const auto dst = dense.at(edge.first);
        const auto src = dense.at(edge.second);
        ++g.in_offsets[static_cast<std::size_t>(dst) + 1];
        ++g.out_degree[static_cast<std::size_t>(src)];
        g.in_sources.push_back(src);
        if (src == dst) ++g.self_loops;
    }
    // Convert incoming edge counts into start offsets using a prefix sum.
    for (std::size_t i = 1; i < g.in_offsets.size(); ++i) g.in_offsets[i] += g.in_offsets[i - 1];
    g.preprocess_seconds = std::chrono::duration<double>(Clock::now() - read_end).count();
    return g;
}
