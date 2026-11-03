#pragma once

#include "graph_io.hpp"
#include <cstdlib>
#include <cstddef>
#include <fstream>
#include <stdexcept>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#ifndef PAGERANK_BUILD_TYPE
#define PAGERANK_BUILD_TYPE "unknown"
#endif

// Shared settings keep serial and parallel experiments comparable.
inline constexpr double alpha = 0.85;
inline constexpr double tolerance = 1e-8;
inline constexpr std::size_t max_iterations = 1000;
inline constexpr std::size_t fixed_iterations = 0;  // Zero uses the convergence rule.
inline int environment_integer(const char* name, int fallback) {
    const char* value = std::getenv(name);
    return value ? std::stoi(value) : fallback;
}
inline std::string environment_string(const char* name, const char* fallback) {
    const char* value = std::getenv(name);
    return value && *value ? value : fallback;
}
inline const std::string& results_root() {
    static const std::string value = environment_string("PAGERANK_RESULTS_ROOT", "results");
    return value;
}
inline int warmup_runs() {
    static const int value = environment_integer("PAGERANK_WARMUPS", 1);
    return value;
}
inline int repeat_runs() {
    static const int value = environment_integer("PAGERANK_REPEATS", 5);
    return value;
}
inline const std::string& experiment_environment() {
    static const std::string value = environment_string("PAGERANK_ENVIRONMENT", "local workstation");
    return value;
}
inline constexpr char build_type[] = PAGERANK_BUILD_TYPE;

struct Result {
    std::vector<double> ranks;    // Dense node order; MPI returns full ranks only on rank 0.
    std::vector<double> deltas;    // One total absolute rank change (L1 difference) per iteration.
    bool converged = false;
    double residual_l1 = 0;    // Difference between the final scores and one more PageRank update.
    double rank_sum = 0;
    double solve_seconds = 0;
    // MPI payload sent across process boundaries per iteration (aggregate bytes).
    double communication_bytes_per_iteration = 0;
    double communication_setup_bytes = 0;
    double communication_seconds = 0;
    double transfer_seconds = 0;
    double device_seconds = 0;
    int threads = 1;    // Actual team size; serial runs use one thread.
};

struct Dataset {
    std::string name, edges, nodes;
};

inline const std::vector<Dataset>& datasets() {
    static const std::vector<Dataset> value = [] {
        const char* manifest_path = std::getenv("PAGERANK_DATASET_MANIFEST");
        if (!manifest_path || !*manifest_path) {
            return std::vector<Dataset>{
                {"google", "data/raw/web-Google.txt", ""},
                {"uniform", "data/synthetic/uniform.edges", "data/synthetic/uniform.nodes"},
                {"hub", "data/synthetic/hub.edges", "data/synthetic/hub.nodes"}
            };
        }

        std::ifstream manifest(manifest_path);
        if (!manifest) throw std::runtime_error("Cannot open dataset manifest: " + std::string(manifest_path));
        std::vector<Dataset> configured;
        std::string line;
        while (std::getline(manifest, line)) {
            if (line.empty() || line.front() == '#') continue;
            std::istringstream row(line);
            Dataset dataset;
            row >> dataset.name >> dataset.edges >> dataset.nodes;
            if (dataset.nodes == "-") dataset.nodes.clear();
            configured.push_back(std::move(dataset));
        }
        return configured;
    }();
    return value;
}

struct TimingStats {
    double minimum, median, maximum;
};

TimingStats summarize_times(std::vector<double> times);
std::ofstream output_file(const std::string& path);
void write_ranks(const std::string& path, const Graph& graph, const Result& result);
void write_history(const std::string& path, const Result& result);
