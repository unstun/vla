#include <plan_env/static_support.h>
#include <array>
#include <fstream>
#include <sstream>
#include <iostream>
#include <cstring>
#include <random>
extern "C" void *legacy_support_create(const char*,const char*);
extern "C" void legacy_support_destroy(void*);
extern "C" int legacy_support_query(void*,double,double,double,double,double*);
int main(int argc,char **argv) {
  if(argc!=2)return 2;
  const char *path="/work/fixtures/building/native.support",*fnv="15212154834549674106";
  reactive_stair::StaticSupportField current(path,fnv);
  void *old=legacy_support_create(path,fnv);std::ifstream input(argv[1]);std::string line;
  std::getline(input,line);size_t queries=0,typed=0,values=0;
  const auto check=[&](std::array<double,4> p){
    double expected[7],actual[7];const int v=legacy_support_query(old,p[0],p[1],p[2],p[3],expected);
    typed+=v!=int(current.assess(p[0],p[1],p[2],p[3]));
    const auto gap=current.gapConstraint(p[0],p[1],p[2],p[3]);actual[0]=gap.blocked;actual[1]=gap.margin;
    for(int i=0;i<3;++i)actual[2+i]=gap.gradient[i];
    double h=0.;actual[5]=current.surfaceHeight(p[0],p[1],p[2]-.3,h);actual[6]=h;
    for(int i=0;i<7;++i)values+=std::memcmp(actual+i,expected+i,sizeof(double))!=0;
    ++queries;
  };
  while(std::getline(input,line)) {
    std::istringstream row(line);std::string part;std::array<double,4> p;
    for(double &v:p){std::getline(row,part,',');v=std::stod(part);}check(p);
  }
  std::mt19937_64 rng(259);std::uniform_real_distribution<double> xy(-9.,11.),z(-.5,7.),yaw(-8*M_PI,8*M_PI);
  for(int i=0;i<20000;++i)check({xy(rng),xy(rng),z(rng),yaw(rng)});
  for(double h:{.0580303,1.5580303,3.0580303,4.5330312})for(int i=0;i<5000;++i){
    const double x=xy(rng),y=xy(rng),a=yaw(rng);check({x,y,h+.3,a});check({x+1e-7,y-1e-7,h+.3+1e-8,a+1e-7});}
  legacy_support_destroy(old);
  std::cout<<"queries="<<queries<<"\ntyped_mismatches="<<typed<<"\nnonidentical_gap_gradient_height_values="<<values<<std::endl;
  return queries!=70928||typed||values?1:0;
}
