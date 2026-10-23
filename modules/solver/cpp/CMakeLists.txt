cmake_minimum_required(VERSION 3.10)
project(modeling CXX)

set(CMAKE_CXX_STANDARD 17)

add_executable(modeling_2d
    main.cpp
    model/sources.cpp
)
target_include_directories(modeling_2d PRIVATE .)

add_executable(grad_optim
    grad_optim.cpp
)