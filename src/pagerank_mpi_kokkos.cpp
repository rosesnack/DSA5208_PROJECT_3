#include "mpi_device_driver.hpp"

#include <Kokkos_Core.hpp>

#include <algorithm>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
using ExecSpace = Kokkos::DefaultExecutionSpace;
using Policy = Kokkos::RangePolicy<ExecSpace>;
using IndexView = Kokkos::View<Index*, ExecSpace>;
using RankView = Kokkos::View<double*, ExecSpace>;

class MpiKokkosBackend {
public:
    MpiKokkosBackend(const Partition& local, const std::vector<Index>& source_slots,
                      std::size_t source_value_count)
        : count_(local.counts[local.rank]), offsets_("incoming_offsets", count_ + 1),
          source_slots_("source_slots", source_slots.size()), degrees_("out_degrees", count_),
          rank_a_("rank_a", count_), rank_b_("rank_b", count_),
          contributions_("contributions", count_), source_values_("source_values", source_value_count) {
        auto host_offsets = Kokkos::create_mirror_view(offsets_);
        auto host_slots = Kokkos::create_mirror_view(source_slots_);
        auto host_degrees = Kokkos::create_mirror_view(degrees_);
        std::copy(local.in_offsets.begin(), local.in_offsets.end(), host_offsets.data());
        std::copy(source_slots.begin(), source_slots.end(), host_slots.data());
        std::copy(local.out_degree.begin(), local.out_degree.end(), host_degrees.data());
        Kokkos::deep_copy(offsets_, host_offsets);
        Kokkos::deep_copy(source_slots_, host_slots);
        Kokkos::deep_copy(degrees_, host_degrees);
        Kokkos::fence("MPI+Kokkos graph setup");
    }

    void reset(double initial_rank) {
        old_ranks_ = rank_a_;
        new_ranks_ = rank_b_;
        Kokkos::deep_copy(old_ranks_, initial_rank);
    }

    void compute_contributions(std::vector<double>& host_contributions, double& local_dangling,
                               double& compute_seconds, double& transfer_seconds) {
        const auto compute_start = Clock::now();
        auto ranks = old_ranks_;
        auto degrees = degrees_;
        auto contributions = contributions_;
        Kokkos::parallel_reduce("MPI PageRank contributions", Policy(0, count_),
            KOKKOS_LAMBDA(const int u, double& dangling) {
                const Index degree = degrees(u);
                contributions(u) = degree ? ranks(u) / static_cast<double>(degree) : 0.0;
                if (degree == 0) dangling += ranks(u);
            }, local_dangling);
        Kokkos::fence("MPI PageRank contributions complete");
        compute_seconds += std::chrono::duration<double>(Clock::now() - compute_start).count();
        const auto transfer_start = Clock::now();
        auto host_view = Kokkos::create_mirror_view_and_copy(Kokkos::HostSpace(), contributions_);
        std::copy(host_view.data(), host_view.data() + count_, host_contributions.begin());
        transfer_seconds += std::chrono::duration<double>(Clock::now() - transfer_start).count();
    }

    double update(const std::vector<double>& host_sources, double base,
                  double& compute_seconds, double& transfer_seconds) {
        const auto transfer_start = Clock::now();
        auto host_view = Kokkos::create_mirror_view(source_values_);
        std::copy(host_sources.begin(), host_sources.end(), host_view.data());
        Kokkos::deep_copy(source_values_, host_view);
        transfer_seconds += std::chrono::duration<double>(Clock::now() - transfer_start).count();
        const auto compute_start = Clock::now();
        auto offsets = offsets_;
        auto source_slots = source_slots_;
        auto source_values = source_values_;
        auto old_ranks = old_ranks_;
        auto new_ranks = new_ranks_;
        double local_delta = 0.0;
        Kokkos::parallel_reduce("MPI PageRank pull update", Policy(0, count_),
            KOKKOS_LAMBDA(const int v, double& delta) {
                double incoming = 0.0;
                for (Index e = offsets(v); e < offsets(v + 1); ++e)
                    incoming += source_values(source_slots(e));
                const double value = base + alpha * incoming;
                new_ranks(v) = value;
                delta += Kokkos::abs(value - old_ranks(v));
            }, local_delta);
        Kokkos::fence("MPI PageRank pull update complete");
        compute_seconds += std::chrono::duration<double>(Clock::now() - compute_start).count();
        std::swap(old_ranks_, new_ranks_);
        return local_delta;
    }

    void download_ranks(std::vector<double>& host_ranks) {
        auto host_view = Kokkos::create_mirror_view_and_copy(Kokkos::HostSpace(), old_ranks_);
        std::copy(host_view.data(), host_view.data() + count_, host_ranks.begin());
    }

private:
    int count_;
    IndexView offsets_, source_slots_, degrees_;
    RankView rank_a_, rank_b_, contributions_, source_values_;
    RankView old_ranks_, new_ranks_;
};
} // namespace

int main(int argc, char** argv) {
    std::string communication = "allgather";
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const std::string prefix = "--communication=";
        if (arg.rfind(prefix, 0) == 0) communication = arg.substr(prefix.size());
        else return 2;
    }
    if (communication != "allgather" && communication != "halo") return 2;
    MPI_Init(nullptr, nullptr);
    Kokkos::initialize();
    int exit_code = 0;
    try {
        const int requested_threads = environment_integer("PAGERANK_KOKKOS_THREADS", 1);
        const int actual_threads = std::string(ExecSpace::name()) == "OpenMP"
            ? ExecSpace().concurrency() : 1;
        if (actual_threads != requested_threads)
            throw std::runtime_error("Kokkos OpenMP thread count differs from requested threads");
        exit_code = run_mpi_device_suite<MpiKokkosBackend>(
            "mpi_kokkos", ExecSpace::name(), communication, ExecSpace::name(),
            requested_threads, actual_threads);
    } catch (const std::exception& error) {
        int rank = 0;
        MPI_Comm_rank(MPI_COMM_WORLD, &rank);
        std::cerr << "MPI+Kokkos rank " << rank << ": " << error.what() << std::endl;
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    }
    Kokkos::finalize();
    MPI_Finalize();
    return exit_code;
}
