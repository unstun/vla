// Read-only observer: actual installed v247 optimization and projection.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <filesystem>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <fstream>
#include <iomanip>
#include <iostream>
namespace fs=std::filesystem;
int canonical(double q){double e=q+.5,n=std::round(e);return int(std::floor(std::abs(e-n)<=32.*std::numeric_limits<double>::epsilon()*std::max(1.,std::abs(e))?n:e));}
int main(int argc,char **argv){
 auto field=std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476");
 auto support=std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","1404261889151999461");
 for(int arg=1;arg<argc;++arg){
  const std::string id=fs::path(argv[arg]).parent_path().filename();fs::path out=fs::path("/output/gpmp")/id;fs::create_directories(out);
  Eigen::Vector3d start,goal;double yaw;std::ifstream in(argv[arg]);in>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>yaw;
  lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);pct.setEnvironmentalField(field);pct.setStaticSupport(support);
  bool accepted=false;std::string error;int static_bad=-1,static_count=0;double max_heading_change=0.;
  const bool smooth=std::getenv("GRAPH_CONTROL")==nullptr;
  std::vector<Eigen::Vector3d> projected;
  try{
   projected=pct.plan(start,goal,smooth);accepted=true;
   geometry_msgs::msg::PoseStamped a,b;a.header.frame_id=b.header.frame_id="world";
   a.pose.position.x=start.x();a.pose.position.y=start.y();a.pose.position.z=start.z();a.pose.orientation.z=std::sin(yaw/2.);a.pose.orientation.w=std::cos(yaw/2.);
   b.pose.position.x=goal.x();b.pose.position.y=goal.y();b.pose.position.z=goal.z();b.pose.orientation.w=1.;
   lite3_nav2::RoutePolicy policy;policy.begin("first-attempt",b,true);
   auto route=policy.plan(a,b,[]{return rclcpp::Time(1000000000LL,RCL_ROS_TIME);},[&]{return projected;});
   auto samples=lite3_nav2::sampleReference(route,a.pose);
   std::ofstream final(out/"projected_route.csv");final<<std::setprecision(17)<<"i,x,y,z,yaw,verdict\n";
   static_bad=0;double previous=yaw;int i=0;
   for(const auto &pose:samples){double angle=lite3_nav2::planarYaw(pose);auto v=support->assess(pose.position.x,pose.position.y,pose.position.z,angle);static_bad+=v!=reactive_stair::Verdict::Free;
    final<<i++<<','<<pose.position.x<<','<<pose.position.y<<','<<pose.position.z<<','<<angle<<','<<int(v)<<'\n';}
   for(const auto &pose:route.poses){double angle=lite3_nav2::planarYaw(pose.pose);max_heading_change=std::max(max_heading_change,std::abs(std::remainder(angle-previous,2.*M_PI)));previous=angle;}
   static_count=samples.size();
  }catch(const std::exception &e){error=e.what();}
  const auto &optimizer=pct.planner_.get_trajectory_optimizer_wnoj();auto tr=optimizer.GetResultMatrix();auto h=optimizer.GetResultHeight();auto layers=optimizer.GetResultLayers();
  std::ofstream raw(out/"raw_gpmp.csv");raw<<std::setprecision(17)<<"i,grid_y,grid_x,z,layer\n";
  std::vector<Eigen::Vector3d> points;for(int i=0;i<tr.rows();++i){raw<<i<<','<<tr(i,0)<<','<<tr(i,tr.cols()/2)<<','<<h(i)<<','<<layers(i)<<'\n';points.emplace_back((tr(i,tr.cols()/2)-pct.nx_/2)*.1+pct.cx_,(tr(i,0)-pct.ny_/2)*.1+pct.cy_,h(i));}
  std::ofstream dense(out/"dense_queries.csv");dense<<std::setprecision(17)<<"segment,fraction,x,y,z,yaw,layer,trunc_x,trunc_y,canonical_x,canonical_y,old_valid,raw_ground,planning_ground,trunc_planning_ground,slice_height_known,continuous_height_known,continuous_floor,native_verdict,nearest_physical_layer,nearest_proxy\n";
  int total=0,missing=0,disagreement=0,bad_native=0,first=0;
  auto inspect=[&](const Eigen::Vector3d &p,int layer,int seg,double fraction,double angle){
   double qx=(p.x()-pct.cx_)/.1+pct.nx_/2,qy=(p.y()-pct.cy_)/.1+pct.ny_/2;
   int x=canonical(qx),y=canonical(qy),tx=int(qx),ty=int(qy);if(x<0||x>=pct.nx_||y<0||y>=pct.ny_||tx<0||tx>=pct.nx_||ty<0||ty>=pct.ny_)return;
   int row=layer*pct.nx_+x;double proxy=pct.planning_ground_(row,y),height=0.,cont=0.;
   const bool known=support->surfaceHeight((x-pct.nx_/2)*.1+pct.cx_,(y-pct.ny_/2)*.1+pct.cy_,proxy,height);
   const bool continuous=support->surfaceHeight(p.x(),p.y(),p.z()-.3,cont);int nearest=-1;double best=1e10,alt=-100.;
   for(int k=0;k<pct.layers_;++k){double z=pct.planning_ground_(k*pct.nx_+x,y);if(z<=-50)continue;double d=std::abs(z-(p.z()-.3));if(d<best){best=d;nearest=k;alt=z;}}
   auto verdict=support->assess(p.x(),p.y(),p.z(),angle);++total;missing+=!known;disagreement+=(x!=tx||y!=ty);bad_native+=verdict!=reactive_stair::Verdict::Free;
   dense<<seg<<','<<fraction<<','<<p.x()<<','<<p.y()<<','<<p.z()<<','<<angle<<','<<layer<<','<<tx<<','<<ty<<','<<x<<','<<y<<','<<int(pct.ground_valid_[row*pct.ny_+y])<<','<<pct.ground_(row,y)<<','<<proxy<<','<<pct.planning_ground_(layer*pct.nx_+tx,ty)<<','<<known<<','<<continuous<<','<<cont<<','<<int(verdict)<<','<<nearest<<','<<alt<<'\n';
   if(!known&&first++<3)std::cout<<std::setprecision(17)<<"MISSING "<<id<<" seg="<<seg<<" f="<<fraction<<" p="<<p.transpose()<<" layer="<<layer<<" q="<<qx<<','<<qy<<" oldValid="<<int(pct.ground_valid_[row*pct.ny_+y])<<" raw="<<pct.ground_(row,y)<<" proxy="<<proxy<<" truncProxy="<<pct.planning_ground_(layer*pct.nx_+tx,ty)<<" actual_known="<<continuous<<" native="<<int(verdict)<<" alternative="<<nearest<<','<<alt<<'\n';
  };
  if(!points.empty())inspect(points.front(),int(layers(0)),0,0,yaw);
  for(size_t i=1;i<points.size();++i){auto delta=points[i]-points[i-1];int n=std::max(1,int(std::ceil(delta.head<2>().norm()/.025)));double a=std::atan2(delta.y(),delta.x());for(int k=1;k<=n;++k)inspect(points[i-1]+delta*(double(k)/n),int(layers(k*2<n?i-1:i)),i,double(k)/n,a);}
  std::ofstream result(out/"result.txt");result<<"case="<<id<<"\naccepted="<<accepted<<"\nerror="<<error<<"\nstatic_bad="<<static_bad<<"\nstatic_count="<<static_count<<"\nmax_heading_change="<<max_heading_change<<"\nraw_samples="<<tr.rows()<<"\ndense_samples="<<total<<"\nmissing="<<missing<<"\npartition_disagreements="<<disagreement<<"\nraw_native_rejected="<<bad_native<<'\n';
  std::cout<<"RESULT "<<id<<" accepted="<<accepted<<" error="<<error<<" static_bad="<<static_bad<<" heading_change="<<max_heading_change<<" raw="<<tr.rows()<<" total="<<total<<" missing="<<missing<<" partitions="<<disagreement<<" raw_native_rejected="<<bad_native<<std::endl;
 }
}
