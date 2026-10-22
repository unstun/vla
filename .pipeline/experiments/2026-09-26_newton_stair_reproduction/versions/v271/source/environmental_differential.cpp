#include <plan_env/environmental_field.h>
#include <plan_env/static_support.h>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <vector>
int main(int argc,char **argv){
  reactive_stair::EnvironmentalField field("/work/fixtures/building/environment225.env","10040917858432847476");
  reactive_stair::StaticSupportField support("/work/fixtures/building/native.support","15212154834549674106");
  std::vector<Eigen::Vector4d> poses;
  const auto append=[&](double x,double y,double z,double yaw){poses.emplace_back(x,y,z,yaw);};
  for(int arg=1;arg<argc;++arg){std::ifstream f(argv[arg]);std::string line;std::getline(f,line);
    while(std::getline(f,line)){std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);double x,y,z,yaw;
      if(row>>x>>y>>z>>yaw)append(x,y,z,yaw);}
  }
  std::mt19937_64 rng(259);std::uniform_real_distribution<double> xy(-9.,11.),z(-.5,7.),yaw(-8*M_PI,8*M_PI);
  for(int i=0;i<20000;++i)append(xy(rng),xy(rng),z(rng),yaw(rng));
  for(double h:{.0580303,1.5580303,3.0580303,4.5330312})for(int i=0;i<5000;++i){
    const double x=xy(rng),y=xy(rng),a=yaw(rng);append(x,y,h+.3,a);append(x+1e-7,y-1e-7,h+.3+1e-8,a+1e-7);
  }
  size_t bad=0;double maximum=0.;
  for(const auto &p:poses)for(const auto *gap:{static_cast<const reactive_stair::SupportGapMask*>(nullptr),support.gapMask()}){
    const double before=field.assess(p.head<3>(),p(3),gap).cost(),after=field.cost(p.head<3>(),p(3),gap);
    bad+=before!=after;maximum=std::max(maximum,std::abs(before-after));
  }
  bool invalid=false;try{field.cost({0.,0.,0.},std::numeric_limits<double>::quiet_NaN());}
  catch(const std::runtime_error &){invalid=true;}
  using Clock=std::chrono::steady_clock;volatile double sink=0.;auto begin=Clock::now();
  for(const auto &p:poses)sink+=field.assess(p.head<3>(),p(3),support.gapMask()).cost();
  const double full=std::chrono::duration<double>(Clock::now()-begin).count();begin=Clock::now();
  for(const auto &p:poses)sink+=field.cost(p.head<3>(),p(3),support.gapMask());
  const double scalar=std::chrono::duration<double>(Clock::now()-begin).count();
  std::cout<<std::setprecision(17)<<"queries="<<poses.size()<<"\nscalar_cost_mismatches="<<bad<<"\nmax_scalar_cost_error="<<maximum
    <<"\ninvalid_query_rejected="<<invalid<<"\nfull_assessment_s="<<full<<"\nscalar_s="<<scalar<<"\n";
  return bad||!invalid||poses.size()!=70928?1:0;
}
