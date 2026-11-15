#pragma once

#include "mpi_graph.hpp"
#include "utility.hpp"

#include <mpi.h>

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

inline void exchange_contributions(const Partition& local, const HaloPlan* halo,
                                   const std::vector<double>& contributions,
                                   std::vector<double>& source_values,
                                   std::vector<double>& halo_receive,
                                   std::vector<double>& halo_send) {
    const int count = local.counts[local.rank];
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
                       source_values.data(), local.counts.data(), local.displacements.data(),
                       MPI_DOUBLE, MPI_COMM_WORLD);
    }
}

template <class Backend>
Result pagerank_mpi_device(const Partition& local, const HaloPlan* halo, Backend& backend) {
    const int count = local.counts[local.rank];
    const double inv_n = 1.0 / local.total_nodes;
    const auto limit = fixed_iterations ? fixed_iterations : max_iterations;
    Result result;
    result.deltas.reserve(limit);
    result.communication_bytes_per_iteration = halo
        ? static_cast<double>(halo->global_halo_size) * sizeof(double)
        : static_cast<double>(local.total_nodes) * (local.processes - 1) * sizeof(double);
    result.communication_setup_bytes = halo
        ? static_cast<double>(halo->global_halo_size) * sizeof(Index) : 0.0;

    std::vector<double> contributions(count);
    std::vector<double> source_values(halo ? count + halo->local_halo_size : local.total_nodes);
    std::vector<double> halo_receive, halo_send;
    if (halo) {
        halo_receive.resize(halo->requested_global_ids.size());
        halo_send.resize(halo->served_local_indices.size());
    }
    backend.reset(inv_n);
    MPI_Barrier(MPI_COMM_WORLD);
    const double start = MPI_Wtime();
    for (std::size_t iteration = 0; iteration < limit; ++iteration) {
        double local_dangling = 0.0;
        backend.compute_contributions(contributions, local_dangling,
                                      result.device_seconds, result.transfer_seconds);
        double dangling = 0.0;
        const double exchange_start = MPI_Wtime();
        exchange_contributions(local, halo, contributions, source_values, halo_receive, halo_send);
        MPI_Allreduce(&local_dangling, &dangling, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        result.communication_seconds += MPI_Wtime() - exchange_start;
        const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
        const double local_delta = backend.update(source_values, base,
                                                  result.device_seconds, result.transfer_seconds);
        double delta = 0.0;
        const double reduction_start = MPI_Wtime();
        MPI_Allreduce(&local_delta, &delta, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        result.communication_seconds += MPI_Wtime() - reduction_start;
        result.deltas.push_back(delta);
        result.converged = delta <= tolerance;
        if (result.converged && !fixed_iterations) break;
    }
    const double elapsed = MPI_Wtime() - start;
    MPI_Allreduce(&elapsed, &result.solve_seconds, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
    double local_timing[3] = {result.communication_seconds, result.device_seconds, result.transfer_seconds};
    double global_timing[3] = {0, 0, 0};
    MPI_Allreduce(local_timing, global_timing, 3, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
    result.communication_seconds = global_timing[0];
    result.device_seconds = global_timing[1];
    result.transfer_seconds = global_timing[2];

    // Final residual, rank mass, and full-rank gather are outside solve_s.
    std::vector<double> local_ranks(count);
    backend.download_ranks(local_ranks);
    double local_dangling = 0.0;
    for (int u = 0; u < count; ++u) {
        contributions[u] = local.out_degree[u]
            ? local_ranks[u] / static_cast<double>(local.out_degree[u]) : 0.0;
        if (local.out_degree[u] == 0) local_dangling += local_ranks[u];
    }
    exchange_contributions(local, halo, contributions, source_values, halo_receive, halo_send);
    double dangling = 0.0;
    MPI_Allreduce(&local_dangling, &dangling, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
    double local_checks[2] = {0.0, 0.0}, checks[2] = {0.0, 0.0};
    for (int v = 0; v < count; ++v) {
        double incoming = 0.0;
        for (Index e = local.in_offsets[v]; e < local.in_offsets[v + 1]; ++e)
            incoming += halo ? source_values[halo->edge_source_slots[e]]
                             : source_values[local.in_sources[e]];
        local_checks[0] += std::abs(base + alpha * incoming - local_ranks[v]);
        local_checks[1] += local_ranks[v];
    }
    MPI_Allreduce(local_checks, checks, 2, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    result.residual_l1 = checks[0];
    result.rank_sum = checks[1];
    std::vector<double> global_ranks;
    if (local.rank == 0) global_ranks.resize(local.total_nodes);
    MPI_Gatherv(local_ranks.data(), count, MPI_DOUBLE, global_ranks.data(),
                local.counts.data(), local.displacements.data(), MPI_DOUBLE, 0, MPI_COMM_WORLD);
    result.ranks = std::move(global_ranks);
    return result;
}

template <class Backend>
int run_mpi_device_suite(const std::string& implementation, const std::string& backend_name,
                         const std::string& communication_mode, const std::string& device_name,
                         int requested_threads = 1, int actual_threads = 1) {
    int rank = 0, processes = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
    const std::string method_root = results_root() + '/' + implementation +
        (communication_mode == "halo" ? "_halo" : "") + '/' + backend_name;
    bool success = true;
    for (const auto& dataset : datasets()) {
        Graph graph;
        if (rank == 0) {
            std::cout << "Running " << dataset.name << " p" << processes << " on "
                      << implementation << '/' << backend_name << ' ' << communication_mode << "..." << std::endl;
            graph = load_graph(dataset.edges, dataset.nodes);
        }
        Partition local = distribute_graph(graph);
        const auto total_edges = graph.in_sources.size();
#ifdef PAGERANK_COMPACT_MPI_SETUP
        // Distribution owns its edge copy; output only needs IDs, offsets and degrees.
        // Release this redundant root allocation before backend setup and solver timing.
        std::vector<Index>().swap(graph.in_sources);
#endif
        HaloPlan halo_plan;
        const HaloPlan* halo = nullptr;
        if (communication_mode == "halo") {
            halo_plan = build_halo_plan(local);
            halo = &halo_plan;
        }
        const std::vector<Index>& source_slots = halo ? halo->edge_source_slots : local.in_sources;
#ifdef PAGERANK_COMPACT_MPI_SETUP
        // Halo validation and backend setup use edge_source_slots, not these edge IDs.
        // Release the local copy before allocating the backend's edge storage.
        if (halo) std::vector<Index>().swap(local.in_sources);
#endif
        Backend backend(local, source_slots, halo ? local.counts[rank] + halo->local_halo_size : local.total_nodes);
        for (int run = 0; run < warmup_runs(); ++run)
            (void)pagerank_mpi_device(local, halo, backend);

        Result result;
        std::vector<double> times, communication_times, compute_times, transfer_times;
        bool converged = true;
        double max_residual = 0.0, max_sum_error = 0.0;
        std::ostringstream timings;
        timings << std::setprecision(17) << std::boolalpha
                << "run,processes,iterations,converged,solve_s,communication_s,backend_compute_s,transfer_s,communication_bytes_per_iteration,communication_setup_bytes,residual_l1,rank_sum\n";
        for (int run = 1; run <= repeat_runs(); ++run) {
            result = pagerank_mpi_device(local, halo, backend);
            times.push_back(result.solve_seconds);
            communication_times.push_back(result.communication_seconds);
            compute_times.push_back(result.device_seconds);
            transfer_times.push_back(result.transfer_seconds);
            converged = converged && result.converged;
            max_residual = std::max(max_residual, result.residual_l1);
            max_sum_error = std::max(max_sum_error, std::abs(result.rank_sum - 1.0));
            if (rank == 0)
                timings << run << ',' << processes << ',' << result.deltas.size() << ','
                        << result.converged << ',' << result.solve_seconds << ','
                        << result.communication_seconds << ',' << result.device_seconds << ','
                        << result.transfer_seconds << ',' << result.communication_bytes_per_iteration << ','
                        << result.communication_setup_bytes << ',' << result.residual_l1 << ','
                        << result.rank_sum << '\n';
        }
        success = success && (converged || fixed_iterations);
        if (rank != 0) continue;
        const TimingStats timing = summarize_times(times);
        const TimingStats communication_timing = summarize_times(communication_times);
        const TimingStats compute_timing = summarize_times(compute_times);
        const TimingStats transfer_timing = summarize_times(transfer_times);
        const std::string folder = method_root + '/' + dataset.name + "/p" + std::to_string(processes) +
            (requested_threads > 1 ? "_t" + std::to_string(requested_threads) : "");
        output_file(folder + "/timings.csv") << timings.str();
        write_ranks(folder + "/ranks.csv", graph, result);
        write_history(folder + "/history.csv", result);
        auto summary = output_file(folder + "/summary.json");
        summary << std::boolalpha
                << "{\n  \"implementation\": " << std::quoted(implementation)
                << ",\n  \"backend\": " << std::quoted(backend_name)
                << ",\n  \"device_name\": " << std::quoted(device_name)
                << ",\n  \"dataset\": " << std::quoted(dataset.name)
                << ",\n  \"environment\": " << std::quoted(experiment_environment())
                << ",\n  \"build_type\": " << std::quoted(build_type)
                << ",\n  \"processes\": " << processes
                << ",\n  \"requested_threads\": " << requested_threads
                << ",\n  \"actual_threads\": " << actual_threads
                << ",\n  \"partition\": \"contiguous_nodes\""
                << ",\n  \"communication\": " << std::quoted(communication_mode)
                << ",\n  \"communication_setup_s\": " << (halo ? halo_plan.setup_seconds : 0.0)
                << ",\n  \"communication_bytes_per_iteration\": " << result.communication_bytes_per_iteration
                << ",\n  \"communication_setup_bytes\": " << result.communication_setup_bytes
                << ",\n  \"communication_max_s\": " << result.communication_seconds
                << ",\n  \"communication_median_s\": " << communication_timing.median
                << ",\n  \"backend_compute_median_s\": " << compute_timing.median
                << ",\n  \"transfer_median_s\": " << transfer_timing.median
                << ",\n  \"min_local_edges\": " << local.min_edges
                << ",\n  \"max_local_edges\": " << local.max_edges
                << ",\n  \"nodes\": " << graph.size()
                << ",\n  \"edges\": " << total_edges
#ifdef PAGERANK_COMPACT_MPI_SETUP
                << ",\n  \"compact_setup\": true"
#endif
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
        std::cout << dataset.name << " p" << processes << ' ' << communication_mode
                  << ": iterations=" << result.deltas.size() << ", median=" << timing.median
                  << "s, residual=" << max_residual << std::endl;
    }
    return success ? 0 : 2;
}
