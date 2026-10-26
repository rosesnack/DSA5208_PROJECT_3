#include "utility.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>

const std::string output_root = "results/serial";

Result pagerank_serial(const Graph& g) {
    using Clock = std::chrono::steady_clock;
    const auto n = g.size();
    const double inv_n = 1.0 / static_cast<double>(n);
    Result result;
    result.ranks.assign(n, inv_n);
    // Keep old and new scores separate so all nodes use the same old iteration.
    std::vector<double> next(n), contributions(n), inv_degree(n);
    for (std::size_t u = 0; u < n; ++u)
        inv_degree[u] = g.out_degree[u] ? 1.0 / static_cast<double>(g.out_degree[u]) : 0.0;
    const auto limit = fixed_iterations ? fixed_iterations : max_iterations;
    result.deltas.reserve(limit);

    const auto apply = [&](const std::vector<double>& old, std::vector<double>& updated) {
        double dangling = 0;
        for (std::size_t u = 0; u < n; ++u) {
            contributions[u] = old[u] * inv_degree[u];
            if (g.out_degree[u] == 0) dangling += old[u];
        }
        // Spread random jumps and dangling rank equally across all nodes.
        const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
        // Pull contributions from every incoming neighbor of node v.
        for (std::size_t v = 0; v < n; ++v) {
            double incoming = 0;
            for (Index e = g.in_offsets[v]; e < g.in_offsets[v + 1]; ++e)
                incoming += contributions[g.in_sources[e]];
            updated[v] = base + alpha * incoming;
        }
    };

    const auto solve_start = Clock::now();
    for (std::size_t k = 0; k < limit; ++k) {
        apply(result.ranks, next);
        // L1 difference is the sum of absolute score changes across all nodes.
        double delta = 0;
        for (std::size_t v = 0; v < n; ++v) delta += std::abs(next[v] - result.ranks[v]);
        result.deltas.push_back(delta);
        result.ranks.swap(next);
        result.converged = delta <= tolerance;
        // Fixed-iteration runs continue even if the scores have converged.
        if (result.converged && !fixed_iterations) break;
    }
    const auto solve_end = Clock::now();
    result.solve_seconds = std::chrono::duration<double>(solve_end - solve_start).count();
    // An additional application validates the returned vector outside solve time.
    apply(result.ranks, next);
    for (std::size_t v = 0; v < n; ++v)
        result.residual_l1 += std::abs(next[v] - result.ranks[v]);
    result.rank_sum = std::accumulate(result.ranks.begin(), result.ranks.end(), 0.0);
    return result;
}

int main() {
    bool success = true;
    for (const auto& dataset : datasets) {
        std::cout << "Running " << dataset.name << "..." << std::endl;
        // Load once; every solver call starts again from equal ranks.
        const auto graph = load_graph(dataset.edges, dataset.nodes);
        for (int run = 0; run < warmup_runs; ++run) pagerank_serial(graph);

        Result result;
        std::vector<double> times;
        bool converged = true;
        double max_residual = 0, max_sum_error = 0;
        std::ostringstream timings;
        timings << std::setprecision(17) << std::boolalpha
                << "run,iterations,converged,solve_s,residual_l1,rank_sum\n";
        for (int run = 1; run <= repeat_runs; ++run) {
            result = pagerank_serial(graph);
            times.push_back(result.solve_seconds);
            converged = converged && result.converged;
            max_residual = std::max(max_residual, result.residual_l1);
            max_sum_error = std::max(max_sum_error, std::abs(result.rank_sum - 1.0));
            timings << run << ',' << result.deltas.size() << ',' << result.converged << ','
                    << result.solve_seconds << ',' << result.residual_l1 << ',' << result.rank_sum << '\n';
        }
        const auto timing = summarize_times(times);

        // Write files after measurements; ranks and history come from the last run.
        const auto folder = output_root + '/' + dataset.name;
        output_file(folder + "/timings.csv") << timings.str();
        write_ranks(folder + "/ranks.csv", graph, result);
        write_history(folder + "/history.csv", result);
        auto summary = output_file(folder + "/summary.json");
        summary << std::boolalpha
                << "{\n  \"implementation\": \"serial\","
                << "\n  \"dataset\": " << std::quoted(dataset.name)
                << ",\n  \"environment\": " << std::quoted(experiment_environment)
                << ",\n  \"nodes\": " << graph.size()
                << ",\n  \"edges\": " << graph.in_sources.size()
                << ",\n  \"alpha\": " << alpha
                << ",\n  \"tolerance_l1\": " << tolerance
                << ",\n  \"max_iterations\": " << max_iterations
                << ",\n  \"fixed_iterations\": " << fixed_iterations
                << ",\n  \"warmup_runs\": " << warmup_runs
                << ",\n  \"repeat_runs\": " << repeat_runs
                << ",\n  \"iterations\": " << result.deltas.size()
                << ",\n  \"converged\": " << converged
                << ",\n  \"solve_median_s\": " << timing.median
                << ",\n  \"solve_min_s\": " << timing.minimum
                << ",\n  \"solve_max_s\": " << timing.maximum
                << ",\n  \"max_residual_l1\": " << max_residual
                << ",\n  \"max_rank_sum_error\": " << max_sum_error << "\n}\n";
        std::cout << dataset.name << ": iterations=" << result.deltas.size()
                << ", converged=" << std::boolalpha << converged
                << ", median=" << timing.median << "s, residual=" << max_residual << '\n';
        success = success && (converged || fixed_iterations);
    }
    return success ? 0 : 2;
}
