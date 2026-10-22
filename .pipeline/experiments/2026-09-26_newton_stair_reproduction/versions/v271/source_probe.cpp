// Exercise the installed field API, not a second compiled copy of its kernel.
#include <plan_env/static_solid.h>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <random>
#include <vector>
#include <array>
#include <stdexcept>
using reactive_stair::StaticSolidField;
using reactive_stair::StaticSolidQueryCache;
void require(bool test,const char *message){if(!test)throw std::runtime_error(message);}
std::string fnv(const std::string &p){std::ifstream f(p,std::ios::binary);require(bool(f),"missing fixture");uint64_t h=14695981039346656037ULL;char c;while(f.get(c)){h^=static_cast<unsigned char>(c);h*=1099511628211ULL;}return std::to_string(h);}
std::string descriptor(const std::string &name,const std::string &tri,const std::string &meta){
  const std::string path="/evaluation/"+name+".surface";std::ofstream f(path);
  f<<"SURFACE271B .35 .18 .55 .35 .3 .15\n"<<std::quoted(tri)<<" "<<fnv(tri)<<"\n"<<std::quoted(meta)<<" "<<fnv(meta)<<"\n";f.close();return path;
}
int main(int argc,char **argv){
 require(argc==3,"source probe arguments");
 StaticSolidField field(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV"));StaticSolidQueryCache cache;
 require(field.radius()==.35&&field.offset()==.18&&field.up()==.55&&field.down()==.35&&field.bodyClearance()==.3,"profile changed");
 std::ifstream queries(argv[1]),expected(argv[2]);double x,y,g,yaw,value;size_t n=0,proofs=0,free=0,core=0;double error=0.;
 while(queries>>x>>y>>g>>yaw){require(bool(expected>>value),"missing reference value");Eigen::Vector3d p(x,y,g+.3);
   const auto actual=field.assess(p,yaw);error=std::max(error,std::abs(value-actual.margin));
   require(std::abs(value-actual.margin)<1e-8,"independent margin differs");require(actual.gradient.allFinite()&&actual.witness.allFinite(),"nonfinite assessment");
   require(field.collides(p,yaw)==(value<=0.)&&field.collides(p,yaw,cache)==(value<=0.),"boolean mismatch");
   const bool allfree=field.certifiesFreeRotation(p),blocked=field.coreCollision(p);free+=allfree;core+=blocked;
   require(field.impossibleAt(p)==blocked,"source impossible proof differs");
   for(int k=0;k<32;++k){const bool hit=field.collides(p,k*M_PI/32.);require(!allfree||!hit,"false rotation freedom");require(!blocked||hit,"false common core collision");++proofs;}
   ++n;
 }
 require(n==512&&!(expected>>value)&&free&&core,"scene coverage incomplete");
 // Exact source cache parity across close XY offsets and tiny height changes.
 std::mt19937_64 rng(271);std::uniform_real_distribution<double> xy(-9.,11.),angle(-8*M_PI,8*M_PI);
 size_t cache_checks=0;
 for(double h:{.0580303,1.5580303,3.0580303,4.5330312})for(int i=0;i<2500;++i){
   const double x=xy(rng),y=xy(rng),yaw=angle(rng);
   for(const auto &delta:std::vector<Eigen::Vector3d>{{0,0,0},{1e-7,-1e-7,0},{.01,-.015,0},{1e-7,-1e-7,1e-8}}){
     const Eigen::Vector3d p=Eigen::Vector3d(x,y,h+.3)+delta;
     const bool exact=field.assess(p,yaw).collision();
     require(field.collides(p,yaw)==exact&&field.collides(p,yaw,cache)==exact,"source early/cache query changed full assessment");++cache_checks;
   }
 }
 require(cache.hits()>0,"source certificate branch untested");
 size_t edge_queries=0;
 for(int i=0;i<5000;++i){
   Eigen::Vector3d a(xy(rng),xy(rng),.3+(i%4)*1.5),b=a+Eigen::Vector3d(.15*std::sin(i),.15*std::cos(i),i%3?0.:.3);
   const double yaw=std::atan2(b.y()-a.y(),b.x()-a.x());const int steps=std::max(1,int(std::ceil((b-a).norm()/.025)));
   for(int k=0;k<=steps;++k){Eigen::Vector3d p=a+(b-a)*(double(k)/steps);
     const bool exact=field.assess(p,yaw).collision();require(field.collides(p,yaw)==exact&&field.collides(p,yaw,cache)==exact,"swept source cache mismatch");++edge_queries;
   }
 }
 const auto cache_hits=cache.hits();

 // Same independent counterexamples, now through the installed API.
 std::ifstream units("/work/fixtures/source_units.tsv");std::string name;size_t unit_count=0;
 while(units>>name>>x>>y>>g>>yaw>>value){const std::string stem="/task/source_surface_native_v270/unit_"+name;
   const auto path=descriptor("unit_"+name,stem+".f64",stem+".meta");StaticSolidField unit(path,fnv(path));
   require(std::abs(unit.assess(Eigen::Vector3d(x,y,g+.3),yaw).margin-value)<1e-8&&unit.collides(Eigen::Vector3d(x,y,g+.3),yaw,cache)==(value<=0.),"installed counterexample differs");++unit_count;
 }
 require(unit_count==14,"unit coverage incomplete");
 // Small nonterrain surfaces are still filled projected polygons for distance.
 using Triangle=std::array<std::array<double,3>,3>;
 const double e=1e-6;std::vector<Triangle> tiny{{{{{-e,-e,.1}},{{e,-e,.1}},{{0,e,.1}}}}};
 const std::string tp="/evaluation/tiny.f64",mp="/evaluation/tiny.meta";
 {std::ofstream f(tp,std::ios::binary);f.write(reinterpret_cast<const char*>(tiny.data()),tiny.size()*sizeof(Triangle));}
 {std::ofstream f(mp);f<<"SURFACE268C 1 0\nF\n-1\n";}
 const auto dp=descriptor("tiny",tp,mp);StaticSolidField tinyfield(dp,fnv(dp));
 const auto t=tinyfield.assess(Eigen::Vector3d(-.18,0,.3),0);
 require(std::abs(t.margin+.35)<1e-12,"tiny triangle interior treated as line");
 require((t.witness-Eigen::Vector3d(0,0,.1)).norm()<1e-12,"tiny witness not actual surface");
 // Analytic wall clearance, derivative and real witness.
 std::vector<Triangle> wall{{{{{.75,-2,-1}},{{.75,2,-1}},{{.75,2,2}}}},{{{{.75,-2,-1}},{{.75,2,2}},{{.75,-2,2}}}}};
 {std::ofstream f(tp,std::ios::binary);f.write(reinterpret_cast<const char*>(wall.data()),wall.size()*sizeof(Triangle));}
 {std::ofstream f(mp);f<<"SURFACE268C 2 0\nF\n-1\n-1\n";}
 const auto wp=descriptor("wall",tp,mp);StaticSolidField wallfield(wp,fnv(wp));auto w=wallfield.assess(Eigen::Vector3d(.3,0,.3),0);
 require(std::abs(w.margin+.08)<1e-12,"wall clearance wrong");require((w.gradient-Eigen::Vector4d(-1,0,0,0)).norm()<1e-8,"wall derivative wrong");
 require(std::abs(w.witness.x()-.75)<1e-12&&std::abs(w.witness.y())<1e-12&&w.witness.z()>=-.25&&w.witness.z()<=.65,"wall witness off geometry");
 bool rejected=false;try{StaticSolidField bad(wp,"0");}catch(const std::runtime_error&){rejected=true;}require(rejected,"root hash not checked");
 for(double dx:{-.03,-1e-8,-1e-12,0.,1e-12,1e-8,.03})for(double dy:{-.11,0.,.11}){
   const Eigen::Vector3d p(.22+dx,dy,.3);require(wallfield.collides(p,0,cache)==wallfield.assess(p,0).collision(),"wall tangent cache mismatch");
 }
 // Dependency identity is checked before use, not merely recorded.
 {std::ofstream f(tp,std::ios::binary|std::ios::app);f.put('x');}
 rejected=false;try{StaticSolidField bad(wp,fnv(wp));}catch(const std::runtime_error&){rejected=true;}require(rejected,"dependency hash not checked");
 rejected=false;try{field.assess(Eigen::Vector3d::Zero(),std::numeric_limits<double>::quiet_NaN());}catch(const std::runtime_error&){rejected=true;}require(rejected,"NaN accepted");
 require(tinyfield.collides(Eigen::Vector3d(-.18,0,.3),0,cache),"cache owner did not change to tiny field");
 require(wallfield.collides(Eigen::Vector3d(.3,0,.3),0,cache),"cache owner did not change to wall field");
 std::cout<<"source_cache_queries="<<cache_checks<<"\nsource_swept_edges=5000\nsource_swept_queries="<<edge_queries<<"\nsource_cache_hits="<<cache_hits<<"\n";
 std::cout<<std::setprecision(17)<<"queries="<<n<<"\nmax_margin_error="<<error<<"\nrotational_implications="<<proofs<<"\nfree_certificates="<<free<<"\ncore_certificates="<<core<<"\ncounterexamples="<<unit_count<<"\nadditional_api_controls=6\nfailures=0\n";
}
