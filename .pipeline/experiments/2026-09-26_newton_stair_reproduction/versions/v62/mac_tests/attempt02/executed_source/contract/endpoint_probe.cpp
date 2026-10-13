#include <plan_env/grid_map.h>
#include <plan_env/goal_region_bounds.h>
#include <random>
#include <iostream>
#include <stdexcept>
int main(int argc,char **argv) {
 rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
 GridMap m;m.initMap(node.get());m.occ_timer_->cancel();m.vis_timer_->cancel();int checks=0;
 auto check=[&](bool ok,const char *name){if(!ok)throw std::runtime_error(name);++checks;std::cout<<"V58_ENDPOINT_CHECK "<<name<<" PASS\n";};
 const auto saved=m.md_.occupancy_buffer_;const auto known=m.reactive_known_trunk_enabled_;
 m.reactive_known_trunk_enabled_=false;
 std::fill(m.md_.occupancy_buffer_.begin(),m.md_.occupancy_buffer_.end(),m.mp_.clamp_min_log_-1.0);
 const Eigen::Vector3d p=(m.mp_.map_min_boundary_+m.mp_.map_max_boundary_)*.5;
 check(!m.bodyEndpointMayBeObserved(p),"all_unknown_remote_endpoint_rejected");
 size_t positions=0;std::mt19937 rng(5070);std::uniform_real_distribution<double> u(-.7,.7),yaw(-3.141592653589793,3.141592653589793);
 for(int i=0;i<3000;++i){Eigen::Vector3d body=p+Eigen::Vector3d(u(rng),u(rng),u(rng));double a=yaw(rng);
  Eigen::Vector3d footprint=body+m.mp_.double_cylinder_offset_*Eigen::Vector3d(std::cos(a),std::sin(a),0);
  Eigen::Vector3i id;m.posToIndex(footprint,id);if(!m.isInMap(id))continue;
  Eigen::Vector3i rear;m.posToIndex(2.0*body-footprint,rear);if(!m.isInMap(rear))continue;
  int address=m.toAddress(id),other=m.toAddress(rear);double before=m.md_.occupancy_buffer_[address],previous=m.md_.occupancy_buffer_[other];
  m.md_.occupancy_buffer_[address]=(i%2)?m.mp_.clamp_min_log_:m.mp_.clamp_max_log_;
  m.md_.occupancy_buffer_[other]=m.mp_.clamp_min_log_;
  if(!m.bodyEndpointMayBeObserved(body))throw std::runtime_error("Observed original footprint pair rejected");
  ++positions;m.md_.occupancy_buffer_[address]=before;m.md_.occupancy_buffer_[other]=previous;
 }
 check(positions>2000,"3000_arbitrary_yaw_observed_footprint_pairs_never_rejected");
 Eigen::Vector3i id,other;m.posToIndex(p+Eigen::Vector3d(m.mp_.double_cylinder_offset_,0,0),id);m.posToIndex(p-Eigen::Vector3d(m.mp_.double_cylinder_offset_,0,0),other);m.md_.occupancy_buffer_[m.toAddress(id)]=m.mp_.clamp_max_log_;m.md_.occupancy_buffer_[m.toAddress(other)]=m.mp_.clamp_max_log_;
 check(m.bodyEndpointMayBeObserved(p),"occupied_observation_is_only_a_possible_endpoint");
 m.md_.occupancy_buffer_[m.toAddress(id)]=m.mp_.clamp_min_log_-1.0;m.md_.occupancy_buffer_[m.toAddress(other)]=m.mp_.clamp_min_log_-1.0;
 check(!m.bodyEndpointMayBeObserved(p),"input_mutation_rechecked_without_cached_verdict");
 m.reactive_known_trunk_enabled_=true;m.md_.sliding_map_frame_pos_=p;
 check(m.bodyEndpointMayBeObserved(p),"unknown_near_body_waiver_cannot_be_pruned");
 check(m.bodyEndpointMayBeObserved(Eigen::Vector3d::Constant(NAN)),"uncertain_input_defers");
 // Exact and tolerance endpoints are separate alternatives. Any possible one
 // defeats the negative certificate; an arbitrary predicate never grants safety.
 Eigen::Vector3i pool(20,20,20),mid(10,10,10),start(3,3,10),end(16,16,10);
 Eigen::Vector3d lo(-2,-2,-2),hi(2,2,2),center=Eigen::Vector3d::Zero(),goal(.6,.6,0);
 auto region=[&](auto predicate,bool plane=true){return reactive_stair::goalRegionMayFitWithEvidence(goal,.35,lo,hi,center,.1,pool,mid,start,end,plane,predicate);};
 check(!region([](const auto&){return false;}),"all_exact_and_tolerance_endpoints_impossible");
 check(region([&](const auto&q){return (q-goal).norm()<1e-8;}),"exact_connector_alone_preserves_search");
 const Eigen::Vector3d tolerance_point(.5,.5,0);
 check(region([&](const auto&q){return (q-tolerance_point).norm()<1e-8;}),"one_tolerance_endpoint_preserves_search");
 check(region([](const auto&){return false;},false),"nonplane_search_remains_native");
 m.md_.occupancy_buffer_=saved;m.reactive_known_trunk_enabled_=known;
 std::cout<<"V58_ENDPOINT_PASSED checks="<<checks<<" sampled_footprints="<<positions<<std::endl;rclcpp::shutdown();
}
