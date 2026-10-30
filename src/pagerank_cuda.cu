#include "utility.hpp"

#include <cuda_runtime.h>

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
constexpr int block_size = 256;
std::string output_root() { return results_root() + "/cuda"; }

void check_cuda(cudaError_t status, const char* operation) {
    if (status != cudaSuccess)
        throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
}

__global__ void contribution_kernel(const double* ranks, const Index* out_degree,
                                    double* contributions, double* partial_dangling,
                                    std::size_t n) {
    extern __shared__ double sums[];
    const unsigned tid = threadIdx.x;
    const std::size_t v = static_cast<std::size_t>(blockIdx.x) * blockDim.x + tid;
    double dangling = 0.0;
    if (v < n) {
        const Index degree = out_degree[v];
        contributions[v] = degree ? ranks[v] / static_cast<double>(degree) : 0.0;
        if (degree == 0) dangling = ranks[v];
    }
    sums[tid] = dangling;
    __syncthreads();
    for (unsigned stride = blockDim.x / 2; stride; stride >>= 1) {
        if (tid < stride) sums[tid] += sums[tid + stride];
        __syncthreads();
    }
    if (tid == 0) partial_dangling[blockIdx.x] = sums[0];
}

__global__ void compute_base_kernel(const double* partial_dangling, int blocks,
                                    double inv_n, double* base) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        double dangling = 0.0;
        for (int i = 0; i < blocks; ++i) dangling += partial_dangling[i];
        *base = ((1.0 - alpha) + alpha * dangling) * inv_n;
    }
}

__global__ void update_kernel(const Index* offsets, const Index* sources,
                              const double* contributions, const double* old_ranks,
                              double* new_ranks, const double* base,
                              double* partial_delta, std::size_t n) {
    extern __shared__ double sums[];
    const unsigned tid = threadIdx.x;
    const std::size_t v = static_cast<std::size_t>(blockIdx.x) * blockDim.x + tid;
    double delta = 0.0;
    if (v < n) {
        double incoming = 0.0;
        for (Index e = offsets[v]; e < offsets[v + 1]; ++e)
            incoming += contributions[sources[e]];
        const double value = *base + alpha * incoming;
        new_ranks[v] = value;
        delta = fabs(value - old_ranks[v]);
    }
    sums[tid] = delta;
    __syncthreads();
    for (unsigned stride = blockDim.x / 2; stride; stride >>= 1) {
        if (tid < stride) sums[tid] += sums[tid + stride];
        __syncthreads();
    }
    if (tid == 0) partial_delta[blockIdx.x] = sums[0];
}

__global__ void compute_delta_kernel(const double* partial_delta, int blocks, double* delta) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        double total = 0.0;
        for (int i = 0; i < blocks; ++i) total += partial_delta[i];
        *delta = total;
    }
}

template <class T>
void allocate_and_copy(T** device, const std::vector<T>& host, const char* label) {
    check_cuda(cudaMalloc(reinterpret_cast<void**>(device), host.size() * sizeof(T)), "cudaMalloc");
    check_cuda(cudaMemcpy(*device, host.data(), host.size() * sizeof(T), cudaMemcpyHostToDevice), label);
}

Result pagerank_cuda(const Graph& graph) {
    using Clock = std::chrono::steady_clock;
    const std::size_t n = graph.size();
    const std::size_t blocks = (n + block_size - 1) / block_size;
    const double inv_n = 1.0 / static_cast<double>(n);
    Result result;
    result.ranks.assign(n, inv_n);
    const auto limit = fixed_iterations ? fixed_iterations : max_iterations;
    result.deltas.reserve(limit);

    Index *d_offsets = nullptr, *d_sources = nullptr, *d_out_degree = nullptr;
    double *d_rank_a = nullptr, *d_rank_b = nullptr, *d_contributions = nullptr;
    double *d_partial_dangling = nullptr, *d_base = nullptr, *d_partial_delta = nullptr, *d_delta = nullptr;
    auto release = [&]() {
        cudaFree(d_offsets); cudaFree(d_sources); cudaFree(d_out_degree);
        cudaFree(d_rank_a); cudaFree(d_rank_b); cudaFree(d_contributions);
        cudaFree(d_partial_dangling); cudaFree(d_base); cudaFree(d_partial_delta); cudaFree(d_delta);
    };

    const auto transfer_start = Clock::now();
    try {
        allocate_and_copy(&d_offsets, graph.in_offsets, "copy CSR offsets");
        allocate_and_copy(&d_sources, graph.in_sources, "copy CSR sources");
        allocate_and_copy(&d_out_degree, graph.out_degree, "copy out-degrees");
        allocate_and_copy(&d_rank_a, result.ranks, "copy initial ranks");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&d_rank_b), n * sizeof(double)), "allocate next ranks");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&d_contributions), n * sizeof(double)), "allocate contributions");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&d_partial_dangling), blocks * sizeof(double)), "allocate dangling partials");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&d_base), sizeof(double)), "allocate base scalar");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&d_partial_delta), blocks * sizeof(double)), "allocate delta partials");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&d_delta), sizeof(double)), "allocate delta scalar");
    } catch (...) { release(); throw; }
    result.transfer_seconds += std::chrono::duration<double>(Clock::now() - transfer_start).count();

    double* old_ranks = d_rank_a;
    double* new_ranks = d_rank_b;
    cudaEvent_t device_start{}, device_stop{};
    check_cuda(cudaEventCreate(&device_start), "create start event");
    check_cuda(cudaEventCreate(&device_stop), "create stop event");
    check_cuda(cudaEventRecord(device_start), "record start event");
    const auto solve_start = Clock::now();
    try {
        for (std::size_t iteration = 0; iteration < limit; ++iteration) {
            contribution_kernel<<<static_cast<unsigned>(blocks), block_size, block_size * sizeof(double)>>>(
                old_ranks, d_out_degree, d_contributions, d_partial_dangling, n);
            check_cuda(cudaGetLastError(), "launch contribution kernel");
            compute_base_kernel<<<1, 1>>>(d_partial_dangling, static_cast<int>(blocks), inv_n, d_base);
            check_cuda(cudaGetLastError(), "launch base reduction kernel");
            update_kernel<<<static_cast<unsigned>(blocks), block_size, block_size * sizeof(double)>>>(
                d_offsets, d_sources, d_contributions, old_ranks, new_ranks,
                d_base, d_partial_delta, n);
            check_cuda(cudaGetLastError(), "launch update kernel");
            compute_delta_kernel<<<1, 1>>>(d_partial_delta, static_cast<int>(blocks), d_delta);
            check_cuda(cudaGetLastError(), "launch delta reduction kernel");

            double delta = 0.0;
            check_cuda(cudaMemcpy(&delta, d_delta, sizeof(double), cudaMemcpyDeviceToHost), "read convergence delta");
            result.deltas.push_back(delta);
            std::swap(old_ranks, new_ranks);
            result.converged = delta <= tolerance;
            if (result.converged && !fixed_iterations) break;
        }
        check_cuda(cudaEventRecord(device_stop), "record stop event");
        check_cuda(cudaEventSynchronize(device_stop), "wait for device timing");
        float device_ms = 0.0f;
        check_cuda(cudaEventElapsedTime(&device_ms, device_start, device_stop), "read device timing");
        result.device_seconds = device_ms / 1000.0;
        result.solve_seconds = std::chrono::duration<double>(Clock::now() - solve_start).count();
        const auto rank_copy_start = Clock::now();
        check_cuda(cudaMemcpy(result.ranks.data(), old_ranks, n * sizeof(double), cudaMemcpyDeviceToHost), "copy final ranks");
        result.transfer_seconds += std::chrono::duration<double>(Clock::now() - rank_copy_start).count();
    } catch (...) {
        cudaEventDestroy(device_start); cudaEventDestroy(device_stop); release(); throw;
    }
    cudaEventDestroy(device_start);
    cudaEventDestroy(device_stop);
    release();

    // Independent host-side residual and mass checks are outside the timed solve.
    std::vector<double> contributions(n), next(n);
    double dangling = 0.0;
    for (std::size_t u = 0; u < n; ++u) {
        if (graph.out_degree[u] == 0) dangling += result.ranks[u];
        else contributions[u] = result.ranks[u] / static_cast<double>(graph.out_degree[u]);
    }
    const double base = ((1.0 - alpha) + alpha * dangling) * inv_n;
    for (std::size_t v = 0; v < n; ++v) {
        double incoming = 0.0;
        for (Index e = graph.in_offsets[v]; e < graph.in_offsets[v + 1]; ++e)
            incoming += contributions[graph.in_sources[e]];
        next[v] = base + alpha * incoming;
        result.residual_l1 += std::abs(next[v] - result.ranks[v]);
    }
    result.rank_sum = std::accumulate(result.ranks.begin(), result.ranks.end(), 0.0);
    return result;
}
} // namespace

int main() {
    int device_count = 0;
    try {
        check_cuda(cudaGetDeviceCount(&device_count), "query CUDA devices");
        if (device_count == 0) throw std::runtime_error("No CUDA device is available");
        cudaDeviceProp device_properties{};
        check_cuda(cudaGetDeviceProperties(&device_properties, 0), "query CUDA device properties");
        const std::string device_name = device_properties.name;
        bool success = true;
        for (const auto& dataset : datasets()) {
            std::cout << "Running " << dataset.name << " on CUDA..." << std::endl;
            const auto graph = load_graph(dataset.edges, dataset.nodes);
            for (int run = 0; run < warmup_runs(); ++run) (void)pagerank_cuda(graph);
            Result result;
            std::vector<double> times;
            std::vector<double> device_times, transfer_times;
            bool converged = true;
            double max_residual = 0.0, max_sum_error = 0.0;
            std::ostringstream timings;
            timings << std::setprecision(17) << std::boolalpha
                    << "run,iterations,converged,solve_s,device_s,transfer_s,residual_l1,rank_sum\n";
            for (int run = 1; run <= repeat_runs(); ++run) {
                result = pagerank_cuda(graph);
                times.push_back(result.solve_seconds);
                device_times.push_back(result.device_seconds);
                transfer_times.push_back(result.transfer_seconds);
                converged = converged && result.converged;
                max_residual = std::max(max_residual, result.residual_l1);
                max_sum_error = std::max(max_sum_error, std::abs(result.rank_sum - 1.0));
                timings << run << ',' << result.deltas.size() << ',' << result.converged << ','
                        << result.solve_seconds << ',' << result.device_seconds << ',' << result.transfer_seconds
                        << ',' << result.residual_l1 << ',' << result.rank_sum << '\n';
            }
            const auto timing = summarize_times(times);
            const auto device_timing = summarize_times(device_times);
            const auto transfer_timing = summarize_times(transfer_times);
            const auto folder = output_root() + '/' + dataset.name;
            output_file(folder + "/timings.csv") << timings.str();
            write_ranks(folder + "/ranks.csv", graph, result);
            write_history(folder + "/history.csv", result);
            auto summary = output_file(folder + "/summary.json");
            summary << std::boolalpha
                    << "{\n  \"implementation\": \"cuda\","
                    << "\n  \"environment\": " << std::quoted(experiment_environment())
                    << ",\n  \"build_type\": " << std::quoted(build_type)
                    << ",\n  \"dataset\": " << std::quoted(dataset.name)
                    << ",\n  \"device_count\": " << device_count
                    << ",\n  \"device_name\": " << std::quoted(device_name)
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
                    << ",\n  \"device_median_s\": " << device_timing.median
                    << ",\n  \"transfer_median_s\": " << transfer_timing.median
                    << ",\n  \"max_residual_l1\": " << max_residual
                    << ",\n  \"max_rank_sum_error\": " << max_sum_error << "\n}\n";
            std::cout << dataset.name << ": iterations=" << result.deltas.size()
                      << ", median=" << timing.median << "s, residual=" << max_residual << std::endl;
            success = success && result.converged;
        }
        return success ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << "CUDA PageRank failed: " << error.what() << std::endl;
        return 1;
    }
}
