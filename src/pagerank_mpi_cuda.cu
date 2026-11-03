#include "mpi_device_driver.hpp"

#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int block_size = 256;
using Clock = std::chrono::steady_clock;

void check_cuda(cudaError_t status, const char* operation) {
    if (status != cudaSuccess)
        throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
}

template <class T>
void allocate_copy(T** device, const std::vector<T>& host) {
    check_cuda(cudaMalloc(reinterpret_cast<void**>(device), host.size() * sizeof(T)), "allocate device array");
    check_cuda(cudaMemcpy(*device, host.data(), host.size() * sizeof(T), cudaMemcpyHostToDevice),
               "copy graph array to device");
}

__global__ void contributions_kernel(const double* ranks, const Index* degrees,
                                     double* contributions, double* partial_dangling, int count) {
    extern __shared__ double sums[];
    const unsigned tid = threadIdx.x;
    const int u = static_cast<int>(blockIdx.x * blockDim.x + tid);
    double dangling = 0.0;
    if (u < count) {
        const Index degree = degrees[u];
        contributions[u] = degree ? ranks[u] / static_cast<double>(degree) : 0.0;
        if (degree == 0) dangling = ranks[u];
    }
    sums[tid] = dangling;
    __syncthreads();
    for (unsigned stride = blockDim.x / 2; stride; stride >>= 1) {
        if (tid < stride) sums[tid] += sums[tid + stride];
        __syncthreads();
    }
    if (tid == 0) partial_dangling[blockIdx.x] = sums[0];
}

__global__ void update_kernel(const Index* offsets, const Index* source_slots,
                              const double* source_values, const double* old_ranks,
                              double* new_ranks, double base, double* partial_delta, int count) {
    extern __shared__ double sums[];
    const unsigned tid = threadIdx.x;
    const int v = static_cast<int>(blockIdx.x * blockDim.x + tid);
    double delta = 0.0;
    if (v < count) {
        double incoming = 0.0;
        for (Index e = offsets[v]; e < offsets[v + 1]; ++e)
            incoming += source_values[source_slots[e]];
        const double value = base + alpha * incoming;
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

class MpiCudaBackend {
public:
    MpiCudaBackend(const Partition& local, const std::vector<Index>& source_slots,
                   std::size_t source_value_count)
        : count_(local.counts[local.rank]), blocks_((count_ + block_size - 1) / block_size),
          source_value_count_(source_value_count), partial_(blocks_), initial_(count_) {
        allocate_copy(&offsets_, local.in_offsets);
        allocate_copy(&source_slots_, source_slots);
        allocate_copy(&degrees_, local.out_degree);
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&rank_a_), count_ * sizeof(double)), "allocate ranks a");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&rank_b_), count_ * sizeof(double)), "allocate ranks b");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&contributions_), count_ * sizeof(double)), "allocate contributions");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&source_values_), source_value_count_ * sizeof(double)),
                   "allocate source values");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&partial_dangling_), blocks_ * sizeof(double)),
                   "allocate dangling partials");
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&partial_delta_), blocks_ * sizeof(double)),
                   "allocate delta partials");
    }

    ~MpiCudaBackend() {
        cudaFree(offsets_); cudaFree(source_slots_); cudaFree(degrees_);
        cudaFree(rank_a_); cudaFree(rank_b_); cudaFree(contributions_);
        cudaFree(source_values_); cudaFree(partial_dangling_); cudaFree(partial_delta_);
    }

    void reset(double initial_rank) {
        std::fill(initial_.begin(), initial_.end(), initial_rank);
        old_ranks_ = rank_a_;
        new_ranks_ = rank_b_;
        check_cuda(cudaMemcpy(old_ranks_, initial_.data(), count_ * sizeof(double), cudaMemcpyHostToDevice),
                   "reset ranks");
    }

    void compute_contributions(std::vector<double>& host_contributions, double& local_dangling,
                               double& compute_seconds, double& transfer_seconds) {
        const auto compute_start = Clock::now();
        contributions_kernel<<<blocks_, block_size, block_size * sizeof(double)>>>(
            old_ranks_, degrees_, contributions_, partial_dangling_, count_);
        check_cuda(cudaGetLastError(), "launch contribution kernel");
        check_cuda(cudaDeviceSynchronize(), "synchronize contribution kernel");
        compute_seconds += std::chrono::duration<double>(Clock::now() - compute_start).count();
        const auto transfer_start = Clock::now();
        check_cuda(cudaMemcpy(host_contributions.data(), contributions_, count_ * sizeof(double),
                              cudaMemcpyDeviceToHost), "copy contributions to host");
        check_cuda(cudaMemcpy(partial_.data(), partial_dangling_, blocks_ * sizeof(double),
                              cudaMemcpyDeviceToHost), "copy dangling partials to host");
        transfer_seconds += std::chrono::duration<double>(Clock::now() - transfer_start).count();
        local_dangling = std::accumulate(partial_.begin(), partial_.end(), 0.0);
    }

    double update(const std::vector<double>& host_sources, double base,
                  double& compute_seconds, double& transfer_seconds) {
        const auto transfer_start = Clock::now();
        check_cuda(cudaMemcpy(source_values_, host_sources.data(), source_value_count_ * sizeof(double),
                              cudaMemcpyHostToDevice), "copy source values to device");
        transfer_seconds += std::chrono::duration<double>(Clock::now() - transfer_start).count();
        const auto compute_start = Clock::now();
        update_kernel<<<blocks_, block_size, block_size * sizeof(double)>>>(
            offsets_, source_slots_, source_values_, old_ranks_, new_ranks_, base, partial_delta_, count_);
        check_cuda(cudaGetLastError(), "launch PageRank update kernel");
        check_cuda(cudaDeviceSynchronize(), "synchronize PageRank update kernel");
        compute_seconds += std::chrono::duration<double>(Clock::now() - compute_start).count();
        const auto delta_transfer_start = Clock::now();
        check_cuda(cudaMemcpy(partial_.data(), partial_delta_, blocks_ * sizeof(double),
                              cudaMemcpyDeviceToHost), "copy convergence partials to host");
        transfer_seconds += std::chrono::duration<double>(Clock::now() - delta_transfer_start).count();
        std::swap(old_ranks_, new_ranks_);
        return std::accumulate(partial_.begin(), partial_.end(), 0.0);
    }

    void download_ranks(std::vector<double>& host_ranks) {
        check_cuda(cudaMemcpy(host_ranks.data(), old_ranks_, count_ * sizeof(double), cudaMemcpyDeviceToHost),
                   "copy final ranks to host");
    }

private:
    int count_, blocks_;
    std::size_t source_value_count_;
    std::vector<double> partial_, initial_;
    Index *offsets_ = nullptr, *source_slots_ = nullptr, *degrees_ = nullptr;
    double *rank_a_ = nullptr, *rank_b_ = nullptr, *contributions_ = nullptr;
    double *source_values_ = nullptr, *partial_dangling_ = nullptr, *partial_delta_ = nullptr;
    double *old_ranks_ = nullptr, *new_ranks_ = nullptr;
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
    int local_rank = 0;
    MPI_Comm shared;
    MPI_Comm_split_type(MPI_COMM_WORLD, MPI_COMM_TYPE_SHARED, 0, MPI_INFO_NULL, &shared);
    MPI_Comm_rank(shared, &local_rank);
    MPI_Comm_free(&shared);
    int exit_code = 0;
    try {
        int device_count = 0;
        check_cuda(cudaGetDeviceCount(&device_count), "query CUDA devices");
        if (device_count == 0) throw std::runtime_error("No CUDA device is available");
        check_cuda(cudaSetDevice(local_rank % device_count), "assign local MPI rank to GPU");
        cudaDeviceProp properties{};
        check_cuda(cudaGetDeviceProperties(&properties, local_rank % device_count), "query selected GPU");
        exit_code = run_mpi_device_suite<MpiCudaBackend>("mpi_cuda", "Cuda", communication, properties.name);
    } catch (const std::exception& error) {
        int rank = 0;
        MPI_Comm_rank(MPI_COMM_WORLD, &rank);
        std::cerr << "MPI+CUDA rank " << rank << ": " << error.what() << std::endl;
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    }
    MPI_Finalize();
    return exit_code;
}
