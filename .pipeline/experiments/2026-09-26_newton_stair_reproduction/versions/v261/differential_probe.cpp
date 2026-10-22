#include <plan_env/static_solid.h>
#include <fstream>
#include <sstream>
#include <random>
#include <iostream>
#include <iomanip>
#include <chrono>
extern "C" void *legacy256Create(const char *,const char *);
extern "C" void legacy256Destroy(void *);
extern "C" bool legacy256Query(void *,double,double,double,double,double *);
extern "C" bool legacy256Collides(void *,double,double,double,double);
int main(int argc,char **argv) {
  const char *path="/work/fixtures/building/static_solids.env",*fnv="17629216882668158307";
  reactive_stair::StaticSolidField fast(path,fnv);void *old=legacy256Create(path,fnv);
  size_t n=0,bad=0,values=0,cached_bad=0;double max_error=0.;
  reactive_stair::StaticSolidQueryCache memo;
  const auto check=[&](double x,double y,double z,double yaw) {
    double v[8];const bool before=legacy256Query(old,x,y,z,yaw,v);
    const auto a=fast.assess({x,y,z},yaw);const bool after=fast.collides({x,y,z},yaw);
    cached_bad+=before!=fast.collides({x,y,z},yaw,memo);
    ++n;bad+=before!=after;double newer[8]={a.margin,a.gradient(0),a.gradient(1),a.gradient(2),a.gradient(3),a.witness(0),a.witness(1),a.witness(2)};
    for(int k=0;k<8;++k){max_error=std::max(max_error,std::abs(v[k]-newer[k]));values+=v[k]!=newer[k];}
    if(before!=after)std::cerr<<"MISMATCH "<<std::setprecision(17)<<x<<','<<y<<','<<z<<','<<yaw<<'\n';
  };
  for(int arg=1;arg<argc;++arg) {
    std::ifstream f(argv[arg]);std::string line;std::getline(f,line);
    while(std::getline(f,line)){std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);double x,y,z,yaw;if(row>>x>>y>>z>>yaw)check(x,y,z,yaw);}
  }
  std::mt19937_64 rng(259);std::uniform_real_distribution<double> xy(-9.,11.),z(-.5,7.),yaw(-8*M_PI,8*M_PI);
  for(int i=0;i<20000;++i)check(xy(rng),xy(rng),z(rng),yaw(rng));
  // Nearby non-lattice perturbations share certificates, including near floors.
  for(double h:{.0580303,1.5580303,3.0580303,4.5330312})for(int i=0;i<5000;++i) {
    const double x=xy(rng),y=xy(rng),a=yaw(rng);
    check(x,y,h+.3,a);check(x+1e-7,y-1e-7,h+.3+1e-8,a+1e-7);
  }
  size_t edges=0,edge_bad=0;
  for(int i=0;i<5000;++i) {
    const Eigen::Vector3d a(xy(rng),xy(rng),.3+(i%4)*1.5);
    const Eigen::Vector3d b=a+Eigen::Vector3d(.15*std::sin(i),.15*std::cos(i),i%3?.0:.3);
    const double angle=std::atan2(b.y()-a.y(),b.x()-a.x());
    bool before=false,after=false;const int count=std::max(1,int(std::ceil((b-a).norm()/.025)));
    for(int k=0;k<=count;++k) {
      const Eigen::Vector3d p=a+(b-a)*(double(k)/count);
      const bool reference=legacy256Collides(old,p.x(),p.y(),p.z(),angle);before|=reference;
      cached_bad+=reference!=fast.collides(p,angle,memo);
      after|=fast.collides(p,angle);
    }
    ++edges;edge_bad+=before!=after;
  }
  legacy256Destroy(old);
  std::cout<<"queries="<<n<<"\nbinary_mismatches="<<bad<<"\nnonidentical_values="<<values<<"\nmax_margin_gradient_witness_error="<<std::setprecision(17)<<max_error<<'\n';
  std::cout<<"edges="<<edges<<"\nedge_mismatches="<<edge_bad<<'\n';
  std::cout<<"cached_mismatches="<<cached_bad<<"\ncache_cylinder_queries="<<memo.queries()<<"\ncache_bound_hits="<<memo.hits()<<'\n';
  return bad||values||edge_bad||cached_bad||!memo.hits()?1:0;
}
