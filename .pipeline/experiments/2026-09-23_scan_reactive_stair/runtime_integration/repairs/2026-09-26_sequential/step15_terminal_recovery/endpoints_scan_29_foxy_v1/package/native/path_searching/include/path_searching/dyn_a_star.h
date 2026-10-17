#ifndef _DYN_A_STAR_H_
#define _DYN_A_STAR_H_

#include <iostream>
#include <rclcpp/rclcpp.hpp>
#include <Eigen/Eigen>
#include <plan_env/grid_map.h>
#include <plan_env/astar_grid_coordinates.h>
#include <queue>
#include <limits>
#include <cstdint>

constexpr double inf = std::numeric_limits<double>::infinity();
struct GridNode;
typedef GridNode *GridNodePtr;

enum ASTAR_RET
{
	SUCCESS,
	INIT_ERR,
	SEARCH_ERR
};

struct GridNode
{
	enum enum_state
	{
		OPENSET = 1,
		CLOSEDSET = 2,
		UNDEFINED = 3
	};

	int rounds{0}; // Distinguish every call
	enum enum_state state
	{
		UNDEFINED
	};
	Eigen::Vector3i index;

	double gScore{inf}, fScore{inf};
	GridNodePtr cameFrom{NULL};
	std::uint64_t queue_revision{0};
};

// Heap keys are snapshots, not references to mutable node scores. A better
// path creates a new record; obsolete records cannot close or finish a node.
struct OpenSetEntry
{
    GridNodePtr node;
    double f_at_enqueue;
    std::uint64_t revision;
    int round;

    explicit OpenSetEntry(GridNodePtr value)
        : node(value), f_at_enqueue(value->fScore),
          revision(value->queue_revision), round(value->rounds) {}

    bool current(int search_round) const
    {
        return round == search_round && node->rounds == search_round &&
               revision == node->queue_revision && node->state == GridNode::OPENSET;
    }
};

class NodeComparator
{
public:
	bool operator()(const OpenSetEntry &node1, const OpenSetEntry &node2) const
	{
		return node1.f_at_enqueue > node2.f_at_enqueue;
	}
};

class AStar
{
private:
	GridMap::Ptr grid_map_;

	inline void coord2gridIndexFast(const double x, const double y, const double z, int &id_x, int &id_y, int &id_z);

	double getDiagHeu(GridNodePtr node1, GridNodePtr node2);
	double getManhHeu(GridNodePtr node1, GridNodePtr node2);
	double getEuclHeu(GridNodePtr node1, GridNodePtr node2);
	inline double getHeu(GridNodePtr node1, GridNodePtr node2);

	bool ConvertToIndexAndAdjustStartEndPoints(const Eigen::Vector3d start_pt, const Eigen::Vector3d end_pt, Eigen::Vector3i &start_idx, Eigen::Vector3i &end_idx);

	inline Eigen::Vector3d Index2Coord(const Eigen::Vector3i &index) const;
	inline bool Coord2Index(const Eigen::Vector3d &pt, Eigen::Vector3i &idx) const;

	//bool (*checkOccupancyPtr)( const Eigen::Vector3d &pos );

	inline int checkOccupancy(const Eigen::Vector3d &pos, const double yaw) { return grid_map_->getInflateOccupancy(pos, yaw); }

	std::vector<GridNodePtr> retrievePath(GridNodePtr current);

	double step_size_, inv_step_size_;
	Eigen::Vector3d center_;
	Eigen::Vector3i CENTER_IDX_, POOL_SIZE_;
	const double tie_breaker_ = 1.0 + 1.0 / 10000;

	std::vector<GridNodePtr> gridPath_;
    bool has_exact_goal_{false};
    Eigen::Vector3d exact_goal_{Eigen::Vector3d::Zero()};

	GridNodePtr ***GridNodeMap_;
	std::priority_queue<OpenSetEntry, std::vector<OpenSetEntry>, NodeComparator> openSet_;

	int rounds_{0};

public:
	typedef std::shared_ptr<AStar> Ptr;

	AStar(){};
	~AStar();

	void initGridMap(GridMap::Ptr occ_map, const Eigen::Vector3i pool_size);

    // Exact mode preserves the requested endpoints and checks a terminal edge
    // from a popped lattice node within two cells (3D Euclidean distance).
    // After queue exhaustion only, longer checked edges can recover a result
    // within the same total budget, ordered by complete reached-path cost.
    // The default keeps the optimizer's existing adjusted-endpoint behavior.
    ASTAR_RET AstarSearch(const double step_size, Eigen::Vector3d start_pt,
                         Eigen::Vector3d end_pt, bool exact_endpoint = false);

	std::vector<Eigen::Vector3d> getPath();
};

inline double AStar::getHeu(GridNodePtr node1, GridNodePtr node2)
{
	return tie_breaker_ * getDiagHeu(node1, node2);
}

inline Eigen::Vector3d AStar::Index2Coord(const Eigen::Vector3i &index) const
{
	return ((index - CENTER_IDX_).cast<double>() * step_size_) + center_;
};

inline bool AStar::Coord2Index(const Eigen::Vector3d &pt, Eigen::Vector3i &idx) const
{
    if (!pt.allFinite()) return false;
    for (int axis = 0; axis < 3; ++axis)
      idx(axis) = reactive_stair::nearestGridOffset((pt(axis) - center_(axis)) * inv_step_size_) + CENTER_IDX_(axis);

	if (idx(0) < 0 || idx(0) >= POOL_SIZE_(0) || idx(1) < 0 || idx(1) >= POOL_SIZE_(1) || idx(2) < 0 || idx(2) >= POOL_SIZE_(2))
	{
		RCLCPP_ERROR(rclcpp::get_logger("path_searching"),
		             "Ran out of pool, index=%d %d %d", idx(0), idx(1), idx(2));
		return false;
	}

	return true;
};

#endif
