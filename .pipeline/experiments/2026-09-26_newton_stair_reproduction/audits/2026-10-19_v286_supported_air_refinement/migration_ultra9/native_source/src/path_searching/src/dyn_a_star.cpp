#include <plan_env/goal_region_bounds.h>
#include "path_searching/dyn_a_star.h"
#include <algorithm>
#include <chrono>
#include <cmath>

using namespace std;
using namespace Eigen;

AStar::~AStar()
{
    for (int i = 0; i < POOL_SIZE_(0); i++)
        for (int j = 0; j < POOL_SIZE_(1); j++)
            for (int k = 0; k < POOL_SIZE_(2); k++)
                delete GridNodeMap_[i][j][k];
}

void AStar::initGridMap(GridMap::Ptr occ_map, const Eigen::Vector3i pool_size)
{
    POOL_SIZE_ = pool_size;
    CENTER_IDX_ = pool_size / 2;

    GridNodeMap_ = new GridNodePtr **[POOL_SIZE_(0)];
    for (int i = 0; i < POOL_SIZE_(0); i++)
    {
        GridNodeMap_[i] = new GridNodePtr *[POOL_SIZE_(1)];
        for (int j = 0; j < POOL_SIZE_(1); j++)
        {
            GridNodeMap_[i][j] = new GridNodePtr[POOL_SIZE_(2)];
            for (int k = 0; k < POOL_SIZE_(2); k++)
            {
                GridNodeMap_[i][j][k] = new GridNode;
            }
        }
    }

    grid_map_ = occ_map;
}

double AStar::getDiagHeu(GridNodePtr node1, GridNodePtr node2)
{
    double dx = abs(node1->index(0) - node2->index(0));
    double dy = abs(node1->index(1) - node2->index(1));
    double dz = abs(node1->index(2) - node2->index(2));

    double h = 0.0;
    int diag = min(min(dx, dy), dz);
    dx -= diag;
    dy -= diag;
    dz -= diag;

    if (dx == 0)
    {
        h = 1.0 * sqrt(3.0) * diag + sqrt(2.0) * min(dy, dz) + 1.0 * abs(dy - dz);
    }
    if (dy == 0)
    {
        h = 1.0 * sqrt(3.0) * diag + sqrt(2.0) * min(dx, dz) + 1.0 * abs(dx - dz);
    }
    if (dz == 0)
    {
        h = 1.0 * sqrt(3.0) * diag + sqrt(2.0) * min(dx, dy) + 1.0 * abs(dx - dy);
    }
    return h;
}

double AStar::getManhHeu(GridNodePtr node1, GridNodePtr node2)
{
    double dx = abs(node1->index(0) - node2->index(0));
    double dy = abs(node1->index(1) - node2->index(1));
    double dz = abs(node1->index(2) - node2->index(2));

    return dx + dy + dz;
}

double AStar::getEuclHeu(GridNodePtr node1, GridNodePtr node2)
{
    return (node2->index - node1->index).norm();
}

vector<GridNodePtr> AStar::retrievePath(GridNodePtr current)
{
    vector<GridNodePtr> path;
    path.push_back(current);

    while (current->cameFrom != NULL)
    {
        current = current->cameFrom;
        path.push_back(current);
    }

    return path;
}

bool AStar::ConvertToIndexAndAdjustStartEndPoints(Vector3d start_pt, Vector3d end_pt, Vector3i &start_idx, Vector3i &end_idx, double goal_tolerance)
{
    if (!Coord2Index(start_pt, start_idx) || !Coord2Index(end_pt, end_idx))
        return false;

    if(terrain_search_) {
      // Quantization adjusts XY only. Every proposal is put back on the
      // nearest support layer, and endpoints use actual connector tangents.
      // Do not retreat indefinitely along a 3D chord through stair risers.
      const auto adjust=[&](const Vector3d &point,Vector3i &index,bool start) {
        const Vector3i initial=index;
        for(int ring=0;ring<=2;++ring)for(int dx=-ring;dx<=ring;++dx)for(int dy=-ring;dy<=ring;++dy) {
          if(std::max(std::abs(dx),std::abs(dy))!=ring)continue;
          Vector3i candidate=initial+Vector3i(dx,dy,0);
          if(candidate.x()<1 || candidate.x()>=POOL_SIZE_.x()-1 || candidate.y()<1 || candidate.y()>=POOL_SIZE_.y()-1)continue;
          Vector3d projected=latticeCoord(candidate);projected.z()=point.z();
          if(!grid_map_->terrainSupportHeight(projected,projected.z()))continue;
          candidate.z()=reactive_stair::nearestGridOffset((projected.z()-center_.z())*inv_step_size_)+CENTER_IDX_.z();
          if(candidate.z()<1 || candidate.z()>=POOL_SIZE_.z()-1)continue;
          bool clear=false;
          // Quantization is not a physical connector. Use an actual adjacent
          // support edge to determine a feasible arrival/departure tangent.
          for(int dx=-1;dx<=1&&!clear;++dx)for(int dy=-1;dy<=1&&!clear;++dy) {
            if(dx==0&&dy==0)continue;
            Vector3d adjacent=projected+step_size_*Vector3d(dx,dy,0);
            if(!grid_map_->terrainSupportHeight(adjacent,adjacent.z()))continue;
            clear=start ? grid_map_->collisionFreeSegment(projected,adjacent) :
                grid_map_->collisionFreeSegment(adjacent,projected);
          }
          if(!clear)continue;
          index=candidate;terrain_points_[terrainKey(index)]=projected;return true;
        }
        return false;
      };
      // A goal region may contain a valid reached neighbor even if its center
      // is occupied. Keep the original center/tolerance; search certifies it.
      return adjust(start_pt,start_idx,true) &&
          (goal_tolerance>0. || adjust(end_pt,end_idx,false));
    }

    Eigen::Vector3d start_to_end = end_pt - start_pt;
    if (start_to_end.norm() < 1e-6)
        return false;
    const double path_yaw = std::atan2(start_to_end(1), start_to_end(0));
    start_to_end.normalize();

    int occ = checkOccupancy(Index2Coord(start_idx), path_yaw);
    if (occ)
    {
        //ROS_WARN("Start point is insdide an obstacle.");
        int attempts=0;
        do
        {
            if(++attempts>2)return false;
            start_pt -= start_to_end * step_size_;
            if (!Coord2Index(start_pt, start_idx))
                return false;

            occ = checkOccupancy(Index2Coord(start_idx), path_yaw);
            if (occ == -1)
            {
                RCLCPP_WARN(rclcpp::get_logger("path_searching"), "[Astar] Start point outside the map region.");
                return false;
            }
        } while (occ);
    }

    occ = checkOccupancy(Index2Coord(end_idx), path_yaw);
    if (occ)
    {
        //ROS_WARN("End point is insdide an obstacle.");
        int attempts=0;
        do
        {
            if(++attempts>2)return false;
            end_pt += start_to_end * step_size_;
            if (!Coord2Index(end_pt, end_idx))
                return false;

            occ = checkOccupancy(Index2Coord(end_idx), path_yaw);
            if (occ == -1)
            {
                RCLCPP_WARN(rclcpp::get_logger("path_searching"), "[Astar] End point outside the map region.");
                return false;
            }
        } while (occ);
    }

    return true;
}

ASTAR_RET AStar::AstarSearch(const double step_size, Vector3d start_pt, Vector3d end_pt, bool exact_endpoint, double goal_tolerance)
{
    const auto time_1 = std::chrono::steady_clock::now();
    // Clear result state even when initialization fails or modes are switched.
    gridPath_.clear();
    has_exact_goal_ = false;
    if (!std::isfinite(goal_tolerance) || goal_tolerance < 0.0 ||
        (!exact_endpoint && goal_tolerance != 0.0 && !grid_map_->hasTerrainSupport()) ||
        !std::isfinite(step_size) || step_size <= 0.0 ||
        !std::isfinite(1.0 / step_size) || !start_pt.allFinite() || !end_pt.allFinite())
      return ASTAR_RET::INIT_ERR;
    const Eigen::Vector3d search_span = (end_pt - start_pt) / step_size;
    if (!search_span.allFinite() || search_span.cwiseAbs().maxCoeff() > std::numeric_limits<int>::max() / 4.0)
      return ASTAR_RET::INIT_ERR;
    ++rounds_;

    // Cooperate with the existing mutually exclusive native callback lane.
    // Queued body/cloud messages must reach the mapper during a long search,
    // rather than only after its 200 ms wall budget has expired. Hold this
    // search's immutable read snapshot while the background mapper works;
    // the caller's original refresh/final validation adopts completed maps.
    // Synchronous input mutations still invalidate the search below.
    const bool live_inputs = grid_map_->planningInputsReady();
    const auto search_revision = grid_map_->mapRevision();
    const double search_observation = grid_map_->observationStamp();
    const Eigen::Vector3d search_origin = live_inputs ? grid_map_->getOrigin() : Eigen::Vector3d::Zero();
    auto next_input_poll = time_1 + std::chrono::milliseconds(20);
    const auto inputs_current = [&]() {
        if (!live_inputs || std::chrono::steady_clock::now() < next_input_poll) return true;
        grid_map_->refreshSensorInputs("astar_search", -1, false);
        next_input_poll = std::chrono::steady_clock::now() + std::chrono::milliseconds(20);
        if (!grid_map_->planningInputsReady() || grid_map_->mapRevision() != search_revision ||
            grid_map_->observationStamp() != search_observation ||
            (grid_map_->getOrigin().array() != search_origin.array()).any()) {
            gridPath_.clear();
            has_exact_goal_ = false;
            RCLCPP_INFO(rclcpp::get_logger("path_searching"),
                        "astar_inputs_changed search_revision=%lu current_revision=%lu source_stamp=%.9f current_stamp=%.9f",
                        static_cast<unsigned long>(search_revision), static_cast<unsigned long>(grid_map_->mapRevision()),
                        search_observation, grid_map_->observationStamp());
            return false;
        }
        return true;
    };

    terrain_points_.clear();
    // Exact endpoint search keeps its existing contract; local repair searches
    // follow the available support surface instead of a start/end sloped plane.
    terrain_search_=!exact_endpoint && grid_map_->hasTerrainSupport();
    step_size_ = step_size;
    inv_step_size_ = 1 / step_size;
    for (int axis = 0; axis < 3; ++axis)
      center_(axis) = reactive_stair::startAlignedSearchCenter(start_pt(axis), end_pt(axis), step_size_);

    Vector3i start_idx, end_idx;
    const bool endpoints_valid = exact_endpoint
        ? (Coord2Index(start_pt, start_idx) && Coord2Index(end_pt, end_idx) &&
           (Index2Coord(start_idx) - start_pt).norm() <= 1e-6)
        : ConvertToIndexAndAdjustStartEndPoints(start_pt, end_pt, start_idx, end_idx, goal_tolerance);
    if (!endpoints_valid)
    {
        RCLCPP_ERROR(rclcpp::get_logger("path_searching"),
                     "Unable to handle the initial or end point, force return!");
        return ASTAR_RET::INIT_ERR;
    }

    // if ( start_pt(0) > -1 && start_pt(0) < 0 )
    //     cout << "start_pt=" << start_pt.transpose() << " end_pt=" << end_pt.transpose() << endl;

    if (goal_region_precheck_enabled && exact_endpoint && goal_tolerance > 0.0) {
        reactive_stair::PlanningProfile::Scope proof(grid_map_->planning_profile_, reactive_stair::PlanningProfile::GoalProof);
        Eigen::Vector3d lower, upper;
        if (grid_map_->bodyCenterBounds(lower, upper) &&
            !reactive_stair::goalRegionMayFit(end_pt, goal_tolerance, lower, upper,
                center_, step_size_, POOL_SIZE_, CENTER_IDX_, start_idx, end_idx, use_upstream_search_plane)) {
            ++goal_region_rejections;
            RCLCPP_INFO(rclcpp::get_logger("path_searching"), "V50_GOAL_REGION_EMPTY bounds_certificate=1");
            return ASTAR_RET::SEARCH_ERR;
        }
    }

    if (goal_endpoint_evidence_enabled && exact_endpoint && goal_tolerance > 0.0 && use_upstream_search_plane) {
        reactive_stair::PlanningProfile::Scope proof(grid_map_->planning_profile_, reactive_stair::PlanningProfile::GoalProof);
        Eigen::Vector3d lower, upper;
        if (grid_map_->bodyCenterBounds(lower, upper) &&
            !reactive_stair::goalRegionMayFitWithEvidence(end_pt, goal_tolerance, lower, upper,
                center_, step_size_, POOL_SIZE_, CENTER_IDX_, start_idx, end_idx, true,
                [this](const Eigen::Vector3d &point) { return grid_map_->bodyEndpointMayBeObserved(point); })) {
            ++goal_region_rejections;
            RCLCPP_INFO(rclcpp::get_logger("path_searching"), "V58_GOAL_ENDPOINT_EMPTY live_unknown_certificate=1");
            return ASTAR_RET::SEARCH_ERR;
        }
    }

    const Eigen::Vector3d search_start = Index2Coord(start_idx);
    const Eigen::Vector3d search_end = Index2Coord(end_idx);
    const Eigen::Vector2d search_start_xy = search_start.head<2>();
    const Eigen::Vector2d search_xy_delta = search_end.head<2>() - search_start_xy;
    const double search_xy_len2 = search_xy_delta.squaredNorm();

    auto interpolateZIndexOnSearchPlane = [&](const int x_idx, const int y_idx) -> int {
        if (search_xy_len2 < 1e-8)
            return start_idx(2);

        Eigen::Vector3i sample_idx(x_idx, y_idx, start_idx(2));
        const Eigen::Vector2d sample_xy = Index2Coord(sample_idx).head<2>();
        double ratio = (sample_xy - search_start_xy).dot(search_xy_delta) / search_xy_len2;
        ratio = std::max(0.0, std::min(1.0, ratio));

        const double z = search_start(2) + ratio * (search_end(2) - search_start(2));
        return static_cast<int>((z - center_(2)) * inv_step_size_ + 0.5) + CENTER_IDX_(2);
    };

    GridNodePtr startPtr = GridNodeMap_[start_idx(0)][start_idx(1)][start_idx(2)];
    GridNodePtr endPtr = GridNodeMap_[end_idx(0)][end_idx(1)][end_idx(2)];

    std::priority_queue<OpenSetEntry, std::vector<OpenSetEntry>, NodeComparator> empty;
    openSet_.swap(empty);

    GridNodePtr neighborPtr = NULL;
    GridNodePtr current = NULL;

    endPtr->index = end_idx;

    startPtr->index = start_idx;
    startPtr->rounds = rounds_;
    startPtr->gScore = 0;
    startPtr->fScore = getHeu(startPtr, endPtr);
    startPtr->state = GridNode::OPENSET; //put start node in open set
    startPtr->cameFrom = NULL;
    ++startPtr->queue_revision;
    openSet_.emplace(startPtr); //put start in open set

    double tentative_gScore;

    struct TerminalCandidate {
        GridNodePtr node;
        double cost_m;
    };
    // Per-call state: only current, reached nodes are eligible for recovery.
    std::vector<TerminalCandidate> terminal_candidates;
    GridNodePtr best_tolerance_node = nullptr;
    double best_tolerance_distance = std::numeric_limits<double>::infinity();
    int approach_iterations = 0;
    int num_iter = 0;
    while (!openSet_.empty())
    {
        if (!inputs_current()) return ASTAR_RET::SEARCH_ERR;
        // The unchanged wall budget also covers obsolete heap records.
        const auto time_2 = std::chrono::steady_clock::now();
        if (std::chrono::duration<double>(time_2 - time_1).count() > 0.2)
        {
            RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                        "Failed in A-star path search: 0.2 second time limit exceeded");
            return ASTAR_RET::SEARCH_ERR;
        }
        num_iter++;
        const OpenSetEntry entry = openSet_.top();
        openSet_.pop();
        if (!entry.current(rounds_)) continue;
        current = entry.node;
        if (exact_endpoint) {
            const double terminal_distance = (Index2Coord(current->index) - end_pt).norm();
            const double cost = current->gScore * step_size_ + terminal_distance;
            if (terminal_distance > 2.0 * step_size_ && std::isfinite(cost))
                terminal_candidates.push_back({current, cost});
        }

        // if ( num_iter < 10000 )
        //     cout << "current=" << current->index.transpose() << endl;

        // Nav2 Smac AStar, Humble 3c3db59 (Apache-2.0): a reached
        // node inside goal tolerance is a valid local proposal. Every edge
        // was checked by SCAN. Default tolerance zero keeps exact semantics.
        if (goal_tolerance > 0.0 && current->cameFrom != nullptr &&
            (Index2Coord(current->index) - end_pt).norm() <= goal_tolerance) {
            const Eigen::Vector3d proposal = Index2Coord(current->index);
            const Eigen::Vector3d direction = proposal - Index2Coord(current->cameFrom->index);
            const double selection_yaw = std::atan2(direction.y(), direction.x());
            const double stopped_yaw = grid_map_->collisionTrajectoryYaw(
                proposal, proposal, Eigen::Vector3d::Zero());
            // A reached edge alone is insufficient for an anisotropic robot.
            // Match the FSM target query and the stopped endpoint query too.
            if (grid_map_->getInflateOccupancy(proposal, selection_yaw) == 0 &&
                grid_map_->getInflateOccupancy(proposal, stopped_yaw) == 0) {
                const double distance = (proposal - end_pt).squaredNorm();
                if (distance < best_tolerance_distance) {
                    best_tolerance_distance = distance;
                    best_tolerance_node = current;
                }
            }
        }
        // Smac's bounded approach phase improves the best reached endpoint
        // instead of returning the first point that enters the tolerance area.
        if (best_tolerance_node && ++approach_iterations >= goal_approach_max_iterations) {
            gridPath_ = retrievePath(best_tolerance_node);
            return ASTAR_RET::SUCCESS;
        }
        if (exact_endpoint && (Index2Coord(current->index) - end_pt).norm() <= 2.0 * step_size_)
        {
            // This is an explicit additional terminal edge, checked with the
            // same heading, endpoint and half-voxel rules as every grid edge.
            const bool terminal_clear = grid_map_->collisionFreeSegment(Index2Coord(current->index), end_pt);
            if (std::chrono::duration<double>(std::chrono::steady_clock::now() - time_1).count() > 0.2)
            {
                RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                            "Failed in A-star path search: 0.2 second time limit exceeded during exact endpoint check");
                return ASTAR_RET::SEARCH_ERR;
            }
            if (terminal_clear)
            {
                gridPath_ = retrievePath(current);
                exact_goal_ = end_pt;
                has_exact_goal_ = true;
                return ASTAR_RET::SUCCESS;
            }
            // A rejected connector, including one at the snapped goal node,
            // does not finish the search. Other approach directions can work.
        }
        if (!exact_endpoint && current->index(0) == endPtr->index(0) && current->index(1) == endPtr->index(1) && current->index(2) == endPtr->index(2) &&
            (goal_tolerance==0. || (Index2Coord(current->index)-end_pt).norm()<=goal_tolerance))
        {
            // ros::Time time_2 = ros::Time::now();
            // printf("\033[34mA star iter:%d, time:%.3f\033[0m\n",num_iter, (time_2 - time_1).toSec()*1000);
            // if((time_2 - time_1).toSec() > 0.1)
            //     ROS_WARN("Time consume in A star path finding is %f", (time_2 - time_1).toSec() );
            gridPath_ = retrievePath(current);
            return ASTAR_RET::SUCCESS;
        }
        current->state = GridNode::CLOSEDSET; //move current node from open set to closed set.

        for (int dx = -1; dx <= 1; dx++)
            for (int dy = -1; dy <= 1; dy++)
              for (int dz_step = ((terrain_search_ || use_upstream_search_plane) ? 0 : -1); dz_step <= ((terrain_search_ || use_upstream_search_plane) ? 0 : 1); dz_step++)
            {
                if (dx == 0 && dy == 0 && dz_step == 0)
                    continue;

                Vector3i neighborIdx;
                neighborIdx(0) = (current->index)(0) + dx;
                neighborIdx(1) = (current->index)(1) + dy;
                Eigen::Vector3d terrain_position;
                if(terrain_search_) {
                  terrain_position=latticeCoord(Vector3i(neighborIdx.x(),neighborIdx.y(),current->index.z()));
                  terrain_position.z()=Index2Coord(current->index).z();
                  if(!grid_map_->terrainSupportHeight(terrain_position,terrain_position.z()))continue;
                  neighborIdx.z()=reactive_stair::nearestGridOffset((terrain_position.z()-center_.z())*inv_step_size_)+CENTER_IDX_.z();
                } else neighborIdx(2) = use_upstream_search_plane
                    ? interpolateZIndexOnSearchPlane(neighborIdx(0), neighborIdx(1))
                    : current->index(2) + dz_step;

                if (neighborIdx(0) < 1 || neighborIdx(0) >= POOL_SIZE_(0) - 1 || neighborIdx(1) < 1 || neighborIdx(1) >= POOL_SIZE_(1) - 1 || neighborIdx(2) < 1 || neighborIdx(2) >= POOL_SIZE_(2) - 1)
                {
                    continue;
                }

                if(terrain_search_) {
                  const auto inserted=terrain_points_.emplace(terrainKey(neighborIdx),terrain_position);
                  // A visited voxel owns its exact support elevation for this
                  // search. Never mutate geometry after validating its edges.
                  if(!inserted.second && (inserted.first->second-terrain_position).norm()>1e-8)continue;
                }
                neighborPtr = GridNodeMap_[neighborIdx(0)][neighborIdx(1)][neighborIdx(2)];
                neighborPtr->index = neighborIdx;

                bool flag_explored = neighborPtr->rounds == rounds_;

                if (flag_explored && neighborPtr->state == GridNode::CLOSEDSET)
                {
                    continue; //in closed set.
                }

                // A rejected approach must leave this node undiscovered.

                if (!grid_map_->collisionFreeSegment(Index2Coord(current->index),
                                                     Index2Coord(neighborPtr->index)))
                {
                    continue;
                }

                const int dz = neighborIdx(2) - current->index(2);
                double static_cost = terrain_search_ ?
                    (Index2Coord(neighborIdx)-Index2Coord(current->index)).norm()*inv_step_size_ :
                    sqrt(dx * dx + dy * dy + dz * dz);
                tentative_gScore = current->gScore + static_cost;

                if (!flag_explored)
                {
                    // Discover only after the original occupancy check passes.
                    neighborPtr->rounds = rounds_;
                    ++neighborPtr->queue_revision;
                    neighborPtr->state = GridNode::OPENSET;
                    neighborPtr->cameFrom = current;
                    neighborPtr->gScore = tentative_gScore;
                    neighborPtr->fScore = tentative_gScore + getHeu(neighborPtr, endPtr);
                    openSet_.emplace(neighborPtr); //put neighbor in open set and record it.
                }
                else if (tentative_gScore < neighborPtr->gScore)
                { // Improved cost: enqueue a fresh key and invalidate old records.
                    ++neighborPtr->queue_revision;
                    neighborPtr->cameFrom = current;
                    neighborPtr->gScore = tentative_gScore;
                    neighborPtr->fScore = tentative_gScore + getHeu(neighborPtr, endPtr);
                    openSet_.emplace(neighborPtr);
                }
            }

    }

    if (!inputs_current()) return ASTAR_RET::SEARCH_ERR;
    if (best_tolerance_node) {
        gridPath_ = retrievePath(best_tolerance_node);
        return ASTAR_RET::SUCCESS;
    }
    if (exact_endpoint && !terminal_candidates.empty()) {
        // Normal search exhausted. Near connectors were already checked.
        // Use its remaining budget, not a new deadline for this second stage.
        const auto expired = [&]() {
            if (!inputs_current()) return true;
            if (std::chrono::duration<double>(std::chrono::steady_clock::now() - time_1).count() <= 0.2)
                return false;
            gridPath_.clear();
            has_exact_goal_ = false;
            RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                        "Failed in A-star path search: 0.2 second time limit exceeded during terminal recovery");
            return true;
        };
        if (expired()) return ASTAR_RET::SEARCH_ERR;
        std::stable_sort(terminal_candidates.begin(), terminal_candidates.end(),
                        [](const TerminalCandidate& a, const TerminalCandidate& b) {
                            return a.cost_m < b.cost_m;
                        });
        if (expired()) return ASTAR_RET::SEARCH_ERR;
        size_t tried = 0;
        for (const auto& candidate : terminal_candidates) {
            if (expired()) return ASTAR_RET::SEARCH_ERR;
            const Eigen::Vector3d from = Index2Coord(candidate.node->index);
            const bool clear = grid_map_->collisionFreeSegment(from, end_pt);
            ++tried;
            if (expired()) return ASTAR_RET::SEARCH_ERR;
            if (!clear) continue;
            auto recovered_path = retrievePath(candidate.node);
            if (expired()) return ASTAR_RET::SEARCH_ERR;
            gridPath_ = std::move(recovered_path);
            exact_goal_ = end_pt;
            has_exact_goal_ = true;
            RCLCPP_INFO(rclcpp::get_logger("path_searching"),
                        "A-star exact endpoint recovered connector_m=%.12f cost_m=%.12f tried=%zu candidates=%zu",
                        (from - end_pt).norm(), candidate.cost_m, tried, terminal_candidates.size());
            return ASTAR_RET::SUCCESS;
        }
    }
    const auto time_2 = std::chrono::steady_clock::now();

    const double elapsed = std::chrono::duration<double>(time_2 - time_1).count();
    if (elapsed > 0.1)
        RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                    "A-star path search took %.3fs, iter=%d", elapsed, num_iter);

    return ASTAR_RET::SEARCH_ERR;
}

vector<Vector3d> AStar::getPath()
{
    vector<Vector3d> path;

    for (auto ptr : gridPath_)
        path.push_back(Index2Coord(ptr->index));

    reverse(path.begin(), path.end());
    if (has_exact_goal_ && !path.empty() && (path.back() - exact_goal_).squaredNorm() > 0.0)
      path.push_back(exact_goal_);
    return path;
}
