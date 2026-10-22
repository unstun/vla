#include <plan_env/environmental_field.h>
#include <fstream>
#include <sstream>
#include <iostream>
#include <chrono>
#include <cmath>
#include <algorithm>

std::shared_ptr<reactive_stair::EnvironmentalField> fixture(bool edge) {
  std::ostringstream s;s<<"ENV225 .1 -1.05 -1.05 .35 0 .55 .35 .3 .15 0\nF 441\n";
  for(int x=0;x<21;++x)for(int y=0;y<21;++y)
    s<<x<<' '<<y<<" 0 "<<(edge ? .35+(-1.+y*.1)*.2 : 2.)<<" 0\n";
  s<<"A .1 .1 -1 -1 0 21 21 7\n";
  for(int x=0;x<21;++x)for(int y=0;y<21;++y)for(int z=0;z<7;++z) {
    float value=edge ? .15f : float(std::clamp((-1.+y*.1)*.2,-.15,.15));
    s.write(reinterpret_cast<char*>(&value),sizeof(value));
  }
  auto bytes=s.str();uint64_t h=14695981039346656037ULL;
  for(unsigned char c:bytes){h^=c;h*=1099511628211ULL;}
  const std::string path=std::string("/evaluation/")+(edge?"edge":"solid")+"_escape.env";
  std::ofstream out(path,std::ios::binary);out.write(bytes.data(),bytes.size());out.close();
  return std::make_shared<reactive_stair::EnvironmentalField>(path,std::to_string(h));
}
int main() {
  int failures=0,checks=0;
  for(bool edge:{false,true}) {
    auto f=fixture(edge);
    for(double y:{-.2,0.,.2}) {
      const Eigen::Vector3d p(0.,y,.3),dy(0.,1e-5,0.);
      const auto a=f->assess(p,0.);const double margin=edge?a.edge_margin:a.solid_margin;
      const double expected=std::pow(edge?std::clamp((.15-margin)/.15,0.,1.):std::max((.15-margin)/.15,0.),2);
      const double numerical=(f->cost(p+dy,0.)-f->cost(p-dy,0.))/2e-5;
      const bool ok=std::abs(a.cost()-expected)<1e-6 && std::abs(f->cost(p,0.)-a.cost())<1e-9 &&
          (edge && margin<=1e-8 ? a.gradient.norm()<1e-6 : a.gradient.y()<-.1) &&
          (edge && std::abs(margin)<1e-8 ? true : std::abs(a.gradient.y()-numerical)<2e-4);
      std::cout<<"ESCAPE edge="<<edge<<" margin="<<margin<<" cost="<<a.cost()<<" gy="<<a.gradient.y()<<" numerical="<<numerical<<" passed="<<ok<<'\n';
      ++checks;failures+=!ok;
    }
    const auto safe=f->assess({0.,.9,.3},0.);++checks;failures+=safe.cost()!=0.||safe.gradient.norm()>1e-8;
    const auto begin=std::chrono::steady_clock::now();double sum=0.;
    for(int i=0;i<100000;++i)sum+=f->assess({0.,(i%31-15)*.01,.3},.2).cost();
    std::cout<<"ENV_TIMING edge="<<edge<<" ns_per_query="<<std::chrono::duration<double,std::nano>(std::chrono::steady_clock::now()-begin).count()/100000<<" checksum="<<sum<<'\n';
  }
  std::cout<<"FIELD {\"checks\":"<<checks<<",\"failures\":"<<failures<<"}\n";return failures?1:0;
}
