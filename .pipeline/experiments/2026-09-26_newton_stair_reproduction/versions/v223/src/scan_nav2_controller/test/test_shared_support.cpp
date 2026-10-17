#include <gtest/gtest.h>
#include <plan_env/grid_map.h>
#include <fstream>
#include <filesystem>

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
