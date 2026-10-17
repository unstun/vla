#include <geometry_msgs/msg/pose_stamped.hpp>
#include <plan_env/observation_window.h>
#include <plan_env/body_time_buffer.h>
#ifndef _GRID_MAP_H
#define _GRID_MAP_H

#include <Eigen/Eigen>
#include <Eigen/StdVector>
#include <algorithm>
#include <cv_bridge/cv_bridge.h>
#include <cmath>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <iostream>
#include <random>
#include <nav_msgs/msg/odometry.hpp>
#include <queue>
#include <rclcpp/rclcpp.hpp>
#include <rmw/qos_profiles.h>
#include <tuple>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/image_encodings.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <tf2_ros/transform_broadcaster.h>
#include <visualization_msgs/msg/marker.hpp>

#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>

#include <message_filters/subscriber.h>
#include <message_filters/sync_policies/approximate_time.h>
#include <message_filters/sync_policies/exact_time.h>
#include <message_filters/time_synchronizer.h>

#include <plan_env/raycast.h>
#include <plan_env/reactive_collision.h>
#include <plan_env/footprint_query.h>
#include <plan_env/collision_segment.h>
#include <plan_env/eth_step_score_adaptation.h>
#include <plan_env/evidence_floor_fill.h>
#include <plan_env/evidence_floor_diagnostic.h>
#include <plan_env/support_gap_mask.h>
#include <set>
#include <unordered_map>
#include <unordered_set>
#include <atomic>
#include <condition_variable>
#include <deque>
#include <map>
#include <mutex>
#include <thread>

#define logit(x) (log((x) / (1 - (x))))

using namespace std;
// voxel hashing
template <typename T>
struct matrix_hash {
  std::size_t operator()(T const& matrix) const {
    size_t seed = 0;
    for (size_t i = 0; i < matrix.size(); ++i) {
      auto elem = *(matrix.data() + i);
      seed ^= std::hash<typename T::Scalar>()(elem) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
    }
    return seed;
  }
};

// Semantic membership does not require tree ordering. Keep full global voxel keys.
struct VoxelKeyHash {
  std::size_t operator()(const std::tuple<int, int, int> &key) const noexcept {
    std::size_t value = std::hash<int>{}(std::get<0>(key));
    value ^= std::hash<int>{}(std::get<1>(key)) + 0x9e3779b9 + (value << 6) + (value >> 2);
    value ^= std::hash<int>{}(std::get<2>(key)) + 0x9e3779b9 + (value << 6) + (value >> 2);
    return value;
  }
};

// constant parameters

struct MappingParameters {
  std::shared_ptr<const reactive_stair::SupportGapMask> support_gap_mask_;

  /* map properties */
  Eigen::Vector3d map_origin_, map_size_;
  Eigen::Vector3d map_min_boundary_, map_max_boundary_;  // map range in pos
  Eigen::Vector3i map_voxel_num_;                        // map range in index
  Eigen::Vector3i map_bound_min_idx_, map_bound_max_idx_;
  Eigen::Vector3i map_origin_idx_;
  Eigen::Vector3d local_update_range_;
  double resolution_, resolution_inv_;
  double obstacles_inflation_z_up, obstacles_inflation_z_down;
  double double_cylinder_radius_, double_cylinder_offset_;
  bool map_sliding_en_;
  double map_sliding_thresh_;
  int map_sliding_thresh_vox_;
  string frame_id_, sliding_map_frame_id_;

  /* depth camera intrinsics */
  double cx_, cy_, fx_, fy_;

  /* depth image projection filtering */
  double depth_filter_maxdist_, depth_filter_mindist_;
  int depth_filter_margin_;
  double k_depth_scaling_factor_;
  int skip_pixel_;

  /* raycasting */
  double p_hit_, p_miss_, p_min_, p_max_, p_occ_;  // occupancy probability
  double prob_hit_log_, prob_miss_log_, clamp_min_log_, clamp_max_log_,
      min_occupancy_log_;                   // logit of occupancy probability
  double min_ray_length_, max_ray_length_;  // range of doing raycasting

  /* visualization and computation time display */
  double vis_height_, ground_height_;
  bool show_occ_time_;

  /* mapping sensor input */
  string sensor_type_;
  bool cloud_is_world_;
  bool need_extrinsic_;
  Eigen::Matrix4d lidar_extrinsic_;
  Eigen::Matrix4d depth_extrinsic_;

  /* active mapping */
  double unknown_flag_;
};

// intermediate mapping data for fusion

struct MappingData {
  // main map data, occupancy of each voxel and Euclidean distance

  std::vector<double> occupancy_buffer_;
  std::vector<char> occupancy_buffer_inflate_;
  std::vector<int> occupancy_buffer_inflate_cnt_;
  vector<Eigen::Vector3i> inflate_offsets_;
  struct InflationColumn { int x, y, z_min, z_max; };
  std::vector<InflationColumn> inflate_columns_;

  // raycast origin and sensor pose data

  Eigen::Vector3d ray_pos_;
  Eigen::Quaterniond ray_q_;
  Eigen::Vector3d sliding_map_frame_pos_;

  // depth image data

  cv::Mat depth_image_;
  int image_cnt_;
  // flags of map state

  bool occ_need_update_;
  bool use_cloud_update_;
  bool has_first_depth_;
  bool has_ray_pose_, has_cloud_;

  // depth image projected point cloud

  vector<Eigen::Vector3d> proj_points_;
  int proj_points_cnt;

  // flag buffers for speeding up raycasting

  vector<short> count_hit_, count_hit_and_miss_;
  vector<char> flag_traverse_, flag_rayend_;
  char raycast_num_;
  queue<Eigen::Vector3i> cache_voxel_;

  // range of updating grid

  Eigen::Vector3i local_bound_min_, local_bound_max_;

  // computation time

  double fuse_time_, max_fuse_time_;
  int update_num_;

  EIGEN_MAKE_ALIGNED_OPERATOR_NEW
};

#include <plan_env/planning_profile.h>
#include <plan_env/environmental_field.h>

struct GridMapSupportState {
  std::shared_ptr<const reactive_stair::EnvironmentalField> environmental_field_;
  reactive_stair::Parameters reactive_parameters_;
  reactive_stair::CollisionDecision reactive_decision_{reactive_parameters_};
  reactive_stair::TerrainSnapshot reactive_terrain_;
  reactive_stair::TerrainSnapshot reactive_ground_; // Unscored positive ground evidence.
  reactive_stair::TerrainSnapshot reactive_navigation_ground_;
  reactive_stair::TerrainSnapshot reactive_surface_ground_;
  reactive_stair::PhysicalFloorSnapshot reactive_physical_floor_;
  bool physical_floor_decoded_valid_{false};
  reactive_stair::StepScoreResult reactive_step_result_;
};

struct GridMapState {
  std::shared_ptr<const GridMapSupportState> support_{std::make_shared<GridMapSupportState>()};
  MappingParameters mp_;
  MappingData md_;
  bool reactive_known_trunk_enabled_ = false;
  std::string reactive_physical_floor_topic_, physical_floor_source_id_, physical_floor_surface_source_id_, physical_floor_navigation_source_id_;
  bool support_lattice_enabled_{false};
  double support_lattice_origin_x_m_{0.0}, support_lattice_origin_y_m_{0.0};
  double physical_floor_origin_x_m_{0.0}, physical_floor_origin_y_m_{0.0}, physical_floor_resolution_m_{0.1};
  std::string reactive_surface_ground_topic_;
  std::unordered_set<std::tuple<int, int, int>, VoxelKeyHash> reactive_terrain_hits_;
  std::unordered_set<std::tuple<int, int, int>, VoxelKeyHash> reactive_nonterrain_hits_;
  std::unordered_set<std::tuple<int, int, int>, VoxelKeyHash> reactive_nonterrain_history_;
  double reactive_cloud_stamp_s_ = 0.0;
  bool reactive_cloud_ready_ = false;
  bool reactive_pending_cloud_ = false;
  double reactive_tomogram_resolution_m_ = 0.1;
  double reactive_tomogram_z_offset_m_ = 0.03;
  double reactive_terrain_band_m_ = 0.05;
  double reactive_cost_limit_ = 20.0;
};

class GridMap {
  struct AsyncMapping;
public:
  GridMap() : owned_state_(std::make_unique<GridMapState>()) {}
  ~GridMap();

  class PublicationLease {
    std::shared_ptr<AsyncMapping> context_;
    std::unique_lock<std::mutex> lock_;
   public:
    explicit PublicationLease(std::shared_ptr<AsyncMapping> context)
      : context_(std::move(context)), lock_(context_->publication_mutex) {}
  };
  void startAsyncMapping();
  void stopAsyncMapping();
  std::atomic<bool> callback_failed_{false};
  bool callbacksHealthy() const {return !callback_failed_.load();}
  bool mapperHealthy() const { return callbacksHealthy() && live_body_inputs_.healthy() && (!async_mapping_ || !async_mapping_->failed.load()) &&
    (!query_context_ || (!query_context_->failed.load() && !query_context_->stopping.load())); }
  uint64_t mapRevision() const { return map_revision_; }
  // Soft-cost fallback only; hard collision queries retain their freshness rule.
  double measuredBodyYaw() const {
    if(reactive_body_stamp_s_<=0 || !reactive_body_quaternion_.coeffs().allFinite() || reactive_body_quaternion_.norm()<1e-12)
      return std::numeric_limits<double>::quiet_NaN();
    const Eigen::Vector3d direction=reactive_body_quaternion_.normalized()*Eigen::Vector3d::UnitX();
    return std::atan2(direction.y(),direction.x());
  }
  double observationStamp() const { return mapState().reactive_cloud_stamp_s_; }
  bool planningInputsReady() const;
  std::unique_ptr<PublicationLease> beginPublication();
  struct QueryLease {
    std::unique_ptr<PublicationLease> publication;
    std::unique_ptr<GridMap> view;
  };
  // Independent query caches and live body state over a pinned immutable map.
  // Does not adopt into or mutate the planner's own read state.
  std::unique_ptr<QueryLease> snapshotQuery(const rclcpp::Clock::SharedPtr &clock,
    const geometry_msgs::msg::PoseStamped &body) const;
  reactive_stair::PlanningProfile planning_profile_;
  // Necessary body-center bounds only; every actual collision query stays live.
  bool bodyCenterBounds(Eigen::Vector3d &lower, Eigen::Vector3d &upper) const {
    if (!mapState().mp_.map_min_boundary_.allFinite() || !mapState().mp_.map_max_boundary_.allFinite() ||
        !std::isfinite(mapState().mp_.double_cylinder_radius_) || mapState().mp_.double_cylinder_radius_<0 ||
        !std::isfinite(mapState().mp_.double_cylinder_offset_) ||
        !std::isfinite(mapState().mp_.obstacles_inflation_z_down) || mapState().mp_.obstacles_inflation_z_down<0 ||
        !std::isfinite(mapState().mp_.obstacles_inflation_z_up) || mapState().mp_.obstacles_inflation_z_up<0) return false;
    lower=mapState().mp_.map_min_boundary_+Eigen::Vector3d(mapState().mp_.double_cylinder_radius_,mapState().mp_.double_cylinder_radius_,mapState().mp_.obstacles_inflation_z_down);
    upper=mapState().mp_.map_max_boundary_-Eigen::Vector3d(mapState().mp_.double_cylinder_radius_,mapState().mp_.double_cylinder_radius_,mapState().mp_.obstacles_inflation_z_up);
    return true;
  }
  // Necessary observation evidence only. True is not an occupancy/support grant.
  bool bodyEndpointMayBeObserved(const Eigen::Vector3d &point);
  enum { INVALID_IDX = -10000 };

  // Only raw classification and terrain-cell lookup data are memoized; query-specific
  // freshness, support decisions, physical position and trunk masking remain live.
  class RawContributorCacheScope {
    GridMap &map_;
    bool previous_;
   public:
    explicit RawContributorCacheScope(GridMap &map) : map_(map), previous_(map.raw_contributor_cache_active_) {
      if (!previous_) {
        map_.invalidateRawContributorCache();
        if (map_.raw_contributor_cache_.bucket_count() < 1024) map_.raw_contributor_cache_.reserve(1024);
        map_.raw_contributor_cache_evaluations_ = map_.raw_contributor_cache_hits_ = 0;
        map_.terrain_cell_cache_hits_ = map_.terrain_cell_cache_evaluations_ = 0;
        map_.raw_contributor_cache_active_ = true;
      }
    }
    ~RawContributorCacheScope() {
      if (!previous_) {
        map_.invalidateRawContributorCache();
        map_.raw_contributor_cache_active_ = false;
      }
    }
    RawContributorCacheScope(const RawContributorCacheScope &) = delete;
    RawContributorCacheScope &operator=(const RawContributorCacheScope &) = delete;
  };

  // occupancy map management
  void resetBuffer();
  void resetBuffer(Eigen::Vector3d min, Eigen::Vector3d max);

  inline void posToIndex(const Eigen::Vector3d& pos, Eigen::Vector3i& id);
  inline void indexToPos(const Eigen::Vector3i& id, Eigen::Vector3d& pos);
  inline int toAddress(const Eigen::Vector3i& id);
  inline int toAddress(int& x, int& y, int& z);
  inline bool isInMap(const Eigen::Vector3d& pos);
  inline bool isInMap(const Eigen::Vector3i& idx);

  inline void setOccupancy(Eigen::Vector3d pos, double occ = 1);
  inline void setOccupied(Eigen::Vector3d pos);
  inline int getOccupancy(Eigen::Vector3d pos);
  inline int getOccupancy(Eigen::Vector3i id);
  inline int getInflateOccupancy(Eigen::Vector3d pos, double yaw);
  reactive_stair::Verdict staticTraversability(Eigen::Vector3d pos, double yaw);
  reactive_stair::Verdict liveTraversability(Eigen::Vector3d pos, double yaw);
  std::string traversabilitySource() const {
    const auto &s=supportState();
    if(s.reactive_navigation_ground_.source_id.empty() || s.reactive_surface_ground_.source_id.empty()) return {};
    return s.reactive_navigation_ground_.source_id+"\n"+s.reactive_surface_ground_.source_id+"\n"+s.reactive_physical_floor_.source_id;
  }
  void logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw);
  // v31: take the pose and scan messages that arrived during a long callback
  // and apply them, in stamp order, through the unchanged callbacks. Call only
  // on the executor's thread, between collision-deciding steps. fsm_odometry is
  // the number of FSM body_pose messages the caller applied just before (-1 if
  // the caller applies none); it is only logged.
  void refreshSensorInputs(const char *site, int fsm_odometry = -1);
  double collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const;
  bool collisionFreeSegment(const Eigen::Vector3d &from, const Eigen::Vector3d &to,
                            int *blocked_sample = nullptr);
  static constexpr double collision_heading_lookahead_s = 0.8;
  double environmentalCost(const Eigen::Vector3d &p,double yaw) const {
    const auto field=supportState().environmental_field_;return field ? field->cost(p,yaw) : 0.;
  }
  double environmentalCostGradient(const Eigen::Vector3d &p,double yaw,Eigen::Vector4d &gradient) const {
    const auto field=supportState().environmental_field_;
    if(field)return field->costGradient(p,yaw,gradient);
    gradient.setZero();return 0.;
  }
  bool hasEnvironmentalField() const {return bool(supportState().environmental_field_);}
  double collisionTrajectoryYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &ahead,
                               const Eigen::Vector3d &velocity) const;

  inline void boundIndex(Eigen::Vector3i& id);
  inline bool isUnknown(const Eigen::Vector3i& id);
  inline bool isUnknown(const Eigen::Vector3d& pos);
  inline bool isKnownFree(const Eigen::Vector3i& id);
  inline bool isKnownOccupied(const Eigen::Vector3i& id);

  void initMap(rclcpp::Node* node, rclcpp::CallbackGroup::SharedPtr callback_group = nullptr);

  void publishMap();
  void publishMapInflate(bool all_info = false);

  void publishUnknown();
  void publishDepth();
  void publishDepthCloud();
  void publishSlidingMapBBox();
  void publishSlidingMapFrame();

  bool hasDepthObservation();
  bool odomValid();
  void getRegion(Eigen::Vector3d& ori, Eigen::Vector3d& size);
  inline double getResolution();
  Eigen::Vector3d getOrigin();
  int getVoxelNum();

  typedef std::shared_ptr<GridMap> Ptr;

  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

private:
  const GridMapState &mapState() const { return read_state_ ? *read_state_ : *owned_state_; }
  GridMapState &mutableMapState() {
    if (read_state_ || async_mapping_) throw std::logic_error("Mutable access to a planner snapshot");
    return *owned_state_;
  }
  const GridMapSupportState &supportState() const { return *mapState().support_; }
  GridMapSupportState &mutableSupportState() {
    auto &pointer = mutableMapState().support_;
    if (!pointer.unique()) pointer = std::make_shared<GridMapSupportState>(*pointer);
    // Every allocation above has mutable underlying storage. The const view
    // protects readers; mutation requires exclusive writer ownership.
    return *std::const_pointer_cast<GridMapSupportState>(pointer);
  }
  std::unique_ptr<GridMapState> owned_state_;
  std::shared_ptr<const GridMapState> read_state_;
  Eigen::Vector3d live_body_position_{Eigen::Vector3d::Zero()};
  Eigen::Vector3d queryBodyPosition() const { return (async_mapping_ || query_body_override_) ? live_body_position_ : mapState().md_.sliding_map_frame_pos_; }
  rclcpp::Time queryNow() const { return query_clock_ ? query_clock_->now() : node_->now(); }
  rclcpp::Clock::SharedPtr query_clock_;
  bool query_body_override_{false};
  struct MappingInput {
    int kind;
    int64_t stamp_ns;
    nav_msgs::msg::Odometry::ConstSharedPtr pose;
    sensor_msgs::msg::PointCloud2::ConstSharedPtr cloud;
  };
  struct MappingSnapshot {
    uint64_t revision = 0;
    std::shared_ptr<const GridMapState> state;
    double mapping_ms = 0.0, copy_ms = 0.0;
    uint64_t applied_clouds = 0, reduced_clouds = 0, maximum_queued_clouds = 0;
    uint64_t expired_clouds = 0, replaced_clouds = 0, capacity_drops = 0;
  };
  struct AsyncMapping {
    std::mutex queue_mutex, publication_mutex;
    std::condition_variable wake;
    std::deque<MappingInput> queue;
    std::shared_ptr<const MappingSnapshot> latest;
    std::deque<std::shared_ptr<const GridMapState>> retired;
    std::thread worker;
    std::atomic<bool> stopping{false}, failed{false};
    std::string error;
    bool drop_backlogged_lidar = false;
    bool nav2_window = false;
    scan_observation_window::Policy observation_policy;
    int64_t last_observation_received_ns = 0;
    int64_t newest_observation_ns = 0;
    std::atomic<uint64_t> expired_clouds{0}, replaced_clouds{0}, capacity_drops{0};
  };
  std::shared_ptr<AsyncMapping> async_mapping_;
  std::shared_ptr<AsyncMapping> query_context_; // Health only; never owns/join-stops the writer.
  uint64_t map_revision_ = 0;
  bool last_fusion_fixed_point_ = false;
  void enqueueMapping(MappingInput input);
  void adoptMappingSnapshotLocked();
  void adoptMappingSnapshot();
  bool reactive_diagnostic_force_ = false;
  bool raw_contributor_cache_active_ = false;
  std::unordered_map<int, reactive_stair::Occupancy> raw_contributor_cache_;
  std::size_t raw_contributor_cache_evaluations_ = 0, raw_contributor_cache_hits_ = 0;
  struct TerrainCellLayers {
    const std::vector<reactive_stair::SurfaceCell> *raw = nullptr;
    const std::vector<reactive_stair::SurfaceCell> *scored = nullptr;
  };
  bool terrain_cell_cache_enabled_ = true;  // Internal paired-test switch, not a runtime parameter.
  std::unordered_map<std::uint64_t, TerrainCellLayers> terrain_cell_cache_;
  std::size_t terrain_cell_cache_hits_ = 0, terrain_cell_cache_evaluations_ = 0;
  static constexpr std::size_t terrain_cell_cache_capacity_ = 4096;
  TerrainCellLayers terrainCellLayers(const reactive_stair::Cell2 &cell);
  bool supportQueryCell(double x, double y, reactive_stair::Cell2 &cell) const;
  void invalidateRawContributorCache() {
    // Drop borrowed pointers before either terrain snapshot can be replaced.
    if (!terrain_cell_cache_.empty()) terrain_cell_cache_.clear();
    if (!raw_contributor_cache_.empty()) raw_contributor_cache_.clear();
  }
  reactive_stair::Occupancy rawContributorOccupancy(const Eigen::Vector3i &id);
  double reactive_body_stamp_s_ = 0.0;
  scan_input_time::BodyTimeBuffer live_body_inputs_;
  void applyDueLiveBody();
  Eigen::Quaterniond reactive_body_quaternion_ = Eigen::Quaterniond::Identity();

  // get depth image and sensor pose
  void guardedDepthPoseCallback(sensor_msgs::msg::Image::ConstSharedPtr image,nav_msgs::msg::Odometry::ConstSharedPtr pose);
  void depthPoseCallback(sensor_msgs::msg::Image::ConstSharedPtr  img,
                         nav_msgs::msg::Odometry::ConstSharedPtr  pose);
  void sensorPoseCallback(nav_msgs::msg::Odometry::ConstSharedPtr  pose);
  void slidingMapFrameCallback(nav_msgs::msg::Odometry::ConstSharedPtr  pose);
  void cloudCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr  img);

  // update occupancy by raycasting
  void updateOccupancyCallback();
  void visCallback();

  // main update process
  void projectDepthImage();
  void raycastProcess();

  inline void inflatePoint(const Eigen::Vector3i& pt, int inf_step_xy, int inf_step_z_up, int inf_step_z_down, vector<Eigen::Vector3i>& pts);
  inline int getInflateOccupancyFromBuffer(Eigen::Vector3d pos, const std::vector<char>& buffer);
  reactive_stair::Verdict footprintSupportVerdict(const Eigen::Vector3d &body_reference,
    const reactive_stair::NonTerrainVoxel &obstacle, reactive_stair::Query &query, bool static_only);
  bool reactiveFootprintSupportQuery(const Eigen::Vector3d &body_reference,
      const reactive_stair::NonTerrainVoxel &obstacle, reactive_stair::Query &query);
  int reactiveOccupancy(const Eigen::Vector3d &point, const Eigen::Vector3d *body_reference = nullptr,
      reactive_stair::Verdict *typed = nullptr);
  bool reactiveTerrainReturn(const Eigen::Vector3d &point) const;
  void reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);
  reactive_stair::TerrainSnapshot decodeReactiveGround(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const;
  // v34: the navigation ground plus the guarded evidence floor (evidence_floor_fill.h).
  reactive_stair::TerrainSnapshot supportGround(const reactive_stair::TerrainSnapshot &navigation);
  void reactivePhysicalFloorCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);
  reactive_stair::PhysicalFloorSnapshot decodePhysicalFloor(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const;
  const reactive_stair::PhysicalFloorSnapshot *qualifiedPhysicalFloor() const;
  bool physicalFloorReady() const;
  reactive_stair::EvidenceFloorDiagnostic physicalSupportDiagnostic(const Eigen::Vector3d &body) const;
  void rescorePhysicalFloorChange();
  void reactiveSurfaceGroundCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);
  bool reactiveSurfaceGroundReady() const;
  inline int getLocalIndex(int id, int dim) const;
  inline int toAddressLocal(const Eigen::Vector3i& id_l) const;
  inline int toAddressLocal(int x, int y, int z) const;
  int setCacheOccupancy(Eigen::Vector3d pos, int occ);
  Eigen::Vector3d closetPointInMap(const Eigen::Vector3d& pt, const Eigen::Vector3d& ray_pos);
  void updateSlidingMap(const Eigen::Vector3d& center);
  void updateMapBoundaryFromIndex();
  void resetAllMapData();
  void resetCellByAddress(int addr);
  void resetCellByAddressForSliding(int addr, const std::vector<char>& clear_mask);
  void hashIdToGlobalIndex(int addr, Eigen::Vector3i& id_g) const;
  void applyOccupancyUpdate(const Eigen::Vector3i& id, double new_log_odds);
  void rebuildInflationOffsets();
  void updateInflation(const Eigen::Vector3i& id, int delta, const std::vector<char>* ignore_mask = nullptr);
  void updateInflationLayer(const Eigen::Vector3i& id, int delta,
                            const vector<Eigen::Vector3i>& offsets,
                            std::vector<int>& cnt_buffer,
                            std::vector<char>& flag_buffer,
                            const std::vector<char>* ignore_mask);

  // typedef message_filters::sync_policies::ExactTime<sensor_msgs::Image,
  // nav_msgs::Odometry> SyncPolicyImageOdom; typedef
  // message_filters::sync_policies::ExactTime<sensor_msgs::Image,
  // nav_msgs::Odometry> SyncPolicyImagePose;
  typedef message_filters::sync_policies::ApproximateTime<sensor_msgs::msg::Image, nav_msgs::msg::Odometry>
      SyncPolicyImagePose;
  typedef shared_ptr<message_filters::Synchronizer<SyncPolicyImagePose>> SynchronizerImagePose;

  rclcpp::Node* node_{nullptr};
  std::shared_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
  shared_ptr<message_filters::Subscriber<sensor_msgs::msg::Image>> depth_sub_;
  shared_ptr<message_filters::Subscriber<nav_msgs::msg::Odometry>> depth_pose_sub_;
  SynchronizerImagePose sync_image_pose_;

  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr lidar_pose_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr sliding_map_frame_sub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_sub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr reactive_tomogram_sub_;
  // v34: the navigation ground as decoded. New evidence is always applied to it,
  // never to supportState().reactive_ground_, which holds the augmented copy.
  // Explicit raw-return classification evidence; scored navigation support stays separate.
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr reactive_physical_floor_sub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr reactive_surface_ground_sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr map_pub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr map_inf_pub_;
  rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr sliding_map_bbox_pub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr unknown_pub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr depth_cloud_pub_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr extrinsic_pose_pub_;
  rclcpp::TimerBase::SharedPtr occ_timer_, vis_timer_;

  //
  uniform_real_distribution<double> rand_noise_;
  normal_distribution<double> rand_noise2_;
  default_random_engine eng_;
};

/* ============================== definition of inline function
 * ============================== */

inline int GridMap::toAddress(const Eigen::Vector3i& id) {
  return getLocalIndex(id(0), 0) * mapState().mp_.map_voxel_num_(1) * mapState().mp_.map_voxel_num_(2) +
         getLocalIndex(id(1), 1) * mapState().mp_.map_voxel_num_(2) + getLocalIndex(id(2), 2);
}

inline int GridMap::toAddress(int& x, int& y, int& z) {
  return getLocalIndex(x, 0) * mapState().mp_.map_voxel_num_(1) * mapState().mp_.map_voxel_num_(2) +
         getLocalIndex(y, 1) * mapState().mp_.map_voxel_num_(2) + getLocalIndex(z, 2);
}

inline int GridMap::getLocalIndex(int id, int dim) const {
  int local_id = id % mapState().mp_.map_voxel_num_(dim);
  if (local_id < 0) local_id += mapState().mp_.map_voxel_num_(dim);
  return local_id;
}

inline int GridMap::toAddressLocal(const Eigen::Vector3i& id_l) const {
  return id_l(0) * mapState().mp_.map_voxel_num_(1) * mapState().mp_.map_voxel_num_(2) + id_l(1) * mapState().mp_.map_voxel_num_(2) + id_l(2);
}

inline int GridMap::toAddressLocal(int x, int y, int z) const {
  return x * mapState().mp_.map_voxel_num_(1) * mapState().mp_.map_voxel_num_(2) + y * mapState().mp_.map_voxel_num_(2) + z;
}

inline void GridMap::boundIndex(Eigen::Vector3i& id) {
  Eigen::Vector3i id1;
  id1(0) = max(min(id(0), mapState().mp_.map_bound_max_idx_(0)), mapState().mp_.map_bound_min_idx_(0));
  id1(1) = max(min(id(1), mapState().mp_.map_bound_max_idx_(1)), mapState().mp_.map_bound_min_idx_(1));
  id1(2) = max(min(id(2), mapState().mp_.map_bound_max_idx_(2)), mapState().mp_.map_bound_min_idx_(2));
  id = id1;
}

inline bool GridMap::isUnknown(const Eigen::Vector3i& id) {
  Eigen::Vector3i id1 = id;
  boundIndex(id1);
  return mapState().md_.occupancy_buffer_[toAddress(id1)] < mapState().mp_.clamp_min_log_ - 1e-3;
}

inline bool GridMap::isUnknown(const Eigen::Vector3d& pos) {
  Eigen::Vector3i idc;
  posToIndex(pos, idc);
  return isUnknown(idc);
}

inline bool GridMap::isKnownFree(const Eigen::Vector3i& id) {
  Eigen::Vector3i id1 = id;
  boundIndex(id1);
  int adr = toAddress(id1);

  // return mapState().md_.occupancy_buffer_[adr] >= mapState().mp_.clamp_min_log_ &&
  //     mapState().md_.occupancy_buffer_[adr] < mapState().mp_.min_occupancy_log_;
  return mapState().md_.occupancy_buffer_[adr] >= mapState().mp_.clamp_min_log_ && mapState().md_.occupancy_buffer_inflate_[adr] == 0;
}

inline bool GridMap::isKnownOccupied(const Eigen::Vector3i& id) {
  Eigen::Vector3i id1 = id;
  boundIndex(id1);
  int adr = toAddress(id1);

  return mapState().md_.occupancy_buffer_inflate_[adr] == 1;
}

inline void GridMap::setOccupied(Eigen::Vector3d pos) {
  if (!isInMap(pos)) return;

  Eigen::Vector3i id;
  posToIndex(pos, id);

  applyOccupancyUpdate(id, mapState().mp_.clamp_max_log_);
}

inline void GridMap::setOccupancy(Eigen::Vector3d pos, double occ) {
  if (occ != 1 && occ != 0) {
    cout << "occ value error!" << endl;
    return;
  }

  if (!isInMap(pos)) return;

  Eigen::Vector3i id;
  posToIndex(pos, id);

  applyOccupancyUpdate(id, occ > 0.5 ? mapState().mp_.clamp_max_log_ : mapState().mp_.clamp_min_log_);
}

inline int GridMap::getOccupancy(Eigen::Vector3d pos) {
  if (!isInMap(pos)) return -1;

  Eigen::Vector3i id;
  posToIndex(pos, id);

  return mapState().md_.occupancy_buffer_[toAddress(id)] > mapState().mp_.min_occupancy_log_ ? 1 : 0;
}

inline int GridMap::getInflateOccupancy(Eigen::Vector3d pos, double yaw) {
  return reactive_stair::twoCylinderQuery({{pos.x(),pos.y(),pos.z()}},yaw,
    mapState().mp_.double_cylinder_offset_,[&](const std::array<double,3> &point) {
      return reactiveOccupancy(Eigen::Vector3d(point[0],point[1],point[2]),&pos);
    });
}

inline int GridMap::getInflateOccupancyFromBuffer(Eigen::Vector3d pos, const std::vector<char>& buffer) {
  if (!isInMap(pos)) return -1;

  Eigen::Vector3i id;
  posToIndex(pos, id);

  return int(buffer[toAddress(id)]);
}

inline int GridMap::getOccupancy(Eigen::Vector3i id) {
  if (!isInMap(id))
    return -1;

  return mapState().md_.occupancy_buffer_[toAddress(id)] > mapState().mp_.min_occupancy_log_ ? 1 : 0;
}

inline bool GridMap::isInMap(const Eigen::Vector3d& pos) {
  if (pos(0) < mapState().mp_.map_min_boundary_(0) + 1e-4 || pos(1) < mapState().mp_.map_min_boundary_(1) + 1e-4 ||
      pos(2) < mapState().mp_.map_min_boundary_(2) + 1e-4) {
    // cout << "less than min range!" << endl;
    return false;
  }
  if (pos(0) > mapState().mp_.map_max_boundary_(0) - 1e-4 || pos(1) > mapState().mp_.map_max_boundary_(1) - 1e-4 ||
      pos(2) > mapState().mp_.map_max_boundary_(2) - 1e-4) {
    return false;
  }
  return true;
}

inline bool GridMap::isInMap(const Eigen::Vector3i& idx) {
  if (idx(0) < mapState().mp_.map_bound_min_idx_(0) || idx(1) < mapState().mp_.map_bound_min_idx_(1) ||
      idx(2) < mapState().mp_.map_bound_min_idx_(2)) {
    return false;
  }
  if (idx(0) > mapState().mp_.map_bound_max_idx_(0) || idx(1) > mapState().mp_.map_bound_max_idx_(1) ||
      idx(2) > mapState().mp_.map_bound_max_idx_(2)) {
    return false;
  }
  return true;
}

inline void GridMap::posToIndex(const Eigen::Vector3d& pos, Eigen::Vector3i& id) {
  // Voxblox c8066b0 point-to-grid convention; numerical boundary correction only.
  constexpr double coordinate_epsilon = 1e-6;
  for (int i = 0; i < 3; ++i) id(i) = floor(pos(i) * mapState().mp_.resolution_inv_ + coordinate_epsilon);
}

inline void GridMap::indexToPos(const Eigen::Vector3i& id, Eigen::Vector3d& pos) {
  for (int i = 0; i < 3; ++i) pos(i) = (id(i) + 0.5) * mapState().mp_.resolution_;
}

inline void GridMap::inflatePoint(const Eigen::Vector3i& pt, int inf_step_xy, int inf_step_z_up, int inf_step_z_down, vector<Eigen::Vector3i>& pts) {

  /* ---------- + shape inflate ---------- */
  // for (int x = -step; x <= step; ++x)
  // {
  //   if (x == 0)
  //     continue;
  //   pts[num++] = Eigen::Vector3i(pt(0) + x, pt(1), pt(2));
  // }
  // for (int y = -step; y <= step; ++y)
  // {
  //   if (y == 0)
  //     continue;
  //   pts[num++] = Eigen::Vector3i(pt(0), pt(1) + y, pt(2));
  // }
  // for (int z = -1; z <= 1; ++z)
  // {
  //   pts[num++] = Eigen::Vector3i(pt(0), pt(1), pt(2) + z);
  // }

  /* ---------- all inflate ---------- */
  pts.clear();
  for (int x = -inf_step_xy; x <= inf_step_xy; ++x)
    for (int y = -inf_step_xy; y <= inf_step_xy; ++y)
    {
      if (std::sqrt(x * x + y * y) > inf_step_xy)
        continue;

      for (int z = -inf_step_z_down; z <= inf_step_z_up; ++z) {
        pts.push_back(Eigen::Vector3i(pt(0) + x, pt(1) + y, pt(2) + z));
      }
    }
}

inline double GridMap::getResolution() { return mapState().mp_.resolution_; }

#endif
