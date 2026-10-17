#include <gtest/gtest.h>
#include <plan_env/grid_map.h>
#include <fstream>
#include <filesystem>

TEST(SharedSupport, QualifiedPhysicalGridDefinesBoundaryIdentityOnly) {
  using namespace reactive_stair;
  int argc=0;rclcpp::init(argc,nullptr);
  {
    auto node=std::make_shared<rclcpp::Node>("canonical_support_test");GridMap map;map.node_=node.get();
    auto &state=*map.owned_state_;auto support=std::const_pointer_cast<GridMapSupportState>(state.support_);
    state.mp_.frame_id_="world";state.mp_.double_cylinder_radius_=.35;state.mp_.double_cylinder_offset_=.18;
    state.mp_.map_min_boundary_=Eigen::Vector3d(-10.,-10.,-10.);state.mp_.map_max_boundary_=Eigen::Vector3d(10.,10.,10.);
    support->reactive_parameters_.body_clearance_m=.3;support->reactive_parameters_.body_height_tolerance_m=.12;
    support->reactive_parameters_.terrain_max_age_s=86400.;const double stamp=node->now().seconds();
    auto &nav=support->reactive_navigation_ground_;nav.source_id="nav";nav.frame="world";nav.stamp_s=stamp;
    nav.resolution_m=.1;nav.origin_x_m=nav.origin_y_m=1e-7;
    auto &physical=support->reactive_physical_floor_;physical.source_id="physical";physical.frame="world";
    physical.stamp_s=stamp;physical.resolution_m=.1;
    for(int x=-5;x<=25;++x)for(int y=-5;y<=25;++y){nav.cells[{x,y}]={{Support::Flat,0.}};physical.cells[{x,y}]={{0.,0.}};}
    nav.cells[{9,9}]={{Support::Stair,-.15}};
    support->reactive_ground_=support->reactive_terrain_=nav;
    support->reactive_surface_ground_=nav;support->reactive_surface_ground_.source_id="surface";
    support->physical_floor_decoded_valid_=true;
    state.reactive_physical_floor_topic_="physical";state.physical_floor_source_id_="physical";
    state.physical_floor_navigation_source_id_="nav";state.physical_floor_surface_source_id_="surface";
    state.reactive_surface_ground_topic_="surface";state.reactive_terrain_band_m_=.03;
    support->reactive_decision_=CollisionDecision(support->reactive_parameters_);
    ASSERT_TRUE(support->reactive_decision_.acceptTerrain(nav));
    Query q{"world",stamp,1.,1.,.35,true};Cell2 cell;
    EXPECT_EQ(support->reactive_decision_.supportVerdict(q),Verdict::WrongHeight);
    ASSERT_TRUE(map.supportQueryCell(q.x_m,q.y_m,cell));EXPECT_EQ(cell.x,10);EXPECT_EQ(cell.y,10);
    EXPECT_EQ(map.staticTraversability({1.,1.,.35},0.),Verdict::Free);
    EXPECT_EQ(map.staticTraversability({1.,1.,.55},0.),Verdict::WrongHeight);
    NonTerrainVoxel obstacle{Occupancy::Occupied,"live","world",stamp};
    EXPECT_EQ(support->reactive_decision_.decide(q,obstacle,&cell),Verdict::StaticObstacle);
    obstacle.occupancy=Occupancy::Unknown;
    EXPECT_EQ(support->reactive_decision_.decide(q,obstacle,&cell),Verdict::UnknownObstacle);
    obstacle.occupancy=Occupancy::Free;
    auto footprint=q;footprint.x_m+=.18;
    EXPECT_EQ(map.footprintSupportVerdict({1.,1.,.35},obstacle,footprint,false),Verdict::Free);
    EXPECT_DOUBLE_EQ(footprint.x_m,1.18);EXPECT_DOUBLE_EQ(footprint.y_m,1.); // No query XY movement.
    EXPECT_FALSE(map.reactiveTerrainReturn({1.,1.,0.})); // Original classifier grid and heights remain.
    EXPECT_DOUBLE_EQ(support->reactive_ground_.cells.at({9,9})[0].elevation_m,-.15);
    state.physical_floor_navigation_source_id_="different-source";
    ASSERT_TRUE(map.supportQueryCell(1.,1.,cell));EXPECT_EQ(cell.x,9);EXPECT_EQ(cell.y,9);
    state.physical_floor_navigation_source_id_="nav";physical.origin_x_m=.001;
    ASSERT_TRUE(map.supportQueryCell(1.,1.,cell));EXPECT_EQ(cell.x,9);EXPECT_EQ(cell.y,9);
    EXPECT_FALSE(map.supportQueryCell(std::numeric_limits<double>::infinity(),1.,cell));
  }
  rclcpp::shutdown();
}

TEST(SharedSupport, EdgeGuardExplanationDoesNotGrantSelectedSupport) {
  using namespace reactive_stair;
  TerrainSnapshot nav;nav.source_id="nav";nav.frame="world";nav.stamp_s=1.;nav.resolution_m=.1;
  TerrainSnapshot evidence=nav;evidence.source_id="surface";
  PhysicalFloorSnapshot physical;physical.source_id="physical";physical.frame="world";
  physical.stamp_s=1.;physical.resolution_m=.1;
  for(int x=-10;x<=10;++x)for(int y=-10;y<=10;++y) {
    nav.cells[{x,y}]={{Support::Flat,0.}};
    evidence.cells[{x,y}]={{Support::Flat,0.},{Support::Stair,1.558}};
    physical.cells[{x,y}]={{0.,0.},{1.558,28.28}};
  }
  physical.cells[{3,3}]={{0.,0.},{1.999,50.}};
  const auto d=diagnoseEvidenceFloor(nav,evidence,&physical,.05,.05,1.58,.12,.26,.35);
  ASSERT_TRUE(d.physical_floor);ASSERT_TRUE(d.edge_blocked);
  EXPECT_DOUBLE_EQ(d.floor_z,1.558);EXPECT_NEAR(d.square_gap_m,std::hypot(.2,.2),1e-12);
  EXPECT_EQ(d.witness_kind,1);
  const auto filled=addGuardedEvidenceFloor(nav,&evidence,.12,.26,.35,nullptr,&physical);
  EXPECT_EQ(filled.cells.at({0,0}).size(),1u);
  CollisionDecision decision({.5,.25,.35,.3,.12});ASSERT_TRUE(decision.acceptTerrain(filled));
  Query q{"world",1.,.05,.05,1.88,true};
  EXPECT_EQ(decision.supportVerdict(q),Verdict::WrongHeight); // Normal selectedSurface gate is retained.
  EXPECT_FALSE(diagnoseEvidenceFloor(nav,evidence,&physical,.05,.05,3.,.12,.26,.35).physical_floor);
  EXPECT_FALSE(diagnoseEvidenceFloor(nav,evidence,nullptr,.05,.05,1.58,.12,.26,.35).physical_floor);
  physical.cells[{3,3}].push_back({1.558,40.});
  EXPECT_FALSE(diagnoseEvidenceFloor(nav,evidence,&physical,.05,.05,1.58,.12,.26,.35).edge_blocked);
  physical.cells[{0,0}].push_back({1.602,0.});
  EXPECT_FALSE(diagnoseEvidenceFloor(nav,evidence,&physical,.05,.05,1.58,.12,.26,.35).physical_floor);
}

TEST(SharedSupport, NativeBodyHeadingAndFloorRulesAreUsedWithoutLiveClearanceGrant) {
  int argc=0;rclcpp::init(argc,nullptr);
  {
    auto node=std::make_shared<rclcpp::Node>("shared_support_test");GridMap map;map.node_=node.get();
    auto &state=*map.owned_state_;auto support=std::const_pointer_cast<GridMapSupportState>(state.support_);
    state.mp_.frame_id_="world";state.mp_.double_cylinder_offset_=.18;state.mp_.double_cylinder_radius_=.35;
    state.mp_.map_min_boundary_=Eigen::Vector3d(-10.,-10.,-10.);
    state.mp_.map_max_boundary_=Eigen::Vector3d(10.,10.,10.);
    support->reactive_parameters_.body_clearance_m=.3;support->reactive_parameters_.body_height_tolerance_m=.12;
    support->reactive_parameters_.terrain_max_age_s=86400.;
    auto &raw=support->reactive_ground_;raw.source_id="same-static-input";raw.frame="world";
    raw.stamp_s=node->now().seconds();raw.resolution_m=.1;
    for(int x=-50;x<=50;++x)for(int y=-1;y<=1;++y)
      raw.cells[{x,y}]={{reactive_stair::Support::Stair,0.},{reactive_stair::Support::Stair,3.}};
    support->reactive_terrain_=raw;
    support->reactive_decision_=reactive_stair::CollisionDecision(support->reactive_parameters_);
    ASSERT_TRUE(support->reactive_decision_.acceptTerrain(raw));
    EXPECT_EQ(map.staticTraversability({0.,0.,.3},0.),reactive_stair::Verdict::Free);
    EXPECT_NE(map.staticTraversability({0.,0.,.3},M_PI/2.),reactive_stair::Verdict::Free);
    EXPECT_EQ(map.staticTraversability({0.,0.,3.3},0.),reactive_stair::Verdict::Free);
    EXPECT_NE(map.staticTraversability({0.,0.,1.3},0.),reactive_stair::Verdict::Free);
    EXPECT_FALSE(map.planningInputsReady()); // Static support is not measured free occupancy.
    const double observation_stamp=node->now().seconds();
    reactive_stair::Query live{"world",observation_stamp,.18,0.,.3,true},global=live;
    reactive_stair::NonTerrainVoxel free{reactive_stair::Occupancy::Free,"live","world",observation_stamp};
    EXPECT_EQ(map.footprintSupportVerdict({0.,0.,.3},free,live,false),
      map.footprintSupportVerdict({0.,0.,.3},free,global,true));
    EXPECT_DOUBLE_EQ(live.z_m,global.z_m);
    const auto path=std::filesystem::temp_directory_path()/"v221_shared_gap.txt";
    const std::string data="2 0 0\n";{std::ofstream file(path);file<<data;}
    uint64_t fnv=14695981039346656037ULL;for(unsigned char byte:data){fnv^=byte;fnv*=1099511628211ULL;}
    state.mp_.support_gap_mask_=std::make_shared<reactive_stair::SupportGapMask>(path.string(),std::to_string(fnv),.35);
    EXPECT_EQ(map.staticTraversability({2.,0.,.3},0.),reactive_stair::Verdict::SupportGap);
    EXPECT_EQ(map.staticTraversability({2.,0.,3.3},0.),reactive_stair::Verdict::Free);
    std::filesystem::remove(path);
  }
  rclcpp::shutdown();
}

TEST(SharedSupport, NativeEdgeReasonPreservesRejection) {
  using namespace reactive_stair;
  int argc=0;rclcpp::init(argc,nullptr);
  {
    auto node=std::make_shared<rclcpp::Node>("edge_reason_test");GridMap map;map.node_=node.get();
    auto &state=*map.owned_state_;auto support=std::const_pointer_cast<GridMapSupportState>(state.support_);
    state.mp_.frame_id_="world";state.mp_.double_cylinder_radius_=.35;
    state.mp_.map_min_boundary_=Eigen::Vector3d(-10.,-10.,-10.);
    state.mp_.map_max_boundary_=Eigen::Vector3d(10.,10.,10.);
    support->reactive_parameters_.body_clearance_m=.3;
    support->reactive_parameters_.body_height_tolerance_m=.12;
    support->reactive_parameters_.terrain_max_age_s=86400.;
    const double stamp=node->now().seconds();
    auto &nav=support->reactive_navigation_ground_;nav.source_id="nav";nav.frame="world";nav.stamp_s=stamp;nav.resolution_m=.1;
    auto &evidence=support->reactive_surface_ground_;evidence=nav;evidence.source_id="surface";
    auto &physical=support->reactive_physical_floor_;physical.source_id="physical";physical.frame="world";physical.stamp_s=stamp;physical.resolution_m=.1;
    for(int x=-8;x<=8;++x)for(int y=-8;y<=8;++y) {
      nav.cells[{x,y}]={{Support::Flat,0.}};
      evidence.cells[{x,y}]={{Support::Flat,0.},{Support::Stair,1.558}};
      physical.cells[{x,y}]={{0.,0.},{1.558,28.28}};
    }
    physical.cells[{3,3}]={{0.,0.},{1.999,50.}};
    support->physical_floor_decoded_valid_=true;
    state.reactive_physical_floor_topic_="physical";state.physical_floor_source_id_="physical";
    state.physical_floor_navigation_source_id_="nav";state.physical_floor_surface_source_id_="surface";
    support->reactive_ground_=support->reactive_terrain_=nav;
    support->reactive_decision_=CollisionDecision(support->reactive_parameters_);
    ASSERT_TRUE(support->reactive_decision_.acceptTerrain(nav));
    Query query{"world",node->now().seconds(),.05,.05,1.858,true};
    NonTerrainVoxel free{Occupancy::Free,"live","world",stamp};
    EXPECT_EQ(map.footprintSupportVerdict({.05,.05,1.858},free,query,false),Verdict::EdgeClearance);
    EXPECT_FALSE(map.reactiveFootprintSupportQuery({.05,.05,1.858},free,query));
    EXPECT_EQ(map.physicalSupportDiagnostic({.05,.05,1.858}).floor_z,1.558);
    query.z_m=4.;
    EXPECT_EQ(map.footprintSupportVerdict({.05,.05,4.},free,query,false),Verdict::WrongHeight);
  }
  rclcpp::shutdown();
}
