#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <sys/mman.h>
#include <sys/stat.h>
#include <string>
#include <sys/file.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>

#include "motionexample.h"
#include "motion_sdk_breath_profile.hpp"
#include "motion_sdk_safety.hpp"
#include "receiver.h"
#include "sender.h"

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kStandHipY = -42.0 * kPi / 180.0;
constexpr double kStandKnee = 78.0 * kPi / 180.0;
constexpr double kFeedbackPauseSeconds = 0.10;
constexpr double kFeedbackReleaseSeconds = 0.25;
constexpr double kFeedbackRecoveryAgeSeconds = 0.02;
constexpr int kFeedbackRecoverySamples = 20;
constexpr double kMaxTrajectoryStepSeconds = 0.005;
constexpr double kTransitionErrorLimit = 0.45;
constexpr double kHoldErrorLimit = 0.10;
constexpr char kLockPath[] = "/dev/shm/emotion_bot_lite3_official_sdk.lock";
constexpr char kMarkerPath[] = "/dev/shm/emotion_bot_lite3_official_sdk.owned";
constexpr char kFeedbackPath[] = "/dev/shm/emotion_bot_lite3_telemetry";
constexpr char kRobotStatePath[] = "/dev/shm/emotion_bot_lite3_robot_state";
constexpr size_t kSharedCapacity = 4096;
constexpr size_t kRobotStateBodySize = 200;
constexpr size_t kRobotStateErrorFlagsOffset = 160;

static_assert(kFeedbackRecoveryAgeSeconds < kFeedbackPauseSeconds,
              "recovery must be fresher than the pause threshold");
static_assert(kFeedbackPauseSeconds < kFeedbackReleaseSeconds,
              "dead-stream release must follow the bounded hold window");

std::atomic<bool> g_stop{false};
std::atomic<bool> g_safety_fault{false};
std::atomic<int64_t> g_feedback_ns{0};

int64_t MonotonicNs() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count();
}

void OnSignal(int) { g_stop.store(true); }

bool FeedbackFresh() {
  const int64_t received = g_feedback_ns.load();
  return received > 0 &&
      (MonotonicNs() - received) * 1e-9 <= kFeedbackPauseSeconds;
}

double FeedbackAgeSeconds() {
  const int64_t received = g_feedback_ns.load();
  if (received <= 0) return INFINITY;
  return std::max(0.0, (MonotonicNs() - received) * 1e-9);
}

#pragma pack(push, 1)
struct SharedHeader {
  char magic[4];
  uint32_t version;
  uint64_t sequence;
  uint64_t receive_ns;
  uint32_t length;
};
#pragma pack(pop)

static_assert(sizeof(SharedHeader) == 28, "shared telemetry header must be packed");

class FeedbackSource {
 public:
  ~FeedbackSource() {
    if (mapping_ != MAP_FAILED) munmap(mapping_, kSharedCapacity);
    if (fd_ >= 0) close(fd_);
  }

  bool Open() {
    fd_ = open(kFeedbackPath, O_RDONLY);
    if (fd_ < 0) return false;
    struct stat details {};
    if (fstat(fd_, &details) != 0 ||
        details.st_size != static_cast<off_t>(kSharedCapacity)) return false;
    mapping_ = mmap(nullptr, kSharedCapacity, PROT_READ, MAP_SHARED, fd_, 0);
    return mapping_ != MAP_FAILED;
  }

  RobotData GetState() {
    RobotData candidate {};
    for (int attempt = 0; attempt < 8; ++attempt) {
      SharedHeader first {};
      SharedHeader second {};
      std::memcpy(&first, mapping_, sizeof(first));
      std::atomic_thread_fence(std::memory_order_acquire);
      if (std::memcmp(first.magic, "EBL3", 4) != 0 || first.version != 1 ||
          first.sequence % 2 != 0 || first.length < sizeof(RobotData) ||
          first.length > kSharedCapacity - sizeof(SharedHeader)) continue;
      std::memcpy(&candidate,
                  static_cast<const char*>(mapping_) + sizeof(SharedHeader),
                  sizeof(candidate));
      std::atomic_thread_fence(std::memory_order_acquire);
      std::memcpy(&second, mapping_, sizeof(second));
      if (std::memcmp(&first, &second, sizeof(first)) == 0) {
        g_feedback_ns.store(static_cast<int64_t>(first.receive_ns));
        const int64_t now_ns = MonotonicNs();
        max_age_seconds_ = std::max(
            max_age_seconds_,
            std::max(0.0, (now_ns - static_cast<int64_t>(first.receive_ns)) * 1e-9));
        if (first.sequence != last_sequence_) {
          if (last_sequence_ != 0 && first.sequence == last_sequence_ + 2 &&
              first.receive_ns >= last_receive_ns_) {
            max_consecutive_gap_seconds_ = std::max(
                max_consecutive_gap_seconds_,
                (first.receive_ns - last_receive_ns_) * 1e-9);
          } else if (last_sequence_ != 0 && first.sequence > last_sequence_ + 2) {
            skipped_updates_ += (first.sequence - last_sequence_) / 2 - 1;
          }
          last_sequence_ = first.sequence;
          last_receive_ns_ = first.receive_ns;
        }
        state_ = candidate;
        return state_;
      }
    }
    return state_;
  }


  double max_age_seconds() const { return max_age_seconds_; }
  double max_consecutive_gap_seconds() const {
    return max_consecutive_gap_seconds_;
  }
  uint64_t skipped_updates() const { return skipped_updates_; }

 private:
  int fd_{-1};
  void* mapping_{MAP_FAILED};
  RobotData state_ {};
  uint64_t last_sequence_{0};
  uint64_t last_receive_ns_{0};
  uint64_t skipped_updates_{0};
  double max_age_seconds_{0.0};
  double max_consecutive_gap_seconds_{0.0};
};

struct RobotSafetyState {
  bool valid{false};
  uint32_t basic_state{0};
  uint32_t error_flags{0};
  double age_seconds{INFINITY};
};

class RobotStateSource {
 public:
  ~RobotStateSource() {
    if (mapping_ != MAP_FAILED) munmap(mapping_, kSharedCapacity);
    if (fd_ >= 0) close(fd_);
  }

  bool Open() {
    fd_ = open(kRobotStatePath, O_RDONLY);
    if (fd_ < 0) return false;
    struct stat details {};
    if (fstat(fd_, &details) != 0 ||
        details.st_size != static_cast<off_t>(kSharedCapacity)) return false;
    mapping_ = mmap(nullptr, kSharedCapacity, PROT_READ, MAP_SHARED, fd_, 0);
    return mapping_ != MAP_FAILED;
  }

  RobotSafetyState GetState() {
    RobotSafetyState result;
    for (int attempt = 0; attempt < 8; ++attempt) {
      SharedHeader first {};
      SharedHeader second {};
      std::array<uint8_t, kRobotStateBodySize> body {};
      std::memcpy(&first, mapping_, sizeof(first));
      std::atomic_thread_fence(std::memory_order_acquire);
      if (std::memcmp(first.magic, "EBL3", 4) != 0 || first.version != 1 ||
          first.sequence % 2 != 0 || first.length != body.size()) continue;
      std::memcpy(body.data(),
                  static_cast<const char*>(mapping_) + sizeof(SharedHeader),
                  body.size());
      std::atomic_thread_fence(std::memory_order_acquire);
      std::memcpy(&second, mapping_, sizeof(second));
      if (std::memcmp(&first, &second, sizeof(first)) != 0) continue;
      std::memcpy(&result.basic_state, body.data(), sizeof(result.basic_state));
      std::memcpy(&result.error_flags,
                  body.data() + kRobotStateErrorFlagsOffset,
                  sizeof(result.error_flags));
      result.age_seconds = std::max(
          0.0, (MonotonicNs() - static_cast<int64_t>(first.receive_ns)) * 1e-9);
      result.valid = true;
      receive_ns_ = static_cast<int64_t>(first.receive_ns);
      state_ = result;
      return state_;
    }
    if (state_.valid) {
      state_.age_seconds = std::max(
          0.0, (MonotonicNs() - receive_ns_) * 1e-9);
    }
    return state_;
  }

 private:
  int fd_{-1};
  void* mapping_{MAP_FAILED};
  int64_t receive_ns_{0};
  RobotSafetyState state_ {};
};

bool RobotSafetyHealthy(RobotStateSource* source, const std::string& phase) {
  const RobotSafetyState state = source->GetState();
  if (!state.valid) {
    std::cerr << "ABORT unavailable 0x0901 safety state in " << phase
              << std::endl;
    g_safety_fault.store(true);
    return false;
  }
  if (RobotStateRequiresStop(state.basic_state, state.error_flags)) {
    std::cerr << "ABORT robot safety state basic_state=" << state.basic_state
              << " error_flags=" << state.error_flags
              << " age_ms=" << state.age_seconds * 1000.0
              << " in " << phase << std::endl;
    g_safety_fault.store(true);
    return false;
  }
  return true;
}

bool WaitForRobotSafetyState(RobotStateSource* source, double seconds) {
  const auto deadline = std::chrono::steady_clock::now() +
      std::chrono::duration<double>(seconds);
  while (std::chrono::steady_clock::now() < deadline && !g_stop.load()) {
    if (source->GetState().valid) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return false;
}

bool FiniteFeedback(const RobotData& data) {
  for (const auto& joint : data.joint_data.joint_data) {
    if (!std::isfinite(joint.position) || !std::isfinite(joint.velocity) ||
        std::abs(joint.velocity) > 20.0 || joint.position < -3.60 ||
        joint.position > 3.60) {
      return false;
    }
  }
  for (float value : data.imu.buffer_float) {
    if (!std::isfinite(value)) return false;
  }
  return true;
}

double TrackingError(const RobotCmd& command, const RobotData& data) {
  double error = 0.0;
  for (size_t i = 0; i < command.joint_cmd.size(); ++i) {
    error = std::max(error, std::abs(
        static_cast<double>(command.joint_cmd[i].position) -
        static_cast<double>(data.joint_data.joint_data[i].position)));
  }
  return error;
}

void SetStandCommand(RobotCmd* command, const BreathPose& pose) {
  std::memset(command, 0, sizeof(*command));
  for (int leg = 0; leg < 4; ++leg) {
    const BreathScalar compression = LegCompression(pose, leg);
    auto& hip_x = command->joint_cmd[3 * leg];
    auto& hip_y = command->joint_cmd[3 * leg + 1];
    auto& knee = command->joint_cmd[3 * leg + 2];
    hip_x.position = 0.0f;
    hip_y.position = static_cast<float>(kStandHipY - compression.position);
    knee.position = static_cast<float>(
        kStandKnee + kKneeToHipCompression * compression.position);
    hip_x.velocity = 0.0f;
    hip_y.velocity = static_cast<float>(-compression.velocity);
    knee.velocity = static_cast<float>(
        kKneeToHipCompression * compression.velocity);
    hip_x.torque = hip_y.torque = knee.torque = 0.0f;
    hip_x.kp = hip_y.kp = knee.kp = 80.0f;
    hip_x.kd = hip_y.kd = knee.kd = 0.7f;
  }
}

struct Watchdog {
  int notify_fd{-1};
  pid_t pid{-1};

  bool Start(const std::string& target_ip, uint16_t target_port) {
    int pipe_fd[2];
    if (pipe(pipe_fd) != 0) return false;
    pid = fork();
    if (pid < 0) {
      close(pipe_fd[0]);
      close(pipe_fd[1]);
      return false;
    }
    if (pid == 0) {
      close(pipe_fd[1]);
      char value = 0;
      ssize_t result;
      do {
        result = read(pipe_fd[0], &value, 1);
      } while (result < 0 && errno == EINTR);
      close(pipe_fd[0]);
      if (result == 0) {
        Sender emergency_release(target_ip, target_port);
        emergency_release.ControlGet(ROBOT);
        unlink(kMarkerPath);
      }
      _exit(0);
    }
    close(pipe_fd[0]);
    notify_fd = pipe_fd[1];
    return true;
  }

  void CompleteNormally() {
    if (notify_fd >= 0) {
      const char done = 'D';
      (void)write(notify_fd, &done, 1);
      close(notify_fd);
      notify_fd = -1;
    }
    if (pid > 0) {
      (void)waitpid(pid, nullptr, 0);
      pid = -1;
    }
  }
};

struct FeedbackPauseStats {
  uint64_t pauses{0};
  uint64_t recoveries{0};
  double max_pause_seconds{0.0};
};

bool WaitForFeedback(FeedbackSource* receiver, RobotStateSource* robot_state,
                     const std::string& phase, double seconds) {
  const auto deadline = std::chrono::steady_clock::now() +
      std::chrono::duration<double>(seconds);
  uint32_t last_tick = 0;
  bool have_tick = false;
  int samples = 0;
  while (std::chrono::steady_clock::now() < deadline && !g_stop.load()) {
    if (!RobotSafetyHealthy(robot_state, phase)) return false;
    const RobotData snapshot = receiver->GetState();
    if (FeedbackFresh() && FiniteFeedback(snapshot)) {
      if (!have_tick || snapshot.tick != last_tick) {
        last_tick = snapshot.tick;
        have_tick = true;
        ++samples;
      }
      if (samples >= 20) return true;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return false;
}

bool BootstrapSdkFeedback(Sender* sender, FeedbackSource* receiver,
                          RobotStateSource* robot_state, RobotCmd* command) {
  std::cout << "PHASE sdk_feedback_bootstrap" << std::endl;
  std::memset(command, 0, sizeof(*command));
  for (auto& joint : command->joint_cmd) {
    joint.kp = 60.0f;
    joint.kd = 0.7f;
  }
  const auto deadline = std::chrono::steady_clock::now() +
      std::chrono::milliseconds(250);
  auto next = std::chrono::steady_clock::now();
  while (std::chrono::steady_clock::now() < deadline && !g_stop.load()) {
    if (!RobotSafetyHealthy(robot_state, "sdk_feedback_bootstrap")) return false;
    sender->SendCmd(*command);
    const RobotData snapshot = receiver->GetState();
    if (FeedbackFresh() && FiniteFeedback(snapshot)) {
      std::cout << "PHASE_COMPLETE sdk_feedback_bootstrap feedback_age_ms="
                << FeedbackAgeSeconds() * 1000.0 << std::endl;
      return true;
    }
    next += std::chrono::milliseconds(1);
    std::this_thread::sleep_until(next);
  }
  return false;
}

template <typename Update>
bool RunPhase(const std::string& name, double duration, double error_limit,
              Sender* sender, FeedbackSource* receiver,
              RobotStateSource* robot_state, RobotCmd* command,
              FeedbackPauseStats* pause_stats, Update update,
              std::array<double, 12>* minimum = nullptr,
              std::array<double, 12>* maximum = nullptr) {
  std::cout << "PHASE " << name << std::endl;
  auto next = std::chrono::steady_clock::now();
  auto last_trajectory_tick = next;
  auto pause_started = next;
  double elapsed = 0.0;
  bool paused = false;
  uint32_t recovery_last_tick = 0;
  int recovery_samples = 0;
  RobotCmd hold_command = *command;
  int tick = 0;
  while (!g_stop.load()) {
    const auto now = std::chrono::steady_clock::now();
    if (!RobotSafetyHealthy(robot_state, name)) return false;
    // Refresh the shared-memory snapshot before evaluating its age.  Checking
    // the timestamp from the previous poll first falsely classifies a delayed
    // runner thread as a dead telemetry producer even when a current frame is
    // already available in the sequence-locked record.
    const RobotData snapshot = receiver->GetState();
    const double feedback_age = FeedbackAgeSeconds();
    if (feedback_age > kFeedbackReleaseSeconds) {
      if (paused) {
        pause_stats->max_pause_seconds = std::max(
            pause_stats->max_pause_seconds,
            std::chrono::duration<double>(now - pause_started).count());
      }
      std::cerr << "ABORT dead 0x0906 feedback age_ms="
                << feedback_age * 1000.0 << " in " << name << std::endl;
      return false;
    }
    if (feedback_age > kFeedbackPauseSeconds) {
      if (!paused) {
        paused = true;
        pause_started = now;
        recovery_samples = 0;
        recovery_last_tick = snapshot.tick;
        hold_command = *command;
        for (auto& joint : hold_command.joint_cmd) {
          joint.velocity = 0.0f;
          joint.torque = 0.0f;
        }
        ++pause_stats->pauses;
        std::cerr << "PAUSE stale 0x0906 feedback age_ms="
                  << feedback_age * 1000.0 << " in " << name
                  << "; holding last validated command" << std::endl;
      }
      sender->SendCmd(hold_command);
      last_trajectory_tick = now;
      next += std::chrono::milliseconds(1);
      if (next < now) next = now + std::chrono::milliseconds(1);
      std::this_thread::sleep_until(next);
      continue;
    }
    if (!FiniteFeedback(snapshot)) {
      std::cerr << "ABORT invalid joint/IMU feedback in " << name << std::endl;
      return false;
    }
    if (paused) {
      if (feedback_age <= kFeedbackRecoveryAgeSeconds &&
          snapshot.tick != recovery_last_tick) {
        recovery_last_tick = snapshot.tick;
        ++recovery_samples;
      } else if (feedback_age > kFeedbackRecoveryAgeSeconds) {
        recovery_samples = 0;
        recovery_last_tick = snapshot.tick;
      }
      sender->SendCmd(hold_command);
      last_trajectory_tick = now;
      if (recovery_samples < kFeedbackRecoverySamples) {
        next += std::chrono::milliseconds(1);
        if (next < now) next = now + std::chrono::milliseconds(1);
        std::this_thread::sleep_until(next);
        continue;
      }
      const double pause_seconds =
          std::chrono::duration<double>(now - pause_started).count();
      pause_stats->max_pause_seconds = std::max(
          pause_stats->max_pause_seconds, pause_seconds);
      ++pause_stats->recoveries;
      paused = false;
      std::cout << "RESUME fresh 0x0906 samples=" << recovery_samples
                << " pause_ms=" << pause_seconds * 1000.0
                << " in " << name << std::endl;
    } else {
      elapsed += std::min(
          std::chrono::duration<double>(now - last_trajectory_tick).count(),
          kMaxTrajectoryStepSeconds);
    }
    last_trajectory_tick = now;
    update(std::min(elapsed, duration), snapshot, command);
    if (tick > 50 && TrackingError(*command, snapshot) > error_limit) {
      std::cerr << "ABORT tracking error " << TrackingError(*command, snapshot)
                << " rad in " << name << std::endl;
      return false;
    }
    if (minimum && maximum) {
      for (size_t i = 0; i < 12; ++i) {
        const double value = snapshot.joint_data.joint_data[i].position;
        (*minimum)[i] = std::min((*minimum)[i], value);
        (*maximum)[i] = std::max((*maximum)[i], value);
      }
    }
    sender->SendCmd(*command);
    if (elapsed >= duration) {
      std::cout << "PHASE_COMPLETE " << name << " elapsed=" << elapsed
                << " feedback_age_ms=" << FeedbackAgeSeconds() * 1000.0
                << std::endl;
      return true;
    }
    ++tick;
    next += std::chrono::milliseconds(1);
    if (next < now) next = now + std::chrono::milliseconds(1);
    std::this_thread::sleep_until(next);
  }
  if (g_stop.load()) {
    std::cerr << "ABORT signal in " << name << std::endl;
  }
  return false;
}

}  // namespace

int main(int argc, char** argv) {
  bool execute = false;
  bool continuous = false;
  std::string target_ip = "192.168.1.120";
  uint16_t target_port = 43893;
  for (int i = 1; i < argc; ++i) {
    const std::string argument(argv[i]);
    if (argument == "--execute") execute = true;
    else if (argument == "--continuous") continuous = true;
    else if (argument.rfind("--target-ip=", 0) == 0) target_ip = argument.substr(12);
    else if (argument.rfind("--target-port=", 0) == 0) {
      target_port = static_cast<uint16_t>(std::stoi(argument.substr(14)));
    } else {
      std::cerr << "usage: " << argv[0]
                << " [--execute] [--continuous] [--target-ip=IP]"
                << " [--target-port=PORT]\n";
      return 2;
    }
  }

  std::signal(SIGINT, OnSignal);
  std::signal(SIGTERM, OnSignal);

  int lock_fd = open(kLockPath, O_CREAT | O_RDWR, 0600);
  if (lock_fd < 0 || flock(lock_fd, LOCK_EX | LOCK_NB) != 0) {
    std::cerr << "exclusive SDK lease unavailable" << std::endl;
    return 2;
  }

  FeedbackSource receiver;
  if (!receiver.Open()) {
    std::cerr << "unable to open reviewed passive 0x0906 feed" << std::endl;
    return 3;
  }
  RobotStateSource robot_state;
  if (!robot_state.Open()) {
    std::cerr << "unable to open validated 0x0901 safety feed" << std::endl;
    return 3;
  }
  if (!WaitForRobotSafetyState(&robot_state, 3.0)) {
    std::cerr << "validated 0x0901 safety feed did not become readable"
              << std::endl;
    return 3;
  }
  if (!RobotSafetyHealthy(&robot_state, "preflight")) return 3;
  const bool initial_feedback = WaitForFeedback(
      &receiver, &robot_state, "preflight", 3.0);
  if (g_safety_fault.load()) return 3;
  if (initial_feedback) {
    const RobotData initial = receiver.GetState();
    std::cout << "PREFLIGHT tick=" << initial.tick << " positions=";
    for (const auto& joint : initial.joint_data.joint_data) {
      std::cout << joint.position << ',';
    }
    std::cout << std::endl;
  } else {
    std::cout << "PREFLIGHT 0x0906 pending until RobotStateInit" << std::endl;
  }
  if (!execute) {
    std::cout << "PREFLIGHT_ONLY no command sent" << std::endl;
    return initial_feedback ? 0 : 3;
  }

  Watchdog watchdog;
  if (!watchdog.Start(target_ip, target_port)) {
    std::cerr << "failed to start independent release watchdog" << std::endl;
    return 4;
  }

  Sender sender(target_ip, target_port);
  MotionExample motion;
  RobotCmd command;
  std::memset(&command, 0, sizeof(command));
  bool success = false;
  bool acquired = true;
  FeedbackPauseStats pause_stats;
  {
    std::ofstream marker(kMarkerPath, std::ios::trunc);
    marker << getpid() << '\n';
  }
  std::cout << "BREATH_PROFILE expansion=" << kBreathExpansion
            << " compression=" << kBreathCompression
            << " knee_scale=" << kKneeToHipCompression
            << " roll_bias=" << kBreathRollBias
            << " pitch_bias=" << kBreathPitchBias
            << " yaw=0 cycle_seconds=" << kBreathDurationSeconds
            << std::endl;

  std::cout << "PHASE robot_state_init" << std::endl;
  sender.RobotStateInit();
  bool okay = WaitForFeedback(
      &receiver, &robot_state, "robot_state_init", 3.0);
  if (!okay && !g_safety_fault.load()) {
    okay = BootstrapSdkFeedback(
        &sender, &receiver, &robot_state, &command);
  }
  if (!okay) {
    std::cerr << "ABORT no fresh valid 0x0906 after RobotStateInit" << std::endl;
  } else {
    motion.GetInitData(receiver.GetState().joint_data, 0.0);
    std::cout << "PHASE_COMPLETE robot_state_init feedback_age_ms="
              << FeedbackAgeSeconds() * 1000.0 << std::endl;
  }

  if (okay) {
    okay = RunPhase(
        "pre_stand", 1.0, kTransitionErrorLimit, &sender, &receiver,
        &robot_state, &command, &pause_stats,
        [&motion](double elapsed, const RobotData& data, RobotCmd* output) {
          motion.PreStandUp(*output, elapsed, const_cast<RobotData&>(data));
        });
  }

  if (okay) {
    motion.GetInitData(receiver.GetState().joint_data, 1.0);
    okay = RunPhase(
        "stand", 1.5, kTransitionErrorLimit, &sender, &receiver,
        &robot_state, &command, &pause_stats,
        [&motion](double elapsed, const RobotData& data, RobotCmd* output) {
          motion.StandUp(*output, 1.0 + elapsed, const_cast<RobotData&>(data));
        });
  }

  if (okay) {
    okay = RunPhase(
        "stand_hold", 1.0, kHoldErrorLimit, &sender, &receiver,
        &robot_state, &command, &pause_stats,
        [](double, const RobotData&, RobotCmd* output) {
          SetStandCommand(output, BreathPose{});
        });
  }

  std::array<double, 12> minimum;
  std::array<double, 12> maximum;
  bool breath_started = false;
  bool breath_completed = false;
  uint64_t breath_cycles = 0;
  if (okay) {
    breath_started = true;
    do {
      minimum.fill(1e9);
      maximum.fill(-1e9);
      std::cout << "BREATH_CYCLE_START cycle=" << breath_cycles + 1
                << std::endl;
      breath_completed = RunPhase(
          "neutral_breath", kBreathDurationSeconds, kHoldErrorLimit,
          &sender, &receiver, &robot_state, &command, &pause_stats,
          [](double elapsed, const RobotData&, RobotCmd* output) {
            SetStandCommand(output, SampleAnimalBreath(elapsed));
          }, &minimum, &maximum);
      okay = breath_completed;
      if (breath_completed) {
        ++breath_cycles;
        std::cout << "BREATH_CYCLE_COMPLETE cycle=" << breath_cycles
                  << " max_feedback_age_ms="
                  << receiver.max_age_seconds() * 1000.0
                  << " max_consecutive_update_gap_ms="
                  << receiver.max_consecutive_gap_seconds() * 1000.0
                  << " feedback_pauses=" << pause_stats.pauses
                  << " feedback_recoveries=" << pause_stats.recoveries
                  << " max_pause_ms="
                  << pause_stats.max_pause_seconds * 1000.0
                  << " spans=";
        for (size_t i = 0; i < 12; ++i) {
          std::cout << (i == 0 ? "" : ",") << maximum[i] - minimum[i];
        }
        std::cout << std::endl;
      }
    } while (okay && continuous && !g_stop.load());
  }

  if (okay && !continuous) {
    okay = RunPhase(
        "neutral_hold", 0.5, kHoldErrorLimit, &sender, &receiver,
        &robot_state, &command, &pause_stats,
        [](double, const RobotData&, RobotCmd* output) {
          SetStandCommand(output, BreathPose{});
        });
  }

  std::cout << "PHASE release_to_robot" << std::endl;
  if (acquired) sender.ControlGet(ROBOT);
  acquired = false;
  unlink(kMarkerPath);
  watchdog.CompleteNormally();

  std::cout << "BREATH_WINDOW started=" << (breath_started ? "true" : "false")
            << " completed=" << (breath_completed ? "true" : "false")
            << " requested_seconds=" << kBreathDurationSeconds
            << " completed_cycles=" << breath_cycles
            << " continuous=" << (continuous ? "true" : "false")
            << std::endl;
  std::cout << "FEEDBACK_STATS max_age_ms="
            << receiver.max_age_seconds() * 1000.0
            << " max_consecutive_update_gap_ms="
            << receiver.max_consecutive_gap_seconds() * 1000.0
            << " skipped_shared_updates=" << receiver.skipped_updates()
            << " pauses=" << pause_stats.pauses
            << " recoveries=" << pause_stats.recoveries
            << " max_pause_ms=" << pause_stats.max_pause_seconds * 1000.0
            << std::endl;
  std::cout << "SDK_OWNERSHIP_RELEASED marker_present="
            << (access(kMarkerPath, F_OK) == 0 ? "true" : "false")
            << std::endl;
  std::cout << "ROBOT_SAFETY_FAULT triggered="
            << (g_safety_fault.load() ? "true" : "false") << std::endl;

  if (okay && !continuous && !g_stop.load()) {
    std::cout << "PASS official SDK stand and neutral breathing" << std::endl;
    success = true;
  }

  close(lock_fd);
  return success ? 0 : 5;
}
