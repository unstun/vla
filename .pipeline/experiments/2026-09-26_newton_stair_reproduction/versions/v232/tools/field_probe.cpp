#include "v84/recording.h"
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <plan_env/environmental_field.h>
#include <bspline_opt/bspline_optimizer.h>
#include <chrono>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  GridMap map;initialize_map(map,*node,std::getenv("REPLAY_INPUT"));
  if(!map.hasEnvironmentalField())throw std::runtime_error("Candidate native profile did not enable the field");
  auto field=std::make_shared<reactive_stair::EnvironmentalField>(std::getenv("ENVIRONMENT_INPUT"),std::getenv("ENVIRONMENT_FNV"));
  const std::array<std::array<double,4>,5> height_witnesses{{
    {{4.4046852111816408,.76318874359130873,4.8812499999999996,-2.3561944901923426}},
    {{6.4046852111816408,5.3631887435913086,3.4105468750000001,-1.9634954084936185}},
    {{4.4046852111816408,.063188743591308605,4.8812499999999996,-1.9634954084936198}},
    {{6.8046852111816412,5.4631887435913091,4.8812499999999996,-2.3561944901923448}},
    {{6.5046852111816413,.76318874359130873,3.4105468750000001,-1.9634954084936216}}
  }};
  for(const auto &w:height_witnesses) {
    const Eigen::Vector3d xyz(w[0],w[1],w[2]);const auto verdict=map.staticTraversability(xyz,w[3]);
    reactive_stair::Query q{"world",map.queryNow().seconds(),w[0],w[1],w[2],true};reactive_stair::Cell2 cell;
    if(!map.supportQueryCell(w[0],w[1],cell))throw std::runtime_error("Invalid height witness index");
    const auto before=map.supportState().reactive_decision_.supportVerdict(q);
    std::cout<<std::setprecision(17)<<"SUPPORT_BOUNDARY_WITNESS xyz="<<xyz.transpose()<<" old_body="<<int(before)
      <<" canonical_cell="<<cell.x<<','<<cell.y<<" native="<<int(verdict)<<std::endl;
    if(verdict!=reactive_stair::Verdict::Free)throw std::runtime_error("Archived boundary witness still rejected");
  }
  lite3_nav2::PCTRoutePlanner pct(std::getenv("PCT_INPUT"),.35);
  std::ifstream poses(std::getenv("BENCH_POSES"));Eigen::Vector3d p;double yaw;std::vector<std::pair<Eigen::Vector3d,double>> queries;
  while(poses>>p.x()>>p.y()>>p.z()>>yaw)queries.emplace_back(p,yaw);
  pct.setEnvironmentalField(field);double maximum=0.,sum=0.;
  auto started=std::chrono::steady_clock::now();
  for(int repetition=0;repetition<10;++repetition)for(const auto &q:queries) {
    const double a=pct.environmentalCost(q.first,q.second),b=map.environmentalCost(q.first,q.second);
    maximum=std::max(maximum,std::abs(a-b));sum+=a;
  }
  const auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
  std::cout<<std::setprecision(17)<<"FIELD_PARITY queries="<<queries.size()*10<<" mismatch="<<maximum<<" query_pair_us="<<seconds*1e6/(queries.size()*10)<<" checksum="<<sum<<'\n';
  if(maximum!=0.)throw std::runtime_error("Consumer mismatch");
  std::ifstream endpoints(std::getenv("ROUTE_ENDPOINTS"));Eigen::Vector3d start,goal;endpoints>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z();
  if(!endpoints)throw std::runtime_error("Missing pinned route endpoints");
  const fs::path output=std::getenv("PROBE_OUTPUT");fs::create_directories(output);
  scan_planner::BsplineOptimizer scan;scan.setParam(node.get());
  scan.setEnvironment(GridMap::Ptr(&map,[](GridMap *){}));
  for(bool smooth:{false,true})for(bool shared:{false,true}) {
    pct.setEnvironmentalField(shared?field:nullptr);started=std::chrono::steady_clock::now();
    const auto route=pct.plan(start,goal,smooth);
    const double planning_s=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    std::ofstream csv(output/((shared?std::string("shared_"):std::string("legacy_"))+(smooth?"route.csv":"graph.csv")));csv<<std::setprecision(17)<<"x,y,z,yaw,edge_margin,solid_margin,cost,hard_support\n";
    double total=0.,distance=0.,edge_min=1e9,solid_min=1e9;size_t samples=0,rejected=0;
    for(size_t i=1;i<route.size();++i) {
      const auto delta=route[i]-route[i-1];const double angle=std::atan2(delta.y(),delta.x());
      const int n=std::max(1,int(std::ceil(delta.norm()/.025)));distance+=delta.norm();
      for(int j=1;j<=n;++j){const Eigen::Vector3d q=route[i-1]+delta*(double(j)/n);const auto a=field->assess(q,angle);
        const auto hard=map.staticTraversability(q,angle);rejected+=hard!=reactive_stair::Verdict::Free;++samples;
        total+=a.cost()*delta.norm()/n;edge_min=std::min(edge_min,a.edge_margin);solid_min=std::min(solid_min,a.solid_margin);
        csv<<q.x()<<','<<q.y()<<','<<q.z()<<','<<angle<<','<<a.edge_margin<<','<<a.solid_margin<<','<<a.cost()<<','<<int(hard)<<'\n';}
    }
    std::cout<<"FIELD_ROUTE smooth="<<smooth<<" shared="<<shared<<" planning_s="<<planning_s<<" points="<<route.size()<<" sampled="<<samples<<" length_m="<<distance<<" integrated_cost="<<total<<" edge_min="<<edge_min<<" solid_min="<<solid_min<<" hard_support_rejected="<<rejected<<'\n';
    size_t active=0;double largest=-1.;
    if(smooth&&shared)for(size_t i=1;i<route.size();++i) {
      const auto d=route[i]-route[i-1];const double value=field->cost(route[i],std::atan2(d.y(),d.x()));
      if(value>largest){largest=value;active=i;}
    }
    if(smooth&&shared)for(int part:{1,2,3,4}) {
      Eigen::MatrixXd control(3,14),gradient;
      const size_t first=std::min(route.size()-14,part==4?(active>7?active-7:0):route.size()*part/4);
      for(int k=0;k<14;++k)control.col(k)=route[first+k];
      scan.bspline_interval_=.2;double objective=0.;
      const auto began=std::chrono::steady_clock::now();
      for(int repetition=0;repetition<3;++repetition)objective=scan.calcEnvironmentalCost(control,gradient);
      std::cout<<"FIELD_SCAN window="<<part<<" first="<<first<<" evaluations=3 mean_ms="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()*1000/3<<" objective="<<objective<<" gradient_norm="<<gradient.norm()<<'\n';
    }
  }
  rclcpp::shutdown();
}
