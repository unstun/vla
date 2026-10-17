#include "raw_reference.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <vector>

int main() {
  const char *source=std::getenv("RAW_FIELD"),*fnv=std::getenv("RAW_FNV"),*destination=std::getenv("ATLAS_OUTPUT");
  if(!source||!fnv||!destination)throw std::runtime_error("Missing explicit atlas input/output");
  if(std::filesystem::exists(destination))throw std::runtime_error("Preserve prior atlas output");
  std::ifstream in(source);std::string first,line,magic;std::getline(in,first);
  std::istringstream header(first);double resolution,ox,oy,radius,offset,up,down,clearance,target,half;
  if(!(header>>magic>>resolution>>ox>>oy>>radius>>offset>>up>>down>>clearance>>target>>half)||magic!="ENV224B")
    throw std::runtime_error("Expected pinned ENV224B raw field");
  std::getline(in,line);std::istringstream floors(line);char kind;size_t count;floors>>kind>>count;
  if(!floors||kind!='F'||count==0)throw std::runtime_error("Invalid raw floor block");
  std::ostringstream prefix;prefix<<"ENV225 "<<first.substr(8)<<'\n'<<line<<'\n';
  int minx=std::numeric_limits<int>::max(),miny=minx,maxx=std::numeric_limits<int>::min(),maxy=maxx;
  double minz=1e100,maxz=-1e100;
  for(size_t i=0;i<count;++i) {
    std::getline(in,line);prefix<<line<<'\n';std::istringstream row(line);int x,y;double z,e,t;row>>x>>y>>z>>e>>t;
    if(!row)throw std::runtime_error("Invalid raw floor record");
    minx=std::min(minx,x);maxx=std::max(maxx,x);miny=std::min(miny,y);maxy=std::max(maxy,y);minz=std::min(minz,z);maxz=std::max(maxz,z);
  }
  const double hxy=.05,hz=.05,padding=std::abs(offset)+2*resolution;
  const double ax=std::floor((ox+(minx+.5)*resolution-padding)/hxy)*hxy;
  const double ay=std::floor((oy+(miny+.5)*resolution-padding)/hxy)*hxy;
  const double az=std::floor((minz+clearance-.26-hz)/hz)*hz;
  const int nx=int(std::ceil((ox+(maxx+.5)*resolution+padding-ax)/hxy))+1;
  const int ny=int(std::ceil((oy+(maxy+.5)*resolution+padding-ay)/hxy))+1;
  const int nz=int(std::ceil((maxz+clearance+.26+hz-az)/hz))+1;
  const size_t samples=size_t(nx)*ny*nz;std::vector<float> atlas(samples);
  void *reference=makePointField(source,fnv,true);
  const auto began=std::chrono::steady_clock::now();std::atomic<int> next{0};std::vector<std::thread> workers;
  for(int worker=0;worker<4;++worker)workers.emplace_back([&] {
    for(int x;(x=next.fetch_add(1))<nx;)for(int y=0;y<ny;++y)for(int z=0;z<nz;++z) {
      double value[4];pointAssessment(reference,ax+x*hxy,ay+y*hxy,az+z*hz,0.,value);
      atlas[(size_t(x)*ny+y)*nz+z]=float(std::clamp(value[1],-target,target));
    }
  });
  for(auto &thread:workers)thread.join();freePointField(reference);
  std::ofstream out(destination,std::ios::binary);out<<prefix.str()<<std::setprecision(17)
    <<"A "<<hxy<<' '<<hz<<' '<<ax<<' '<<ay<<' '<<az<<' '<<nx<<' '<<ny<<' '<<nz<<'\n';
  out.write(reinterpret_cast<const char*>(atlas.data()),atlas.size()*sizeof(float));
  if(!out)throw std::runtime_error("Atlas write failed");
  std::cout<<std::setprecision(17)<<"ATLAS_EXPORT dimensions="<<nx<<','<<ny<<','<<nz<<" samples="<<samples
    <<" float_bytes="<<samples*sizeof(float)<<" seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()<<" physics_steps=0\n";
}
