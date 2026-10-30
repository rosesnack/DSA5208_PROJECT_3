#include "utility.hpp"

#include <Kokkos_Core.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using ExecSpace = Kokkos::DefaultExecutionSpace;
using Policy = Kokkos::RangePolicy<ExecSpace>;
std::string output_root() { return results_root() + "/kokkos/" + ExecSpace::name(); }

Result pagerank_kokkos(const Graph& graph) {
    using Clock = std::chrono::steady_clock;
    const std::size_t n = graph.size();
    const double inv_n = 1.0 / static_cast<double>(n);
    Result result;
    result.ranks.resize(n);
    const auto limit = fixed_iterations ? fixed_iterations : max_iterations;
    result.deltas.reserve(limit);

    using IndexView = Kokkos::View<Index*, ExecSpace>;
    using RankView = Kokkos::View<double*, ExecSpace>;
    IndexView offsets("incoming_offsets", n + 1);
    IndexView sources("incoming_sources", graph.in_sources.size());
    IndexView degrees("out_degrees", n);
    RankView old_ranks("old_ranks", n), new_ranks("new_ranks", n), contributions("contributions", n);

    const auto setup_start = Clock::now();
    auto h_offsets = Kokkos::create_mirror_view(offsets);
    auto h_sources = Kokkos::create_mirror_view(sources);
    auto h_degrees = Kokkos::create_mirror_view(degrees);
    std::copy(graph.in_offsets.begin(), graph.in_offsets.end(), h_offsets.data());
    std::copy(graph.in_sources.begin(), graph.in_sources.end(), h_sources.data());
    std::copy(graph.out_degree.begin(), graph.out_degree.end(), h_degrees.data());
    Kokkos::deep_copy(offsets, h_offsets);
    Kokkos::deep_copy(sources, h_sources);
    Kokkos::deep_copy(degrees, h_degrees);
    Kokkos::deep_copy(old_ranks, inv_n);
    Kokkos::fence("PageRank input setup");
    result.transfer_seconds = std::chrono::duration<double>(Clock::now() - setup_start).count();

    const auto solve_start = Clock::now();
    for (std::size_t iteration = 0; iteration < limit; ++iteration) {
        double dangling = 0.0;
        Kokkos::parallel_reduce("PageRank contributions", Policy(0, n),
            KOKKOS_LAMBDA(const std::size_t u, double& update) {
                const Index degree = degrees(u);
                contributions(u) = degree ? old_ranks(u) / static_cast<double>(degree) : 0.0;
                if (degree == 0) update += old_ranks(u);
            }, dangling);
        const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;

        double delta = 0.0;
        Kokkos::parallel_reduce("PageRank pull update", Policy(0, n),
            KOKKOS_LAMBDA(const std::size_t v, double& update) {
                double incoming = 0.0;
                for (Index e = offsets(v); e < offsets(v + 1); ++e)
                    incoming += contributions(sources(e));
                const double value = base + alpha * incoming;
                new_ranks(v) = value;
                update += Kokkos::abs(value - old_ranks(v));
            }, delta);
        result.deltas.push_back(delta);
        RankView temporary = old_ranks;
        old_ranks = new_ranks;
        new_ranks = temporary;
        result.converged = delta <= tolerance;
        if (result.converged && !fixed_iterations) break;
    }
    Kokkos::fence("PageRank solve complete");
    result.solve_seconds = std::chrono::duration<double>(Clock::now() - solve_start).count();

    const auto copy_start = Clock::now();
    auto h_ranks = Kokkos::create_mirror_view_and_copy(Kokkos::HostSpace(), old_ranks);
    std::copy(h_ranks.data(), h_ranks.data() + n, result.ranks.begin());
    result.transfer_seconds += std::chrono::duration<double>(Clock::now() - copy_start).count();

    // Recompute the final residual on the host independently of the backend reductions.
    std::vector<double> host_contributions(n), next(n);
    double dangling = 0.0;
    for (std::size_t u = 0; u < n; ++u) {
        if (graph.out_degree[u] == 0) dangling += result.ranks[u];
        else host_contributions[u] = result.ranks[u] / static_cast<double>(graph.out_degree[u]);
    }
    const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
    for (std::size_t v = 0; v < n; ++v) {
        double incoming = 0.0;
        for (Index e = graph.in_offsets[v]; e < graph.in_offsets[v + 1]; ++e)
            incoming += host_contributions[graph.in_sources[e]];
        next[v] = base + alpha * incoming;
        result.residual_l1 += std::abs(next[v] - result.ranks[v]);
    }
    result.rank_sum = std::accumulate(result.ranks.begin(), result.ranks.end(), 0.0);
    return result;
}
} // namespace

int main(int argc, char** argv) {
    Kokkos::initialize(argc, argv);
    int exit_code = 0;
    try {
        bool success = true;
        for (const auto& dataset : datasets()) {
            std::cout << "Running " << dataset.name << " on Kokkos " << ExecSpace::name() << "..." << std::endl;
            const auto graph = load_graph(dataset.edges, dataset.nodes);
            for (int run = 0; run < warmup_runs(); ++run) (void)pagerank_kokkos(graph);
            Result result;
            std::vector<double> times;
            std::vector<double> transfer_times;
            bool converged = true;
            double max_residual = 0.0, max_sum_error = 0.0;
            std::ostringstream timings;
            timings << std::setprecision(17) << std::boolalpha
                    << "run,iterations,converged,solve_s,setup_transfer_s,residual_l1,rank_sum\n";
            for (int run = 1; run <= repeat_runs(); ++run) {
                result = pagerank_kokkos(graph);
                times.push_back(result.solve_seconds);
                transfer_times.push_back(result.transfer_seconds);
                converged = converged && result.converged;
                max_residual = std::max(max_residual, result.residual_l1);
                max_sum_error = std::max(max_sum_error, std::abs(result.rank_sum - 1.0));
                timings << run << ',' << result.deltas.size() << ',' << result.converged << ','
                        << result.solve_seconds << ',' << result.transfer_seconds << ','
                        << result.residual_l1 << ',' << result.rank_sum << '\n';
            }
            const auto timing = summarize_times(times);
            const auto transfer_timing = summarize_times(transfer_times);
            const auto folder = output_root() + '/' + dataset.name;
            output_file(folder + "/timings.csv") << timings.str();
            write_ranks(folder + "/ranks.csv", graph, result);
            write_history(folder + "/history.csv", result);
            auto summary = output_file(folder + "/summary.json");
            summary << std::boolalpha
                    << "{\n  \"implementation\": \"kokkos\","
                    << "\n  \"backend\": " << std::quoted(ExecSpace::name())
                    << ",\n  \"environment\": " << std::quoted(experiment_environment())
                    << ",\n  \"build_type\": " << std::quoted(build_type)
                    << ",\n  \"dataset\": " << std::quoted(dataset.name)
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
                    << ",\n  \"setup_transfer_median_s\": " << transfer_timing.median
                    << ",\n  \"max_residual_l1\": " << max_residual
                    << ",\n  \"max_rank_sum_error\": " << max_sum_error << "\n}\n";
            std::cout << dataset.name << ": iterations=" << result.deltas.size()
                      << ", median=" << timing.median << "s, residual=" << max_residual << std::endl;
            success = success && converged;
        }
        exit_code = success ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << "Kokkos PageRank failed: " << error.what() << std::endl;
        exit_code = 1;
    }
    Kokkos::finalize();
    return exit_code;
}
