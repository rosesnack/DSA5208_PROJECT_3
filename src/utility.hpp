#pragma once

#include "graph_io.hpp"
#include <cstddef>
#include <fstream>
#include <string>
#include <vector>

// Shared settings keep serial and parallel experiments comparable.
inline constexpr double alpha = 0.85;
inline constexpr double tolerance = 1e-8;
inline constexpr std::size_t max_iterations = 1000;
inline constexpr std::size_t fixed_iterations = 0;  // Zero uses the convergence rule.
inline constexpr int warmup_runs = 1;
inline constexpr int repeat_runs = 3;
inline const std::string experiment_environment = "local workstation";

struct Result {
    std::vector<double> ranks;    // Scores follow the dense node order in Graph::original_ids.
    std::vector<double> deltas;    // One total absolute rank change (L1 difference) per iteration.
    bool converged = false;
    double residual_l1 = 0;    // Difference between the final scores and one more PageRank update.
    double rank_sum = 0;
    double solve_seconds = 0;
    int threads = 1;    // Actual team size; serial runs use one thread.
};

struct Dataset {
    std::string name, edges, nodes;
};

inline const std::vector<Dataset> datasets = {
    {"google", "data/raw/web-Google.txt", ""},
    {"uniform", "data/synthetic/uniform.edges",
                "data/synthetic/uniform.nodes"},
    {"hub", "data/synthetic/hub.edges",
            "data/synthetic/hub.nodes"}
};

struct TimingStats {
    double minimum, median, maximum;
};

TimingStats summarize_times(std::vector<double> times);
std::ofstream output_file(const std::string& path);
void write_ranks(const std::string& path, const Graph& graph, const Result& result);
void write_history(const std::string& path, const Result& result);
