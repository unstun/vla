#include "recording.h"
#include <cstdlib>
#include <cmath>

int main(int argc, char **argv) {
  try {
    const auto required = [](const char *name) {
      const char *value = std::getenv(name);
      if (!value) throw std::runtime_error(std::string("Missing ") + name);
      return std::string(value);
    };
    const fs::path input(required("V84_INPUT")), output(required("V84_OUTPUT"));
    const std::string mode = required("V84_MODE"), schedule = required("V84_SCHEDULE");
    if (mode != "fifo" && mode != "latest" && mode != "timer") throw std::runtime_error("Unknown admission mode");
    if (schedule != "nominal" && schedule != "blackout") throw std::runtime_error("Unknown exposure");
    if (!fs::create_directory(output)) throw std::runtime_error("Output already exists");
    const auto scans = read_scans(input);
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
    GridMap map; initialize_map(map, *node, input);
    std::ofstream rows(output / "events.jsonl"); rows << std::setprecision(15);
    const double origin = scans.front().stamp * 1e-9;
    const auto release = [&](std::size_t index) { return scans[index].stamp * 1e-9 - origin; };
    double ready = 0, service_sum = 0, max_age = 0, max_service = 0;
    std::size_t next = 0, skipped = 0, processed = 0, stale = 0, max_pending = 0, blackout = 0;
    const double blackouts[] = {release(60), release(120)};
    std::deque<std::size_t> pending;
    while (next < scans.size() || !pending.empty()) {
      if (pending.empty() && next < scans.size()) ready = std::max(ready, release(next));
      if (mode == "timer") ready = std::ceil((ready - 1e-10) / .05) * .05;
      if (schedule == "blackout" && blackout < 2 && ready >= blackouts[blackout]) {
        ready = std::max(ready, blackouts[blackout] + .650); ++blackout;
      }
      while (next < scans.size() && release(next) <= ready + 1e-9) pending.push_back(next++);
      if (pending.empty()) continue;
      max_pending = std::max(max_pending, pending.size());
      if (mode != "fifo") {
        while (pending.size() > 1) {
          rows << "{\"event\":\"skip\",\"scan\":" << scans[pending.front()].index
               << ",\"source_s\":" << release(pending.front()) << ",\"decision_s\":" << ready << "}\n";
          pending.pop_front(); ++skipped;
        }
      }
      const auto i = pending.front(); pending.pop_front();
      const double begin = ready;
      const double native = apply_scan(map, *node, scans[i]);
      ready += native; service_sum += native; max_service = std::max(max_service, native);
      const double age = ready - release(i);
      max_age = std::max(max_age, age); stale += age > .250; ++processed;
      rows << "{\"event\":\"complete\",\"scan\":" << scans[i].index
           << ",\"source_s\":" << release(i) << ",\"begin_s\":" << begin
           << ",\"complete_s\":" << ready << ",\"native_service_s\":" << native
           << ",\"source_age_s\":" << age << ",\"input_points\":" << scans[i].cloud->width << "}\n";
    }
    const auto &state = map.mapState();
    std::ofstream occupancy(output / "occupancy.bin", std::ios::binary);
    std::size_t occupied = 0, unknown = 0, inflated = 0;
    for (double value : state.md_.occupancy_buffer_) {
      unsigned char category = value > state.mp_.min_occupancy_log_ ? 2 :
          value < state.mp_.clamp_min_log_ ? 0 : 1;
      occupied += category == 2; unknown += category == 0;
      occupancy.write(reinterpret_cast<const char *>(&category), 1);
    }
    std::ofstream inflation(output / "inflation.bin", std::ios::binary);
    for (char value : state.md_.occupancy_buffer_inflate_) {
      unsigned char category = value != 0;
      inflated += category; inflation.write(reinterpret_cast<const char *>(&category), 1);
    }
    std::ofstream summary(output / "summary.json"); summary << std::setprecision(15);
    summary << "{\"mode\":\"" << mode << "\",\"schedule\":\"" << schedule
       << "\",\"offered\":" << scans.size() << ",\"processed\":" << processed
       << ",\"skipped\":" << skipped << ",\"max_pending\":" << max_pending
       << ",\"native_service_total_s\":" << service_sum << ",\"native_service_max_s\":" << max_service
       << ",\"completion_source_age_max_s\":" << max_age << ",\"stale_completions\":" << stale
       << ",\"virtual_end_s\":" << ready << ",\"occupied\":" << occupied
       << ",\"unknown\":" << unknown << ",\"inflated\":" << inflated
       << ",\"origin\":[" << state.mp_.map_origin_idx_.x() << ',' << state.mp_.map_origin_idx_.y() << ',' << state.mp_.map_origin_idx_.z()
       << "],\"state_sha256\":\"" << map_digest(map)
       << "\",\"claim\":\"Measured native service in discrete-event admission replay; not live DDS or physics\"}\n";
    if (processed + skipped != scans.size()) throw std::runtime_error("Unaccounted observations");
    std::cout << "V84_REPLAY_COMPLETE mode=" << mode << " schedule=" << schedule
              << " processed=" << processed << " skipped=" << skipped << " max_source_age=" << max_age << '\n';
    rclcpp::shutdown(); return 0;
  } catch (const std::exception &error) {
    std::cerr << "V84_FAILED " << error.what() << '\n';
    if (rclcpp::ok()) rclcpp::shutdown(); return 1;
  }
}
