// Ordered original-input prefix reconstruction, with original frozen ROS time.
#include "v84/recording.h"
#include <plan_manage/scan_replan_fsm.h>
#include <plan_manage/reference_path_utils.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include "/output/generated/dyn_a_star.cpp"
nav_msgs::msg::Odometry readBody(const fs::path &path) {
 auto p=read_pose(path);std::ifstream in(path);double ignored;for(int i=0;i<7;++i)in>>ignored;
 auto &t=p.twist.twist;in>>t.linear.x>>t.linear.y>>t.linear.z>>t.angular.x>>t.angular.y>>t.angular.z;
 if(!in)throw std::runtime_error("Missing original body twist");return p;
}
int main(int argc,char **argv) {
 rclcpp::init(argc,argv);const fs::path input=std::getenv("G07_INPUT"),out=std::getenv("G07_OUTPUT");fs::create_directories(out);
 const int selected=std::stoi(std::getenv("G07_FRAME"));std::ostringstream number;number<<std::setw(4)<<std::setfill('0')<<selected;
 edges.open(out/"rejected_edges.csv");searches.open(out/"searches.csv");edges<<std::setprecision(17)<<"search,query,ros_s,revision,cloud_s,from_x,from_y,from_z,to_x,to_y,to_z,yaw,blocked_sample,intervals,x,y,z,verdict\n";
 searches<<"search,result,source_line,edge_queries,free_edges,blocked_edges,expanded_from_nodes,typed_counts\n";
 rclcpp::NodeOptions options;options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
 auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);set_clock(*node,1000000000LL);
 scan_planner::SCANReplanFSM fsm;fsm.init(node.get());auto map=fsm.planner_manager_->grid_map_;
 fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();map->occ_timer_->cancel();map->vis_timer_->cancel();
 for(auto name:{"navigation","surface","physical_floor"}) {
  auto cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(fs::path("/work/fixtures/building")/(std::string(name)+".f32"),true));cloud->header.stamp=node->now();
  if(std::string(name)=="navigation")map->reactiveTomogramCallback(cloud);else if(std::string(name)=="surface")map->reactiveSurfaceGroundCallback(cloud);else map->reactivePhysicalFloorCallback(cloud);
 }
 std::ifstream frames(input/"frames.txt");int frame;int64_t ns=0,body_ns=0,cutoff=0;
 while(frames>>frame>>ns>>body_ns>>cutoff)if(frame==selected)break;
 if(frame!=selected||!frames)throw std::runtime_error("Missing frame");
 std::ifstream scans(input/"scans.txt");int index;int64_t stamp;std::string bf,sf,cf;size_t applied=0;
 while(scans>>index>>stamp>>bf>>sf>>cf) {
  if(stamp>cutoff)break;
  RecordedScan scan{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(readBody(input/bf)),std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sf)),std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cf,false))};
  scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);apply_scan(*map,*node,scan);++applied;
 }
 set_clock(*node,ns);auto body=std::make_shared<nav_msgs::msg::Odometry>(readBody(input/("query_"+number.str()+".txt")));body->header.stamp=rclcpp::Time(body_ns,RCL_ROS_TIME);map->slidingMapFrameCallback(body);fsm.applyOdometry(body);
 nav_msgs::msg::Path route;route.header.frame_id="world";std::ifstream route_file(input/("route_"+number.str()+".txt"));Eigen::Vector3d p;
 while(route_file>>p.x()>>p.y()>>p.z()){geometry_msgs::msg::PoseStamped pose;pose.header=route.header;pose.pose.position.x=p.x();pose.pose.position.y=p.y();pose.pose.position.z=p.z();pose.pose.orientation.w=1.;route.poses.push_back(pose);}
 std::vector<Eigen::Vector3d> waypoints;std::string error;if(!scan_planner::prepareReferenceWaypoints(route,fsm.body_height_,fsm.reference_path_min_distance_,waypoints,&error,fsm.reference_path_simplify_tolerance_))throw std::runtime_error(error);
 std::vector<Eigen::Vector3d> tail(waypoints.begin()+1,waypoints.end());if(!fsm.planner_manager_->planGlobalTrajWaypoints(waypoints.front(),Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero(),tail,Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero()))throw std::runtime_error("Reference failed");
 fsm.navi_mode_=scan_planner::SCANReplanFSM::REFERENCE_PATH;fsm.end_pt_=waypoints.back();fsm.route_generation_=selected?14:13;fsm.have_odom_=true;
 std::ifstream curve_file(input/("curve_"+number.str()+".txt"));double origin;int nc,nk;curve_file>>origin>>nc>>nk;Eigen::MatrixXd controls(3,nc);Eigen::VectorXd knots(nk);
 for(int i=0;i<nc;++i)curve_file>>controls(0,i)>>controls(1,i)>>controls(2,i);for(int i=0;i<nk;++i)curve_file>>knots(i);
 scan_planner::UniformBspline curve(controls,3,knots(4)-knots(3));curve.setKnot(knots);auto &local=fsm.planner_manager_->local_data_;
 local.position_traj_=curve;local.velocity_traj_=curve.getDerivative();local.acceleration_traj_=local.velocity_traj_.getDerivative();local.start_time_=rclcpp::Time(int64_t(std::llround(origin*1e9)),RCL_ROS_TIME);local.duration_=curve.getTimeSum();local.traj_id_=1690;
 const auto digest=map_digest(*map);const auto began=std::chrono::steady_clock::now();const bool planned=fsm.planFromCurrentTraj();
 const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();
 int final_status=-1;double first_collision=-1.;
 if(planned) {
  const auto final=reactive_stair::checkFullCubicTrajectory(local.position_traj_,0.,map->getResolution(),GridMap::collision_heading_lookahead_s,
    [&](const Eigen::Vector3d &p,const Eigen::Vector3d &a,const Eigen::Vector3d &v){return map->collisionTrajectoryYaw(p,a,v);},
    [&](const Eigen::Vector3d &p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
  final_status=int(final.status);first_collision=final.first_time_s;
 }
 set_clock(*node,cutoff+360000000LL);const bool stale_ready=map->planningInputsReady();
 const int stale_verdict=int(map->liveTraversability(fsm.odom_pos_,lite3_nav2::planarYaw(body->pose.pose)));
 set_clock(*node,ns);
 std::ofstream contract(out/"final_gate.json");contract<<"{\"planned\":"<<planned<<",\"final_curve_status\":"<<final_status<<",\"first_collision_s\":"<<first_collision<<",\"stale_ready\":"<<stale_ready<<",\"stale_verdict\":"<<stale_verdict<<",\"physics_steps\":0}\n";

 std::ofstream summary(out/"summary.json");summary<<std::setprecision(17)<<"{\"planned\":"<<planned<<",\"original_query_s\":"<<ns*1e-9<<",\"body_stamp_s\":"<<body_ns*1e-9<<",\"cloud_s\":"<<cutoff*1e-9<<",\"applied_published_scans\":"<<applied<<",\"map_revision\":"<<map->mapRevision()<<",\"map_digest\":\""<<digest<<"\",\"reference_duration\":"<<fsm.planner_manager_->global_data_.global_duration_<<",\"elapsed_s\":"<<elapsed<<",\"physics_steps\":0}\n";summary.close();
 // Recover a NEW global candidate using the same native graph and route-heading
 // policy. Original service requests were not recorded; do not label these exact
 // historical rejected coordinates unless the whole signature matches.
 auto field=std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476");
 auto support=std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","1404261889151999461");
 lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);pct.setEnvironmentalField(field);pct.setStaticSupport(support);
 geometry_msgs::msg::PoseStamped start,goal;start.header.frame_id=goal.header.frame_id="world";start.pose=body->pose.pose;goal.pose=route.poses.back().pose;goal.pose.orientation.z=-.9238795325112863;goal.pose.orientation.w=.38268343236509084;
 lite3_nav2::RoutePolicy policy;policy.begin("g07-reconstruction",goal,false);
 std::ofstream rejected(out/"global_graph_review.csv");rejected<<std::setprecision(17)<<"sample,x,y,z,yaw,verdict\n";
 try {auto path=policy.plan(start,goal,[&]{return node->now();},[&]{return pct.plan(fsm.odom_pos_,fsm.end_pt_,false);});auto poses=lite3_nav2::sampleReference(path,start.pose);int i=0,bad=0;
  for(const auto &pose:poses){const double yaw=lite3_nav2::planarYaw(pose);auto v=map->staticTraversability({pose.position.x,pose.position.y,pose.position.z},yaw);rejected<<i++<<','<<pose.position.x<<','<<pose.position.y<<','<<pose.position.z<<','<<yaw<<','<<int(v)<<'\n';bad+=v!=reactive_stair::Verdict::Free;}
  std::cout<<"GLOBAL_REVIEW samples="<<poses.size()<<" rejected="<<bad<<std::endl;
 }catch(const std::exception&e){std::cout<<"GLOBAL_REVIEW error="<<e.what()<<std::endl;}
 rclcpp::shutdown();return 0;
}
