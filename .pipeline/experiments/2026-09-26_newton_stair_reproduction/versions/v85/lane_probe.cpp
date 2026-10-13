#include "../v84/recording.h"
#include "lane_guard.h"
#include <condition_variable>
#include <atomic>
#include <limits>

using Decision = LaneGuard::Decision;

// Exact original discrete inflation offsets, tested at a measured stationary
// body footprint. This veto does not certify a swept moving/braking trajectory.
bool direct_body_threat(GridMap &support, const RecordedScan &scan) {
  if (scan.cloud->header.stamp != scan.sensor->header.stamp ||
      scan.cloud->header.stamp != scan.body->header.stamp ||
      scan.cloud->point_step != 12 || scan.cloud->is_bigendian ||
      scan.cloud->data.size() != std::size_t(scan.cloud->width) * 12)
    throw std::runtime_error("Invalid direct-sensor layout or pairing");
  const auto &p=scan.sensor->pose.pose.position; const auto &q=scan.sensor->pose.pose.orientation;
  const Eigen::Vector3d origin(p.x,p.y,p.z);
  const Eigen::Quaterniond rotation(q.w,q.x,q.y,q.z);
  if (!origin.allFinite() || !rotation.coeffs().allFinite() || std::abs(rotation.norm()-1)>1e-4)
    throw std::runtime_error("Invalid sensor transform");
  const auto &bp=scan.body->pose.pose.position; const auto &bq=scan.body->pose.pose.orientation;
  const Eigen::Vector3d body(bp.x,bp.y,bp.z);
  const Eigen::Quaterniond br(bq.w,bq.x,bq.y,bq.z);
  if (!body.allFinite() || !br.coeffs().allFinite() || std::abs(br.norm()-1)>1e-4)
    throw std::runtime_error("Invalid body pose");
  Eigen::Vector3d heading=br*Eigen::Vector3d::UnitX(); heading.z()=0;
  if (heading.norm()<1e-6) throw std::runtime_error("Undefined body heading");
  heading.normalize();
  Eigen::Vector3i queries[2];
  const double offset=support.mapState().mp_.double_cylinder_offset_;
  support.posToIndex(body+offset*heading,queries[0]); support.posToIndex(body-offset*heading,queries[1]);
  const double resolution=support.mapState().mp_.resolution_,radius=support.mapState().mp_.double_cylinder_radius_;
  const int up=std::ceil(support.mapState().mp_.obstacles_inflation_z_up/resolution);
  const int down=std::ceil(support.mapState().mp_.obstacles_inflation_z_down/resolution);
  for (std::size_t i=0;i<scan.cloud->width;++i) {
    float xyz[3]; std::memcpy(xyz,scan.cloud->data.data()+i*12,sizeof(xyz));
    const Eigen::Vector3d local(xyz[0],xyz[1],xyz[2]);
    if(!local.allFinite()) throw std::runtime_error("Non-finite raw return");
    const Eigen::Vector3d world=origin+rotation*local;
    if(support.reactiveTerrainReturn(world)) continue;
    Eigen::Vector3i hit; support.posToIndex(world,hit);
    for(const auto &query:queries) {
      const auto delta=query-hit;
      if(delta.z()>=-down && delta.z()<=up &&
         std::hypot(double(delta.x())*resolution,double(delta.y())*resolution)<radius) return true;
    }
  }
  return false;
}

int main(int argc,char **argv) {
 try {
  const fs::path input(std::getenv("V85_INPUT")),output(std::getenv("V85_OUTPUT"));
  if(!fs::create_directory(output))throw std::runtime_error("Output already exists");
  const auto scans=read_scans(input);
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  GridMap map;initialize_map(map,*node,input);
  const double max_age=map.supportState().reactive_parameters_.obstacle_max_age_s;
  if(max_age!=.250 || map.mapState().mp_.need_extrinsic_ || map.mapState().mp_.cloud_is_world_)
    throw std::runtime_error("Unexpected original sensor/freshness configuration");
  int checks=0;
  const auto require=[&](bool value,const char *name){if(!value)throw std::runtime_error(name);++checks;};
  LaneGuard contract(max_age);
  contract.beginOwner(1);
  require(contract.evaluate(1,1)==Decision::SensorInvalid,"Missing sensor must reject");
  require(contract.observe(1,1,true,false),"First complete sensor pair");
  require(contract.mapped(1,1,true,1),"Original clear map accepted");
  require(contract.evaluate(1,1.249)==Decision::AllowExisting,"Fresh original evidence permits existing command");
  contract.observe(1,1.260,true,false);
  require(contract.evaluate(1,1.260)==Decision::MapStale,"Fresh sensor cannot refresh old map");
  contract.observe(1,1.270,true,true);
  contract.observe(1,1.280,true,false);
  contract.mapped(1,1.280,true,1.260);
  require(contract.evaluate(1,1.280)==Decision::HazardPending,"Skipped transient cannot be cleared by latest map");
  contract.mapped(1,1.281,false,1.280);
  require(contract.evaluate(1,1.281)!=Decision::AllowExisting,"Unsafe applied map cannot authorize execution");
  contract.mapped(1,1.282,true,1.280);
  require(contract.evaluate(1,1.282)==Decision::AllowExisting,"Covered hazard requires actual clear map evidence");
  require(contract.evaluate(1,1.1)==Decision::SensorStale,"Future source data rejected");
  require(contract.evaluate(1,2)==Decision::SensorStale,"Lost sensor rejected");
  contract.cancel(1);contract.beginOwner(1);contract.mapped(1,1.283,true,1.280);
  require(contract.evaluate(1,1.283)==Decision::Cancelled,"Same owner cannot revive cancelled execution");
  contract.beginOwner(2);
  require(!contract.mapped(1,1.3,true,1.3),"Late old-owner map rejected");
  require(!contract.observe(1,1.3,true,false),"Late old-owner sensor rejected");
  require(contract.observe(2,1.3,true,false),"New owner fresh sensor");
  contract.mapped(2,1.3,true,1.3);
  require(contract.evaluate(2,1.3)==Decision::AllowExisting,"New owner can acquire new evidence");
  require(!contract.observe(2,1.4,false,false),"Unpaired input rejected");
  contract.observe(2,1.5,true,false);
  require(contract.evaluate(2,1.5)==Decision::SensorInvalid,"Malformed stream failure stays latched");
  contract.beginOwner(3);contract.observe(3,2,true,false);contract.observe(3,1.9,true,false);
  require(contract.evaluate(3,2)==Decision::SensorInvalid,"Regressed observation rejected");
  require(!contract.mapped(3,2,true,2.1),"Impossible applied bound rejected");
  contract.beginOwner(4);contract.observe(4,std::numeric_limits<double>::quiet_NaN(),true,false);
  require(contract.evaluate(4,2)==Decision::SensorInvalid,"Non-finite observation rejected");

  // Three actual threads consume every measured cloud. Execution decisions are
  // logged, never published as robot commands. Source clocks use elapsed wall
  // time; slow mapping cannot restamp a cloud or reset the control clock.
  auto sensor_node=std::make_shared<rclcpp::Node>("scan_planner_node");
  GridMap sensor_support;initialize_map(sensor_support,*sensor_node,input);
  // Drive the actual PointCloud2 transform/geometry seam, not only a fabricated
  // boolean threat. This one-return body intrusion is a synthetic negative.
  RecordedScan intrusion=scans.front();
  intrusion.cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(*intrusion.cloud);
  intrusion.cloud->width=intrusion.cloud->height=1;intrusion.cloud->row_step=12;intrusion.cloud->data.resize(12);
  const auto &sp=intrusion.sensor->pose.pose.position;const auto &sq=intrusion.sensor->pose.pose.orientation;
  const auto &bp=intrusion.body->pose.pose.position;
  const Eigen::Vector3d body_point(bp.x,bp.y,bp.z),sensor_origin(sp.x,sp.y,sp.z);
  const Eigen::Quaterniond sensor_rotation(sq.w,sq.x,sq.y,sq.z);
  const Eigen::Vector3d local_point=sensor_rotation.conjugate()*(body_point-sensor_origin);
  const float raw_hit[]={float(local_point.x()),float(local_point.y()),float(local_point.z())};
  std::memcpy(intrusion.cloud->data.data(),raw_hit,sizeof(raw_hit));
  set_clock(*sensor_node,intrusion.stamp);
  const bool actual_raw_threat=direct_body_threat(sensor_support,intrusion);
  require(actual_raw_threat,"Actual raw body-intrusion return triggers independent veto");
  LaneGuard transient(max_age);transient.beginOwner(501);
  const double t=intrusion.stamp*1e-9;
  transient.observe(501,t,true,actual_raw_threat);transient.observe(501,t+.001,true,false);
  transient.mapped(501,t+.001,true,t-.001);
  require(transient.evaluate(501,t+.001)==Decision::HazardPending,"Later clear latest-only map cannot erase actual skipped threat");
  intrusion.cloud->header.stamp=rclcpp::Time(intrusion.stamp+1,RCL_ROS_TIME);
  bool rejected=false;try{direct_body_threat(sensor_support,intrusion);}catch(const std::runtime_error &){rejected=true;}
  require(rejected,"Actual sensor geometry rejects mismatched pose stamp");
  intrusion.cloud->header.stamp=intrusion.sensor->header.stamp;
  const float malformed[]={std::numeric_limits<float>::quiet_NaN(),0,0};
  std::memcpy(intrusion.cloud->data.data(),malformed,sizeof(malformed));
  rejected=false;try{direct_body_threat(sensor_support,intrusion);}catch(const std::runtime_error &){rejected=true;}
  require(rejected,"Actual sensor geometry rejects non-finite return");
  LaneGuard guard(max_age);guard.beginOwner(101);
  const auto start=std::chrono::steady_clock::now()+std::chrono::milliseconds(100);
  const double first=scans.front().stamp*1e-9;
  const auto elapsed=[&]{return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
  std::mutex queue_mutex,error_mutex;
  std::condition_variable wake;
  std::deque<std::size_t> pending;
  std::atomic<bool> sensor_done{false},map_done{false},failed{false};
  std::string failure;
  const auto fail=[&](const std::exception &e){std::lock_guard<std::mutex> lock(error_mutex);failure=e.what();failed=true;wake.notify_all();};
  std::ofstream sensor_rows(output/"sensor.jsonl"),map_rows(output/"map.jsonl"),control_rows(output/"execution.jsonl");
  sensor_rows<<std::setprecision(15);map_rows<<std::setprecision(15);control_rows<<std::setprecision(15);
  std::size_t processed=0,observed=0,ticks=0,max_queue=0;double max_sensor_ms=0,max_tick_gap=0;
  std::thread sensor_thread([&]{try{
    for(std::size_t i=0;i<scans.size() && !failed;++i){
      const double release=(scans[i].stamp-scans.front().stamp)*1e-9;
      std::this_thread::sleep_until(start+std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(release)));
      const double began=elapsed();set_clock(*sensor_node,scans[i].stamp);
      const bool threat=direct_body_threat(sensor_support,scans[i]);
      if(!guard.observe(101,scans[i].stamp*1e-9,true,threat))throw std::runtime_error("Recorded sensor admission failed");
      const double complete=elapsed(),cost=(complete-began)*1000;
      max_sensor_ms=std::max(max_sensor_ms,cost);++observed;
      sensor_rows<<"{\"scan\":"<<i<<",\"release_s\":"<<release<<",\"complete_s\":"<<complete<<",\"service_ms\":"<<cost<<",\"body_threat\":"<<(threat?"true":"false")<<"}\n";
      {std::lock_guard<std::mutex> lock(queue_mutex);pending.push_back(i);max_queue=std::max(max_queue,pending.size());}
      wake.notify_one();
    }
  }catch(const std::exception &e){fail(e);}sensor_done=true;wake.notify_all();});
  std::thread mapper_thread([&]{try{
    while(!failed){std::size_t i;
      {std::unique_lock<std::mutex> lock(queue_mutex);wake.wait(lock,[&]{return failed||sensor_done||!pending.empty();});
       if(failed||(pending.empty()&&sensor_done))break;i=pending.front();pending.pop_front();}
      const double began=elapsed();
      if(i==60||i==120)std::this_thread::sleep_for(std::chrono::milliseconds(650));
      const double cost=apply_scan(map,*node,scans[i]);
      set_clock(*node,int64_t((first+elapsed())*1e9));
      const auto &p=scans[i].body->pose.pose.position;
      const Eigen::Vector3d body(p.x,p.y,p.z);
      const bool native_clear=map.getInflateOccupancy(body,map.collisionSegmentYaw(body,body))==0;
      guard.mapped(101,scans[i].stamp*1e-9,native_clear,scans[i].stamp*1e-9);++processed;
      map_rows<<"{\"scan\":"<<i<<",\"begin_s\":"<<began<<",\"complete_s\":"<<elapsed()<<",\"native_service_s\":"<<cost<<",\"native_body_clear\":"<<(native_clear?"true":"false")<<"}\n";
    }
  }catch(const std::exception &e){fail(e);}map_done=true;});
  std::thread execution_thread([&]{try{
    double previous=-1;
    while(!failed && (!map_done||!sensor_done)){
      const auto target=start+std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(ticks/30.0));
      std::this_thread::sleep_until(target);
      const double now=elapsed();if(previous>=0)max_tick_gap=std::max(max_tick_gap,now-previous);previous=now;
      const auto verdict=guard.evaluate(101,first+now);
      control_rows<<"{\"tick\":"<<ticks++<<",\"wall_s\":"<<now<<",\"decision\":"<<int(verdict)<<"}\n";
    }
  }catch(const std::exception &e){fail(e);}});
  sensor_thread.join();mapper_thread.join();execution_thread.join();
  if(failed)throw std::runtime_error(failure);
  require(observed==scans.size() && processed==scans.size(),"No distinct observation lost between lanes");
  require(ticks>500,"Execution decisions continue through both mapper stalls");
  std::ofstream summary(output/"summary.json");summary<<std::setprecision(15)
    <<"{\"checks\":"<<checks<<",\"offered\":"<<scans.size()<<",\"sensor_processed\":"<<observed
    <<",\"mapped\":"<<processed<<",\"execution_ticks\":"<<ticks<<",\"max_pending\":"<<max_queue
    <<",\"max_sensor_service_ms\":"<<max_sensor_ms<<",\"max_execution_gap_s\":"<<max_tick_gap
    <<",\"state_sha256\":\""<<map_digest(map)<<"\",\"robot_commands_published\":0,\"physics_steps\":0,"
    <<"\"scope\":\"Three-lane native replay with stationary-body sensor veto and original map rejection; not moving-trajectory or braking qualification\"}\n";
  std::cout<<"V85_LANES_COMPLETE checks="<<checks<<" sensors="<<observed<<" maps="<<processed<<" execution_ticks="<<ticks<<" max_tick_gap="<<max_tick_gap<<"\n";
  rclcpp::shutdown();return 0;
 }catch(const std::exception &e){std::cerr<<"V85_FAILED "<<e.what()<<'\n';if(rclcpp::ok())rclcpp::shutdown();return 1;}
}
