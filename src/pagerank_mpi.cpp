#include "utility.hpp"
#include <mpi.h>

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <utility>

const std::string output_root = "results/mpi";

struct Partition {
    int rank, processes, total_nodes;
    std::vector<int> counts, displacements;
    std::vector<Index> in_offsets, in_sources, out_degree;
    int min_edges = 0, max_edges = 0;
};

Partition distribute_graph(const Graph& graph) {
    Partition local;
    MPI_Comm_rank(MPI_COMM_WORLD, &local.rank);
    MPI_Comm_size(MPI_COMM_WORLD, &local.processes);
    local.total_nodes = local.rank == 0 ? static_cast<int>(graph.size()) : 0;
    MPI_Bcast(&local.total_nodes, 1, MPI_INT, 0, MPI_COMM_WORLD);

    // Split consecutive dense IDs evenly; the first processes get any remainder.
    local.counts.resize(local.processes);
    local.displacements.resize(local.processes);
    int begin = 0;
    for (int p = 0; p < local.processes; ++p) {
        local.counts[p] = local.total_nodes / local.processes + (p < local.total_nodes % local.processes);
        local.displacements[p] = begin;
        begin += local.counts[p];
    }

    std::vector<int> edge_counts(local.processes), edge_displacements(local.processes);
    if (local.rank == 0) {
        for (int p = 0; p < local.processes; ++p) {
            const auto first = graph.in_offsets[local.displacements[p]];
            const auto last = graph.in_offsets[local.displacements[p] + local.counts[p]];
            edge_counts[p] = static_cast<int>(last - first);
            edge_displacements[p] = static_cast<int>(first);
        }
        local.min_edges = *std::min_element(edge_counts.begin(), edge_counts.end());
        local.max_edges = *std::max_element(edge_counts.begin(), edge_counts.end());
    }

    const int count = local.counts[local.rank];
    int edge_count = 0;
    MPI_Scatter(edge_counts.data(), 1, MPI_INT, &edge_count, 1, MPI_INT, 0, MPI_COMM_WORLD);
    local.in_offsets.resize(count + 1);
    local.in_sources.resize(edge_count);
    local.out_degree.resize(count);
    
    // Send row starts without overlapping boundary entries; append the final offset locally.
    MPI_Scatterv(graph.in_offsets.data(), local.counts.data(), local.displacements.data(), MPI_UINT64_T,
                local.in_offsets.data(), count, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    MPI_Scatterv(graph.in_sources.data(), edge_counts.data(), edge_displacements.data(), MPI_UINT64_T,
                local.in_sources.data(), edge_count, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    MPI_Scatterv(graph.out_degree.data(), local.counts.data(), local.displacements.data(), MPI_UINT64_T,
                local.out_degree.data(), count, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    const Index first = local.in_offsets.front();
    for (int v = 0; v < count; ++v) local.in_offsets[v] -= first;
    local.in_offsets[count] = edge_count;
    return local;
}

Result pagerank_mpi(const Partition& local) {
    const int count = local.counts[local.rank];
    const double inv_n = 1.0 / local.total_nodes;
    Result result;
    result.ranks.assign(count, inv_n);
    std::vector<double> next(count), contributions(count), inv_degree(count);
    std::vector<double> all_contributions(local.total_nodes);
    for (int u = 0; u < count; ++u)
        inv_degree[u] = local.out_degree[u] ? 1.0 / local.out_degree[u] : 0.0;
    const auto limit = fixed_iterations ? fixed_iterations : max_iterations;
    result.deltas.reserve(limit);

    const auto apply = [&]() {
        double local_dangling = 0, dangling = 0;
        for (int u = 0; u < count; ++u) {
            contributions[u] = result.ranks[u] * inv_degree[u];
            if (local.out_degree[u] == 0) local_dangling += result.ranks[u];
        }
        // Every process needs source contributions for its own incoming edges.
        MPI_Allgatherv(contributions.data(), count, MPI_DOUBLE,
                    all_contributions.data(), local.counts.data(), local.displacements.data(),
                    MPI_DOUBLE, MPI_COMM_WORLD);
        MPI_Allreduce(&local_dangling, &dangling, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
        for (int v = 0; v < count; ++v) {
            double incoming = 0;
            for (Index e = local.in_offsets[v]; e < local.in_offsets[v + 1]; ++e)
                incoming += all_contributions[local.in_sources[e]];
            next[v] = base + alpha * incoming;
        }
    };

    MPI_Barrier(MPI_COMM_WORLD);
    const double start = MPI_Wtime();
    for (std::size_t k = 0; k < limit; ++k) {
        apply();
        double local_delta = 0, delta = 0;
        for (int v = 0; v < count; ++v) local_delta += std::abs(next[v] - result.ranks[v]);
        MPI_Allreduce(&local_delta, &delta, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        result.deltas.push_back(delta);
        result.ranks.swap(next);
        result.converged = delta <= tolerance;
        // All processes use the same global delta and stop at the same iteration.
        if (result.converged && !fixed_iterations) break;
    }
    const double elapsed = MPI_Wtime() - start;
    MPI_Allreduce(&elapsed, &result.solve_seconds, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);

    // Validate globally and gather the final ranks outside the measured iteration loop.
    apply();
    double local_checks[2] = {0, 0}, checks[2];
    for (int v = 0; v < count; ++v) {
        local_checks[0] += std::abs(next[v] - result.ranks[v]);
        local_checks[1] += result.ranks[v];
    }
    MPI_Allreduce(local_checks, checks, 2, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    result.residual_l1 = checks[0];
    result.rank_sum = checks[1];
    std::vector<double> global_ranks;
    if (local.rank == 0) global_ranks.resize(local.total_nodes);
    MPI_Gatherv(result.ranks.data(), count, MPI_DOUBLE, global_ranks.data(),
                local.counts.data(), local.displacements.data(), MPI_DOUBLE, 0, MPI_COMM_WORLD);
    result.ranks = std::move(global_ranks);  // Only rank 0 returns the complete ranking.
    return result;
}

int main() {
    MPI_Init(nullptr, nullptr);
    int rank, processes;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
    bool success = true;
    try {
        for (const auto& dataset : datasets) {
            Graph graph;
            if (rank == 0) {
                std::cout << "Running " << dataset.name << " p" << processes << "..." << std::endl;
                graph = load_graph(dataset.edges, dataset.nodes);
            }
            const auto local = distribute_graph(graph);
            for (int run = 0; run < warmup_runs; ++run) pagerank_mpi(local);

            Result result;
            std::vector<double> times;
            bool converged = true;
            double max_residual = 0, max_sum_error = 0;
            std::ostringstream timings;
            timings << std::setprecision(17) << std::boolalpha
                    << "run,processes,iterations,converged,solve_s,residual_l1,rank_sum\n";
            for (int run = 1; run <= repeat_runs; ++run) {
                result = pagerank_mpi(local);
                times.push_back(result.solve_seconds);
                converged = converged && result.converged;
                max_residual = std::max(max_residual, result.residual_l1);
                max_sum_error = std::max(max_sum_error, std::abs(result.rank_sum - 1.0));
                if (rank == 0)
                    timings << run << ',' << processes << ',' << result.deltas.size() << ',' << result.converged << ','
                            << result.solve_seconds << ',' << result.residual_l1 << ',' << result.rank_sum << '\n';
            }
            success = success && (converged || fixed_iterations);
            if (rank != 0) continue;

            const auto timing = summarize_times(times);
            const auto folder = output_root + '/' + dataset.name + "/p" + std::to_string(processes);
            output_file(folder + "/timings.csv") << timings.str();
            write_ranks(folder + "/ranks.csv", graph, result);
            write_history(folder + "/history.csv", result);
            auto summary = output_file(folder + "/summary.json");
            summary << std::boolalpha
                    << "{\n  \"implementation\": \"mpi\","
                    << "\n  \"dataset\": " << std::quoted(dataset.name)
                    << ",\n  \"environment\": " << std::quoted(experiment_environment)
                    << ",\n  \"processes\": " << processes
                    << ",\n  \"partition\": \"contiguous_nodes\""
                    << ",\n  \"communication\": \"allgatherv\""
                    << ",\n  \"min_local_edges\": " << local.min_edges
                    << ",\n  \"max_local_edges\": " << local.max_edges
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
            std::cout << dataset.name << " p" << processes << ": iterations=" << result.deltas.size()
                    << ", converged=" << std::boolalpha << converged
                    << ", median=" << timing.median << "s, residual=" << max_residual << std::endl;
        }
    } catch (const std::exception& error) {
        // Stop the whole job if one process fails, instead of leaving others in a collective.
        std::cerr << "Rank " << rank << ": " << error.what() << std::endl;
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    }
    MPI_Finalize();
    return success ? 0 : 2;
}
