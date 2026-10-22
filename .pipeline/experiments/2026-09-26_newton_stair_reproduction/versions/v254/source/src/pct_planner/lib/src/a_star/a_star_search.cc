#include "a_star/a_star_search.h"

#include <algorithm>
#include <chrono>
#include <iostream>
#include <queue>
#include <set>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

using std::cout;
using std::endl;

// 9 neighbors in 2d
static std::vector<Eigen::Vector2i> kNeighbors = std::vector<Eigen::Vector2i>{
    Eigen::Vector2i(-1, -1), Eigen::Vector2i(-1, 0), Eigen::Vector2i(-1, 1),
    Eigen::Vector2i(0, -1),  Eigen::Vector2i(0, 1),  Eigen::Vector2i(1, -1),
    Eigen::Vector2i(1, 0),   Eigen::Vector2i(1, 1),
};

void Astar::Init(const double cost_threshold, const int num_layers,
                 const double resolution,  const double step_cost_weight, const Eigen::MatrixXd& cost_map,
                 const Eigen::MatrixXd& height_map,
                 const Eigen::MatrixXd& ele_map) {
  auto t0 = std::chrono::high_resolution_clock::now();
  continuous_endpoints_=false;
  resolution_=resolution;
  cost_threshold_ = cost_threshold;
step_cost_weight_  = step_cost_weight;

  max_x_ = cost_map.cols();
  max_y_ = cost_map.rows() / num_layers;
  max_layers_ = num_layers;
  xy_size_ = max_x_ * max_y_;

  int row_offset = 0;
  grid_map_.resize(max_layers_);
  for (int i = 0; i < max_layers_; ++i) {
    row_offset = i * max_y_;
    grid_map_[i].resize(max_y_);
    for (int j = 0; j < max_y_; ++j) {
      grid_map_[i][j].resize(max_x_);
      for (int k = 0; k < max_x_; ++k) {
        double height = height_map(j + row_offset, k);
        double z = static_cast<int>(height / resolution);
        grid_map_[i][j][k] = Node(Eigen::Vector3i(z, j, k), nullptr);
        grid_map_[i][j][k].cost = cost_map(j + row_offset, k);
        grid_map_[i][j][k].height = height;
        grid_map_[i][j][k].ele = ele_map(j + row_offset, k);
        grid_map_[i][j][k].layer = i;
      }
    }
  }
  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
      std::chrono::high_resolution_clock::now() - t0);

  search_layers_offset_.clear();
  search_layers_offset_.emplace_back(0);
  for (int i = 0; i < search_layer_depth_; ++i) {
    search_layers_offset_.emplace_back(-(i + 1));
    search_layers_offset_.emplace_back(i + 1);
  }

  printf(
      "Astar initialized, max_x: %d, max_y: %d, max_layers: %d, time elapsed: "
      "%f ms\n",
      max_x_, max_y_, max_layers_, duration.count() / 1000.0);
}

void Astar::Reset() {
  for (size_t i = 0; i < grid_map_.size(); ++i) {
    for (size_t j = 0; j < grid_map_[i].size(); ++j) {
      for (size_t k = 0; k < grid_map_[i][j].size(); ++k) {
        grid_map_[i][j][k].Reset();
      }
    }
  }
}

int Astar::GetHash(const Eigen::Vector3i& idx) const {
  return idx[0] * 10000000 + idx[1] * max_x_ + idx[2];
}

bool Astar::Search(const Eigen::Vector3i& start, const Eigen::Vector3i& goal) {
  auto t0 = std::chrono::high_resolution_clock::now();

  // Every request owns fresh search scores and parent links, including after
  // a failed search or a start-equals-goal query with an empty result.
  Reset();
  search_result_.clear();
  if(physical_support_mode_&&!transition_validator_)throw std::runtime_error("Physical support search requires a validator");

  if(continuous_endpoints_&&!physical_support_mode_)
    throw std::runtime_error("Continuous endpoints require physical support mode");
  auto start_node = continuous_endpoints_ ? &start_endpoint_ : &grid_map_[start[0]][start[2]][start[1]];
  auto goal_node = continuous_endpoints_ ? &goal_endpoint_ : &grid_map_[goal[0]][goal[2]][goal[1]];
  if(continuous_endpoints_){start_node->Reset();goal_node->Reset();}
  start_node->g = 0.0;

  if (!physical_support_mode_ && goal_node->cost > cost_threshold_) {
    printf("goal node is not reachable, cost: %f", goal_node->cost);
    return false;
  }

  std::priority_queue<Node*, std::vector<Node*>, NodeCompare> open_set;
  std::unordered_map<int, Node*> closed_set;

  open_set.push(start_node);

  printf("start searching\n");

  while (!open_set.empty()) {
    Node* current_node = open_set.top();
    open_set.pop();

    if (continuous_endpoints_ ? current_node==goal_node : current_node->idx==goal_node->idx) {
      while (current_node->parent != nullptr || (continuous_endpoints_&&current_node==start_node)) {
        // search_result_.emplace_back(Eigen::Vector3i(
        //     current_node->layer, current_node->idx[1],
        //     current_node->idx[2]));
        search_result_.emplace_back(current_node);
        if(!current_node->parent)break;
        current_node = current_node->parent;
      }
      std::reverse(search_result_.begin(), search_result_.end());
      if (debug_) ConvertClosedSetToMatrix(closed_set);
      auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
          std::chrono::high_resolution_clock::now() - t0);
      printf("path found, time elapsed: %f ms\n",
             duration.count() / 1000.0);
      return true;
    }

    // Endpoint nodes do not occupy the rounded cell in the closed set.
    if(!current_node->continuous)closed_set[GetHash(current_node->idx)] = current_node;
    if(continuous_endpoints_ &&
       (current_node->idx.tail<2>()-goal_node->idx.tail<2>()).cwiseAbs().maxCoeff()<=1 &&
       std::abs(current_node->SupportHeight()-goal_node->SupportHeight())<.26 &&
       transition_validator_(*current_node,*goal_node)) {
      const double horizontal=(current_node->GridPosition()-goal_node->GridPosition()).squaredNorm();
      const double vertical=(current_node->height-goal_node->height)/resolution_;
      const double distance=std::sqrt(horizontal+vertical*vertical);
      const double extra=environmental_cost_?environmental_cost_(*current_node,*goal_node):0.;
      const double score=current_node->g+distance+extra;
      if(score<goal_node->g){goal_node->g=goal_node->f=score;goal_node->parent=current_node;open_set.push(goal_node);}
    }

    // int layer = current_node->layer;
    // if (current_node->ele > 0.5) {
    //   layer = std::min(layer + 1, max_layers_ - 1);
    // } else if (current_node->ele < -0.5) {
    //   layer = std::max(layer - 1, 0);
    // }
    const int layer = physical_support_mode_ ? current_node->layer : DecideLayer(current_node);

    int i, j = 0;
    double tentative_g = 0.0;
    auto neighbors=kNeighbors;
    if(current_node->continuous)neighbors.emplace_back(0,0);
    for (const auto& neighbor : neighbors) {
      i = current_node->idx[1] + neighbor[0];
      j = current_node->idx[2] + neighbor[1];

      if (i < 0 || i >= max_y_ || j < 0 || j >= max_x_) {
        continue;
      }

      std::set<int> physical_heights;
      // Enumerate physical neighboring surfaces symmetrically. Stored slice
      // gateway direction and raw margin cost have no admission authority.
      for(int candidate=physical_support_mode_?0:layer;
          candidate<(physical_support_mode_?max_layers_:layer+1);++candidate) {
      auto neighbor_node = &grid_map_[candidate][i][j];
      if(physical_support_mode_) {
        if(neighbor_node->height<=-50.||std::abs(neighbor_node->height-current_node->SupportHeight())>=.26)continue;
        if(!physical_heights.insert(neighbor_node->idx[0]).second)continue;
      }
      const double distance=continuous_endpoints_ ? std::sqrt(
        (neighbor_node->GridPosition()-current_node->GridPosition()).squaredNorm()+
        std::pow((neighbor_node->height-current_node->height)/resolution_,2)) :
        (neighbor_node->idx-current_node->idx).cast<double>().norm();
      if(physical_support_mode_ && current_node->g+distance>=neighbor_node->g)continue;
      // Explicit geometric constraints must not be bypassed by a layer gateway.
      if (transition_validator_ && !transition_validator_(*current_node,*neighbor_node)) continue;

      if (!physical_support_mode_ && neighbor_node->cost > cost_threshold_) {
        if (abs(neighbor_node->ele) < 0.5) {
          continue;
        } else {
          if (std::abs(neighbor_node->height - current_node->height) > 0.3) {
            continue;
          }
        }
      }

      // if ((neighbor_node->cost > cost_threshold_) ||
      //     std::abs(neighbor_node->height - current_node->height) > 0.3) {
      //   continue;
      // }

      double step_cost = physical_support_mode_ ? 0. : step_cost_weight_ * neighbor_node->cost;
      if (step_cost < 5) step_cost = 0.0;
      // Every shared environmental score is nonnegative. Avoid an expensive
      // query when even its zero lower bound cannot improve this neighbor.
      if(environmental_cost_ && current_node->g+distance+step_cost>=neighbor_node->g)continue;
      if(environmental_cost_) step_cost+=environmental_cost_(*current_node,*neighbor_node);
      tentative_g =
          current_node->g +
          distance +
          step_cost;

      auto p_neighbor = closed_set.find(GetHash(neighbor_node->idx));
      if (p_neighbor != closed_set.end()) {
        if (tentative_g >= p_neighbor->second->g) {
          continue;
        }
      }

      if (tentative_g < neighbor_node->g) {
        neighbor_node->g = tentative_g;
        neighbor_node->f = tentative_g + GetHeuristic(neighbor_node, goal_node);
        neighbor_node->parent = current_node;
        open_set.push(neighbor_node);
      }
      }
    }
  }

  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
      std::chrono::high_resolution_clock::now() - t0);
  printf("path not found\n, time elapsed: %f ms\n",
         duration.count() / 1000.0);
  if (debug_) {
    ConvertClosedSetToMatrix(closed_set);
  }
  return false;
}

int Astar::DecideLayer(const Node* cur_node) const {
  int layer = cur_node->layer;
  int i = cur_node->idx[1];
  int j = cur_node->idx[2];
  double cur_height = cur_node->height;

  int true_layer = layer;

  for (const auto offset : search_layers_offset_) {
    int cur_layer = layer + offset;

    if (cur_layer < 0 || cur_layer >= max_layers_) {
      continue;
    }

    const Node& search_node = grid_map_[cur_layer][i][j];

    if (abs(search_node.height - cur_height) > 0.2) {
      continue;
    }

    if (search_node.ele > 0.5) {
      true_layer = std::min(cur_layer + 1, max_layers_ - 1);
      break;
    } else if (search_node.ele < -0.5) {
      true_layer = std::max(cur_layer - 1, 0);
      break;
    }
  }

  return true_layer;
}

double Astar::CalculateStepCost(const Node* node1, const Node* node2) const {
  (void)node1;
  (void)node2;
  return 0.0;
}

double Astar::GetHeuristic(const Node* node1, const Node* node2) const {
  double cost = 0.0;

  if(continuous_endpoints_) {
    return std::sqrt((node1->GridPosition()-node2->GridPosition()).squaredNorm()+
      std::pow((node1->height-node2->height)/resolution_,2));
  }
  if (physical_support_mode_ || h_type_ == kEuclidean) {
    // l2 distance
    cost = (node1->idx - node2->idx).norm();
  } else if (h_type_ == kDiagonal) {
    // octile distance
    Eigen::Vector3i d = node1->idx - node2->idx;
    int dx = abs(d(0)), dy = abs(d(1)), dz = abs(d(2));
    int dmin = std::min(dx, std::min(dy, dz));
    int dmax = std::max(dx, std::max(dy, dz));
    int dmid = dx + dy + dz - dmin - dmax;
    double h =
        std::sqrt(3) * dmin + std::sqrt(2) * (dmid - dmin) + (dmax - dmid);
    cost = h;
  } else if (h_type_ == kManhattan) {
    cost = (node1->idx - node2->idx).lpNorm<1>();
  } else {
    assert(false && "not implemented");
  }

  // cost += std::abs(node1->idx[0] - node2->idx[0]) * 10;
  return cost;
}

std::vector<PathPoint> Astar::GetPathPoints() const {
  std::vector<PathPoint> path_points;

  auto size = search_result_.size();
  path_points.resize(size);

  if (size == 0) {
    printf("path is empty\n, convert to path points failed\n");
    return path_points;
  }

  for (size_t i = 0; i < size; ++i) {
    // path_points[i].layer = search_result_[i][0];
    // path_points[i].x = search_result_[i][2];
    // path_points[i].y = search_result_[i][1];
    // if (i > 0) {
    //   path_points[i].heading =
    //       std::atan2(search_result_[i][1] - search_result_[i - 1][1],
    //                  search_result_[i][2] - search_result_[i - 1][2]);
    // }
    path_points[i].layer = search_result_[i]->layer;
    path_points[i].x = search_result_[i]->GridPosition()(1);
    path_points[i].y = search_result_[i]->GridPosition()(0);
    path_points[i].height = search_result_[i]->height;
    if (i > 0) {
      path_points[i].heading =
          std::atan2(search_result_[i]->GridPosition()(0) - search_result_[i - 1]->GridPosition()(0),
                     search_result_[i]->GridPosition()(1) - search_result_[i - 1]->GridPosition()(1));
    }
  }

  if (size > 1) {
    path_points[0].heading = path_points[1].heading;
  }

  return path_points;
}

Eigen::MatrixXd Astar::GetResultMatrix() const {
  if (search_result_.empty()) {
    printf("path is empty\n, convert to matrix failed\n");
    return Eigen::MatrixXd();
  }

  Eigen::MatrixXd path_matrix(search_result_.size(), 3);
  for (size_t i = 0; i < search_result_.size(); ++i) {
    path_matrix(i, 0) = search_result_[i]->layer;
    path_matrix(i, 1) = search_result_[i]->GridPosition()(0);
    path_matrix(i, 2) = search_result_[i]->GridPosition()(1);
  }
  return path_matrix;
}

void Astar::ConvertClosedSetToMatrix(
    const std::unordered_map<int, Node*>& closed_set) {
  visited_set_ = Eigen::MatrixXi(closed_set.size(), 3);
  int count = 0;
  for (auto i = closed_set.begin(); i != closed_set.end(); ++i) {
    visited_set_(count, 0) = i->second->layer;
    visited_set_(count, 1) = i->second->idx[1];
    visited_set_(count, 2) = i->second->idx[2];
    count += 1;
  }
}

std::vector<Eigen::Vector3i> Astar::GetNeighbors(Node* node) const {
  (void)node;
  return std::vector<Eigen::Vector3i>();
}

Eigen::MatrixXd Astar::GetCostLayer(int layer) const {
  Eigen::MatrixXd cost_layer(max_y_, max_x_);
  for (int i = 0; i < max_y_; ++i) {
    for (int j = 0; j < max_x_; ++j) {
      cost_layer(i, j) = grid_map_[layer][i][j].cost;
    }
  }
  return cost_layer;
}
Eigen::MatrixXd Astar::GetEleLayer(int layer) const {
  Eigen::MatrixXd ele_layer(max_y_, max_x_);
  for (int i = 0; i < max_y_; ++i) {
    for (int j = 0; j < max_x_; ++j) {
      ele_layer(i, j) = grid_map_[layer][i][j].ele;
    }
  }
  return ele_layer;
}