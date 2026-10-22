#pragma once

#include <Eigen/Core>
#include <unordered_map>
#include <vector>
#include <functional>
#include <limits>
#include <memory>
#include <cstdint>

#include "common/data_types.h"

enum HeuristicType : int { kEuclidean = 0, kManhattan = 1, kDiagonal = 2 };

class Node {
 public:
  Node() = default;
  Node(Eigen::Vector3i idx, Node* parent) : idx(idx), parent(parent) {}
  ~Node() = default;

  bool operator==(const Node& other) const { return idx == other.idx; }

  void Reset() {
    f = 0.0;
    g = 1e9;
    parent = nullptr;
  }

  double f = 1e9;
  double g = 1e9;
  bool free_heading=false;
  double parent_departure_yaw=std::numeric_limits<double>::quiet_NaN();
  double pose_yaw = std::numeric_limits<double>::quiet_NaN();
  double height = 0.0;
  double ele = 0;
  double cost = 0.0;
  int layer = 0;
  Eigen::Vector3i idx = Eigen::Vector3i(0, 0, 0);  // layer, row, col
  // Transient endpoints keep real fractional grid coordinates. idx remains a
  // topology hint; it never substitutes for an endpoint's physical position.
  bool continuous = false;
  Eigen::Vector2d position = Eigen::Vector2d::Zero();
  double support_height = 0.0;
  Eigen::Vector2d GridPosition() const { if(continuous)return position;return idx.tail<2>().cast<double>(); }
  double SupportHeight() const { return continuous ? support_height : height; }
  Node* parent = nullptr;
};

struct NodeCompare {
  bool operator()(const Node* a, const Node* b) const { return a->f > b->f; }
};

using MultiLayerGridMap = std::vector<std::vector<std::vector<Node>>>;

// Obstacle-, orientation- and ENV-free graph containing every pose primitive.
// Distances are lower bounds only; they never admit a pose or connection.
std::vector<double> poseDistanceLowerBounds(const MultiLayerGridMap &grid,
                                          const Node &goal,double resolution,
                                          const std::function<bool(const Node&)> &necessary={});

class Astar {
 public:
  Astar(const HeuristicType h_type = kDiagonal) : h_type_(h_type) {
    switch (h_type) {
      case kEuclidean:
        printf("Euclidean heuristic is used\n");
        break;
      case kManhattan:
        printf("Manhattan heuristic is used\n");
        break;
      case kDiagonal:
        printf("Diagonal heuristic is used\n");
        break;
    };
  }
  Astar(const Astar&)=delete;
  Astar& operator=(const Astar&)=delete;
  Astar(Astar&&)=default;
  Astar& operator=(Astar&&)=default;
  ~Astar() = default;

  void Init(const double cost_threshold, const int num_layers,
            const double resolution, const double step_cost_weight,  const Eigen::MatrixXd& cost_map,
            const Eigen::MatrixXd& height_map, const Eigen::MatrixXd& ele_map);

  void Reset();
  void SetPhysicalSupportMode(bool enabled) { physical_support_mode_=enabled; }
  void SetEnvironmentalCost(std::function<double(const Node &,const Node &)> cost) { environmental_cost_=std::move(cost); }
  void SetTransitionValidator(std::function<bool(const Node &,const Node &)> check) { transition_validator_=std::move(check); }

  void SetContinuousEndpoints(const Node &start,const Node &goal) {
    start_endpoint_=start;goal_endpoint_=goal;continuous_endpoints_=true;
  }
  using PoseValidator=std::function<bool(const Node &,const Node &)>;
  using PoseCost=std::function<double(const Node &,const Node &)>;
  void SetPoseCallbacks(PoseValidator valid,PoseCost cost) {pose_validator_=std::move(valid);pose_cost_=std::move(cost);pose_edges_.clear();pose_rotation_free_.clear();pose_validity_cache_.clear();}
  void SetPoseValidity(std::function<bool(const Node&)> valid) {pose_validity_=std::move(valid);pose_validity_cache_.clear();pose_edges_.clear();}
  void SetPoseNecessaryValidity(std::function<bool(const Node&)> valid) {pose_necessary_validity_=std::move(valid);}
  void SetFreeRotation(std::function<bool(const Node&)> certificate) {free_rotation_=std::move(certificate);pose_rotation_free_.clear();}
  void SetPoseHeadings(double start,double goal) {pose_start_yaw_=start;pose_goal_yaw_=goal;}
  void Debug() { debug_ = true; }

  bool Search(const Eigen::Vector3i& start, const Eigen::Vector3i& goal);

  std::vector<PathPoint> GetPathPoints() const;

  Eigen::MatrixXd GetResultMatrix() const;
  Eigen::MatrixXi GetVisitedSet() const { return visited_set_; }

  Eigen::MatrixXd GetCostLayer(int layer) const;
  Eigen::MatrixXd GetEleLayer(int layer) const;

 private:
  bool SearchPoses(const Eigen::Vector3i &start,const Eigen::Vector3i &goal);
  PoseValidator pose_validator_;PoseCost pose_cost_;
  std::function<bool(const Node&)> free_rotation_,pose_validity_,pose_necessary_validity_;
  std::unordered_map<uint32_t,bool> pose_validity_cache_;
  std::unordered_map<uint32_t,bool> pose_rotation_free_;
  double pose_start_yaw_=std::numeric_limits<double>::quiet_NaN(),pose_goal_yaw_=std::numeric_limits<double>::quiet_NaN();
  std::vector<std::unique_ptr<Node>> pose_nodes_;
  std::unordered_map<uint64_t,double> pose_edges_; // Exact directed static queries, reset on map/constraint change.
  double CalculateStepCost(const Node* node1, const Node* node2) const;

  int DecideLayer(const Node* cur_node) const;

  int GetHash(const Eigen::Vector3i& idx) const;

  std::vector<Eigen::Vector3i> GetNeighbors(Node* node) const;

  double GetHeuristic(const Node* node1, const Node* node2) const;

  Eigen::MatrixXd PathToMatrix(const std::vector<Eigen::Vector3i>& path);

  void ToPathPoints(const std::vector<Eigen::Vector3i>& path,
                    std::vector<PathPoint>& path_points);

  void ConvertClosedSetToMatrix(
      const std::unordered_map<int, Node*>& closed_set);

 private:
  std::function<bool(const Node &,const Node &)> transition_validator_;
  std::function<double(const Node &,const Node &)> environmental_cost_;
  bool physical_support_mode_=false;
  bool continuous_endpoints_=false;
  Node start_endpoint_,goal_endpoint_;
  HeuristicType h_type_ = kDiagonal;

  int max_x_ = 0;
  int max_y_ = 0;
  int max_layers_ = 0;
  int xy_size_ = 0;
  double resolution_ = 0;
  MultiLayerGridMap grid_map_;
  double cost_threshold_ = 35;
  double step_cost_weight_ = 1.0;

  int search_layer_depth_ = 1;
  std::vector<int> search_layers_offset_;

  bool debug_ = false;
  Eigen::MatrixXi visited_set_;

  // std::vector<Eigen::Vector3i> search_result_;
  std::vector<Node*> search_result_;
};
