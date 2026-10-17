// Local algorithm-only adapter. ABI recovered from the pinned executable DWARF.
// This file has no robot transport, service, device or calibration-write code.
#include <array>
#include <cerrno>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unistd.h>

struct OneTypeLegData { double value[3]; };
struct DataLegs { OneTypeLegData pos[4], vel[4], torque[4]; };
struct DataGyro { double roll, pitch, yaw, rol_vel, pit_vel, yaw_vel, acc_x, acc_y, acc_z; };
struct alignas(8) ControlCommands { std::uint8_t bytes[552]; };
struct alignas(8) MotionConfig { std::uint8_t bytes[216]; };
struct DownLoadParameters { double kp[12], kd[12], t_ff[12], goal_angle[12],
                                  goal_angle_vel[12], goal_angle_comp[12]; };
struct RobotStateUpload {
    std::int32_t robot_basic_state, robot_gait_state, robot_policy_state;
    double rpy[3], rpy_vel[3], xyz_acc[3], pos_world[3], vel_world[3], vel_body[3];
    std::uint32_t touch_down_and_stair_trot;
    bool is_charging;
    std::uint32_t error_state;
    std::int32_t robot_motion_state;
    double battery_level;
    std::int32_t task_state;
    bool is_robot_need_move, zero_position_flag;
    double ultrasound[2];
};
struct Request { double time, period; DataLegs legs; DataGyro gyro; ControlCommands command; };
struct Reply { DataLegs legs; DownLoadParameters motor; double scope[140];
               RobotStateUpload state; std::int32_t basic_phase; std::uint32_t cycle; };
static_assert(sizeof(DataLegs) == 288 && sizeof(DataGyro) == 72);
static_assert(sizeof(MotionConfig) == 216 && sizeof(ControlCommands) == 552);
static_assert(sizeof(DownLoadParameters) == 576);
static_assert(offsetof(DownLoadParameters, goal_angle) == 0x120);
static_assert(sizeof(RobotStateUpload) == 208);
static_assert(offsetof(RobotStateUpload, zero_position_flag) == 0xbd);
static_assert(sizeof(Request) == 928 && sizeof(Reply) == 2200);

bool read_exact(int fd, void* target, std::size_t bytes) {
    auto* p = static_cast<char*>(target);
    std::size_t done = 0;
    while (done < bytes) {
        auto n = ::read(fd, p + done, bytes - done);
        if (n == 0 && done == 0) return false;
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) throw std::runtime_error("truncated request");
        done += n;
    }
    return true;
}
void write_exact(int fd, const void* source, std::size_t bytes) {
    const auto* p = static_cast<const char*>(source);
    std::size_t done = 0;
    while (done < bytes) {
        auto n = ::write(fd, p + done, bytes - done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) throw std::runtime_error("reply write failed");
        done += n;
    }
}
template<class T> T symbol(void* handle, const char* name) {
    void* p = dlsym(handle, name);
    if (!p) throw std::runtime_error(std::string("missing symbol: ") + name);
    return reinterpret_cast<T>(p);
}
int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("expected config binary and identity text paths");
        const int reply_fd = dup(STDOUT_FILENO);
        if (reply_fd < 0 || dup2(STDERR_FILENO, STDOUT_FILENO) < 0)
            throw std::runtime_error("cannot separate diagnostic and protocol streams");
        MotionConfig config{};
        std::ifstream conf(argv[1], std::ios::binary);
        conf.read(reinterpret_cast<char*>(&config), sizeof config);
        if (conf.gcount() != sizeof config || conf.peek() != EOF)
            throw std::runtime_error("bad MotionConfig length");
        std::ifstream id(argv[2]);
        std::string name, type;
        std::getline(id, name); std::getline(id, type);
        if (name.empty() || type.empty()) throw std::runtime_error("empty factory identity");
        void* handle = dlopen("/snapshot/lib/ras_lib/libdeepras.so", RTLD_NOW | RTLD_LOCAL);
        if (!handle) throw std::runtime_error(dlerror());
        using Init = void (*)(const std::string&, const std::string&, const MotionConfig&);
        using Step = void (*)(const DataLegs*, const DataGyro&, const double&, const double&,
                             const ControlCommands&, double (*)[140], DataLegs*);
        auto init = symbol<Init>(handle, "_Z13MotionInitialRKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEES6_RK12MotionConfig");
        auto step = symbol<Step>(handle, "_Z6MotionPK8DataLegsRK8DataGyroRKdS6_RK15ControlCommandsPA140_dPS_");
        auto* motor = symbol<const DownLoadParameters*>(handle, "download_parameters");
        auto* state = symbol<const RobotStateUpload*>(handle, "robot_state_upload");
        auto* basic = symbol<const std::uint8_t*>(handle, "_ZN12basic_motion11BasicMotion7global_E");
        std::cerr << "FACTORY_INIT_BEGIN\n";
        init(name, type, config);
        std::cerr << "FACTORY_INIT_OK\n";
        write_exact(reply_fd, "VLAFACT1", 8);
        Request req{};
        double previous = -1;
        std::uint32_t cycle = 0;
        while (read_exact(STDIN_FILENO, &req, sizeof req)) {
            if (++cycle > 15000 || !std::isfinite(req.time) || req.time <= previous ||
                !std::isfinite(req.period) || req.period <= 0 || req.period > 0.02 || req.time > 30)
                throw std::runtime_error("invalid time or bounded-call limit reached");
            std::array<double, 45> measured{};
            std::memcpy(measured.data(), &req.legs, sizeof req.legs);
            std::memcpy(measured.data() + 36, &req.gyro, sizeof req.gyro);
            for (int i = 0; i < 45; ++i)
                if (!std::isfinite(measured[i])) throw std::runtime_error("nonfinite measured input");
            for (auto value : req.command.bytes)
                if (value > 1) throw std::runtime_error("probe permits boolean commands only");
            Reply out{};
            step(&req.legs, req.gyro, req.time, req.period, req.command, &out.scope, &out.legs);
            out.motor = *motor; out.state = *state; out.cycle = cycle;
            std::memcpy(&out.basic_phase, basic + 0x20, sizeof out.basic_phase);
            std::array<double, 72> command{};
            std::memcpy(command.data(), &out.motor, sizeof out.motor);
            for (int i = 0; i < 72; ++i)
                if (!std::isfinite(command[i])) throw std::runtime_error("nonfinite motor output");
            write_exact(reply_fd, &out, sizeof out);
            previous = req.time;
        }
        std::cerr << "FACTORY_CALLS_OK " << cycle << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FACTORY_ADAPTER_ERROR " << e.what() << '\n';
        return 2;
    }
}
