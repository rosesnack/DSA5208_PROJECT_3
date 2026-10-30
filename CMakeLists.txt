cmake_minimum_required(VERSION 3.16)
project(pagerank_project LANGUAGES CXX)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_CUDA "Build the native CUDA PageRank implementation" OFF)
option(BUILD_KOKKOS "Build the Kokkos PageRank implementation" OFF)

if(MSVC)
    add_compile_options("$<$<COMPILE_LANGUAGE:CXX>:/W4>")
else()
    add_compile_options("$<$<COMPILE_LANGUAGE:CXX>:-Wall>"
                        "$<$<COMPILE_LANGUAGE:CXX>:-Wextra>"
                        "$<$<COMPILE_LANGUAGE:CXX>:-Wpedantic>")
endif()

add_library(graph_io src/graph_io.cpp)
target_include_directories(graph_io PUBLIC src)
target_compile_features(graph_io PUBLIC cxx_std_17)

add_library(utility src/utility.cpp)
target_link_libraries(utility PUBLIC graph_io)
target_compile_definitions(utility PUBLIC PAGERANK_BUILD_TYPE="${CMAKE_BUILD_TYPE}")

add_executable(pagerank_serial src/pagerank_serial.cpp)
target_link_libraries(pagerank_serial PRIVATE utility)

find_package(OpenMP REQUIRED COMPONENTS CXX)
add_executable(pagerank_openmp src/pagerank_openmp.cpp)
target_link_libraries(pagerank_openmp PRIVATE utility OpenMP::OpenMP_CXX)

find_package(MPI REQUIRED COMPONENTS CXX)
add_library(mpi_graph src/mpi_graph.cpp)
target_link_libraries(mpi_graph PUBLIC graph_io MPI::MPI_CXX)

add_executable(pagerank_mpi src/pagerank_mpi.cpp)
target_link_libraries(pagerank_mpi PRIVATE utility mpi_graph)

add_executable(pagerank_hybrid src/pagerank_hybrid.cpp)
target_link_libraries(pagerank_hybrid PRIVATE utility mpi_graph OpenMP::OpenMP_CXX)

if(BUILD_CUDA)
    enable_language(CUDA)
    find_package(CUDAToolkit REQUIRED)
    add_executable(pagerank_cuda src/pagerank_cuda.cu)
    target_link_libraries(pagerank_cuda PRIVATE utility CUDA::cudart)
    set_target_properties(pagerank_cuda PROPERTIES CUDA_STANDARD 17 CUDA_STANDARD_REQUIRED ON)
endif()

if(BUILD_KOKKOS)
    find_package(Kokkos CONFIG REQUIRED)
    add_executable(pagerank_kokkos src/pagerank_kokkos.cpp)
    target_link_libraries(pagerank_kokkos PRIVATE utility Kokkos::kokkos)
    target_compile_features(pagerank_kokkos PRIVATE cxx_std_17)
endif()
