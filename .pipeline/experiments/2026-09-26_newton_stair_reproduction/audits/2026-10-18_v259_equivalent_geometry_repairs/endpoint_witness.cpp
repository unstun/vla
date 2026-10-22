#include <plan_env/static_support.h>
#include <plan_env/static_solid.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char **argv){
  if(argc!=3)throw std::runtime_error("endpoint input and output required");
  reactive_stair::StaticSupportField support("/work/fixtures/building/native.support","15212154834549674106");
  reactive_stair::StaticSolidField solid("/work/fixtures/building/static_solids.env","17629216882668158307");
  std::ifstream input(argv[1]);std::ofstream out(argv[2]);
  std::ofstream details(std::string(argv[2])+".surfaces.csv");
  details<<std::setprecision(17)<<"case_id,endpoint,part,x,y,body_z,ground_hint,cell_x,cell_y,elevation,raw_support,scored_support\n";
  out<<std::setprecision(17)<<"case_id,endpoint,x,y,z,yaw,support_verdict,solid_margin,witness_x,witness_y,witness_z,gradient_x,gradient_y,gradient_z,gradient_yaw\n";
  std::string id,which;Eigen::Vector3d p;double yaw;size_t n=0;
  while(input>>id>>which>>p.x()>>p.y()>>p.z()>>yaw){
    const auto a=solid.assess(p,yaw);out<<id<<','<<which<<','<<p.x()<<','<<p.y()<<','<<p.z()<<','<<yaw<<','<<int(support.assess(p.x(),p.y(),p.z(),yaw))<<','<<a.margin;
    for(double v:{a.witness.x(),a.witness.y(),a.witness.z(),a.gradient(0),a.gradient(1),a.gradient(2),a.gradient(3)})out<<','<<v;
    out<<'\n';++n;
    for(int part:{0,-1,1}){
      const double x=p.x()+part*support.offset()*std::cos(yaw),y=p.y()+part*support.offset()*std::sin(yaw);
      reactive_stair::Cell2 cell;reactive_stair::staticSupportCell(x,y,support.raw_,support.canonical_,support.ox_,support.oy_,cell);
      const auto raw=support.raw_.cells.find(cell),scored=support.scored_.cells.find(cell);
      const auto prefix=[&](){details<<id<<','<<which<<','<<part<<','<<x<<','<<y<<','<<p.z()<<','<<p.z()-.3<<','<<cell.x<<','<<cell.y<<',';};
      if(raw==support.raw_.cells.end()||scored==support.scored_.cells.end()){prefix();details<<"nan,-1,-1\n";}
      else for(size_t i=0;i<raw->second.size();++i){prefix();details<<raw->second[i].elevation_m<<','<<int(raw->second[i].support)<<','<<int(scored->second[i].support)<<'\n';}
    }
  }
  if(!input.eof()||!n)throw std::runtime_error("Invalid endpoint witness input");
  std::cout<<"queries="<<n<<"\n";
}
