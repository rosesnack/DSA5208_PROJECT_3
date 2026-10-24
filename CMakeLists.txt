cmake_minimum_required(VERSION 3.16)
project(pagerank_project LANGUAGES CXX)
set(CMAKE_CXX_EXTENSIONS OFF)

if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

add_library(graph_io src/graph_io.cpp)
target_include_directories(graph_io PUBLIC src)
target_compile_features(graph_io PUBLIC cxx_std_17)

add_executable(pagerank_serial src/pagerank_serial.cpp)
target_link_libraries(pagerank_serial PRIVATE graph_io)
