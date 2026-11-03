#include "utility.hpp"
#include <omp.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

const int chunk_size = 64;
std::string output_root() { return results_root() + "/openmp"; }

std::vector<int> configured_thread_counts() {
    std::istringstream input(environment_string("PAGERANK_OPENMP_THREADS", "1 2 4 8 16 32"));
    std::vector<int> counts;
    for (int threads = 0; input >> threads;) counts.push_back(threads);
    return counts;
}

Result pagerank_openmp(const Graph& g, int thread_count) {
    using Clock = std::chrono::steady_clock;
    const auto n = g.size();
    const double inv_n = 1.0 / static_cast<double>(n);
    Result result;
    result.ranks.assign(n, inv_n);
    std::vector<double> next(n), contributions(n), inv_degree(n);
    for (std::size_t u = 0; u < n; ++u)
        inv_degree[u] = g.out_degree[u] ? 1.0 / static_cast<double>(g.out_degree[u]) : 0.0;
    const auto limit = fixed_iterations ? fixed_iterations : max_iterations;
    result.deltas.reserve(limit);
    double dangling = 0, delta = 0;
    bool stop = false;

    // Keep one thread team for all iterations; include its startup and shutdown in timing.
    const auto solve_start = Clock::now();
    #pragma omp parallel num_threads(thread_count)
    {
        #pragma omp single
        { result.threads = omp_get_num_threads(); }
        for (std::size_t k = 0; k < limit; ++k) {
            #pragma omp single
            { dangling = 0; delta = 0; }

            #pragma omp for schedule(static) reduction(+:dangling)
            for (std::size_t u = 0; u < n; ++u) {
                contributions[u] = result.ranks[u] * inv_degree[u];
                if (g.out_degree[u] == 0) dangling += result.ranks[u];
            }
            // The loop barrier completes contributions and the dangling-rank reduction.
            const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
            #pragma omp for schedule(dynamic, chunk_size) reduction(+:delta)
            for (std::size_t v = 0; v < n; ++v) {
                double incoming = 0;
                for (Index e = g.in_offsets[v]; e < g.in_offsets[v + 1]; ++e)
                    incoming += contributions[g.in_sources[e]];
                // Each node has one writer, so no atomics are needed for its rank.
                next[v] = base + alpha * incoming;
                delta += std::abs(next[v] - result.ranks[v]);
            }
            #pragma omp single
            {
                result.deltas.push_back(delta);
                result.ranks.swap(next);
                result.converged = delta <= tolerance;
                stop = result.converged && !fixed_iterations;
            }
            // The single-region barrier makes the new ranks and stop flag visible to all threads.
            if (stop) break;
        }
    }
    result.solve_seconds = std::chrono::duration<double>(Clock::now() - solve_start).count();

    // Check the final ranks outside solve time, using the same equation as the serial version.
    dangling = 0;
    for (std::size_t u = 0; u < n; ++u) {
        contributions[u] = result.ranks[u] * inv_degree[u];
        if (g.out_degree[u] == 0) dangling += result.ranks[u];
    }
    const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
    for (std::size_t v = 0; v < n; ++v) {
        double incoming = 0;
        for (Index e = g.in_offsets[v]; e < g.in_offsets[v + 1]; ++e)
            incoming += contributions[g.in_sources[e]];
        result.residual_l1 += std::abs(base + alpha * incoming - result.ranks[v]);
    }
    result.rank_sum = std::accumulate(result.ranks.begin(), result.ranks.end(), 0.0);
    return result;
}

int main() {
    omp_set_dynamic(0);
    bool success = true;
    for (const auto& dataset : datasets()) {
        std::cout << "Running " << dataset.name << "..." << std::endl;
        // Load once; every solver call starts again from equal ranks.
        const auto graph = load_graph(dataset.edges, dataset.nodes);
        for (int thread_count : configured_thread_counts()) {
            for (int run = 0; run < warmup_runs(); ++run) pagerank_openmp(graph, thread_count);

            Result result;
            std::vector<double> times;
            bool converged = true;
            double max_residual = 0, max_sum_error = 0;
            std::ostringstream timings;
            timings << std::setprecision(17) << std::boolalpha
                    << "run,threads,iterations,converged,solve_s,residual_l1,rank_sum\n";
            
            for (int run = 1; run <= repeat_runs(); ++run) {
                result = pagerank_openmp(graph, thread_count);
                times.push_back(result.solve_seconds);
                converged = converged && result.converged;
                max_residual = std::max(max_residual, result.residual_l1);
                max_sum_error = std::max(max_sum_error, std::abs(result.rank_sum - 1.0));
                timings << run << ',' << result.threads << ',' << result.deltas.size() << ',' << result.converged << ','
                        << result.solve_seconds << ',' << result.residual_l1 << ',' << result.rank_sum << '\n';
            }
            const auto timing = summarize_times(times);

            // Write files after measurements; ranks and history come from the last run.
            const auto folder = output_root() + '/' + dataset.name + "/t" + std::to_string(thread_count);
            output_file(folder + "/timings.csv") << timings.str();
            write_ranks(folder + "/ranks.csv", graph, result);
            write_history(folder + "/history.csv", result);
            auto summary = output_file(folder + "/summary.json");
            summary << std::boolalpha
                    << "{\n  \"implementation\": \"openmp\","
                    << "\n  \"dataset\": " << std::quoted(dataset.name)
                    << ",\n  \"environment\": " << std::quoted(experiment_environment())
                    << ",\n  \"build_type\": " << std::quoted(build_type)
                    << ",\n  \"requested_threads\": " << thread_count
                    << ",\n  \"threads\": " << result.threads
                    << ",\n  \"schedule\": \"dynamic\""
                    << ",\n  \"chunk_size\": " << chunk_size
                    << ",\n  \"nodes\": " << graph.size()
                    << ",\n  \"edges\": " << graph.in_sources.size()
                    << ",\n  \"alpha\": " << alpha
                    << ",\n  \"tolerance_l1\": " << tolerance
                    << ",\n  \"max_iterations\": " << max_iterations
                    << ",\n  \"fixed_iterations\": " << fixed_iterations
                    << ",\n  \"warmup_runs\": " << warmup_runs()
                    << ",\n  \"repeat_runs\": " << repeat_runs()
                    << ",\n  \"iterations\": " << result.deltas.size()
                    << ",\n  \"converged\": " << converged
                    << ",\n  \"solve_median_s\": " << timing.median
                    << ",\n  \"solve_min_s\": " << timing.minimum
                    << ",\n  \"solve_max_s\": " << timing.maximum
                    << ",\n  \"max_residual_l1\": " << max_residual
                    << ",\n  \"max_rank_sum_error\": " << max_sum_error << "\n}\n";
            std::cout << dataset.name << " t" << thread_count << " (actual=" << result.threads << "): iterations=" << result.deltas.size()
                    << ", converged=" << std::boolalpha << converged
                    << ", median=" << timing.median << "s, residual=" << max_residual << '\n';
            success = success && (converged || fixed_iterations);
        }
    }
    return success ? 0 : 2;
}
