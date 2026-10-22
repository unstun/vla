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

namespace {
constexpr int pose_dx[]={1,2,1,1,0,-1,-1,-2,-1,-2,-1,-1,0,1,1,2};
constexpr int pose_dy[]={0,1,1,2,1,2,1,1,0,-1,-1,-2,-1,-2,-1,-1};
}

std::vector<double> poseDistanceLowerBounds(const MultiLayerGridMap &grid,
                                          const Node &goal,double resolution,
                                          const std::function<bool(const Node&)> &necessary) {
  if(grid.empty()||grid.front().empty()||grid.front().front().empty()||resolution<=0.)
    throw std::runtime_error("Invalid relaxed pose graph");
  const size_t rows=grid.front().size(),cols=grid.front().front().size();
  std::vector<std::vector<const Node*>> columns(rows*cols);
  std::vector<double> distances(grid.size()*rows*cols,std::numeric_limits<double>::infinity());
  const auto key=[&](const Node &n){return (size_t(n.layer)*rows+n.idx[1])*cols+n.idx[2];};
  std::vector<size_t> aliases(distances.size(),distances.size());
  for(const auto &layer:grid)for(const auto &row:layer)for(const auto &n:row)
    if(n.height>-50.&&std::isfinite(n.height)&&(!necessary||necessary(n))){
      auto &column=columns[size_t(n.idx[1])*cols+n.idx[2]];
      const auto same=std::find_if(column.begin(),column.end(),[&](const Node *a){return a->height==n.height;});
      if(same==column.end()){column.push_back(&n);aliases[key(n)]=key(n);}
      else aliases[key(n)]=key(**same);
    }
  std::set<std::pair<int,int>> moves;
  for(int h=0;h<16;++h){moves.emplace(pose_dx[h],pose_dy[h]);
    for(int turn:{-1,1}){const int next=(h+turn+16)%16;moves.emplace(pose_dx[h]+pose_dx[next],pose_dy[h]+pose_dy[next]);}}
  struct Entry{double distance;const Node *node;bool operator<(const Entry &b)const{return distance>b.distance;}};
  std::priority_queue<Entry> open;
  // The exact endpoint is joined to all position candidates in the same
  // neighbourhood as the real pose search, using a zero-constraint chord.
  for(int x=goal.idx[1]-1;x<=goal.idx[1]+1;++x)for(int y=goal.idx[2]-1;y<=goal.idx[2]+1;++y){
    if(x<0||y<0||x>=int(rows)||y>=int(cols))continue;
    for(const Node *n:columns[size_t(x)*cols+y])if(std::abs(n->height-goal.SupportHeight())<.26){
      const double d=std::sqrt((n->GridPosition()-goal.GridPosition()).squaredNorm()+std::pow((n->height-goal.height)/resolution,2));
      distances[key(*n)]=d;open.push({d,n});
    }
  }
  while(!open.empty()){
    const auto item=open.top();open.pop();if(item.distance!=distances[key(*item.node)])continue;
    for(const auto &move:moves){const int x=item.node->idx[1]+move.first,y=item.node->idx[2]+move.second;
      if(x<0||y<0||x>=int(rows)||y>=int(cols))continue;
      for(const Node *n:columns[size_t(x)*cols+y]){
        const double dz=n->height-item.node->height;if(std::abs(dz)>=.26)continue;
        const double d=item.distance+std::sqrt(double(move.first*move.first+move.second*move.second)+std::pow(dz/resolution,2));
        auto &best=distances[key(*n)];if(d<best){best=d;open.push({d,n});}
      }
    }
  }
  for(size_t i=0;i<aliases.size();++i)if(aliases[i]<distances.size())distances[i]=distances[aliases[i]];
  return distances;
}

void Astar::Init(const double cost_threshold, const int num_layers,
                 const double resolution,  const double step_cost_weight, const Eigen::MatrixXd& cost_map,
                 const Eigen::MatrixXd& height_map,
                 const Eigen::MatrixXd& ele_map) {
  auto t0 = std::chrono::high_resolution_clock::now();
  continuous_endpoints_=false;pose_edges_.clear();pose_costs_.clear();pose_rotation_free_.clear();pose_validity_cache_.clear();pose_nodes_.clear();
  pose_necessary_cells_.clear();
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

void Astar::SetPoseNecessaryValidity(std::function<bool(const Node&)> valid) {
  pose_necessary_cells_.clear();if(!valid)return;
  pose_necessary_cells_.resize(size_t(max_layers_)*max_y_*max_x_);
  for(const auto &layer:grid_map_)for(const auto &row:layer)for(const auto &n:row){
    const size_t key=(size_t(n.layer)*max_y_+n.idx[1])*max_x_+n.idx[2];
    pose_necessary_cells_[key]=n.height>-50.&&std::isfinite(n.height)&&valid(n);
  }
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
  if(physical_support_mode_&&std::isfinite(pose_start_yaw_)&&pose_validator_)return SearchPoses(start,goal);
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
    if(std::isfinite(search_result_[i]->pose_yaw)){path_points[i].heading=M_PI/2-search_result_[i]->pose_yaw;continue;}
    if (i > 0) {
      path_points[i].heading =
          std::atan2(search_result_[i]->GridPosition()(0) - search_result_[i - 1]->GridPosition()(0),
                     search_result_[i]->GridPosition()(1) - search_result_[i - 1]->GridPosition()(1));
    }
  }

  if (size > 1&&!std::isfinite(search_result_[0]->pose_yaw)) {
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
bool Astar::SearchPoses(const Eigen::Vector3i &start,const Eigen::Vector3i &goal) {
  // Pose states remain distinct near boundaries. Only a proved FREE full
  // rotation permits merging their reachability in open space. Every emitted
  // turn is retained in the actual pose reference and checked downstream.
  using Clock=std::chrono::steady_clock;const auto phase_began=Clock::now();
  double hard_s=0.,soft_s=0.,certificate_s=0.;size_t hard_n=0,soft_n=0,certificate_n=0;
  const auto phase=[&](size_t states,size_t expanded){std::cout<<"POSE_PHASE states="<<states<<" expanded="<<expanded<<" hard_calls="<<hard_n<<" hard_s="<<hard_s<<" soft_calls="<<soft_n<<" soft_s="<<soft_s<<" certificates="<<certificate_n<<" certificate_s="<<certificate_s<<" total_s="<<std::chrono::duration<double>(Clock::now()-phase_began).count()<<std::endl;};
  search_result_.clear();pose_nodes_.clear();
  if(uint64_t(max_layers_)*max_y_*max_x_*32>UINT32_MAX)throw std::runtime_error("Pose lattice exceeds key capacity");
  if(!pose_cost_)throw std::runtime_error("Pose search requires a cost callback");
  Node first=continuous_endpoints_?start_endpoint_:grid_map_[start[0]][start[2]][start[1]];
  Node last=continuous_endpoints_?goal_endpoint_:grid_map_[goal[0]][goal[2]][goal[1]];
  first.continuous=last.continuous=true;first.free_heading=last.free_heading=false;
  if(!continuous_endpoints_){first.position=first.idx.tail<2>().cast<double>();last.position=last.idx.tail<2>().cast<double>();first.support_height=first.height;last.support_height=last.height;}
  first.pose_yaw=pose_start_yaw_;last.pose_yaw=pose_goal_yaw_;first.Reset();last.Reset();first.g=0.;
  const auto cell_id=[&](const Node &n){return uint32_t((uint64_t(n.layer)*max_y_+n.idx[1])*max_x_+n.idx[2]);};
  const auto lower_began=Clock::now();
  const auto lower_bounds=poseDistanceLowerBounds(grid_map_,last,resolution_,[&](const Node &n){return pose_necessary_cells_.empty()||pose_necessary_cells_[cell_id(n)]!=0;});
  std::cout<<"POSE_LOWER seconds="<<std::chrono::duration<double>(Clock::now()-lower_began).count()<<std::endl;
  const auto heuristic=[&](const Node *n){
    const double direct=std::sqrt((n->GridPosition()-last.GridPosition()).squaredNorm()+std::pow((n->height-last.height)/resolution_,2));
    const double relaxed=n->continuous?direct:lower_bounds[cell_id(*n)];
    const double angular=std::isfinite(pose_goal_yaw_)?pose_angular_lower_bound_*std::abs(std::remainder(n->pose_yaw-pose_goal_yaw_,2*M_PI)):0.;
    return (std::isfinite(relaxed)?std::max(direct,relaxed):direct)+angular;
  };
  const auto id=[&](const Node &n,int h){return (uint64_t(cell_id(n))<<5)|uint64_t(h);};
  const auto heading=[](double yaw){int h=int(std::lround(yaw/(M_PI/8)))%16;return (h+16)%16;};
  const auto rotation_free=[&](const Node &n){
    if(!free_rotation_)return false;const auto key=cell_id(n);auto it=pose_rotation_free_.find(key);
    if(it!=pose_rotation_free_.end())return it->second;
    const auto began=Clock::now();const bool free=free_rotation_(n);certificate_s+=std::chrono::duration<double>(Clock::now()-began).count();++certificate_n;pose_rotation_free_.emplace(key,free);return free;
  };
  std::unordered_map<uint64_t,Node*> nodes;
  const auto get=[&](const Node &base,int h){
    const bool free=rotation_free(base);const auto key=id(base,free?16:h);auto it=nodes.find(key);if(it!=nodes.end())return it->second;
    auto p=std::make_unique<Node>(base);p->Reset();p->pose_yaw=h*M_PI/8;p->continuous=false;p->free_heading=free;
    Node *raw=p.get();pose_nodes_.push_back(std::move(p));nodes.emplace(key,raw);return raw;
  };
  struct Item{double f,g;Node *node;bool operator<(const Item &b)const{return f>b.f;}};
  std::priority_queue<Item> open;open.push({heuristic(&first),0.,&first});std::unordered_set<Node*> closed;
  const auto valid_pose=[&](const Node &n){
    if(!pose_validity_||n.free_heading)return true;
    if(n.continuous)return pose_validity_(n);
    const auto key=uint32_t(id(n,heading(n.pose_yaw)));const auto it=pose_validity_cache_.find(key);if(it!=pose_validity_cache_.end())return it->second;
    const bool valid=pose_validity_(n);pose_validity_cache_.emplace(key,valid);return valid;
  };
  const auto edge=[&](const Node &a,const Node &b,bool cache,bool certified,double base,double turn,double best){
    uint64_t key=0;if(cache){key=(id(a,heading(a.pose_yaw))<<32)|id(b,heading(b.pose_yaw));const auto it=pose_edges_.find(key);if(it!=pose_edges_.end())return it->second;}
    if(!valid_pose(a)||!valid_pose(b)){if(cache)pose_edges_.emplace(key,-1.);return -1.;}
    double cost=-1.;const auto cached_cost=cache?pose_costs_.find(key):pose_costs_.end();
    if(cached_cost!=pose_costs_.end())cost=cached_cost->second;
    else {const auto began=Clock::now();cost=pose_cost_(a,b);soft_s+=std::chrono::duration<double>(Clock::now()-began).count();++soft_n;if(!std::isfinite(cost)||cost<0.)throw std::runtime_error("Invalid pose edge cost");if(cache)pose_costs_.emplace(key,cost);}
    // A pure objective that cannot improve this node needs no collision query.
    // Its geometry remains unknown, rather than being cached as an obstacle.
    if(base+(turn+cost)>=best)return -1.;
    bool valid=certified;if(!valid){const auto began=Clock::now();valid=pose_validator_(a,b);hard_s+=std::chrono::duration<double>(Clock::now()-began).count();++hard_n;}
    if(!valid)cost=-1.;
    if(cache)pose_edges_.emplace(key,cost);return cost;
  };
  const auto attempt=[&](Node *a,Node *b,double departure,double arrival,bool cache){
    if(closed.count(b))return;
    const double lower=std::sqrt((b->GridPosition()-a->GridPosition()).squaredNorm()+std::pow((b->height-a->height)/resolution_,2))+
      pose_angular_lower_bound_*std::abs(std::remainder(arrival-departure,2*M_PI));
    const double departure_lower=pose_angular_lower_bound_*std::abs(std::remainder(departure-a->pose_yaw,2*M_PI));
    // The original objective includes both translation and swept cylinder
    // centre rotation. Use both unavoidable distances before an exact query.
    if(a->g+(departure_lower+lower)>=b->g)return;
    Node source=*a,target=*b;source.pose_yaw=departure;target.pose_yaw=arrival;double cost=0.;
    if(std::abs(std::remainder(departure-a->pose_yaw,2*M_PI))>1e-10){
      if(!a->free_heading)throw std::runtime_error("Uncertified merged pose turn");
      cost=edge(*a,source,true,true,0.,0.,std::numeric_limits<double>::infinity());if(cost<0.)throw std::runtime_error("Free rotation certificate disagrees with edge cache");
    }
    if(a->g+cost+lower>=b->g)return;
    const double travel=edge(source,target,cache,false,a->g,cost,b->g);if(travel<0.)return;cost+=travel;
    const double g=a->g+cost;if(g<b->g){b->g=g;b->f=g+heuristic(b);b->parent=a;b->pose_yaw=arrival;b->parent_departure_yaw=departure;open.push({b->f,g,b});}
  };
  const auto neighbours=[&](int x,int y,double height,auto visit){
    if(x<0||y<0||x>=max_y_||y>=max_x_)return;std::set<int> heights;
    for(int l=0;l<max_layers_;++l){const Node &n=grid_map_[l][x][y];if(n.height<=-50.||std::abs(n.height-height)>=.26||!heights.insert(n.idx[0]).second)continue;
      if(!pose_necessary_cells_.empty()&&!pose_necessary_cells_[cell_id(n)])continue;
      visit(n);}
  };
  while(!open.empty()) {
    const auto item=open.top();open.pop();Node *current=item.node;if(item.g!=current->g||closed.count(current))continue;
    if(current==&last){
      std::vector<Node*> chain;for(Node *p=current;p;p=p->parent)chain.push_back(p);std::reverse(chain.begin(),chain.end());
      const auto append=[&](const Node &n,double yaw){auto copy=std::make_unique<Node>(n);copy->pose_yaw=yaw;copy->parent=search_result_.empty()?nullptr:search_result_.back();search_result_.push_back(copy.get());pose_nodes_.push_back(std::move(copy));};
      for(size_t i=0;i<chain.size();++i){
        if(i&&std::isfinite(chain[i]->parent_departure_yaw)&&std::abs(std::remainder(chain[i]->parent_departure_yaw-chain[i-1]->pose_yaw,2*M_PI))>1e-10)append(*chain[i-1],chain[i]->parent_departure_yaw);
        append(*chain[i],chain[i]->pose_yaw);
      }
      phase(nodes.size(),closed.size());return true;
    }
    closed.insert(current);
    if((current->idx.tail<2>()-last.idx.tail<2>()).cwiseAbs().maxCoeff()<=1&&std::abs(current->SupportHeight()-last.SupportHeight())<.26){
      const auto d=last.GridPosition()-current->GridPosition();const double goal_yaw=std::isfinite(pose_goal_yaw_)?pose_goal_yaw_:d.norm()>1e-10?std::atan2(d(1),d(0)):current->pose_yaw;
      if(current->free_heading)for(int h=0;h<16;++h)attempt(current,&last,h*M_PI/8,goal_yaw,false);
      else attempt(current,&last,current->pose_yaw,goal_yaw,false);
    }
    if(current==&first){
      for(int x=current->idx[1]-1;x<=current->idx[1]+1;++x)for(int y=current->idx[2]-1;y<=current->idx[2]+1;++y)
        neighbours(x,y,current->SupportHeight(),[&](const Node &n){for(int h=0;h<16;++h)attempt(current,get(n,h),current->pose_yaw,h*M_PI/8,false);});
    }else{
      const int here=heading(current->pose_yaw);
      if(!current->free_heading){attempt(current,get(*current,(here+1)%16),current->pose_yaw,(here+1)%16*M_PI/8,true);attempt(current,get(*current,(here+15)%16),current->pose_yaw,(here+15)%16*M_PI/8,true);}
      for(int h=0;h<16;++h){if((!current->free_heading&&h!=here)||(current->free_heading&&h%2))continue;
        neighbours(current->idx[1]+pose_dx[h],current->idx[2]+pose_dy[h],current->SupportHeight(),[&](const Node &n){attempt(current,get(n,h),h*M_PI/8,h*M_PI/8,true);});
        if(!current->free_heading)for(int turn:{-1,1}){const int next=(h+turn+16)%16;
          neighbours(current->idx[1]+pose_dx[h]+pose_dx[next],current->idx[2]+pose_dy[h]+pose_dy[next],current->SupportHeight(),[&](const Node &n){attempt(current,get(n,next),h*M_PI/8,next*M_PI/8,true);});
        }
      }
    }
  }
  phase(nodes.size(),closed.size());return false;
}
