#pragma once
// Shared native support geometry. This cannot grant observed obstacle freedom.
#include <plan_env/reactive_collision.h>
#include <plan_env/eth_step_score_adaptation.h>
#include <plan_env/support_gap_mask.h>
#include <plan_env/footprint_query.h>
#include <plan_env/rotation_cover.h>
#include <algorithm>
#include <array>
#include <fstream>
#include <iomanip>
#include <memory>
#include <sstream>

namespace reactive_stair {
inline bool staticSupportCell(double x,double y,const TerrainSnapshot &raw,
    bool canonical,double ox,double oy,Cell2 &cell) {
  const auto index=[&](double world,double origin) {
    double q=(world-origin)/raw.resolution_m;
    const double nearest=std::round(q);
    const double scale=std::max({1.,std::abs(q),std::abs(world)/raw.resolution_m,std::abs(origin)/raw.resolution_m});
    if(std::abs(q-nearest)<=32.*std::numeric_limits<double>::epsilon()*scale)q=nearest;
    return std::floor(q);
  };
  const double ix=canonical ? index(x,ox)-std::round((raw.origin_x_m-ox)/raw.resolution_m) : std::floor((x-raw.origin_x_m)/raw.resolution_m);
  const double iy=canonical ? index(y,oy)-std::round((raw.origin_y_m-oy)/raw.resolution_m) : std::floor((y-raw.origin_y_m)/raw.resolution_m);
  if(!std::isfinite(ix)||!std::isfinite(iy)||ix<std::numeric_limits<int>::min()||ix>std::numeric_limits<int>::max()||iy<std::numeric_limits<int>::min()||iy>std::numeric_limits<int>::max())return false;
  cell={int(ix),int(iy)};return true;
}

struct StaticSupportSamples {const std::vector<SurfaceCell> *raw=nullptr,*scored=nullptr;};
struct UncachedSupportSamples {StaticSupportSamples operator()(const Cell2 &) const {return {};}};
template<class CellLookup,class SurfaceLookup=UncachedSupportSamples>
Verdict staticSupportGeometry(const std::array<double,3> &body,double yaw,
    const TerrainSnapshot &raw,const TerrainSnapshot &scored,const CollisionDecision &decision,
    const Parameters &parameters,double offset,CellLookup cell_at,const SupportGapMask *gap,
    SurfaceLookup samples_at={}) {
  using V=Verdict;
  if(!std::isfinite(body[0])||!std::isfinite(body[1])||!std::isfinite(body[2])||!std::isfinite(yaw))return V::InvalidQuery;
  if(raw.source_id!=scored.source_id||raw.frame!=scored.frame||raw.resolution_m!=scored.resolution_m||raw.origin_x_m!=scored.origin_x_m||raw.origin_y_m!=scored.origin_y_m)return V::MissingInput;
  Query body_query;body_query.frame=raw.frame;body_query.in_map=true;
  body_query.x_m=body[0];body_query.y_m=body[1];body_query.z_m=body[2];
  Cell2 body_cell;
  if(!cell_at(body[0],body[1],body_cell))return V::InvalidQuery;
  const auto bv=decision.supportVerdict(body_query,&body_cell,samples_at(body_cell).scored);

  const auto associate=[&](double x,double y,double target,double limit,double &height) {
    Cell2 cell;if(!cell_at(x,y,cell))return false;
    auto samples=samples_at(cell);
    if(!samples.raw||!samples.scored){const auto a=raw.cells.find(cell),b=scored.cells.find(cell);
      if(a==raw.cells.end()||b==scored.cells.end())return false;samples={&a->second,&b->second};}
    if(samples.raw->size()!=samples.scored->size())return false;
    const int layer=nearestSurface(*samples.raw,target,limit);
    if(layer<0||(*samples.scored)[layer].elevation_m!=(*samples.raw)[layer].elevation_m||!selectedSurface((*samples.scored)[layer]))return false;
    height=(*samples.scored)[layer].elevation_m;return true;
  };
  double body_ground=0.;
  const bool body_associated=associate(body[0],body[1],body[2]-parameters.body_clearance_m,parameters.body_height_tolerance_m,body_ground);
  V verdict=V::Free;
  const auto test=[&](const std::array<double,3> &p) {
    if(gap&&gap->blocks(p[0],p[1],p[2]-parameters.body_clearance_m)){verdict=V::SupportGap;return 1;}
    if(bv!=V::Free){verdict=bv;return 1;}
    if(!body_associated){verdict=V::UnknownSupport;return 1;}
    double ground;
    const double step=StepScoreParameters{}.critical_height_m;
    if(!associate(p[0],p[1],body_ground,step,ground))verdict=V::UnknownSupport;
    else if(std::abs(ground-body_ground)>=step)verdict=V::UnsupportedTerrain;
    else {
      auto q=body_query;q.x_m=p[0];q.y_m=p[1];q.z_m=ground+parameters.body_clearance_m;
      Cell2 cell;verdict=cell_at(p[0],p[1],cell)?decision.supportVerdict(q,&cell,samples_at(cell).scored):V::InvalidQuery;
    }
    return verdict==V::Free?0:1;
  };
  if(twoCylinderQuery(body,yaw,offset,test)!=0&&verdict==V::Free)return V::InvalidQuery;
  return verdict;
}

// Immutable export of native raw/scored support, not a margin threshold mask.
class StaticSupportField {
 public:
  StaticSupportField(const std::string &path,const std::string &expected_fnv) : decision_(parameters_) {
    std::ifstream file(path,std::ios::binary);
    if(!file)throw std::runtime_error("Missing native support field");
    const std::string bytes((std::istreambuf_iterator<char>(file)),{});
    uint64_t hash=14695981039346656037ULL;for(unsigned char c:bytes){hash^=c;hash*=1099511628211ULL;}
    if(bytes.size()>64*1024*1024||std::to_string(hash)!=expected_fnv)throw std::runtime_error("Native support field identity mismatch");
    std::istringstream input(bytes);std::string magic,gap_path,gap_fnv;size_t count;
    input>>magic>>raw_.resolution_m>>raw_.origin_x_m>>raw_.origin_y_m>>canonical_>>ox_>>oy_
      >>parameters_.body_clearance_m>>parameters_.body_height_tolerance_m>>parameters_.robot_radius_m>>offset_
      >>raw_.source_id>>raw_.frame>>count>>std::quoted(gap_path)>>gap_fnv;
    if(!input||magic!="SUPPORT247"||count==0||count>1000000||raw_.resolution_m<=0||parameters_.robot_radius_m<=0||parameters_.body_height_tolerance_m<0||offset_<0)throw std::runtime_error("Invalid native support header");
    for(double v:{raw_.resolution_m,raw_.origin_x_m,raw_.origin_y_m,ox_,oy_,parameters_.body_clearance_m,parameters_.body_height_tolerance_m,parameters_.robot_radius_m,offset_})if(!std::isfinite(v))throw std::runtime_error("Nonfinite native support geometry");
    raw_.stamp_s=1.;scored_=raw_;
    for(size_t i=0;i<count;++i){int x,y,a,b;double z;input>>x>>y>>z>>a>>b;
      if(!input||!std::isfinite(z)||a<0||a>3||b<0||b>3)throw std::runtime_error("Invalid native support cell");
      raw_.cells[{x,y}].push_back({Support(a),z});scored_.cells[{x,y}].push_back({Support(b),z});}
    std::string extra;if(input>>extra)throw std::runtime_error("Trailing native support data");
    decision_=CollisionDecision(parameters_);
    if(!valid(raw_)||!decision_.acceptTerrain(scored_))throw std::runtime_error("Invalid native support snapshot");
    buildDenseIndex();
    if(!gap_path.empty())gap_=std::make_shared<SupportGapMask>(gap_path,gap_fnv,parameters_.robot_radius_m);
  }
  Verdict assess(double x,double y,double z,double yaw) const {
    return staticSupportGeometry({{x,y,z}},yaw,raw_,scored_,decision_,parameters_,offset_,
      [&](double a,double b,Cell2 &cell){return staticSupportCell(a,b,raw_,canonical_,ox_,oy_,cell);},gap_.get(),
      [&](const Cell2 &cell){return samplesAt(cell);});
  }
  bool surfaceHeight(double x,double y,double target,double &height,double limit=-1.) const {
    Cell2 cell;if(!staticSupportCell(x,y,raw_,canonical_,ox_,oy_,cell))return false;
    const auto s=samplesAt(cell);if(!s.raw||!s.scored||s.raw->size()!=s.scored->size())return false;
    const int layer=nearestSurface(*s.raw,target,limit<0.?parameters_.body_height_tolerance_m:limit);
    if(layer<0||(*s.scored)[layer].elevation_m!=(*s.raw)[layer].elevation_m||!selectedSurface((*s.scored)[layer]))return false;
    height=(*s.raw)[layer].elevation_m;return true;
  }
  std::vector<double> surfaceHeights(double x,double y) const {
    Cell2 cell;if(!staticSupportCell(x,y,raw_,canonical_,ox_,oy_,cell))return {};
    const auto s=samplesAt(cell);if(!s.raw||!s.scored||s.raw->size()!=s.scored->size())return {};
    std::vector<double> out;
    for(size_t i=0;i<s.raw->size();++i)
      if((*s.raw)[i].elevation_m==(*s.scored)[i].elevation_m&&selectedSurface((*s.scored)[i]))out.push_back((*s.raw)[i].elevation_m);
    std::sort(out.begin(),out.end());out.erase(std::unique(out.begin(),out.end()),out.end());return out;
  }
  bool certifiesFreeRotation(double x,double y,double z) const {
    if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||assess(x,y,z,0.)!=Verdict::Free)return false;
    double body_ground=0.;if(!surfaceHeight(x,y,z-parameters_.body_clearance_m,body_ground))return false;
    Cell2 lo,hi;
    if(!staticSupportCell(x-offset_,y-offset_,raw_,canonical_,ox_,oy_,lo)||
       !staticSupportCell(x+offset_,y+offset_,raw_,canonical_,ox_,oy_,hi))return false;
    const int64_t nx=int64_t(hi.x)-lo.x+1,ny=int64_t(hi.y)-lo.y+1;
    if(nx<=0||ny<=0||nx>256||ny>256||nx*ny>256)return false;
    Query q;q.frame=raw_.frame;q.in_map=true;q.x_m=x;q.y_m=y;
    for(int64_t ix=lo.x;ix<=hi.x;++ix)for(int64_t iy=lo.y;iy<=hi.y;++iy){
      const Cell2 cell{int(ix),int(iy)};const auto s=samplesAt(cell);
      if(!s.raw||!s.scored||s.raw->size()!=s.scored->size())return false;
      const int layer=nearestSurface(*s.raw,body_ground,StepScoreParameters{}.critical_height_m);
      if(layer<0||!selectedSurface((*s.scored)[layer])||(*s.raw)[layer].elevation_m!=(*s.scored)[layer].elevation_m)return false;
      q.z_m=(*s.raw)[layer].elevation_m+parameters_.body_clearance_m;
      if(decision_.supportVerdict(q,&cell,s.scored)!=Verdict::Free)return false;
    }
    if(gap_){const auto cover=rotationCover(parameters_.robot_radius_m,offset_);if(!cover)return false;
      for(const auto &p:*cover)if(gap_->blocks(x+p.x(),y+p.y(),z-parameters_.body_clearance_m))return false;
    }
    return true;
  }
  bool coreSupported(double x,double y,double z) const {
    Cell2 cell;if(!staticSupportCell(x,y,raw_,canonical_,ox_,oy_,cell))return false;
    Query q;q.frame=raw_.frame;q.in_map=true;q.x_m=x;q.y_m=y;q.z_m=z;
    if(decision_.supportVerdict(q,&cell,samplesAt(cell).scored)!=Verdict::Free)return false;
    double ground;if(!surfaceHeight(x,y,z-parameters_.body_clearance_m,ground))return false;
    const double squared=parameters_.robot_radius_m*parameters_.robot_radius_m-offset_*offset_;
    if(gap_&&squared>0.){
      std::array<double,2> gradient;
      const double margin=gap_->penetrationMargin(x,y,z-parameters_.body_clearance_m,gradient);
      if(margin+parameters_.robot_radius_m-std::sqrt(squared)<-1e-9)return false;
    }
    return true;
  }
  const SupportGapMask *gapMask() const {return gap_.get();}
  struct GapConstraint {
    bool blocked=false;double margin=0.;
    std::array<double,3> gradient{{0.,0.,0.}}; // World X,Y,yaw.
  };
  GapConstraint gapConstraint(double x,double y,double z,double yaw) const {
    if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||!std::isfinite(yaw))
      throw std::runtime_error("Invalid physical gap query");
    GapConstraint result;if(!gap_)return result;
    const double c=std::cos(yaw),s=std::sin(yaw);
    for(double sign:{-1.,1.}) {
      const double cx=x+sign*offset_*c,cy=y+sign*offset_*s,ground=z-parameters_.body_clearance_m;
      if(!gap_->blocks(cx,cy,ground))continue;
      std::array<double,2> gradient;const double margin=gap_->penetrationMargin(cx,cy,ground,gradient);
      if(!result.blocked||margin<result.margin) {
        result.margin=margin;
        result.gradient={{gradient[0],gradient[1],sign*offset_*(-s*gradient[0]+c*gradient[1])}};
      }
      result.blocked=true;
    }
    return result;
  }
  double radius()const{return parameters_.robot_radius_m;}
  double offset()const{return offset_;}
  double bodyClearance()const{return parameters_.body_clearance_m;}
  double heightTolerance()const{return parameters_.body_height_tolerance_m;}
 private:
  struct DenseCell {std::vector<SurfaceCell> raw,scored;};
  int dense_x_=0,dense_y_=0,dense_nx_=0,dense_ny_=0;
  std::vector<DenseCell> dense_cells_;
  void buildDenseIndex() {
    if(raw_.cells.empty())return;
    int lo_x=raw_.cells.begin()->first.x,hi_x=lo_x,lo_y=raw_.cells.begin()->first.y,hi_y=lo_y;
    for(const auto &c:raw_.cells){lo_x=std::min(lo_x,c.first.x);hi_x=std::max(hi_x,c.first.x);lo_y=std::min(lo_y,c.first.y);hi_y=std::max(hi_y,c.first.y);}
    const int64_t nx=int64_t(hi_x)-lo_x+1,ny=int64_t(hi_y)-lo_y+1;
    if(nx<=0||ny<=0||nx>4000000||ny>4000000||nx*ny>4000000)return;
    dense_x_=lo_x;dense_y_=lo_y;dense_nx_=int(nx);dense_ny_=int(ny);dense_cells_.resize(size_t(nx)*ny);
    for(const auto &c:raw_.cells){auto &d=dense_cells_[size_t(c.first.x-lo_x)*dense_ny_+c.first.y-lo_y];d.raw=c.second;
      const auto s=scored_.cells.find(c.first);if(s!=scored_.cells.end())d.scored=s->second;}
  }
  StaticSupportSamples samplesAt(const Cell2 &cell) const {
    if(!dense_cells_.empty()){
      const int64_t x=int64_t(cell.x)-dense_x_,y=int64_t(cell.y)-dense_y_;
      if(x<0||y<0||x>=dense_nx_||y>=dense_ny_)return {};
      const auto &d=dense_cells_[size_t(x)*dense_ny_+size_t(y)];
      return {d.raw.empty()?nullptr:&d.raw,d.scored.empty()?nullptr:&d.scored};
    }
    const auto a=raw_.cells.find(cell),b=scored_.cells.find(cell);
    return {a==raw_.cells.end()?nullptr:&a->second,b==scored_.cells.end()?nullptr:&b->second};
  }
  Parameters parameters_;
  TerrainSnapshot raw_,scored_;
  CollisionDecision decision_;
  bool canonical_=false;double ox_=0.,oy_=0.,offset_=0.;
  std::shared_ptr<const SupportGapMask> gap_;
};
} // namespace reactive_stair
