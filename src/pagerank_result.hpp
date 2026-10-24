#pragma once

#include <vector>

// Shared result type for serial and parallel PageRank implementations.
struct Result {
    std::vector<double> ranks;    // Scores follow the dense node order in Graph::original_ids.
    std::vector<double> deltas;    // One total absolute rank change (L1 difference) per iteration.
    bool converged = false;
    double residual_l1 = 0;    // Difference between the final scores and one more PageRank update.
    double rank_sum = 0;
    double solve_seconds = 0;
};
