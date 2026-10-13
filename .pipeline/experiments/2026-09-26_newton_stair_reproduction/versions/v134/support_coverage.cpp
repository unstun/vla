// Offline static-map negative coverage generation. No simulator state input.
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>
using Point=std::array<double,3>;
using Cell=std::pair<int,int>;
struct Triangle { Point a,b,c; };
int main(int argc,char**argv) {
  if(argc!=4)throw std::runtime_error("triangles.f64 floors.f32 output.txt required");
  std::ifstream tf(argv[1],std::ios::binary),pf(argv[2],std::ios::binary);
  if(!tf||!pf)throw std::runtime_error("missing input");
  std::vector<Triangle> triangles;Triangle t;
  while(tf.read(reinterpret_cast<char*>(&t),sizeof(t)))triangles.push_back(t);
  if(!tf.eof()||tf.gcount()!=0)throw std::runtime_error("partial triangle");
  std::map<Cell,std::vector<size_t>> index;
  for(size_t i=0;i<triangles.size();++i) {
    auto a=triangles[i];double det=(a.b[0]-a.a[0])*(a.c[1]-a.a[1])-(a.b[1]-a.a[1])*(a.c[0]-a.a[0]);
    if(std::abs(det)<1e-10)continue;
    double lx=std::min(a.a[0],std::min(a.b[0],a.c[0])),hx=std::max(a.a[0],std::max(a.b[0],a.c[0]));
    double ly=std::min(a.a[1],std::min(a.b[1],a.c[1])),hy=std::max(a.a[1],std::max(a.b[1],a.c[1]));
    for(int x=std::floor(lx/.1);x<=int(std::floor(hx/.1));++x)
      for(int y=std::floor(ly/.1);y<=int(std::floor(hy/.1));++y)index[{x,y}].push_back(i);
  }
  auto present=[&](double x,double y,double level) {
    auto found=index.find({int(std::floor(x/.1)),int(std::floor(y/.1))});if(found==index.end())return false;
    for(auto i:found->second) {
      auto a=triangles[i];double ux=a.b[0]-a.a[0],uy=a.b[1]-a.a[1],vx=a.c[0]-a.a[0],vy=a.c[1]-a.a[1];
      double d=ux*vy-uy*vx,s=((x-a.a[0])*vy-(y-a.a[1])*vx)/d,r=(ux*(y-a.a[1])-uy*(x-a.a[0]))/d;
      if(s>=-1e-9&&r>=-1e-9&&s+r<=1+1e-9) {
        double z=a.a[2]+s*(a.b[2]-a.a[2])+r*(a.c[2]-a.a[2]);
        if(std::abs(z-level)<.26)return true;
      }
    }
    return false;
  };
  std::ofstream out(argv[3]);out<<std::setprecision(17);std::array<float,4> p;size_t total=0,partial=0;
  while(pf.read(reinterpret_cast<char*>(p.data()),sizeof(p))) {
    bool complete=true;
    for(int x=0;x<4;++x)for(int y=0;y<4;++y)
      if(!present(p[0]-.05+(x+.5)*.025,p[1]-.05+(y+.5)*.025,p[2]-.03))complete=false;
    ++total;
    if(!complete){out<<double(p[0])<<' '<<double(p[1])<<' '<<double(p[2])-.03<<'\n';++partial;}
  }
  if(!pf.eof()||pf.gcount()!=0||total==0)throw std::runtime_error("invalid floor input");
  std::cout<<"{\"cells\":"<<total<<",\"partial\":"<<partial<<"}\n";
}
