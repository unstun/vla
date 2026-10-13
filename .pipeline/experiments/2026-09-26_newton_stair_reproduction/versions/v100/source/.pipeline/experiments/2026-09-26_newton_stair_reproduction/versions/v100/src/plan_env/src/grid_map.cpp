#include "plan_env/grid_map.h"
#include <cmath>
#include <limits>
#include <string>
#include <geometry_msgs/msg/transform_stamped.hpp>

namespace
{
template <typename T>
void load_parameter(rclcpp::Node *node, const std::string &name, T &value, const T &default_value)
{
  if (!node->has_parameter(name))
    node->declare_parameter<T>(name, default_value);
  node->get_parameter(name, value);
}
}  // namespace

void GridMap::initMap(rclcpp::Node *node, rclcpp::CallbackGroup::SharedPtr callback_group)
{
  invalidateRawContributorCache();
  node_ = node;

  /* get parameter */
  double x_size, y_size, z_size;
  load_parameter(node_, "grid_map.resolution", mutableMapState().mp_.resolution_, -1.0);
  load_parameter(node_, "grid_map.sliding_map_size_x", x_size, -1.0);
  load_parameter(node_, "grid_map.sliding_map_size_y", y_size, -1.0);
  load_parameter(node_, "grid_map.sliding_map_size_z", z_size, -1.0);
  load_parameter(node_, "grid_map.local_update_range_x", mutableMapState().mp_.local_update_range_(0), x_size / 2.0);
  load_parameter(node_, "grid_map.local_update_range_y", mutableMapState().mp_.local_update_range_(1), y_size / 2.0);
  load_parameter(node_, "grid_map.local_update_range_z", mutableMapState().mp_.local_update_range_(2), z_size / 2.0);
  
  load_parameter(node_, "grid_map.obstacles_inflation_z_up", mutableMapState().mp_.obstacles_inflation_z_up, -1.0);
  load_parameter(node_, "grid_map.obstacles_inflation_z_down", mutableMapState().mp_.obstacles_inflation_z_down, -1.0);
  load_parameter(node_, "grid_map.double_cylinder_radius", mutableMapState().mp_.double_cylinder_radius_, -1.0);
  load_parameter(node_, "grid_map.double_cylinder_offset", mutableMapState().mp_.double_cylinder_offset_, 0.0);
  load_parameter(node_, "grid_map.map_sliding_en", mutableMapState().mp_.map_sliding_en_, true);
  load_parameter(node_, "grid_map.map_sliding_thresh", mutableMapState().mp_.map_sliding_thresh_, mutableMapState().mp_.resolution_);

  load_parameter(node_, "grid_map.fx", mutableMapState().mp_.fx_, -1.0);
  load_parameter(node_, "grid_map.fy", mutableMapState().mp_.fy_, -1.0);
  load_parameter(node_, "grid_map.cx", mutableMapState().mp_.cx_, -1.0);
  load_parameter(node_, "grid_map.cy", mutableMapState().mp_.cy_, -1.0);

  load_parameter(node_, "grid_map.depth_filter_maxdist", mutableMapState().mp_.depth_filter_maxdist_, -1.0);
  load_parameter(node_, "grid_map.depth_filter_mindist", mutableMapState().mp_.depth_filter_mindist_, -1.0);
  load_parameter(node_, "grid_map.depth_filter_margin", mutableMapState().mp_.depth_filter_margin_, -1);
  load_parameter(node_, "grid_map.k_depth_scaling_factor", mutableMapState().mp_.k_depth_scaling_factor_, -1.0);
  load_parameter(node_, "grid_map.skip_pixel", mutableMapState().mp_.skip_pixel_, -1);

  load_parameter(node_, "grid_map.p_hit", mutableMapState().mp_.p_hit_, -1.0);
  load_parameter(node_, "grid_map.p_miss", mutableMapState().mp_.p_miss_, -1.0);
  load_parameter(node_, "grid_map.p_min", mutableMapState().mp_.p_min_, -1.0);
  load_parameter(node_, "grid_map.p_max", mutableMapState().mp_.p_max_, -1.0);
  load_parameter(node_, "grid_map.p_occ", mutableMapState().mp_.p_occ_, -1.0);
  load_parameter(node_, "grid_map.max_ray_length", mutableMapState().mp_.max_ray_length_, -0.1);

  load_parameter(node_, "grid_map.vis_height", mutableMapState().mp_.vis_height_, 0.3);
  load_parameter(node_, "grid_map.show_occ_time", mutableMapState().mp_.show_occ_time_, false);

  load_parameter(node_, "grid_map.frame_id", mutableMapState().mp_.frame_id_, string("world"));
  load_parameter(node_, "grid_map.sliding_map_frame_id", mutableMapState().mp_.sliding_map_frame_id_, string("sliding_map"));
  load_parameter(node_, "grid_map.ground_height", mutableMapState().mp_.ground_height_, 0.0);

  load_parameter(node_, "grid_map.sensor_type", mutableMapState().mp_.sensor_type_, string("lidar"));
  load_parameter(node_, "grid_map.cloud_is_world", mutableMapState().mp_.cloud_is_world_, true);
  load_parameter(node_, "grid_map.reactive_tomogram_resolution", mutableMapState().reactive_tomogram_resolution_m_, 0.1);
  load_parameter(node_, "grid_map.reactive_tomogram_z_offset", mutableMapState().reactive_tomogram_z_offset_m_, 0.03);
  load_parameter(node_, "grid_map.reactive_terrain_band", mutableMapState().reactive_terrain_band_m_, 0.05);
  load_parameter(node_, "grid_map.reactive_cost_limit", mutableMapState().reactive_cost_limit_, 20.0);
  load_parameter(node_, "grid_map.reactive_surface_ground_topic", mutableMapState().reactive_surface_ground_topic_, string(""));
  load_parameter(node_, "grid_map.reactive_physical_floor_topic", mutableMapState().reactive_physical_floor_topic_, string(""));
  load_parameter(node_, "grid_map.physical_floor_source_id", mutableMapState().physical_floor_source_id_, string(""));
  load_parameter(node_, "grid_map.physical_floor_surface_source_id", mutableMapState().physical_floor_surface_source_id_, string(""));
  load_parameter(node_, "grid_map.physical_floor_navigation_source_id", mutableMapState().physical_floor_navigation_source_id_, string(""));
  load_parameter(node_, "grid_map.physical_floor_origin_x", mutableMapState().physical_floor_origin_x_m_, 0.0);
  load_parameter(node_, "grid_map.physical_floor_origin_y", mutableMapState().physical_floor_origin_y_m_, 0.0);
  load_parameter(node_, "grid_map.physical_floor_resolution", mutableMapState().physical_floor_resolution_m_, 0.1);
  if (!mutableMapState().reactive_physical_floor_topic_.empty() && (mutableMapState().physical_floor_source_id_.empty() ||
      mutableMapState().physical_floor_surface_source_id_.empty() || mutableMapState().physical_floor_navigation_source_id_.empty() ||
      !std::isfinite(mutableMapState().physical_floor_origin_x_m_) || !std::isfinite(mutableMapState().physical_floor_origin_y_m_) ||
      !std::isfinite(mutableMapState().physical_floor_resolution_m_) || mutableMapState().physical_floor_resolution_m_ != mutableMapState().reactive_tomogram_resolution_m_))
    throw std::runtime_error("Configured physical floor requires pinned source and grid metadata");
  load_parameter(node_, "grid_map.reactive_cloud_max_age", mutableSupportState().reactive_parameters_.obstacle_max_age_s, 0.25);
  load_parameter(node_, "grid_map.reactive_tomogram_max_age", mutableSupportState().reactive_parameters_.terrain_max_age_s, 86400.0);
  load_parameter(node_, "grid_map.reactive_body_clearance", mutableSupportState().reactive_parameters_.body_clearance_m, 0.35);
  load_parameter(node_, "grid_map.reactive_known_lite3_trunk", mutableMapState().reactive_known_trunk_enabled_, false);
  mutableSupportState().reactive_parameters_.robot_radius_m = mutableMapState().mp_.double_cylinder_radius_;
  mutableSupportState().reactive_decision_ = reactive_stair::CollisionDecision(mutableSupportState().reactive_parameters_);
  load_parameter(node_, "grid_map.need_extrinsic", mutableMapState().mp_.need_extrinsic_, true);

  mutableMapState().mp_.lidar_extrinsic_ <<
      1.0, 0.0, 0.0, -0.01100,
      0.0, 1.0, 0.0, -0.02329,
      0.0, 0.0, 1.0,  0.04412,
      0.0, 0.0, 0.0,  1.00000;

  mutableMapState().mp_.depth_extrinsic_ <<
      0.0,  0.707107, 0.707107, -0.15170,
     -1.0,  0.000000, 0.000000,  0.00000,
      0.0, -0.707107, 0.707107,  0.07510,
      0.0,  0.000000, 0.000000,  1.00000;
      
  if (mutableMapState().mp_.sensor_type_ != "lidar" && mutableMapState().mp_.sensor_type_ != "depth")
  {
    RCLCPP_ERROR(node_->get_logger(), "[GridMap] invalid grid_map.sensor_type: %s; falling back to lidar",
                 mutableMapState().mp_.sensor_type_.c_str());
    mutableMapState().mp_.sensor_type_ = "lidar";
  }

  mutableMapState().mp_.resolution_inv_ = 1 / mutableMapState().mp_.resolution_;
  mutableMapState().mp_.map_origin_ = Eigen::Vector3d(-x_size / 2.0, -y_size / 2.0, mutableMapState().mp_.ground_height_);
  mutableMapState().mp_.map_size_ = Eigen::Vector3d(x_size, y_size, z_size);

  mutableMapState().mp_.prob_hit_log_ = logit(mutableMapState().mp_.p_hit_);
  mutableMapState().mp_.prob_miss_log_ = logit(mutableMapState().mp_.p_miss_);
  mutableMapState().mp_.clamp_min_log_ = logit(mutableMapState().mp_.p_min_);
  mutableMapState().mp_.clamp_max_log_ = logit(mutableMapState().mp_.p_max_);
  mutableMapState().mp_.min_occupancy_log_ = logit(mutableMapState().mp_.p_occ_);
  mutableMapState().mp_.unknown_flag_ = 0.01;
  mutableMapState().mp_.map_sliding_thresh_vox_ = std::max(1, static_cast<int>(std::ceil(mutableMapState().mp_.map_sliding_thresh_ * mutableMapState().mp_.resolution_inv_)));

  cout << "hit: " << mutableMapState().mp_.prob_hit_log_ << endl;
  cout << "miss: " << mutableMapState().mp_.prob_miss_log_ << endl;
  cout << "min log: " << mutableMapState().mp_.clamp_min_log_ << endl;
  cout << "max: " << mutableMapState().mp_.clamp_max_log_ << endl;
  cout << "thresh log: " << mutableMapState().mp_.min_occupancy_log_ << endl;

  for (int i = 0; i < 3; ++i)
    mutableMapState().mp_.map_voxel_num_(i) = ceil(mutableMapState().mp_.map_size_(i) / mutableMapState().mp_.resolution_);

  mutableMapState().mp_.map_min_boundary_ = mutableMapState().mp_.map_origin_;
  mutableMapState().mp_.map_max_boundary_ = mutableMapState().mp_.map_origin_ + mutableMapState().mp_.map_size_;
  posToIndex(mutableMapState().mp_.map_origin_, mutableMapState().mp_.map_bound_min_idx_);
  mutableMapState().mp_.map_bound_max_idx_ = mutableMapState().mp_.map_bound_min_idx_ + mutableMapState().mp_.map_voxel_num_ - Eigen::Vector3i::Ones();
  mutableMapState().mp_.map_origin_idx_ = mutableMapState().mp_.map_bound_min_idx_ + mutableMapState().mp_.map_voxel_num_ / 2;
  updateMapBoundaryFromIndex();

  // initialize data buffers

  int buffer_size = mutableMapState().mp_.map_voxel_num_(0) * mutableMapState().mp_.map_voxel_num_(1) * mutableMapState().mp_.map_voxel_num_(2);

  mutableMapState().md_.occupancy_buffer_ = vector<double>(buffer_size, mutableMapState().mp_.clamp_min_log_ - mutableMapState().mp_.unknown_flag_);
  mutableMapState().md_.occupancy_buffer_inflate_ = vector<char>(buffer_size, 0);
  mutableMapState().md_.occupancy_buffer_inflate_cnt_ = vector<int>(buffer_size, 0);
  rebuildInflationOffsets();

  mutableMapState().md_.count_hit_and_miss_ = vector<short>(buffer_size, 0);
  mutableMapState().md_.count_hit_ = vector<short>(buffer_size, 0);
  mutableMapState().md_.flag_rayend_ = vector<char>(buffer_size, -1);
  mutableMapState().md_.flag_traverse_ = vector<char>(buffer_size, -1);

  mutableMapState().md_.raycast_num_ = 0;

  mutableMapState().md_.proj_points_.resize(640 * 480 / mutableMapState().mp_.skip_pixel_ / mutableMapState().mp_.skip_pixel_);
  mutableMapState().md_.proj_points_cnt = 0;

  /* init callback */
  rclcpp::SubscriptionOptions subscription_options;
  subscription_options.callback_group = callback_group;
  tf_broadcaster_ = std::make_shared<tf2_ros::TransformBroadcaster>(*node_);

  if (mutableMapState().mp_.sensor_type_ == "depth")
  {
    // Foxy's message_filters::Subscriber has no callback-group overload.
    // The plugin retains the original executor for this unmodified input mode.
    if (callback_group) throw std::runtime_error("Isolated Foxy clock requires lidar input callbacks");
    depth_sub_ = std::make_shared<message_filters::Subscriber<sensor_msgs::msg::Image>>();
    depth_pose_sub_ = std::make_shared<message_filters::Subscriber<nav_msgs::msg::Odometry>>();
    depth_sub_->subscribe(node_, "depth", rmw_qos_profile_sensor_data);
    depth_pose_sub_->subscribe(node_, "sensor_pose", rmw_qos_profile_sensor_data);

    sync_image_pose_.reset(new message_filters::Synchronizer<SyncPolicyImagePose>(
        SyncPolicyImagePose(100), *depth_sub_, *depth_pose_sub_));
    sync_image_pose_->registerCallback(
        std::bind(&GridMap::depthPoseCallback, this, std::placeholders::_1, std::placeholders::_2));
  }
  else if (mutableMapState().mp_.sensor_type_ == "lidar")
  {
    lidar_pose_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
        "sensor_pose", rclcpp::SensorDataQoS(),
        std::bind(&GridMap::sensorPoseCallback, this, std::placeholders::_1), subscription_options);
    cloud_sub_ = node_->create_subscription<sensor_msgs::msg::PointCloud2>(
        "cloud", rclcpp::SensorDataQoS(),
        std::bind(&GridMap::cloudCallback, this, std::placeholders::_1), subscription_options);
  }

  sliding_map_frame_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
      "body_pose", rclcpp::SensorDataQoS(),
      std::bind(&GridMap::slidingMapFrameCallback, this, std::placeholders::_1), subscription_options);

  reactive_tomogram_sub_ = node_->create_subscription<sensor_msgs::msg::PointCloud2>(
      "/pct_tomogram", rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local(),
      std::bind(&GridMap::reactiveTomogramCallback, this, std::placeholders::_1), subscription_options);
  if (!mutableMapState().reactive_surface_ground_topic_.empty())
    reactive_surface_ground_sub_ = node_->create_subscription<sensor_msgs::msg::PointCloud2>(
        mutableMapState().reactive_surface_ground_topic_, rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local(),
        std::bind(&GridMap::reactiveSurfaceGroundCallback, this, std::placeholders::_1), subscription_options);
  if (!mutableMapState().reactive_physical_floor_topic_.empty())
    reactive_physical_floor_sub_ = node_->create_subscription<sensor_msgs::msg::PointCloud2>(
        mutableMapState().reactive_physical_floor_topic_, rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local(),
        std::bind(&GridMap::reactivePhysicalFloorCallback, this, std::placeholders::_1), subscription_options);

  occ_timer_ = node_->create_wall_timer(std::chrono::milliseconds(50),
                                        std::bind(&GridMap::updateOccupancyCallback, this), callback_group);
  vis_timer_ = node_->create_wall_timer(std::chrono::milliseconds(50),
                                        std::bind(&GridMap::visCallback, this), callback_group);

  map_pub_ = node_->create_publisher<sensor_msgs::msg::PointCloud2>("grid_map/occupancy", rclcpp::SensorDataQoS());
  map_inf_pub_ = node_->create_publisher<sensor_msgs::msg::PointCloud2>("grid_map/occupancy_inflate", rclcpp::SensorDataQoS());
  sliding_map_bbox_pub_ = node_->create_publisher<visualization_msgs::msg::Marker>("grid_map/sliding_map_bbox", 10);

  unknown_pub_ = node_->create_publisher<sensor_msgs::msg::PointCloud2>("grid_map/unknown", rclcpp::SensorDataQoS());
  depth_cloud_pub_ = node_->create_publisher<sensor_msgs::msg::PointCloud2>("grid_map/depth_cloud", rclcpp::SensorDataQoS());
  extrinsic_pose_pub_ = node_->create_publisher<nav_msgs::msg::Odometry>("grid_map/sensor_pose_extrinsic", 10);

  mutableMapState().md_.occ_need_update_ = false;
  mutableMapState().md_.use_cloud_update_ = false;
  mutableMapState().md_.has_first_depth_ = false;
  mutableMapState().md_.has_ray_pose_ = false;
  mutableMapState().md_.has_cloud_ = false;
  mutableMapState().md_.image_cnt_ = 0;
  mutableMapState().md_.ray_pos_.setZero();
  mutableMapState().md_.sliding_map_frame_pos_.setZero();
  mutableMapState().md_.ray_q_ = Eigen::Quaterniond::Identity();

  mutableMapState().md_.fuse_time_ = 0.0;
  mutableMapState().md_.update_num_ = 0;
  mutableMapState().md_.max_fuse_time_ = 0.0;
  mutableMapState().md_.local_bound_min_ = mutableMapState().mp_.map_bound_min_idx_;
  mutableMapState().md_.local_bound_max_ = mutableMapState().mp_.map_bound_max_idx_;

  // rand_noise_ = uniform_real_distribution<double>(-0.2, 0.2);
  // rand_noise2_ = normal_distribution<double>(0, 0.2);
  // random_device rd;
  // eng_ = default_random_engine(rd());

  bool asynchronous_mapping = false;
  load_parameter(node_, "grid_map.asynchronous_mapping", asynchronous_mapping, false);
  if (asynchronous_mapping) startAsyncMapping();
}

void GridMap::updateMapBoundaryFromIndex()
{
  invalidateRawContributorCache();
  mutableMapState().mp_.map_bound_min_idx_ = mutableMapState().mp_.map_origin_idx_ - mutableMapState().mp_.map_voxel_num_ / 2;
  mutableMapState().mp_.map_bound_max_idx_ = mutableMapState().mp_.map_bound_min_idx_ + mutableMapState().mp_.map_voxel_num_ - Eigen::Vector3i::Ones();

  mutableMapState().mp_.map_min_boundary_ = mutableMapState().mp_.map_bound_min_idx_.cast<double>() * mutableMapState().mp_.resolution_;
  mutableMapState().mp_.map_max_boundary_ = (mutableMapState().mp_.map_bound_max_idx_.cast<double>() + Eigen::Vector3d::Ones()) * mutableMapState().mp_.resolution_;
  mutableMapState().mp_.map_origin_ = mutableMapState().mp_.map_min_boundary_;
}

void GridMap::rebuildInflationOffsets()
{
  invalidateRawContributorCache();
  const double double_radius = std::max(0.0, mutableMapState().mp_.double_cylinder_radius_);
  const int inf_step_xy = ceil(double_radius / mutableMapState().mp_.resolution_);
  const int inf_step_z_up = ceil(mutableMapState().mp_.obstacles_inflation_z_up / mutableMapState().mp_.resolution_);
  const int inf_step_z_down = ceil(mutableMapState().mp_.obstacles_inflation_z_down / mutableMapState().mp_.resolution_);

  mutableMapState().md_.inflate_offsets_.clear();
  for (int x = -inf_step_xy; x <= inf_step_xy; ++x)
    for (int y = -inf_step_xy; y <= inf_step_xy; ++y)
    {
      Eigen::Vector2d offset_xy(x * mutableMapState().mp_.resolution_, y * mutableMapState().mp_.resolution_);
      if (offset_xy.norm() >= double_radius)
        continue;

      for (int z = -inf_step_z_down; z <= inf_step_z_up; ++z)
        mutableMapState().md_.inflate_offsets_.push_back(Eigen::Vector3i(x, y, z));
    }
}

void GridMap::resetAllMapData()
{
  invalidateRawContributorCache();
  mutableMapState().reactive_terrain_hits_.clear();
  mutableMapState().reactive_nonterrain_hits_.clear();
  mutableMapState().reactive_nonterrain_history_.clear();
  mutableMapState().reactive_cloud_ready_ = false;
  mutableMapState().reactive_pending_cloud_ = false;
  std::fill(mutableMapState().md_.occupancy_buffer_.begin(), mutableMapState().md_.occupancy_buffer_.end(), mutableMapState().mp_.clamp_min_log_ - mutableMapState().mp_.unknown_flag_);
  std::fill(mutableMapState().md_.occupancy_buffer_inflate_.begin(), mutableMapState().md_.occupancy_buffer_inflate_.end(), 0);
  std::fill(mutableMapState().md_.occupancy_buffer_inflate_cnt_.begin(), mutableMapState().md_.occupancy_buffer_inflate_cnt_.end(), 0);
  std::fill(mutableMapState().md_.count_hit_and_miss_.begin(), mutableMapState().md_.count_hit_and_miss_.end(), 0);
  std::fill(mutableMapState().md_.count_hit_.begin(), mutableMapState().md_.count_hit_.end(), 0);
  std::fill(mutableMapState().md_.flag_rayend_.begin(), mutableMapState().md_.flag_rayend_.end(), -1);
  std::fill(mutableMapState().md_.flag_traverse_.begin(), mutableMapState().md_.flag_traverse_.end(), -1);
  std::queue<Eigen::Vector3i> empty;
  std::swap(mutableMapState().md_.cache_voxel_, empty);
}

void GridMap::hashIdToGlobalIndex(int addr, Eigen::Vector3i& id_g) const
{
  Eigen::Vector3i id_l;
  id_l(0) = addr / (mapState().mp_.map_voxel_num_(1) * mapState().mp_.map_voxel_num_(2));
  id_l(1) = (addr - id_l(0) * mapState().mp_.map_voxel_num_(1) * mapState().mp_.map_voxel_num_(2)) / mapState().mp_.map_voxel_num_(2);
  id_l(2) = addr - id_l(0) * mapState().mp_.map_voxel_num_(1) * mapState().mp_.map_voxel_num_(2) -
            id_l(1) * mapState().mp_.map_voxel_num_(2);

  for (int i = 0; i < 3; ++i)
  {
    const int min_l = getLocalIndex(mapState().mp_.map_bound_min_idx_(i), i);
    int dist = id_l(i) - min_l;
    if (dist < 0)
      dist += mapState().mp_.map_voxel_num_(i);
    id_g(i) = mapState().mp_.map_bound_min_idx_(i) + dist;
  }
}

void GridMap::updateInflationLayer(const Eigen::Vector3i& id, int delta,
                                   const vector<Eigen::Vector3i>& offsets,
                                   std::vector<int>& cnt_buffer,
                                   std::vector<char>& flag_buffer,
                                   const std::vector<char>* ignore_mask)
{
  invalidateRawContributorCache();
  // The unchanged offset sequence is grouped only by x/y. Clip against the
  // same global bounds and advance the ring-buffer z address without a modulo
  // for every neighbor. Counts, ignore masks and offset ordering are preserved.
  std::size_t first = 0;
  const int ny = mutableMapState().mp_.map_voxel_num_.y(), nz = mutableMapState().mp_.map_voxel_num_.z();
  while (first < offsets.size()) {
    std::size_t last = first + 1;
    while (last < offsets.size() && offsets[last].x() == offsets[first].x() &&
           offsets[last].y() == offsets[first].y()) ++last;
    const int x = id.x() + offsets[first].x(), y = id.y() + offsets[first].y();
    if (x >= mutableMapState().mp_.map_bound_min_idx_.x() && x <= mutableMapState().mp_.map_bound_max_idx_.x() &&
        y >= mutableMapState().mp_.map_bound_min_idx_.y() && y <= mutableMapState().mp_.map_bound_max_idx_.y()) {
      const int base = (getLocalIndex(x, 0) * ny + getLocalIndex(y, 1)) * nz;
      int previous_z = 0, local_z = 0;
      bool have_z = false;
      for (std::size_t i = first; i < last; ++i) {
        const int z = id.z() + offsets[i].z();
        if (z < mutableMapState().mp_.map_bound_min_idx_.z() || z > mutableMapState().mp_.map_bound_max_idx_.z()) continue;
        if (have_z && z == previous_z + 1) {
          if (++local_z == nz) local_z = 0;
        } else local_z = getLocalIndex(z, 2);
        have_z = true;
        previous_z = z;
        const int addr = base + local_z;
        if (ignore_mask && (*ignore_mask)[addr]) continue;
        cnt_buffer[addr] = std::max(0, cnt_buffer[addr] + delta);
        flag_buffer[addr] = cnt_buffer[addr] > 0 ? 1 : 0;
      }
    }
    first = last;
  }
}

void GridMap::updateInflation(const Eigen::Vector3i& id, int delta, const std::vector<char>* ignore_mask)
{
  updateInflationLayer(id, delta, mutableMapState().md_.inflate_offsets_, mutableMapState().md_.occupancy_buffer_inflate_cnt_,
                       mutableMapState().md_.occupancy_buffer_inflate_, ignore_mask);
}

void GridMap::applyOccupancyUpdate(const Eigen::Vector3i& id, double new_log_odds)
{
  invalidateRawContributorCache();
  if (!isInMap(id))
    return;

  const int addr = toAddress(id);
  const bool was_occ = mutableMapState().md_.occupancy_buffer_[addr] > mutableMapState().mp_.min_occupancy_log_;
  const bool now_occ = new_log_odds > mutableMapState().mp_.min_occupancy_log_;

  mutableMapState().md_.occupancy_buffer_[addr] = new_log_odds;
  if (!now_occ) {
    const auto key = std::make_tuple(id.x(), id.y(), id.z());
    mutableMapState().reactive_nonterrain_history_.erase(key);
    mutableMapState().reactive_terrain_hits_.erase(key);
  }
  if (was_occ != now_occ)
    updateInflation(id, now_occ ? 1 : -1);
}

void GridMap::resetCellByAddress(int addr)
{
  invalidateRawContributorCache();
  Eigen::Vector3i id_g;
  hashIdToGlobalIndex(addr, id_g);
  const auto key = std::make_tuple(id_g.x(), id_g.y(), id_g.z());
  mutableMapState().reactive_terrain_hits_.erase(key);
  mutableMapState().reactive_nonterrain_hits_.erase(key);
  mutableMapState().reactive_nonterrain_history_.erase(key);
  if (mutableMapState().md_.occupancy_buffer_[addr] > mutableMapState().mp_.min_occupancy_log_)
    updateInflation(id_g, -1);

  mutableMapState().md_.occupancy_buffer_[addr] = mutableMapState().mp_.clamp_min_log_ - mutableMapState().mp_.unknown_flag_;
  mutableMapState().md_.count_hit_[addr] = 0;
  mutableMapState().md_.count_hit_and_miss_[addr] = 0;
  mutableMapState().md_.flag_rayend_[addr] = -1;
  mutableMapState().md_.flag_traverse_[addr] = -1;
}

void GridMap::resetCellByAddressForSliding(int addr, const std::vector<char>& clear_mask)
{
  invalidateRawContributorCache();
  Eigen::Vector3i id_g;
  hashIdToGlobalIndex(addr, id_g);
  const auto key = std::make_tuple(id_g.x(), id_g.y(), id_g.z());
  mutableMapState().reactive_terrain_hits_.erase(key);
  mutableMapState().reactive_nonterrain_hits_.erase(key);
  mutableMapState().reactive_nonterrain_history_.erase(key);
  if (mutableMapState().md_.occupancy_buffer_[addr] > mutableMapState().mp_.min_occupancy_log_)
    updateInflation(id_g, -1, &clear_mask);
}

void GridMap::updateSlidingMap(const Eigen::Vector3d& center)
{
  reactive_stair::PlanningProfile::Scope profile(planning_profile_, reactive_stair::PlanningProfile::SlidingMap);
  invalidateRawContributorCache();
  if (!mutableMapState().mp_.map_sliding_en_)
    return;

  Eigen::Vector3i new_origin_idx;
  posToIndex(center, new_origin_idx);
  const Eigen::Vector3i shift_num = new_origin_idx - mutableMapState().mp_.map_origin_idx_;
  if (shift_num.cwiseAbs().maxCoeff() < mutableMapState().mp_.map_sliding_thresh_vox_)
    return;

  if ((shift_num.cwiseAbs().array() >= mutableMapState().mp_.map_voxel_num_.array()).any())
  {
    resetAllMapData();
    mutableMapState().mp_.map_origin_idx_ = new_origin_idx;
    updateMapBoundaryFromIndex();
    mutableMapState().md_.local_bound_min_ = mutableMapState().mp_.map_bound_min_idx_;
    mutableMapState().md_.local_bound_max_ = mutableMapState().mp_.map_bound_max_idx_;
    return;
  }

  const int buffer_size = mutableMapState().mp_.map_voxel_num_(0) * mutableMapState().mp_.map_voxel_num_(1) * mutableMapState().mp_.map_voxel_num_(2);
  std::vector<char> clear_mask(buffer_size, 0);
  std::vector<int> clear_addrs;
  clear_addrs.reserve(buffer_size / 8);

  auto add_clear_addr = [&](const Eigen::Vector3i& id_l) {
    const int addr = toAddressLocal(id_l);
    if (!clear_mask[addr])
    {
      clear_mask[addr] = 1;
      clear_addrs.push_back(addr);
    }
  };

  for (int dim = 0; dim < 3; ++dim)
  {
    const int shift = shift_num(dim);
    if (shift == 0)
      continue;

    if (shift > 0)
    {
      for (int k = 0; k < shift; ++k)
      {
        const int clear_g = mutableMapState().mp_.map_bound_min_idx_(dim) + k;
        const int clear_l = getLocalIndex(clear_g, dim);

        for (int a = 0; a < mutableMapState().mp_.map_voxel_num_((dim + 1) % 3); ++a)
          for (int b = 0; b < mutableMapState().mp_.map_voxel_num_((dim + 2) % 3); ++b)
          {
            Eigen::Vector3i id_l;
            id_l(dim) = clear_l;
            id_l((dim + 1) % 3) = a;
            id_l((dim + 2) % 3) = b;
            add_clear_addr(id_l);
          }
      }
    }
    else
    {
      for (int k = 0; k < -shift; ++k)
      {
        const int clear_g = mutableMapState().mp_.map_bound_max_idx_(dim) - k;
        const int clear_l = getLocalIndex(clear_g, dim);

        for (int a = 0; a < mutableMapState().mp_.map_voxel_num_((dim + 1) % 3); ++a)
          for (int b = 0; b < mutableMapState().mp_.map_voxel_num_((dim + 2) % 3); ++b)
          {
            Eigen::Vector3i id_l;
            id_l(dim) = clear_l;
            id_l((dim + 1) % 3) = a;
            id_l((dim + 2) % 3) = b;
            add_clear_addr(id_l);
          }
      }
    }
  }

  for (int addr : clear_addrs)
    resetCellByAddressForSliding(addr, clear_mask);

  for (int addr : clear_addrs)
  {
    mutableMapState().md_.occupancy_buffer_[addr] = mutableMapState().mp_.clamp_min_log_ - mutableMapState().mp_.unknown_flag_;
    mutableMapState().md_.occupancy_buffer_inflate_cnt_[addr] = 0;
    mutableMapState().md_.occupancy_buffer_inflate_[addr] = 0;
    mutableMapState().md_.count_hit_[addr] = 0;
    mutableMapState().md_.count_hit_and_miss_[addr] = 0;
    mutableMapState().md_.flag_rayend_[addr] = -1;
    mutableMapState().md_.flag_traverse_[addr] = -1;
  }

  mutableMapState().mp_.map_origin_idx_ = new_origin_idx;
  updateMapBoundaryFromIndex();
  boundIndex(mutableMapState().md_.local_bound_min_);
  boundIndex(mutableMapState().md_.local_bound_max_);
}

void GridMap::resetBuffer()
{
  resetAllMapData();
  mutableMapState().md_.local_bound_min_ = mutableMapState().mp_.map_bound_min_idx_;
  mutableMapState().md_.local_bound_max_ = mutableMapState().mp_.map_bound_max_idx_;
}

void GridMap::resetBuffer(Eigen::Vector3d min_pos, Eigen::Vector3d max_pos)
{
  Eigen::Vector3i min_id, max_id;
  posToIndex(min_pos, min_id);
  posToIndex(max_pos, max_id);

  boundIndex(min_id);
  boundIndex(max_id);

  for (int x = min_id(0); x <= max_id(0); ++x)
    for (int y = min_id(1); y <= max_id(1); ++y)
    {
      for (int z = min_id(2); z <= max_id(2); ++z)
      {
        resetCellByAddress(toAddress(x, y, z));
      }
    }
}

int GridMap::setCacheOccupancy(Eigen::Vector3d pos, int occ)
{
  if (occ != 1 && occ != 0)
    return INVALID_IDX;

  Eigen::Vector3i id;
  posToIndex(pos, id);
  if (!isInMap(id))
    return INVALID_IDX;

  int idx_ctns = toAddress(id);

  mutableMapState().md_.count_hit_and_miss_[idx_ctns] += 1;

  if (mutableMapState().md_.count_hit_and_miss_[idx_ctns] == 1)
  {
    mutableMapState().md_.cache_voxel_.push(id);
  }

  if (occ == 1)
    mutableMapState().md_.count_hit_[idx_ctns] += 1;

  return idx_ctns;
}

void GridMap::projectDepthImage()
{
  // mutableMapState().md_.proj_points_.clear();
  mutableMapState().md_.proj_points_cnt = 0;

  uint16_t *row_ptr;
  // int cols = current_img_.cols, rows = current_img_.rows;
  int cols = mutableMapState().md_.depth_image_.cols;
  int rows = mutableMapState().md_.depth_image_.rows;

  double depth;

  Eigen::Matrix3d sensor_r = mutableMapState().md_.ray_q_.toRotationMatrix();

  // cout << "rotate: " << mutableMapState().md_.ray_q_.toRotationMatrix() << endl;
  // std::cout << "pos in proj: " << mutableMapState().md_.ray_pos_ << std::endl;

  if (!mutableMapState().md_.has_first_depth_)
  {
    mutableMapState().md_.has_first_depth_ = true;
    return;
  }

  Eigen::Vector3d pt_cur, pt_world;
  const double inv_factor = 1.0 / mutableMapState().mp_.k_depth_scaling_factor_;

  for (int v = mutableMapState().mp_.depth_filter_margin_; v < rows - mutableMapState().mp_.depth_filter_margin_; v += mutableMapState().mp_.skip_pixel_)
  {
    row_ptr = mutableMapState().md_.depth_image_.ptr<uint16_t>(v) + mutableMapState().mp_.depth_filter_margin_;

    for (int u = mutableMapState().mp_.depth_filter_margin_; u < cols - mutableMapState().mp_.depth_filter_margin_; u += mutableMapState().mp_.skip_pixel_)
    {
      const uint16_t raw_depth = *row_ptr;
      depth = raw_depth * inv_factor;
      row_ptr = row_ptr + mutableMapState().mp_.skip_pixel_;

      // filter depth
      // depth += rand_noise_(eng_);
      // if (depth > 0.01) depth += rand_noise2_(eng_);

      if (raw_depth == 0)
      {
        depth = mutableMapState().mp_.max_ray_length_ + 0.1;
      }
      else if (depth < mutableMapState().mp_.depth_filter_mindist_)
      {
        continue;
      }
      else if (depth > mutableMapState().mp_.depth_filter_maxdist_)
      {
        depth = mutableMapState().mp_.max_ray_length_ + 0.1;
      }

      // project to world frame
      pt_cur(0) = (u - mutableMapState().mp_.cx_) * depth / mutableMapState().mp_.fx_;
      pt_cur(1) = (v - mutableMapState().mp_.cy_) * depth / mutableMapState().mp_.fy_;
      pt_cur(2) = depth;

      pt_world = sensor_r * pt_cur + mutableMapState().md_.ray_pos_;
      // if (!isInMap(pt_world)) {
      //   pt_world = closetPointInMap(pt_world, mutableMapState().md_.ray_pos_);
      // }

      mutableMapState().md_.proj_points_[mutableMapState().md_.proj_points_cnt++] = pt_world;
    }
  }
}

void GridMap::raycastProcess()
{
  last_fusion_fixed_point_ = true;

  invalidateRawContributorCache();
  // if (mutableMapState().md_.proj_points_.size() == 0)
  if (mutableMapState().md_.proj_points_cnt == 0)
    return;

  updateSlidingMap(mutableMapState().md_.ray_pos_);

  mutableMapState().md_.raycast_num_ += 1;

  int vox_idx;
  double length;

  // bounding box of updated region
  double min_x = mutableMapState().mp_.map_max_boundary_(0);
  double min_y = mutableMapState().mp_.map_max_boundary_(1);
  double min_z = mutableMapState().mp_.map_max_boundary_(2);

  double max_x = mutableMapState().mp_.map_min_boundary_(0);
  double max_y = mutableMapState().mp_.map_min_boundary_(1);
  double max_z = mutableMapState().mp_.map_min_boundary_(2);

  RayCaster raycaster;
  Eigen::Vector3d half = Eigen::Vector3d(0.5, 0.5, 0.5);
  Eigen::Vector3d ray_pt, pt_w;

  for (int i = 0; i < mutableMapState().md_.proj_points_cnt; ++i)
  {
    pt_w = mutableMapState().md_.proj_points_[i];

    // set flag for projected point

    if (!isInMap(pt_w))
    {
      pt_w = closetPointInMap(pt_w, mutableMapState().md_.ray_pos_);

      length = (pt_w - mutableMapState().md_.ray_pos_).norm();
      if (length > mutableMapState().mp_.max_ray_length_)
      {
        pt_w = (pt_w - mutableMapState().md_.ray_pos_) / length * mutableMapState().mp_.max_ray_length_ + mutableMapState().md_.ray_pos_;
      }
      vox_idx = setCacheOccupancy(pt_w, 0);
    }
    else
    {
      length = (pt_w - mutableMapState().md_.ray_pos_).norm();

      if (length > mutableMapState().mp_.max_ray_length_)
      {
        pt_w = (pt_w - mutableMapState().md_.ray_pos_) / length * mutableMapState().mp_.max_ray_length_ + mutableMapState().md_.ray_pos_;
        vox_idx = setCacheOccupancy(pt_w, 0);
      }
      else
      {
        vox_idx = setCacheOccupancy(pt_w, 1);
      }
    }

    max_x = max(max_x, pt_w(0));
    max_y = max(max_y, pt_w(1));
    max_z = max(max_z, pt_w(2));

    min_x = min(min_x, pt_w(0));
    min_y = min(min_y, pt_w(1));
    min_z = min(min_z, pt_w(2));

    // raycasting between ray origin and point

    if (vox_idx != INVALID_IDX)
    {
      if (mutableMapState().md_.flag_rayend_[vox_idx] == mutableMapState().md_.raycast_num_)
      {
        continue;
      }
      else
      {
        mutableMapState().md_.flag_rayend_[vox_idx] = mutableMapState().md_.raycast_num_;
      }
    }

    raycaster.setInput(pt_w / mutableMapState().mp_.resolution_, mutableMapState().md_.ray_pos_ / mutableMapState().mp_.resolution_);

    while (raycaster.step(ray_pt))
    {
      Eigen::Vector3d tmp = (ray_pt + half) * mutableMapState().mp_.resolution_;
      length = (tmp - mutableMapState().md_.ray_pos_).norm();

      vox_idx = setCacheOccupancy(tmp, 0);

      if (vox_idx != INVALID_IDX)
      {
        if (mutableMapState().md_.flag_traverse_[vox_idx] == mutableMapState().md_.raycast_num_)
        {
          break;
        }
        else
        {
          mutableMapState().md_.flag_traverse_[vox_idx] = mutableMapState().md_.raycast_num_;
        }
      }
    }
  }

  min_x = min(min_x, mutableMapState().md_.ray_pos_(0));
  min_y = min(min_y, mutableMapState().md_.ray_pos_(1));
  min_z = min(min_z, mutableMapState().md_.ray_pos_(2));

  max_x = max(max_x, mutableMapState().md_.ray_pos_(0));
  max_y = max(max_y, mutableMapState().md_.ray_pos_(1));
  max_z = max(max_z, mutableMapState().md_.ray_pos_(2));
  max_z = max(max_z, mutableMapState().mp_.ground_height_);

  posToIndex(Eigen::Vector3d(max_x, max_y, max_z), mutableMapState().md_.local_bound_max_);
  posToIndex(Eigen::Vector3d(min_x, min_y, min_z), mutableMapState().md_.local_bound_min_);
  boundIndex(mutableMapState().md_.local_bound_min_);
  boundIndex(mutableMapState().md_.local_bound_max_);

  // update occupancy cached in queue
  Eigen::Vector3d local_range_min = mutableMapState().md_.ray_pos_ - mutableMapState().mp_.local_update_range_;
  Eigen::Vector3d local_range_max = mutableMapState().md_.ray_pos_ + mutableMapState().mp_.local_update_range_;

  Eigen::Vector3i min_id, max_id;
  posToIndex(local_range_min, min_id);
  posToIndex(local_range_max, max_id);
  boundIndex(min_id);
  boundIndex(max_id);

  // std::cout << "cache all: " << mutableMapState().md_.cache_voxel_.size() << std::endl;

  while (!mutableMapState().md_.cache_voxel_.empty())
  {

    Eigen::Vector3i idx = mutableMapState().md_.cache_voxel_.front();
    int idx_ctns = toAddress(idx);
    // Observe net occupancy changes without altering any fusion arithmetic.
    struct FusionFixedPoint {
      bool &fixed;
      const std::vector<double> &buffer;
      int address;
      double previous;
      ~FusionFixedPoint() { fixed = fixed && buffer[address] == previous; }
    } fixed_point{last_fusion_fixed_point_,mutableMapState().md_.occupancy_buffer_,idx_ctns,
                  mutableMapState().md_.occupancy_buffer_[idx_ctns]};
    mutableMapState().md_.cache_voxel_.pop();

    double log_odds_update =
        mutableMapState().md_.count_hit_[idx_ctns] >= mutableMapState().md_.count_hit_and_miss_[idx_ctns] - mutableMapState().md_.count_hit_[idx_ctns] ? mutableMapState().mp_.prob_hit_log_ : mutableMapState().mp_.prob_miss_log_;

    mutableMapState().md_.count_hit_[idx_ctns] = mutableMapState().md_.count_hit_and_miss_[idx_ctns] = 0;

    if (log_odds_update >= 0 && mutableMapState().md_.occupancy_buffer_[idx_ctns] >= mutableMapState().mp_.clamp_max_log_)
    {
      continue;
    }
    else if (log_odds_update <= 0 && mutableMapState().md_.occupancy_buffer_[idx_ctns] <= mutableMapState().mp_.clamp_min_log_)
    {
      applyOccupancyUpdate(idx, mutableMapState().mp_.clamp_min_log_);
      continue;
    }

    bool in_local = idx(0) >= min_id(0) && idx(0) <= max_id(0) && idx(1) >= min_id(1) &&
                    idx(1) <= max_id(1) && idx(2) >= min_id(2) && idx(2) <= max_id(2);
    if (!in_local)
    {
      applyOccupancyUpdate(idx, mutableMapState().mp_.clamp_min_log_);
    }

    const double new_log_odds =
        std::min(std::max(mutableMapState().md_.occupancy_buffer_[idx_ctns] + log_odds_update, mutableMapState().mp_.clamp_min_log_),
                 mutableMapState().mp_.clamp_max_log_);
    applyOccupancyUpdate(idx, new_log_odds);
  }
}

Eigen::Vector3d GridMap::closetPointInMap(const Eigen::Vector3d &pt, const Eigen::Vector3d &ray_pos)
{
  Eigen::Vector3d diff = pt - ray_pos;
  Eigen::Vector3d max_tc = mapState().mp_.map_max_boundary_ - ray_pos;
  Eigen::Vector3d min_tc = mapState().mp_.map_min_boundary_ - ray_pos;

  double min_t = 1000000;

  for (int i = 0; i < 3; ++i)
  {
    if (fabs(diff[i]) > 0)
    {

      double t1 = max_tc[i] / diff[i];
      if (t1 > 0 && t1 < min_t)
        min_t = t1;

      double t2 = min_tc[i] / diff[i];
      if (t2 > 0 && t2 < min_t)
        min_t = t2;
    }
  }

  return ray_pos + (min_t - 1e-3) * diff;
}

void GridMap::visCallback()
{
  adoptMappingSnapshot();


  publishMap();
  publishMapInflate(true);
  publishSlidingMapFrame();
  publishSlidingMapBBox();
  publishDepthCloud();
}

void GridMap::updateOccupancyCallback()
{
  if (async_mapping_) { adoptMappingSnapshot(); return; }

  if (!mutableMapState().md_.occ_need_update_)
    return;

  /* update occupancy */
  // ros::Time t1, t2, t3, t4;
  // t1 = ros::Time::now();

  if (!mutableMapState().md_.use_cloud_update_)
    projectDepthImage();
  // t2 = ros::Time::now();
  raycastProcess();
  // t3 = ros::Time::now();

  // t4 = ros::Time::now();

  // cout << setprecision(7);
  // cout << "t2=" << (t2-t1).toSec() << " t3=" << (t3-t2).toSec() << " t4=" << (t4-t3).toSec() << endl;;

  // mutableMapState().md_.fuse_time_ += (t2 - t1).toSec();
  // mutableMapState().md_.max_fuse_time_ = max(mutableMapState().md_.max_fuse_time_, (t2 - t1).toSec());

  // if (mutableMapState().mp_.show_occ_time_)
  //   ROS_WARN("Fusion: cur t = %lf, avg t = %lf, max t = %lf", (t2 - t1).toSec(),
  //            mutableMapState().md_.fuse_time_ / mutableMapState().md_.update_num_, mutableMapState().md_.max_fuse_time_);

  mutableMapState().md_.occ_need_update_ = false;
  mutableMapState().md_.use_cloud_update_ = false;
  if (mutableMapState().reactive_pending_cloud_) mutableMapState().reactive_cloud_ready_ = true;
  mutableMapState().reactive_pending_cloud_ = false;
}

void GridMap::depthPoseCallback(sensor_msgs::msg::Image::ConstSharedPtr img,
                                nav_msgs::msg::Odometry::ConstSharedPtr pose)
{
  if (mutableMapState().mp_.sensor_type_ != "depth")
    return;

  /* get depth image */
  cv_bridge::CvImagePtr cv_ptr;
  cv_ptr = cv_bridge::toCvCopy(img, img->encoding);

  if (img->encoding == sensor_msgs::image_encodings::TYPE_32FC1)
  {
    (cv_ptr->image).convertTo(cv_ptr->image, CV_16UC1, mutableMapState().mp_.k_depth_scaling_factor_);
  }
  cv_ptr->image.copyTo(mutableMapState().md_.depth_image_);

  // std::cout << "depth: " << mutableMapState().md_.depth_image_.cols << ", " << mutableMapState().md_.depth_image_.rows << std::endl;

  /* get pose */
  const geometry_msgs::msg::Pose &sensor_pose = pose->pose.pose;
  Eigen::Quaterniond ray_q(sensor_pose.orientation.w, sensor_pose.orientation.x,
                           sensor_pose.orientation.y, sensor_pose.orientation.z);
  if (ray_q.norm() < 1e-6)
    return;
  ray_q.normalize();

  Eigen::Vector3d ray_pos(sensor_pose.position.x, sensor_pose.position.y, sensor_pose.position.z);
  if (mutableMapState().mp_.need_extrinsic_)
  {
    const Eigen::Matrix3d pose_r = ray_q.toRotationMatrix();
    ray_pos += pose_r * mutableMapState().mp_.depth_extrinsic_.block<3, 1>(0, 3);
    ray_q = Eigen::Quaterniond(pose_r * mutableMapState().mp_.depth_extrinsic_.block<3, 3>(0, 0));
    ray_q.normalize();
  }

  nav_msgs::msg::Odometry extrinsic_pose = *pose;
  extrinsic_pose.pose.pose.position.x = ray_pos.x();
  extrinsic_pose.pose.pose.position.y = ray_pos.y();
  extrinsic_pose.pose.pose.position.z = ray_pos.z();
  extrinsic_pose.pose.pose.orientation.x = ray_q.x();
  extrinsic_pose.pose.pose.orientation.y = ray_q.y();
  extrinsic_pose.pose.pose.orientation.z = ray_q.z();
  extrinsic_pose.pose.pose.orientation.w = ray_q.w();
  extrinsic_pose.child_frame_id =
      pose->child_frame_id.empty() ? "sensor_extrinsic" : pose->child_frame_id + "_extrinsic";
  extrinsic_pose_pub_->publish(extrinsic_pose);

  mutableMapState().md_.ray_pos_ = ray_pos;
  mutableMapState().md_.ray_q_ = ray_q;
  mutableMapState().md_.use_cloud_update_ = false;
  updateSlidingMap(mutableMapState().md_.ray_pos_);
  if (isInMap(mutableMapState().md_.ray_pos_))
  {
    mutableMapState().md_.has_ray_pose_ = true;
    mutableMapState().md_.update_num_ += 1;
    mutableMapState().md_.occ_need_update_ = true;
  }
  else
  {
    mutableMapState().md_.occ_need_update_ = false;
  }
}

void GridMap::sensorPoseCallback(nav_msgs::msg::Odometry::ConstSharedPtr pose_msg)
{
  if (async_mapping_) {
    enqueueMapping({0, rclcpp::Time(pose_msg->header.stamp).nanoseconds(), pose_msg, nullptr});
    return;
  }

  if (mutableMapState().mp_.sensor_type_ != "lidar")
    return;

  const geometry_msgs::msg::Pose &sensor_pose = pose_msg->pose.pose;
  Eigen::Quaterniond ray_q(sensor_pose.orientation.w, sensor_pose.orientation.x,
                           sensor_pose.orientation.y, sensor_pose.orientation.z);
  if (ray_q.norm() < 1e-6)
    return;
  ray_q.normalize();

  Eigen::Vector3d ray_pos(sensor_pose.position.x, sensor_pose.position.y, sensor_pose.position.z);
  if (mutableMapState().mp_.need_extrinsic_)
  {
    const Eigen::Matrix3d pose_r = ray_q.toRotationMatrix();
    ray_pos += pose_r * mutableMapState().mp_.lidar_extrinsic_.block<3, 1>(0, 3);
    ray_q = Eigen::Quaterniond(pose_r * mutableMapState().mp_.lidar_extrinsic_.block<3, 3>(0, 0));
    ray_q.normalize();
  }
  if (!std::isfinite(ray_pos.x()) || !std::isfinite(ray_pos.y()) || !std::isfinite(ray_pos.z()))
    return;

  mutableMapState().md_.ray_pos_ = ray_pos;
  mutableMapState().md_.ray_q_ = ray_q;
  mutableMapState().md_.has_ray_pose_ = true;
  updateSlidingMap(mutableMapState().md_.ray_pos_);
}

void GridMap::slidingMapFrameCallback(nav_msgs::msg::Odometry::ConstSharedPtr pose)
{
  if (async_mapping_) {
    const auto &p = pose->pose.pose.position;
    live_body_position_ = Eigen::Vector3d(p.x,p.y,p.z);
    const auto &q = pose->pose.pose.orientation;
    Eigen::Quaterniond rotation(q.w,q.x,q.y,q.z);
    const double stamp = rclcpp::Time(pose->header.stamp).seconds();
    reactive_body_stamp_s_ = 0.0;
    if (std::isfinite(stamp) && stamp>0.0 && live_body_position_.allFinite() &&
        rotation.coeffs().allFinite() && rotation.norm()>1e-6) {
      reactive_body_stamp_s_=stamp; reactive_body_quaternion_=rotation.normalized();
    }

    enqueueMapping({2, rclcpp::Time(pose->header.stamp).nanoseconds(), pose, nullptr});
    return;
  }

  const geometry_msgs::msg::Point &pos = pose->pose.pose.position;
  mutableMapState().md_.sliding_map_frame_pos_ = Eigen::Vector3d(pos.x, pos.y, pos.z);
  const auto &q = pose->pose.pose.orientation;
  Eigen::Quaterniond rotation(q.w, q.x, q.y, q.z);
  const double stamp = rclcpp::Time(pose->header.stamp).seconds();
  reactive_body_stamp_s_ = 0.0;
  if (pose->header.frame_id == mutableMapState().mp_.frame_id_ && mutableMapState().md_.sliding_map_frame_pos_.allFinite() &&
      rotation.coeffs().allFinite() && std::abs(rotation.norm() - 1.0) < 1e-3 && stamp > 0.0) {
    reactive_body_quaternion_ = rotation.normalized();
    reactive_body_stamp_s_ = stamp;
  }
}

void GridMap::refreshSensorInputs(const char *site, int fsm_odometry)
{
  reactive_stair::PlanningProfile::Scope profile(planning_profile_, reactive_stair::PlanningProfile::Inputs);
  // Actual occupancy/ground mutations invalidate. An empty input drain does not.
  // v31: SCAN serves its planning and safety timers and these subscriptions on
  // one single-threaded executor, timers first, while the simulation clock runs
  // on its own thread. Pose and scan messages that arrive during a long callback
  // therefore wait, and their age can pass the 0.1 s pose and 0.25 s scan limits
  // before a decision uses them. Take the pending messages here, on the same
  // thread, and apply them through the unchanged callbacks in stamp order (ties
  // in subscription creation order), so each collision-deciding step starts
  // from the newest received inputs. The limits and callbacks are unchanged.
  struct PendingInput
  {
    double stamp_s;
    int subscription;  // 0 sensor_pose, 1 cloud, 2 body_pose (creation order)
    nav_msgs::msg::Odometry::ConstSharedPtr pose;
    sensor_msgs::msg::PointCloud2::ConstSharedPtr cloud;
  };
  std::vector<PendingInput> pending;
  rclcpp::MessageInfo info;
  // Stamps are read as plain numbers here, so no stamp can throw. A failed take
  // is logged and ends that subscription's drain, as the executor's
  // take_and_do_error_handling logs and skips it.
  const auto stamp_s = [](const builtin_interfaces::msg::Time &stamp) {
    return static_cast<double>(stamp.sec) + 1e-9 * static_cast<double>(stamp.nanosec);
  };
  const auto take = [&](auto &subscription, auto message, int order, const char *topic) {
    try
    {
      if (!subscription->take(*message, info)) return false;
    }
    catch (const rclcpp::exceptions::RCLError &error)
    {
      RCLCPP_ERROR(node_->get_logger(), "input_refresh site=%s take from %s failed: %s", site, topic, error.what());
      return false;
    }
    if constexpr (std::is_same_v<decltype(message), std::shared_ptr<sensor_msgs::msg::PointCloud2>>)
      pending.push_back({stamp_s(message->header.stamp), order, nullptr, message});
    else
      pending.push_back({stamp_s(message->header.stamp), order, message, nullptr});
    return true;
  };
  // Reverse publication order: the bridge publishes each scan's sensor pose
  // before its cloud, so a pair that arrives during this drain cannot leave its
  // cloud taken without its pose (a delivery that reorders the two topics would
  // mispair them on the executor path as well).
  while (cloud_sub_ && take(cloud_sub_, std::make_shared<sensor_msgs::msg::PointCloud2>(), 1, "cloud")) {}
  while (lidar_pose_sub_ && take(lidar_pose_sub_, std::make_shared<nav_msgs::msg::Odometry>(), 0, "sensor_pose")) {}
  while (sliding_map_frame_sub_ &&
         take(sliding_map_frame_sub_, std::make_shared<nav_msgs::msg::Odometry>(), 2, "body_pose")) {}
  std::stable_sort(pending.begin(), pending.end(), [](const PendingInput &a, const PendingInput &b) {
    return a.stamp_s != b.stamp_s ? a.stamp_s < b.stamp_s : a.subscription < b.subscription;
  });
  const double now = node_->now().seconds();
  const double cloud_age = now - mapState().reactive_cloud_stamp_s_;
  const double body_age = now - reactive_body_stamp_s_;
  int applied[3] = {0, 0, 0};
  for (const PendingInput &input : pending)
  {
    ++applied[input.subscription];
    if (input.subscription == 0)
      sensorPoseCallback(input.pose);
    else if (input.subscription == 1)
      cloudCallback(input.cloud);
    else
      slidingMapFrameCallback(input.pose);
  }
  adoptMappingSnapshot();
  const double cloud_age_after = now - mapState().reactive_cloud_stamp_s_;
  const double body_age_after = now - reactive_body_stamp_s_;
  const std::string where(site);
  // Log every call at the sites inside a timer callback, which show how much the
  // inputs aged within a step; at the two timers, log a stale input applied or
  // any input stamped ahead of the clock (a freshness test reads it as stale).
  if ((where != "exec" && where != "safety") || (applied[1] > 0 && cloud_age > 0.15) ||
      (applied[2] > 0 && body_age > 0.05) || cloud_age_after < 0.0 || body_age_after < 0.0)
    RCLCPP_INFO(node_->get_logger(),
                "input_refresh site=%s sensor_poses=%d clouds=%d body_poses=%d fsm_odom=%d "
                "cloud_age=%.4f->%.4f body_age=%.4f->%.4f cloud_ready=%d",
                site, applied[0], applied[1], applied[2], fsm_odometry, cloud_age, cloud_age_after,
                body_age, body_age_after, static_cast<int>(mapState().reactive_cloud_ready_));
}

void GridMap::cloudCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr img)
{
  if (async_mapping_) {
    enqueueMapping({1, rclcpp::Time(img->header.stamp).nanoseconds(), nullptr, img});
    return;
  }

  reactive_stair::PlanningProfile::Scope profile(planning_profile_, reactive_stair::PlanningProfile::Cloud);
  invalidateRawContributorCache();
  if (!reactiveSurfaceGroundReady()) return;
  if (mutableMapState().mp_.sensor_type_ != "lidar")
    return;
  mutableMapState().reactive_cloud_ready_ = false;
  mutableMapState().reactive_pending_cloud_ = false;
  if (mutableMapState().mp_.cloud_is_world_ && img->header.frame_id != mutableMapState().mp_.frame_id_) return;
  mutableMapState().reactive_cloud_stamp_s_ = rclcpp::Time(img->header.stamp).seconds();
  if (!std::isfinite(mutableMapState().reactive_cloud_stamp_s_) || mutableMapState().reactive_cloud_stamp_s_ <= 0.0) return;

  if (!mutableMapState().md_.has_ray_pose_)
  {
    RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
                         "[GridMap] no sensor_pose received for lidar cloud update");
    return;
  }

  pcl::PointCloud<pcl::PointXYZ> latest_cloud;
  pcl::fromROSMsg(*img, latest_cloud);

  mutableMapState().md_.has_cloud_ = true;

  if (latest_cloud.points.size() == 0)
    return;

  const Eigen::Matrix3d sensor_r = mutableMapState().md_.ray_q_.toRotationMatrix();
  const Eigen::Vector3d ray_pos = mutableMapState().md_.ray_pos_;
  if (!std::isfinite(ray_pos.x()) || !std::isfinite(ray_pos.y()) || !std::isfinite(ray_pos.z()))
    return;

  updateSlidingMap(ray_pos);

  mutableMapState().md_.proj_points_cnt = 0;
  mutableMapState().reactive_nonterrain_hits_.clear();

  for (size_t i = 0; i < latest_cloud.points.size(); ++i)
  {
    const pcl::PointXYZ &pt = latest_cloud.points[i];
    if (!std::isfinite(pt.x) || !std::isfinite(pt.y) || !std::isfinite(pt.z))
      continue;

    Eigen::Vector3d pt_world;
    if (mutableMapState().mp_.cloud_is_world_)
    {
      pt_world = Eigen::Vector3d(pt.x, pt.y, pt.z);
    }
    else
    {
      const Eigen::Vector3d pt_sensor(pt.x, pt.y, pt.z);
      pt_world = sensor_r * pt_sensor + ray_pos;
    }
    const Eigen::Vector3d devi = pt_world - ray_pos;
    const double ray_length = devi.norm();
    const bool in_local_range =
        fabs(devi(0)) <= mutableMapState().mp_.local_update_range_(0) && fabs(devi(1)) <= mutableMapState().mp_.local_update_range_(1) &&
        fabs(devi(2)) <= mutableMapState().mp_.local_update_range_(2);
    if (!in_local_range && ray_length <= mutableMapState().mp_.max_ray_length_)
      continue;

    if (mutableMapState().md_.proj_points_cnt >= static_cast<int>(mutableMapState().md_.proj_points_.size()))
      mutableMapState().md_.proj_points_.push_back(pt_world);
    else
      mutableMapState().md_.proj_points_[mutableMapState().md_.proj_points_cnt] = pt_world;

    mutableMapState().md_.proj_points_cnt++;
    if (isInMap(pt_world)) {
      Eigen::Vector3i reactive_id;
      posToIndex(pt_world, reactive_id);
      const auto key = std::make_tuple(reactive_id.x(), reactive_id.y(), reactive_id.z());
      if (reactiveTerrainReturn(pt_world)) mutableMapState().reactive_terrain_hits_.insert(key);
      else {
        mutableMapState().reactive_nonterrain_hits_.insert(key);
        mutableMapState().reactive_nonterrain_history_.insert(key);
      }
    }
  }

  if (mutableMapState().md_.proj_points_cnt == 0)
    return;

  mutableMapState().md_.use_cloud_update_ = true;
  mutableMapState().md_.occ_need_update_ = true;
  mutableMapState().reactive_pending_cloud_ = true;
  updateOccupancyCallback();
}

void GridMap::publishMap()
{

  if (map_pub_->get_subscription_count() == 0)
    return;

  pcl::PointXYZ pt;
  pcl::PointCloud<pcl::PointXYZ> cloud;

  Eigen::Vector3i min_cut = mapState().mp_.map_bound_min_idx_;
  Eigen::Vector3i max_cut = mapState().mp_.map_bound_max_idx_;

  for (int x = min_cut(0); x <= max_cut(0); ++x)
    for (int y = min_cut(1); y <= max_cut(1); ++y)
      for (int z = min_cut(2); z <= max_cut(2); ++z)
      {
        if (mapState().md_.occupancy_buffer_[toAddress(x, y, z)] < mapState().mp_.min_occupancy_log_)
          continue;

        Eigen::Vector3d pos;
        indexToPos(Eigen::Vector3i(x, y, z), pos);
        if (mapState().md_.has_ray_pose_ && pos(2) > mapState().md_.ray_pos_(2) + mapState().mp_.vis_height_)
          continue;
        pt.x = pos(0);
        pt.y = pos(1);
        pt.z = pos(2);
        cloud.push_back(pt);
      }

  cloud.width = cloud.points.size();
  cloud.height = 1;
  cloud.is_dense = true;
  cloud.header.frame_id = mapState().mp_.frame_id_;
  sensor_msgs::msg::PointCloud2 cloud_msg;

  pcl::toROSMsg(cloud, cloud_msg);
  cloud_msg.header.stamp = node_->now();
  map_pub_->publish(cloud_msg);
}

void GridMap::publishMapInflate(bool all_info)
{

  if (map_inf_pub_->get_subscription_count() == 0)
    return;

  pcl::PointXYZ pt;
  pcl::PointCloud<pcl::PointXYZ> cloud;

  Eigen::Vector3i min_cut = mapState().mp_.map_bound_min_idx_;
  Eigen::Vector3i max_cut = mapState().mp_.map_bound_max_idx_;

  const std::vector<char> &inflate_buffer = mapState().md_.occupancy_buffer_inflate_;
  for (int x = min_cut(0); x <= max_cut(0); ++x)
    for (int y = min_cut(1); y <= max_cut(1); ++y)
      for (int z = min_cut(2); z <= max_cut(2); ++z)
      {
        if (inflate_buffer[toAddress(x, y, z)] == 0)
          continue;

        Eigen::Vector3d pos;
        indexToPos(Eigen::Vector3i(x, y, z), pos);
        if (mapState().md_.has_ray_pose_ && pos(2) > mapState().md_.ray_pos_(2) + mapState().mp_.vis_height_)
          continue;

        pt.x = pos(0);
        pt.y = pos(1);
        pt.z = pos(2);
        cloud.push_back(pt);
      }

  cloud.width = cloud.points.size();
  cloud.height = 1;
  cloud.is_dense = true;
  cloud.header.frame_id = mapState().mp_.frame_id_;
  sensor_msgs::msg::PointCloud2 cloud_msg;

  pcl::toROSMsg(cloud, cloud_msg);
  cloud_msg.header.stamp = node_->now();
  map_inf_pub_->publish(cloud_msg);

  // ROS_INFO("pub map");
}

void GridMap::publishSlidingMapFrame()
{
  if (mapState().mp_.sliding_map_frame_id_.empty())
    return;

  geometry_msgs::msg::TransformStamped transform;
  transform.header.stamp = node_->now();
  transform.header.frame_id = mapState().mp_.frame_id_;
  transform.child_frame_id = mapState().mp_.sliding_map_frame_id_;
  transform.transform.translation.x = mapState().md_.sliding_map_frame_pos_.x();
  transform.transform.translation.y = mapState().md_.sliding_map_frame_pos_.y();
  transform.transform.translation.z = mapState().md_.sliding_map_frame_pos_.z();
  transform.transform.rotation.w = 1.0;
  tf_broadcaster_->sendTransform(transform);
}

void GridMap::publishSlidingMapBBox()
{
  if (sliding_map_bbox_pub_->get_subscription_count() == 0)
    return;

  visualization_msgs::msg::Marker marker;
  marker.header.frame_id = mapState().mp_.frame_id_;
  marker.header.stamp = node_->now();
  marker.ns = "sliding_map";
  marker.id = 0;
  marker.type = visualization_msgs::msg::Marker::LINE_LIST;
  marker.action = visualization_msgs::msg::Marker::ADD;
  marker.pose.orientation.w = 1.0;
  marker.scale.x = 0.04;
  marker.color.r = 0.0;
  marker.color.g = 0.8;
  marker.color.b = 1.0;
  marker.color.a = 1.0;

  const Eigen::Vector3d& min_pt = mapState().mp_.map_min_boundary_;
  const Eigen::Vector3d& max_pt = mapState().mp_.map_max_boundary_;
  Eigen::Vector3d corners[8] = {
      {min_pt.x(), min_pt.y(), min_pt.z()},
      {max_pt.x(), min_pt.y(), min_pt.z()},
      {max_pt.x(), max_pt.y(), min_pt.z()},
      {min_pt.x(), max_pt.y(), min_pt.z()},
      {min_pt.x(), min_pt.y(), max_pt.z()},
      {max_pt.x(), min_pt.y(), max_pt.z()},
      {max_pt.x(), max_pt.y(), max_pt.z()},
      {min_pt.x(), max_pt.y(), max_pt.z()},
  };

  auto pushPoint = [&](const Eigen::Vector3d& p) {
    geometry_msgs::msg::Point point;
    point.x = p.x();
    point.y = p.y();
    point.z = p.z();
    marker.points.push_back(point);
  };

  const int edges[12][2] = {
      {0, 1}, {1, 2}, {2, 3}, {3, 0},
      {4, 5}, {5, 6}, {6, 7}, {7, 4},
      {0, 4}, {1, 5}, {2, 6}, {3, 7},
  };

  for (const auto& edge : edges)
  {
    pushPoint(corners[edge[0]]);
    pushPoint(corners[edge[1]]);
  }

  sliding_map_bbox_pub_->publish(marker);
}

void GridMap::publishUnknown()
{
  pcl::PointXYZ pt;
  pcl::PointCloud<pcl::PointXYZ> cloud;

  Eigen::Vector3i min_cut = mapState().md_.local_bound_min_;
  Eigen::Vector3i max_cut = mapState().md_.local_bound_max_;

  boundIndex(max_cut);
  boundIndex(min_cut);

  for (int x = min_cut(0); x <= max_cut(0); ++x)
    for (int y = min_cut(1); y <= max_cut(1); ++y)
      for (int z = min_cut(2); z <= max_cut(2); ++z)
      {

        if (mapState().md_.occupancy_buffer_[toAddress(x, y, z)] < mapState().mp_.clamp_min_log_ - 1e-3)
        {
          Eigen::Vector3d pos;
          indexToPos(Eigen::Vector3i(x, y, z), pos);
          if (mapState().md_.has_ray_pose_ && pos(2) > mapState().md_.ray_pos_(2) + mapState().mp_.vis_height_)
            continue;

          pt.x = pos(0);
          pt.y = pos(1);
          pt.z = pos(2);
          cloud.push_back(pt);
        }
      }

  cloud.width = cloud.points.size();
  cloud.height = 1;
  cloud.is_dense = true;
  cloud.header.frame_id = mapState().mp_.frame_id_;

  sensor_msgs::msg::PointCloud2 cloud_msg;
  pcl::toROSMsg(cloud, cloud_msg);
  cloud_msg.header.stamp = node_->now();
  unknown_pub_->publish(cloud_msg);
}

bool GridMap::odomValid() { return mapState().md_.has_ray_pose_; }

bool GridMap::hasDepthObservation() { return mapState().md_.has_first_depth_; }

Eigen::Vector3d GridMap::getOrigin() { return mapState().mp_.map_origin_; }

// int GridMap::getVoxelNum() {
//   return mapState().mp_.map_voxel_num_[0] * mapState().mp_.map_voxel_num_[1] * mapState().mp_.map_voxel_num_[2];
// }

void GridMap::getRegion(Eigen::Vector3d &ori, Eigen::Vector3d &size)
{
  ori = mapState().mp_.map_origin_, size = mapState().mp_.map_size_;
}

// GridMap

void GridMap::publishDepthCloud()
{
  if (depth_cloud_pub_->get_subscription_count() == 0)
    return;

  if (mapState().md_.proj_points_cnt == 0)
    return;

  pcl::PointCloud<pcl::PointXYZ> cloud;
  pcl::PointXYZ pt;

  for (int i = 0; i < mapState().md_.proj_points_cnt; ++i)
  {
    pt.x = mapState().md_.proj_points_[i](0);
    pt.y = mapState().md_.proj_points_[i](1);
    pt.z = mapState().md_.proj_points_[i](2);
    cloud.push_back(pt);
  }

  cloud.width = cloud.points.size();
  cloud.height = 1;
  cloud.is_dense = true;
  cloud.header.frame_id = mapState().mp_.frame_id_;

  sensor_msgs::msg::PointCloud2 cloud_msg;
  pcl::toROSMsg(cloud, cloud_msg);
  cloud_msg.header.stamp = node_->now();
  depth_cloud_pub_->publish(cloud_msg);
}

#include "plan_env/scan_reactive_grid_methods.inc"

#include <plan_env/async_mapping_methods.inc>
