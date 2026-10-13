// Single writer; published map states are immutable and never shared for writes.
GridMap::~GridMap() { stopAsyncMapping(); }

void GridMap::enqueueMapping(MappingInput input) {
  auto context = async_mapping_;
  {
    std::lock_guard<std::mutex> lock(context->queue_mutex);
    if (context->stopping || context->failed) return;
    context->queue.push_back(std::move(input));
  }
  context->wake.notify_one();
}

void GridMap::adoptMappingSnapshotLocked() {
  const auto latest = async_mapping_->latest;
  if (!latest || latest->revision == map_revision_) return;
  // Borrowed terrain pointers must be dropped before the old state is released.
  invalidateRawContributorCache();
  read_state_ = latest->state;
  map_revision_ = latest->revision;
}

void GridMap::adoptMappingSnapshot() {
  if (!async_mapping_) return;
  std::lock_guard<std::mutex> lock(async_mapping_->publication_mutex);
  adoptMappingSnapshotLocked();
}

std::unique_ptr<GridMap::PublicationLease> GridMap::beginPublication() {
  if (!async_mapping_) return nullptr;
  auto lease = std::make_unique<PublicationLease>(async_mapping_);
  adoptMappingSnapshotLocked();
  return lease;
}

void GridMap::stopAsyncMapping() {
  if (!async_mapping_) return;
  auto context = async_mapping_;
  context->stopping = true;
  context->wake.notify_all();
  if (context->worker.joinable()) context->worker.join();
  async_mapping_.reset();
}

void GridMap::startAsyncMapping() {
  if (async_mapping_) return;
  if (mapState().mp_.sensor_type_ != "lidar")
    throw std::invalid_argument("Asynchronous mapping requires the paired LiDAR input path");
  auto writer = std::make_unique<GridMap>();
  writer->owned_state_ = std::move(owned_state_);
  writer->node_ = node_;
  writer->reactive_body_stamp_s_ = reactive_body_stamp_s_;
  writer->reactive_body_quaternion_ = reactive_body_quaternion_;
  writer->extrinsic_pose_pub_ = extrinsic_pose_pub_;
  live_body_position_ = writer->mapState().md_.sliding_map_frame_pos_;
  auto context = std::make_shared<AsyncMapping>();
  auto initial = std::make_shared<MappingSnapshot>();
  initial->state = std::make_shared<const GridMapState>(writer->mapState());
  context->latest = initial;
  read_state_ = initial->state;
  async_mapping_ = context;
  context->worker = std::thread([context, writer = std::move(writer)]() mutable {
    std::map<int64_t, nav_msgs::msg::Odometry::ConstSharedPtr> sensor_poses;
    std::deque<MappingInput> unpaired_clouds;
    uint64_t revision = 0, clouds = 0;
    try {
      while (!context->stopping) {
        std::deque<MappingInput> received;
        {
          std::unique_lock<std::mutex> lock(context->queue_mutex);
          context->wake.wait(lock, [&] { return context->stopping || !context->queue.empty(); });
          if (context->stopping) break;
          received.swap(context->queue);
        }
        std::vector<MappingInput> inputs(received.begin(),received.end());
        // Callbacks already run in executor order; the explicit DDS drain sorts
        // before enqueueing. Preserve that order across worker batches as well.
        const auto began = std::chrono::steady_clock::now();
        bool dirty = false;
        const auto apply_cloud = [&](const MappingInput &input) {
          const auto pose = sensor_poses.find(input.stamp_ns);
          if (pose == sensor_poses.end()) return false;
          // Exact timestamp pairing prevents a newer pose transforming an old scan.
          writer->sensorPoseCallback(pose->second);
          writer->cloudCallback(input.cloud);
          ++clouds;
          dirty = true;
          return true;
        };
        for (const auto &input : inputs) {
          switch (input.kind) {
            case 0:
              sensor_poses[input.stamp_ns] = input.pose;
              {
                const auto before = writer->mapState().mp_.map_origin_idx_;
                writer->sensorPoseCallback(input.pose);
                if (before != writer->mapState().mp_.map_origin_idx_) dirty = true;
              }
              break;
            case 1:
              unpaired_clouds.push_back(input);
              break;
            case 2: {
              const auto before = writer->mapState().mp_.map_origin_idx_;
              writer->slidingMapFrameCallback(input.pose);
              if (before != writer->mapState().mp_.map_origin_idx_) dirty = true;
              break;
            }
            case 3: writer->reactiveTomogramCallback(input.cloud); dirty = true; break;
            case 4: writer->reactiveSurfaceGroundCallback(input.cloud); dirty = true; break;
            case 5: writer->reactivePhysicalFloorCallback(input.cloud); dirty = true; break;
            default: throw std::logic_error("Unknown mapping input kind");
          }
          while (!unpaired_clouds.empty() && apply_cloud(unpaired_clouds.front()))
            unpaired_clouds.pop_front();
        }
        // Do not discard incomplete pairs. A malformed stream is an explicit
        // mapper failure, so original occupancy/freshness gates reject it.
        if (unpaired_clouds.size() > 1000) throw std::runtime_error("Unpaired LiDAR input accumulation");
        while (sensor_poses.size() > 1000) {
          if (!unpaired_clouds.empty() && unpaired_clouds.front().stamp_ns <= sensor_poses.begin()->first)
            throw std::runtime_error("Unpaired LiDAR pose history exhausted");
          sensor_poses.erase(sensor_poses.begin());
        }
        if (!dirty) continue;
        const auto mapped = std::chrono::steady_clock::now();
        auto snapshot = std::make_shared<MappingSnapshot>();
        snapshot->state = std::make_shared<const GridMapState>(writer->mapState());
        snapshot->revision = ++revision;
        snapshot->applied_clouds = clouds;
        snapshot->mapping_ms = std::chrono::duration<double,std::milli>(mapped-began).count();
        snapshot->copy_ms = std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-mapped).count();
        {
          std::lock_guard<std::mutex> lock(context->publication_mutex);
          // Reclaim large arrays/terrain tables on the mapper, never on a
          // planner callback that releases its previous snapshot.
          context->retired.push_back(context->latest->state);
          context->latest = snapshot;
        }
        for (auto it = context->retired.begin(); it != context->retired.end();) {
          if (it->use_count() == 1) it = context->retired.erase(it);
          else ++it;
        }
        RCLCPP_INFO(writer->node_->get_logger(),
          "V81_MAP_SNAPSHOT revision=%lu clouds=%lu cloud_stamp=%.9f mapping_ms=%.3f copy_ms=%.3f",
          snapshot->revision,clouds,snapshot->state->reactive_cloud_stamp_s_,snapshot->mapping_ms,snapshot->copy_ms);
      }
    } catch (const std::exception &error) {
      // The previous completed state stays intact. No half-applied map is exposed.
      context->failed = true;
      std::lock_guard<std::mutex> lock(context->queue_mutex);
      context->error = error.what();
      RCLCPP_ERROR(writer->node_->get_logger(),"V81_MAP_WORKER_FAILED %s",error.what());
    }
  });
}
