#include "utility.hpp"

#include <algorithm>
#include <filesystem>
#include <iomanip>
#include <stdexcept>

TimingStats summarize_times(std::vector<double> times) {
    std::sort(times.begin(), times.end());
    const auto middle = times.size() / 2;
    const double median = times.size() % 2 ? times[middle] : (times[middle - 1] + times[middle]) / 2;
    return {times.front(), median, times.back()};
}

std::ofstream output_file(const std::string& path) {
    const auto directory = std::filesystem::path(path).parent_path();
    if (!directory.empty()) std::filesystem::create_directories(directory);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot create output: " + path);
    out << std::setprecision(17);
    return out;
}

void write_ranks(const std::string& path, const Graph& graph, const Result& result) {
    auto out = output_file(path);
    out << "node_id,rank,in_degree,out_degree\n";
    for (std::size_t v = 0; v < graph.size(); ++v)
        out << graph.original_ids[v] << ',' << result.ranks[v] << ','
            << graph.in_offsets[v + 1] - graph.in_offsets[v] << ',' << graph.out_degree[v] << '\n';
}

void write_history(const std::string& path, const Result& result) {
    auto out = output_file(path);
    out << "iteration,delta_l1\n";
    for (std::size_t k = 0; k < result.deltas.size(); ++k)
        out << k + 1 << ',' << result.deltas[k] << '\n';
}

