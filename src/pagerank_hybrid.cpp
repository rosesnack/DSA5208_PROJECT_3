#include "utility.hpp"
#include "mpi_graph.hpp"
#include <mpi.h>
#include <omp.h>

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <utility>

const int chunk_size = 64;
std::string communication_mode = "allgather";
std::string output_root() { return results_root() + (communication_mode == "halo" ? "/hybrid_halo" : "/hybrid"); }

std::vector<int> configured_thread_counts() {
    const char* value = std::getenv("PAGERANK_HYBRID_THREADS");
    std::istringstream input(value ? value : "1 2 4 8");
    std::vector<int> counts;
    for (int count; input >> count;) counts.push_back(count);
    return counts;
}

Result pagerank_hybrid(const Partition& local, int thread_count, const HaloPlan* halo) {
    const int count = local.counts[local.rank];
    const double inv_n = 1.0 / local.total_nodes;
    Result result;
    result.ranks.assign(count, inv_n);
    std::vector<double> next(count), contributions(count), inv_degree(count);
    std::vector<double> all_contributions(halo ? 0 : local.total_nodes);
    std::vector<double> source_values, halo_receive, halo_send;
    if (halo) {
        source_values.resize(count + halo->local_halo_size);
        halo_receive.resize(halo->requested_global_ids.size());
        int served_count = 0;
        for (const int n : halo->serve_counts) served_count += n;
        halo_send.resize(served_count);
        result.communication_bytes_per_iteration =
            static_cast<double>(halo->global_halo_size) * sizeof(double);
        result.communication_setup_bytes =
            static_cast<double>(halo->global_halo_size) * sizeof(Index);
    } else {
        result.communication_bytes_per_iteration =
            static_cast<double>(local.total_nodes) * (local.processes - 1) * sizeof(double);
    }
    for (int u = 0; u < count; ++u)
        inv_degree[u] = local.out_degree[u] ? 1.0 / local.out_degree[u] : 0.0;
    const auto limit = fixed_iterations ? fixed_iterations : max_iterations;
    result.deltas.reserve(limit);
    double local_dangling = 0, dangling = 0, local_delta = 0, base = 0;
    bool stop = false;
    double local_communication_seconds = 0;

    MPI_Barrier(MPI_COMM_WORLD);
    const double start = MPI_Wtime();
    // Reuse a team; only the thread that initialized MPI may call MPI functions.
    #pragma omp parallel num_threads(thread_count)
    {
        const bool main_thread = omp_get_thread_num() == 0;
        if (main_thread)
        { result.threads = omp_get_num_threads(); }
        for (std::size_t k = 0; k < limit; ++k) {
            if (main_thread)
            { local_dangling = 0; local_delta = 0; }
            #pragma omp barrier

            #pragma omp for schedule(static) reduction(+:local_dangling)
            for (int u = 0; u < count; ++u) {
                contributions[u] = result.ranks[u] * inv_degree[u];
                if (local.out_degree[u] == 0) local_dangling += result.ranks[u];
            }
            if (main_thread)
            {
                const double communication_start = MPI_Wtime();
                if (halo) {
                    std::copy(contributions.begin(), contributions.end(), source_values.begin());
                    for (std::size_t i = 0; i < halo->served_local_indices.size(); ++i)
                        halo_send[i] = contributions[halo->served_local_indices[i]];
                    MPI_Alltoallv(halo_send.data(), halo->serve_counts.data(), halo->serve_displacements.data(), MPI_DOUBLE,
                                  halo_receive.data(), halo->request_counts.data(), halo->request_displacements.data(), MPI_DOUBLE,
                                  MPI_COMM_WORLD);
                    std::copy(halo_receive.begin(), halo_receive.end(), source_values.begin() + count);
                } else {
                    MPI_Allgatherv(contributions.data(), count, MPI_DOUBLE,
                                   all_contributions.data(), local.counts.data(), local.displacements.data(),
                                   MPI_DOUBLE, MPI_COMM_WORLD);
                }
                MPI_Allreduce(&local_dangling, &dangling, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
                local_communication_seconds += MPI_Wtime() - communication_start;
                base = ((1.0 - alpha) + alpha * dangling) * inv_n;
            }
            // Wait for the main thread to finish MPI before reading received contributions.
            #pragma omp barrier
            #pragma omp for schedule(dynamic, chunk_size) reduction(+:local_delta)
            for (int v = 0; v < count; ++v) {
                double incoming = 0;
                for (Index e = local.in_offsets[v]; e < local.in_offsets[v + 1]; ++e)
                    incoming += halo ? source_values[halo->edge_source_slots[e]]
                                     : all_contributions[local.in_sources[e]];
                next[v] = base + alpha * incoming;
                local_delta += std::abs(next[v] - result.ranks[v]);
            }
            if (main_thread)
            {
                double delta = 0;
                const double communication_start = MPI_Wtime();
                MPI_Allreduce(&local_delta, &delta, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
                local_communication_seconds += MPI_Wtime() - communication_start;
                result.deltas.push_back(delta);
                result.ranks.swap(next);
                result.converged = delta <= tolerance;
                stop = result.converged && !fixed_iterations;
            }
            // Every thread and process must use the same completed iteration and stop decision.
            #pragma omp barrier
            if (stop) break;
        }
    }
    const double elapsed = MPI_Wtime() - start;
    MPI_Allreduce(&elapsed, &result.solve_seconds, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
    MPI_Allreduce(&local_communication_seconds, &result.communication_seconds, 1,
                  MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);

    // Recompute the residual and gather final ranks outside solve time, on the main thread.
    local_dangling = 0;
    for (int u = 0; u < count; ++u) {
        contributions[u] = result.ranks[u] * inv_degree[u];
        if (local.out_degree[u] == 0) local_dangling += result.ranks[u];
    }
    if (halo) {
        std::copy(contributions.begin(), contributions.end(), source_values.begin());
        for (std::size_t i = 0; i < halo->served_local_indices.size(); ++i)
            halo_send[i] = contributions[halo->served_local_indices[i]];
        MPI_Alltoallv(halo_send.data(), halo->serve_counts.data(), halo->serve_displacements.data(), MPI_DOUBLE,
                      halo_receive.data(), halo->request_counts.data(), halo->request_displacements.data(), MPI_DOUBLE,
                      MPI_COMM_WORLD);
        std::copy(halo_receive.begin(), halo_receive.end(), source_values.begin() + count);
    } else {
        MPI_Allgatherv(contributions.data(), count, MPI_DOUBLE,
                       all_contributions.data(), local.counts.data(), local.displacements.data(),
                       MPI_DOUBLE, MPI_COMM_WORLD);
    }
    MPI_Allreduce(&local_dangling, &dangling, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    base = ((1.0 - alpha) + alpha * dangling) * inv_n;
    double local_checks[2] = {0, 0}, checks[2];
    for (int v = 0; v < count; ++v) {
        double incoming = 0;
        for (Index e = local.in_offsets[v]; e < local.in_offsets[v + 1]; ++e)
            incoming += halo ? source_values[halo->edge_source_slots[e]]
                             : all_contributions[local.in_sources[e]];
        local_checks[0] += std::abs(base + alpha * incoming - result.ranks[v]);
        local_checks[1] += result.ranks[v];
    }
    MPI_Allreduce(local_checks, checks, 2, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    result.residual_l1 = checks[0];
    result.rank_sum = checks[1];
    std::vector<double> global_ranks;
    if (local.rank == 0) global_ranks.resize(local.total_nodes);
    MPI_Gatherv(result.ranks.data(), count, MPI_DOUBLE, global_ranks.data(),
                local.counts.data(), local.displacements.data(), MPI_DOUBLE, 0, MPI_COMM_WORLD);
    result.ranks = std::move(global_ranks);
    return result;
}

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const std::string prefix = "--communication=";
        if (arg.rfind(prefix, 0) == 0) communication_mode = arg.substr(prefix.size());
        else {
            std::cerr << "Usage: pagerank_hybrid [--communication=allgather|halo]" << std::endl;
            return 2;
        }
    }
    if (communication_mode != "allgather" && communication_mode != "halo") {
        std::cerr << "Unknown communication mode: " << communication_mode << std::endl;
        return 2;
    }
    int provided;
    MPI_Init_thread(nullptr, nullptr, MPI_THREAD_FUNNELED, &provided);
    if (provided < MPI_THREAD_FUNNELED) {
        std::cerr << "MPI_THREAD_FUNNELED is required." << std::endl;
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    }
    omp_set_dynamic(0);
    int rank, processes;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
    const int max_total_threads = environment_integer("PAGERANK_HYBRID_MAX_TOTAL_THREADS", 8);
    const auto thread_counts = configured_thread_counts();
    if (processes > max_total_threads) {
        if (rank == 0) std::cerr << "Increase max_total_threads for this process count." << std::endl;
        MPI_Finalize();
        return 1;
    }
    bool success = true;
    try {
        for (const auto& dataset : datasets()) {
            Graph graph;
            if (rank == 0) {
                std::cout << "Running " << dataset.name << " p" << processes << "..." << std::endl;
                graph = load_graph(dataset.edges, dataset.nodes);
            }
            const auto local = distribute_graph(graph);
            HaloPlan halo_plan;
            const HaloPlan* halo = nullptr;
            if (communication_mode == "halo") {
                halo_plan = build_halo_plan(local);
                halo = &halo_plan;
            }
            for (int thread_count : thread_counts) {
                if (processes * thread_count > max_total_threads) continue;
                for (int run = 0; run < warmup_runs(); ++run) pagerank_hybrid(local, thread_count, halo);

                Result result;
                std::vector<double> times;
                std::vector<int> threads_per_process(processes);
                int total_threads = 0;
                bool converged = true;
                double max_residual = 0, max_sum_error = 0;
                std::ostringstream timings;
                timings << std::setprecision(17) << std::boolalpha
                        << "run,processes,threads_min,threads_max,total_threads,iterations,converged,solve_s,communication_s,communication_bytes_per_iteration,communication_setup_bytes,residual_l1,rank_sum\n";
                for (int run = 1; run <= repeat_runs(); ++run) {
                    result = pagerank_hybrid(local, thread_count, halo);
                    MPI_Allgather(&result.threads, 1, MPI_INT, threads_per_process.data(), 1, MPI_INT, MPI_COMM_WORLD);
                    total_threads = std::accumulate(threads_per_process.begin(), threads_per_process.end(), 0);
                    times.push_back(result.solve_seconds);
                    converged = converged && result.converged;
                    max_residual = std::max(max_residual, result.residual_l1);
                    max_sum_error = std::max(max_sum_error, std::abs(result.rank_sum - 1.0));
                    if (rank == 0)
                        timings << run << ',' << processes << ','
                                << *std::min_element(threads_per_process.begin(), threads_per_process.end()) << ','
                                << *std::max_element(threads_per_process.begin(), threads_per_process.end()) << ','
                                << total_threads << ',' << result.deltas.size() << ',' << result.converged << ','
                                << result.solve_seconds << ',' << result.communication_seconds << ','
                                << result.communication_bytes_per_iteration << ',' << result.communication_setup_bytes << ','
                                << result.residual_l1 << ',' << result.rank_sum << '\n';
                }
                success = success && (converged || fixed_iterations);
                if (rank != 0) continue;

                const auto timing = summarize_times(times);
                const auto folder = output_root() + '/' + dataset.name + "/p" + std::to_string(processes) + "_t" + std::to_string(thread_count);
                output_file(folder + "/timings.csv") << timings.str();
                write_ranks(folder + "/ranks.csv", graph, result);
                write_history(folder + "/history.csv", result);
                auto summary = output_file(folder + "/summary.json");
                summary << std::boolalpha
                        << "{\n  \"implementation\": \"hybrid\","
                        << "\n  \"dataset\": " << std::quoted(dataset.name)
                        << ",\n  \"environment\": " << std::quoted(experiment_environment())
                        << ",\n  \"build_type\": " << std::quoted(build_type)
                        << ",\n  \"processes\": " << processes
                        << ",\n  \"requested_threads\": " << thread_count
                        << ",\n  \"total_threads\": " << total_threads
                        << ",\n  \"threads_per_process\": [";
                for (int p = 0; p < processes; ++p) {
                    if (p) summary << ',';
                    summary << threads_per_process[p];
                }
                summary << ']'
                        << ",\n  \"mpi_thread_mode\": \"funneled\""
                        << ",\n  \"schedule\": \"dynamic\""
                        << ",\n  \"chunk_size\": " << chunk_size
                        << ",\n  \"partition\": \"contiguous_nodes\""
                        << ",\n  \"communication\": " << std::quoted(communication_mode == "halo" ? "halo" : "allgatherv")
                        << ",\n  \"communication_setup_s\": " << (halo ? halo_plan.setup_seconds : 0.0)
                        << ",\n  \"communication_bytes_per_iteration\": " << result.communication_bytes_per_iteration
                        << ",\n  \"communication_setup_bytes\": " << result.communication_setup_bytes
                        << ",\n  \"communication_max_s\": " << result.communication_seconds
                        << ",\n  \"min_local_edges\": " << local.min_edges
                        << ",\n  \"max_local_edges\": " << local.max_edges
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
                std::cout << dataset.name << " p" << processes << "_t" << thread_count << ": iterations=" << result.deltas.size()
                        << ", converged=" << std::boolalpha << converged
                        << ", median=" << timing.median << "s, residual=" << max_residual << std::endl;
            }
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
