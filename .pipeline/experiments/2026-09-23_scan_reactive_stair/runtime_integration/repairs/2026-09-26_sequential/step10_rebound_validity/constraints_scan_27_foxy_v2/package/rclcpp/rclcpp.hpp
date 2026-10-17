#pragma once
#include <cstdio>
namespace rclcpp {
inline const char* get_logger(const char* name) { return name; }
}
#define RCLCPP_ERROR(logger, ...) std::fprintf(stderr, __VA_ARGS__)
#define RCLCPP_WARN(logger, ...) std::fprintf(stderr, __VA_ARGS__)
