#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <lite3_nav2_plugins/support_height.hpp>
#include <plan_env/reactive_collision.h>
#include <map_manager/support_grid_index.h>

namespace lite3_nav2
{
namespace
{
uint64_t readUnsigned(std::istream &stream, int bytes) {
  uint64_t value=0;
  for (int i=0;i<bytes;++i) {
    const auto byte=stream.get();
    if (byte==std::char_traits<char>::eof()) throw std::runtime_error("Truncated PCT map");
    value|=static_cast<uint64_t>(static_cast<uint8_t>(byte))<<(8*i);
  }
  return value;
}
double readDouble(std::istream &stream) {
  const uint64_t bits=readUnsigned(stream,8);
  double value;static_assert(sizeof(value)==sizeof(bits),"PCT map requires IEEE float64");
  std::memcpy(&value,&bits,sizeof(value));
  if (!std::isfinite(value)) throw std::runtime_error("Nonfinite PCT map value");
  return value;
}
// numpy.round uses ties-to-even, while std::round rounds ties away from zero.
double roundEven(double value) {
  const double lower=std::floor(value), fraction=value-lower;
  if (fraction<0.5) return lower;
  if (fraction>0.5) return lower+1;
  return std::fmod(lower,2.0)==0.0 ? lower : lower+1;
}
}

PCTRoutePlanner::PCTRoutePlanner(const std::string &bundle,double reference_height,
    bool quintic,double max_heading_rate): quintic_(quintic),planner_(max_heading_rate,quintic)
{
  if (!std::isfinite(reference_height) || !std::isfinite(max_heading_rate) || max_heading_rate<=0)
    throw std::runtime_error("Invalid PCT optimizer parameters");
  std::ifstream input(bundle,std::ios::binary);
  char magic[8];input.read(magic,8);
  if (!input || std::memcmp(magic,"PCTMAP01",8)!=0) throw std::runtime_error("Invalid PCT map format");
  const auto layers=readUnsigned(input,4), nx=readUnsigned(input,4), ny=readUnsigned(input,4);
  if (!layers || !nx || !ny || layers*nx>static_cast<uint64_t>(std::numeric_limits<int>::max()) ||
      ny>static_cast<uint64_t>(std::numeric_limits<int>::max())) throw std::runtime_error("Invalid PCT dimensions");
  layers_=static_cast<int>(layers);nx_=static_cast<int>(nx);ny_=static_cast<int>(ny);
  resolution_=readDouble(input);cx_=readDouble(input);cy_=readDouble(input);
  h0_=readDouble(input);dh_=readDouble(input);
  if (resolution_<=0 || dh_<=0) throw std::runtime_error("Invalid PCT map resolution");
  const auto start=input.tellg();input.seekg(0,std::ios::end);
  const uint64_t bytes=static_cast<uint64_t>(input.tellg()-start);
  const uint64_t cells=layers*nx*ny;
  if (bytes/49!=cells || bytes%49!=0) throw std::runtime_error("PCT map dimensions do not match payload");
  input.seekg(start);
  auto matrix=[&]() {
    Eigen::MatrixXd result(layers_*nx_,ny_);
    for(int row=0;row<result.rows();++row)
      for(int col=0;col<result.cols();++col) result(row,col)=readDouble(input);
    return result;
  };
  costs_=matrix();ground_=matrix();ceiling_=matrix();
  gateway_=matrix();grad_x_=matrix();grad_y_=matrix();
  ground_valid_.resize(cells);
  input.read(reinterpret_cast<char *>(ground_valid_.data()),ground_valid_.size());
  if (!input || std::any_of(ground_valid_.begin(),ground_valid_.end(),[](uint8_t x){return x>1;}))
    throw std::runtime_error("Invalid PCT ground validity mask");
  reference_height_=reference_height;
  rebuildMap();
}

void PCTRoutePlanner::clearRepairConstraints() {
  if(rejected_.empty()) return;
  rejected_.clear();rebuildMap();
}

void PCTRoutePlanner::addRepairConstraints(const std::vector<RejectedPose> &poses) {
  for(const auto &pose:poses) {
    if(!pose.position.allFinite() || !std::isfinite(pose.yaw)) throw std::runtime_error("pct_invalid_rejection");
    const auto index=poseToIndex(pose.position);
    if(std::abs(ground_(index[0]*nx_+index[2],index[1])+reference_height_-pose.position.z())>=.26)continue;
    const auto duplicate=std::find_if(rejected_.begin(),rejected_.end(),[&](const auto &old) {
      return poseToIndex(old.position)==index && old.all_headings==pose.all_headings &&
        std::abs(std::remainder(old.yaw-pose.yaw,M_PI))<.15;
    });
    if(duplicate==rejected_.end()) rejected_.push_back(pose);
    if(rejected_.size()>512) throw std::runtime_error("pct_repair_constraint_budget");
  }
  rebuildMap();
}

void PCTRoutePlanner::setFeedbackConstraints(const std::vector<RejectedPose> &poses) {
  if(poses.size()>128)throw std::runtime_error("pct_feedback_budget");
  std::vector<RejectedPose> next;
  for(const auto &pose:poses) {
    if(!pose.position.allFinite()||!std::isfinite(pose.yaw))throw std::runtime_error("pct_invalid_feedback");
    const auto index=poseToIndex(pose.position);
    if(std::abs(ground_(index[0]*nx_+index[2],index[1])+reference_height_-pose.position.z())<.26)next.push_back(pose);
  }
  bool same=next.size()==feedback_.size();
  for(size_t i=0;same&&i<next.size();++i)same=next[i].position==feedback_[i].position&&next[i].yaw==feedback_[i].yaw&&next[i].all_headings==feedback_[i].all_headings;
  if(!same){feedback_=std::move(next);rebuildMap();}
}

bool PCTRoutePlanner::rejectedAt(const Eigen::Vector3d &point,double yaw,bool feedback_only) const {
  const auto hit=[&](const auto &poses) {
    return std::any_of(poses.begin(),poses.end(),[&](const auto &pose) {
      return (pose.all_headings || std::abs(std::remainder(yaw-pose.yaw,M_PI))<=.35) &&
        std::abs(point.z()-pose.position.z())<.26 &&
        (point-pose.position).head(2).norm()<=resolution_*.75;
    });
  };
  return (!feedback_only&&hit(rejected_))||hit(feedback_);
}

Eigen::Vector3d PCTRoutePlanner::nodePosition(const Node &node) const {
  const auto xy=node.GridPosition();
  return {(xy(0)-nx_/2)*resolution_+cx_,(xy(1)-ny_/2)*resolution_+cy_,node.height+reference_height_};
}

Node PCTRoutePlanner::continuousEndpoint(const Eigen::Vector3d &pose) const {
  if(!pose.allFinite())throw std::runtime_error("Nonfinite PCT pose");
  const Eigen::Vector2d q((pose.x()-cx_)/resolution_+nx_/2,(pose.y()-cy_)/resolution_+ny_/2);
  if((q.array()<-.5).any()||q(0)>=nx_-.5||q(1)>=ny_-.5)throw std::runtime_error("PCT pose outside map");
  const int x=int(roundEven(q(0))),y=int(roundEven(q(1)));
  double floor;
  if(!support_->surfaceHeight(pose.x(),pose.y(),pose.z()-support_->bodyClearance(),floor,
      reactive_stair::StepScoreParameters{}.critical_height_m))
    throw std::runtime_error("pct_no_physical_support_at_endpoint");
  Node node;node.continuous=true;node.position=q;
  node.height=pose.z()-reference_height_;node.support_height=floor;
  node.idx=Eigen::Vector3i(int(floor/resolution_),x,y);
  // The stored layer is only a hint; the native continuous floor is authority.
  double best=std::numeric_limits<double>::infinity();
  for(int k=0;k<layers_;++k) {
    const double h=planning_ground_(k*nx_+x,y),d=std::abs(h-floor);
    if(h>-50.&&d<best){node.layer=k;best=d;}
  }
  return node;
}

bool PCTRoutePlanner::poseFree(const PoseSample &p) const {
  return !rejectedAt(p.position,p.yaw)&&(!support_||support_->assess(p.position.x(),p.position.y(),p.position.z(),p.yaw)==reactive_stair::Verdict::Free)&&(!solid_||!solid_->collides(p.position,p.yaw));
}
std::vector<PoseSample> PCTRoutePlanner::endpointConnection(const Node &from,const Node &to) const {
  const Eigen::Vector3d a=nodePosition(from),b=nodePosition(to),delta=b-a;
  const double chord=std::atan2(delta.y(),delta.x());
  if(std::isfinite(from.pose_yaw)&&std::isfinite(to.pose_yaw)) {
    const PoseSample first{a,from.pose_yaw},last{b,to.pose_yaw};
    if(!from.continuous&&!to.continuous){
      if(delta.head<2>().norm()>1e-10&&(std::abs(std::remainder(last.yaw-first.yaw,2*M_PI))>1e-10||std::abs(std::remainder(first.yaw-chord,2*M_PI))>1e-10))return samplePoseHermite(first,last);
      return samplePoseLine(first,last);
    }
    if(delta.head<2>().norm()<1e-10)return samplePoseLine(first,last);
    auto turn=samplePoseLine(first,{a,chord});
    const auto move=samplePoseLine({a,chord},{b,chord}),finish=samplePoseLine({b,chord},last);
    turn.insert(turn.end(),move.begin()+1,move.end());turn.insert(turn.end(),finish.begin()+1,finish.end());
    if(std::all_of(turn.begin(),turn.end(),[&](const auto &p){return poseFree(p);}))return turn;
    return samplePoseHermite(first,last);
  }
  double incoming=chord;
  if(!from.continuous&&from.parent){const Eigen::Vector3d d=a-nodePosition(*from.parent);if(d.head<2>().norm()>1e-10)incoming=std::atan2(d.y(),d.x());}
  double first=from.continuous&&std::isfinite(start_yaw_)?start_yaw_:incoming;
  const double last=to.continuous&&std::isfinite(goal_yaw_)?goal_yaw_:chord;
  if(from.continuous&&std::isfinite(start_yaw_)) {
    const auto turn=samplePoseLine({a,first},{a,chord});
    if(std::all_of(turn.begin(),turn.end(),[&](const auto &p){return poseFree(p);}))first=chord;
  }
  if((to.continuous&&std::isfinite(goal_yaw_))||std::abs(std::remainder(first-chord,2*M_PI))>1e-10)
    return samplePoseHermite({a,first},{b,last});
  return samplePoseLine({a,chord},{b,chord});
}
void PCTRoutePlanner::prepareEndpointPath(std::vector<PathPoint> &path) const {
  if(!support_||path.size()<2||(!std::isfinite(start_yaw_)&&!std::isfinite(goal_yaw_)))return;
  const auto node=[&](const PathPoint &p,bool endpoint){Node n;n.continuous=endpoint;
    n.position<<p.y,p.x;n.idx<<int(p.height/resolution_),int(std::round(p.y)),int(std::round(p.x));
    n.height=n.support_height=p.height;n.layer=p.layer;n.pose_yaw=M_PI/2-p.heading;return n;};
  std::vector<PathPoint> out;
  for(size_t i=1;i<path.size();++i) {
    auto a=node(path[i-1],i==1);const auto b=node(path[i],i+1==path.size());
    Node previous;if(i>=2){previous=node(path[i-2],false);a.parent=&previous;}
    for(const auto &sample:endpointConnection(a,b)) {
      PathPoint p;p.x=(sample.position.y()-cy_)/resolution_+ny_/2;p.y=(sample.position.x()-cx_)/resolution_+nx_/2;
      p.height=sample.position.z()-reference_height_;p.layer=path[i].layer;p.heading=M_PI/2-sample.yaw;
      if(!out.empty()&&std::hypot(out.back().x-p.x,out.back().y-p.y)<1e-10&&std::abs(out.back().height-p.height)<1e-10&&std::abs(std::remainder(out.back().heading-p.heading,2*M_PI))<1e-10)continue;
      out.push_back(p);
    }
  }
  path=std::move(out);
}

bool PCTRoutePlanner::transitionAllowed(const Node &from,const Node &to) const {
  if(support_) {
    const auto valid=[&](const Node &node) {
      if(node.continuous)return node.position.allFinite()&&std::isfinite(node.height);
      const size_t index=(node.layer*nx_+node.idx[1])*ny_+node.idx[2];
      return planning_ground_(node.layer*nx_+node.idx[1],node.idx[2])>-50.&&std::isfinite(node.height)&&node.height>-50.;
    };
    if(!valid(from)||!valid(to)||std::abs(to.SupportHeight()-from.SupportHeight())>=reactive_stair::StepScoreParameters{}.critical_height_m)return false;
  }
  if(support_&&((from.continuous&&std::isfinite(start_yaw_))||(to.continuous&&std::isfinite(goal_yaw_)))) {
    const auto poses=endpointConnection(from,to);
    return std::all_of(poses.begin(),poses.end(),[&](const auto &p){return poseFree(p);});
  }
  const auto a=nodePosition(from),b=nodePosition(to);const auto delta=b-a;
  const double yaw=std::atan2(delta.y(),delta.x());
  const int count=support_?std::max(1,int(std::ceil(delta.norm()/.025))):2;
  for(int i=0;i<=count;++i) {
    const auto p=a+delta*(double(i)/count);
    if(rejectedAt(p,yaw)||(support_&&support_->assess(p.x(),p.y(),p.z(),yaw)!=reactive_stair::Verdict::Free)||
        (solid_&&solid_->collides(p,yaw)))return false;
  }
  return true;
}

void PCTRoutePlanner::rebuildMap() {
  auto costs=costs_;
  planning_ground_=ground_;planning_ceiling_=ceiling_;
  if(support_) {
    // A tomogram slice boundary is not another physical floor. Associate each
    // proxy with the nearest original selected support before graph expansion.
    for(int x=0;x<nx_;++x)for(int y=0;y<ny_;++y) {
      for(int layer=0;layer<layers_;++layer) {
        const int row=layer*nx_+x;double height;
        if(!ground_valid_[row*ny_+y]||!support_->surfaceHeight(
            (x-nx_/2)*resolution_+cx_,(y-ny_/2)*resolution_+cy_,ground_(row,y),height))
          planning_ground_(row,y)=-100.;
        else planning_ground_(row,y)=height;
      }
      // Original tomogram reduction can lose a real lower floor beneath an
      // overhead surface. Native selected support, not a slice alias, owns
      // physical floor existence. Reuse vacant/duplicate proxy slots only.
      for(double height:support_->surfaceHeights((x-nx_/2)*resolution_+cx_,(y-ny_/2)*resolution_+cy_)) {
        bool present=false;for(int k=0;k<layers_;++k)present|=std::abs(planning_ground_(k*nx_+x,y)-height)<1e-9;
        if(present)continue;
        int slot=-1;double best=std::numeric_limits<double>::infinity();
        for(int k=0;k<layers_;++k) {
          const double h=planning_ground_(k*nx_+x,y);int aliases=0;
          if(h>-50.)for(int j=0;j<layers_;++j)aliases+=std::abs(planning_ground_(j*nx_+x,y)-h)<1e-9;
          if(h>-50.&&aliases<2)continue;
          const double d=std::abs(ground_(k*nx_+x,y)-height);
          if(d<best){best=d;slot=k;}
        }
        if(slot<0)throw std::runtime_error("pct_native_support_layer_capacity");
        planning_ground_(slot*nx_+x,y)=height;
        // A slice cut is not a physical ceiling for a newly recovered floor.
        // Actual overhead body solids are enforced by the shared solid field.
        planning_ceiling_(slot*nx_+x,y)=std::max(planning_ceiling_(slot*nx_+x,y),height+reference_height_+support_->heightTolerance());
      }
      // Aliases of one physical surface share its least restrictive observed
      // slice upper bound. A lower cut through that floor is not a ceiling.
      for(int layer=0;layer<layers_;++layer) {
        const int row=layer*nx_+x;const double height=planning_ground_(row,y);
        if(height<=-50.)continue;
        double upper=planning_ceiling_(row,y);
        for(int other=0;other<layers_;++other)
          if(planning_ground_(other*nx_+x,y)==height)upper=std::max(upper,planning_ceiling_(other*nx_+x,y));
        planning_ceiling_(row,y)=upper;
      }
    }
  }
  auto constraints=rejected_;constraints.insert(constraints.end(),feedback_.begin(),feedback_.end());
  if(!support_)for(const auto &pose:constraints) {
    const auto index=poseToIndex(pose.position);
    // A soft optimizer hint, never a position-only hard obstacle. The exact
    // rejected direction is enforced independently in graph expansion.
    for(int dx=-1;dx<=1;++dx) for(int dy=-1;dy<=1;++dy) {
      const int x=index[2]+dx,y=index[1]+dy;
      if(x<0||x>=nx_||y<0||y>=ny_)continue;
      auto &value=costs(index[0]*nx_+x,y);
      value=std::max(value,19.-2.*(std::abs(dx)+std::abs(dy)));
    }
  }
  const auto delta=costs-costs_;auto gx=grad_x_,gy=grad_y_;
  for(int layer=0;layer<layers_;++layer) {
    for(int x=1;x+1<nx_;++x)for(int y=0;y<ny_;++y)
      gx(layer*nx_+x,y)+=delta(layer*nx_+x+1,y)-delta(layer*nx_+x-1,y);
    for(int x=0;x<nx_;++x)for(int y=1;y+1<ny_;++y)
      gy(layer*nx_+x,y)+=delta(layer*nx_+x,y+1)-delta(layer*nx_+x,y-1);
  }
  planner_.InitMap(20.,15.,resolution_,layers_,.2,costs,planning_ground_,planning_ceiling_,gateway_,gx,gy);
  planner_.SetReferenceHeight(reference_height_);
  planner_.SetPhysicalSupportMode(bool(support_),reactive_stair::StepScoreParameters{}.critical_height_m);
  if(support_)planner_.SetPhysicalSurfaceQuery([this](double x,double y,double hint,double &height) {
    return support_->surfaceHeight((y-nx_/2)*resolution_+cx_,(x-ny_/2)*resolution_+cy_,hint,height,
      reactive_stair::StepScoreParameters{}.critical_height_m);
  });
  else planner_.SetPhysicalSurfaceQuery({});
  if(support_)planner_.SetPhysicalGapCost([this](double x,double y,double ground,double yaw,Eigen::Vector4d *gradient) {
    const auto gap=support_->gapConstraint((y-nx_/2)*resolution_+cx_,(x-ny_/2)*resolution_+cy_,ground+support_->bodyClearance(),yaw);
    if(gradient)gradient->setZero();
    double residual=0.;
    if(gap.blocked) {
      residual=1.-gap.margin/resolution_;
      if(gradient)*gradient<<-gap.gradient[1],-gap.gradient[0],0.,-gap.gradient[2]/resolution_;
    }
    if(solid_) {
      const Eigen::Vector3d p((y-nx_/2)*resolution_+cx_,(x-ny_/2)*resolution_+cy_,ground+reference_height_);
      if(!solid_->collides(p,yaw))return residual;
      const auto solid=solid_->assess(p,yaw);
      const double violation=solid.collision()?1.-solid.margin/resolution_:0.;
      if(violation>residual) {
        residual=violation;
        if(gradient)*gradient<<-solid.gradient(1),-solid.gradient(0),-solid.gradient(2)/resolution_,-solid.gradient(3)/resolution_;
      }
    }
    // A violated hard domain has an indicator plus penetration, measured in
    // cells. A legal pose has exactly zero residual and no added margin.
    return residual;
  });
  else planner_.SetPhysicalGapCost({});
  if(environment_) planner_.SetEnvironmentalCost(
    [this](const Node &a,const Node &b) {
      if(support_&&((a.continuous&&std::isfinite(start_yaw_))||(b.continuous&&std::isfinite(goal_yaw_)))) {
        const auto poses=endpointConnection(a,b);double integral=0.;
        for(size_t i=1;i<poses.size();++i)integral+=.5*(poses[i].position-poses[i-1].position).norm()*
          (environment_->cost(poses[i-1].position,poses[i-1].yaw,support_->gapMask())+environment_->cost(poses[i].position,poses[i].yaw,support_->gapMask()));
        return 2.*integral/resolution_;
      }
      const Eigen::Vector3d from=nodePosition(a),to=nodePosition(b);
      const double yaw=std::atan2(to.y()-from.y(),to.x()-from.x());double total=0.;
      const int steps=std::max(1,int(std::ceil((to-from).norm()/.025)));
      for(int i=0;i<=steps;++i)total+=(i==0||i==steps?.5:1.)*
        environment_->cost(from+(to-from)*(double(i)/steps),yaw,support_?support_->gapMask():nullptr);
      return 2.*total/steps*(to-from).norm()/resolution_;
    },[this](double x,double y,double height,double yaw,Eigen::Vector4d *gradient) {
      const Eigen::Vector3d p((y-nx_/2)*resolution_+cx_,(x-ny_/2)*resolution_+cy_,height+reference_height_);
      if(!gradient)return environment_->cost(p,yaw,support_?support_->gapMask():nullptr);
      Eigen::Vector4d world;const double cost=environment_->costGradient(p,yaw,world,support_?support_->gapMask():nullptr);
      *gradient<<world.y()*resolution_,world.x()*resolution_,world.z(),world(3);return cost;
    });
  else planner_.SetEnvironmentalCost({},{});
  planner_.SetPathTransform([this](std::vector<PathPoint> &path){prepareEndpointPath(path);});
  planner_.SetTransitionValidator([this](const Node &a,const Node &b){return transitionAllowed(a,b);});
  planner_.SetPoseValidity([this](const Node &n){return poseFree({nodePosition(n),n.pose_yaw});});
  planner_.SetPoseNecessaryValidity([this](const Node &n){return !solid_||!solid_->coreCollision(nodePosition(n));});
  planner_.SetFreeRotation([this](const Node &n){
    const auto p=nodePosition(n);
    const auto near=[&](const auto &poses){return std::any_of(poses.begin(),poses.end(),[&](const auto &q){return std::abs(p.z()-q.position.z())<.26&&std::hypot(p.x()-q.position.x(),p.y()-q.position.y())<=resolution_*.75;});};
    if(near(rejected_)||near(feedback_))return false;
    return support_&&support_->certifiesFreeRotation(p.x(),p.y(),p.z())&&(!solid_||solid_->certifiesFreeRotation(p));
  });
  planner_.SetPoseCallbacks([this](const Node &a,const Node &b){
    if(std::abs(a.SupportHeight()-b.SupportHeight())>=reactive_stair::StepScoreParameters{}.critical_height_m)return false;
    const auto poses=endpointConnection(a,b);
    for(const auto &p:poses)if(rejectedAt(p.position,p.yaw)||(support_&&support_->assess(p.position.x(),p.position.y(),p.position.z(),p.yaw)!=reactive_stair::Verdict::Free))return false;
    if(!solid_)return true;
    std::vector<Eigen::Vector4d> samples;samples.reserve(poses.size());
    for(const auto &p:poses)samples.emplace_back(p.position.x(),p.position.y(),p.position.z(),p.yaw);
    if(solid_->certifiesFreeSamples(samples))return true;
    return std::all_of(poses.begin(),poses.end(),[&](const auto &p){return !solid_->collides(p.position,p.yaw);});
  },[this](const Node &a,const Node &b){
    const auto poses=endpointConnection(a,b);double total=0.;
    for(size_t i=1;i<poses.size();++i){const auto &p=poses[i-1],&q=poses[i];
      const double distance=((q.position-p.position).norm()+(support_?support_->offset():0.)*std::abs(std::remainder(q.yaw-p.yaw,2*M_PI)))/resolution_;
      const double soft=environment_?environment_->cost(p.position,p.yaw,support_?support_->gapMask():nullptr)+environment_->cost(q.position,q.yaw,support_?support_->gapMask():nullptr):0.;
      total+=distance*(1.+soft);
    }
    return total;
  });
}

Eigen::Vector3i PCTRoutePlanner::poseToIndex(const Eigen::Vector3d &pose) const
{
  if (!pose.allFinite()) throw std::runtime_error("Nonfinite PCT pose");
  // Preserve TomogramPlanner.pose2idx's float32 XY input before double map math.
  const double gx=roundEven((static_cast<float>(pose.x())-cx_)/resolution_)+nx_/2;
  const double gy=roundEven((static_cast<float>(pose.y())-cy_)/resolution_)+ny_/2;
  if (gx<0 || gy<0 || gx>=nx_ || gy>=ny_) throw std::runtime_error("PCT pose outside map");
  const int x=static_cast<int>(gx),y=static_cast<int>(gy);
  int layer=-1;double distance=std::numeric_limits<double>::infinity();
  for(int i=0;i<layers_;++i) {
    if ((!support_&&!ground_valid_[(i*nx_+x)*ny_+y])||(support_&&planning_ground_(i*nx_+x,y)<=-50.)) continue;
    // numpy subtracts the scalar from its float32 elevation array before argmin.
    const double candidate=std::abs(static_cast<float>(planning_ground_(i*nx_+x,y))-static_cast<float>(pose.z()-(support_?reference_height_:0.)));
    if (candidate<distance) {distance=candidate;layer=i;}
  }
  if (layer<0&&support_)throw std::runtime_error("pct_no_physical_support_at_endpoint");
  if (layer<0) layer=static_cast<int>(std::clamp(roundEven((pose.z()-h0_)/dh_),0.0,static_cast<double>(layers_-1)));
  return Eigen::Vector3i(layer,y,x);
}

std::vector<Eigen::Vector3d> PCTRoutePlanner::plan(const Eigen::Vector3d &start,const Eigen::Vector3d &goal,bool smooth,double start_yaw,double goal_yaw)
{
  planned_yaws_.clear();
  start_yaw_=support_?start_yaw:std::numeric_limits<double>::quiet_NaN();goal_yaw_=support_?goal_yaw:std::numeric_limits<double>::quiet_NaN();
  if(std::isinf(start_yaw)||std::isinf(goal_yaw))throw std::runtime_error("pct_invalid_endpoint_yaw");
  if((std::isfinite(start_yaw_)&&!poseFree({start,start_yaw_}))||(std::isfinite(goal_yaw_)&&!poseFree({goal,goal_yaw_})))throw std::runtime_error("pct_endpoint_pose_rejected");
  const bool oriented=std::isfinite(start_yaw_)||std::isfinite(goal_yaw_);
  if(solid_&&(solid_->impossibleAt(start)||solid_->impossibleAt(goal)))
    throw std::runtime_error("pct_endpoint_solid_collision_all_headings");
  if(oriented&&!std::isfinite(start_yaw_))start_yaw_=std::atan2(goal.y()-start.y(),goal.x()-start.x());
  planner_.SetPoseHeadings(oriented?start_yaw_:NAN,oriented?goal_yaw_:NAN);
  Eigen::Vector3i first,last;
  if(support_) {
    const Node a=continuousEndpoint(start),b=continuousEndpoint(goal);
    first<<a.layer,a.idx(2),a.idx(1);last<<b.layer,b.idx(2),b.idx(1);
    planner_.SetContinuousEndpoints(a,b);
  } else {first=poseToIndex(start);last=poseToIndex(goal);}
  Eigen::Ref<const Eigen::Vector3i> first_ref(first),last_ref(last);
  if (!planner_.Plan(first_ref,last_ref,smooth) || planner_.get_path_finder().GetResultMatrix().rows()==0) {
    if(smooth&&planner_.get_path_finder().GetResultMatrix().rows()>0)throw PCTOptimizationFailure("pct_gpmp_no_route");
    throw std::runtime_error("pct_no_route");
  }
  if(!smooth) {
    std::vector<Eigen::Vector3d> result;
    if(!support_)result.push_back(start);
    for(const auto &point:planner_.get_prepared_path()) {
      if(oriented)planned_yaws_.push_back(M_PI/2-point.heading);
      result.emplace_back((point.y-nx_/2)*resolution_+cx_,
        (point.x-ny_/2)*resolution_+cy_,point.height+reference_height_);
    }
    if(support_&&result.size()>=2){result.front()=start;result.back()=goal;}
    if(result.size()<2)throw std::runtime_error("pct_no_route");
    validateSolidPath(result,false,oriented?&planned_yaws_:nullptr);
    return result;
  }
  const Eigen::MatrixXd trajectory=quintic_ ? planner_.get_trajectory_optimizer_wnoj().GetResultMatrix() :
    planner_.get_trajectory_optimizer().GetResultMatrix();
  const Eigen::VectorXd heights=quintic_ ? planner_.get_trajectory_optimizer_wnoj().GetResultHeight() :
    planner_.get_trajectory_optimizer().GetResultHeight();
  if (trajectory.rows()<2 || trajectory.rows()!=heights.rows())
    throw std::runtime_error("pct_height_count_mismatch_or_empty_route");
  if (trajectory.cols()<4) throw std::runtime_error("pct_invalid_trajectory");
  if (!trajectory.allFinite() || !heights.allFinite()) throw std::runtime_error("pct_nonfinite_route");
  std::vector<Eigen::Vector3d> result;
  for(int i=0;i<trajectory.rows();++i) {
    const double x=(trajectory(i,trajectory.cols()/2)-nx_/2)*resolution_+cx_;
    const double y=(trajectory(i,0)-ny_/2)*resolution_+cy_;
    // The MissionBridge path used get_heights(), replacing the wrapper's +0.5 m.
    result.emplace_back(x,y,heights(i));
  }
  if(oriented)for(int i=0;i<trajectory.rows();++i) {
    const double vx=trajectory(i,trajectory.cols()/2+1),vy=trajectory(i,1);
    const Eigen::Vector3d delta=result[std::min(size_t(i+1),result.size()-1)]-result[i?i-1:0];
    planned_yaws_.push_back(std::hypot(vx,vy)>1e-10?std::atan2(vy,vx):std::atan2(delta.y(),delta.x()));
  }
  if(oriented&&std::isfinite(goal_yaw_))planned_yaws_.back()=goal_yaw_;
  if(support_){result.front()=start;result.back()=goal;}
  if(environment_||support_) {
    const Eigen::VectorXd layers=quintic_ ? planner_.get_trajectory_optimizer_wnoj().GetResultLayers() :
        planner_.get_trajectory_optimizer().GetResultLayers();
    try {projectSupportHeights(result,layers,start,goal,oriented?&planned_yaws_:nullptr);}
    catch(const std::runtime_error &error){throw PCTOptimizationFailure(error.what());}
  }
  validateSolidPath(result,true,oriented?&planned_yaws_:nullptr);
  return result;
}

void PCTRoutePlanner::validateSolidPath(const std::vector<Eigen::Vector3d> &points,bool smooth,const std::vector<double> *yaws) const {
  if(yaws) {
    if(yaws->size()!=points.size())throw std::runtime_error("pct_pose_heading_count_mismatch");
    const auto reject=[&](const PoseSample &p){
      const auto reason=std::string("pct_oriented_physical_collision x=")+std::to_string(p.position.x())+" y="+std::to_string(p.position.y())+" z="+std::to_string(p.position.z())+" yaw="+std::to_string(p.yaw)+" support="+std::to_string(support_?int(support_->assess(p.position.x(),p.position.y(),p.position.z(),p.yaw)):0)+" solid="+std::to_string(solid_?solid_->assess(p.position,p.yaw).margin:1.);
      if(smooth){throw PCTOptimizationFailure(reason);}
      throw std::runtime_error(reason);};
    if(std::isfinite(start_yaw_))for(const auto &p:samplePoseLine({points.front(),start_yaw_},{points.front(),yaws->front()}))if(!poseFree(p))reject(p);
    for(size_t i=1;i<points.size();++i)for(const auto &p:samplePoseLine({points[i-1],(*yaws)[i-1]},{points[i],(*yaws)[i]}))if(!poseFree(p))reject(p);
    return;
  }
  if(!solid_)return;
  for(size_t i=1;i<points.size();++i) {
    const Eigen::Vector3d delta=points[i]-points[i-1];
    const double yaw=std::atan2(delta.y(),delta.x());
    const int steps=std::max(1,int(std::ceil(delta.norm()/.025)));
    for(int k=0;k<=steps;++k)if(solid_->collides(points[i-1]+delta*(double(k)/steps),yaw)) {
      if(smooth)throw PCTOptimizationFailure("pct_solid_body_collision");
      throw std::runtime_error("pct_solid_body_collision");
    }
  }
}

void PCTRoutePlanner::projectSupportHeights(std::vector<Eigen::Vector3d> &points,
    const Eigen::VectorXd &layers,const Eigen::Vector3d &start,const Eigen::Vector3d &goal,std::vector<double> *yaws) const {
  if(yaws&&yaws->size()!=points.size())throw std::runtime_error("pct_pose_heading_count_mismatch");
  std::vector<double> dense_yaws;
  if(layers.size()!=int(points.size())||!layers.allFinite()||
      (layers.array()<0).any()||(layers.array()>=layers_).any())throw std::runtime_error("pct_height_layer_count_mismatch");
  std::vector<Eigen::Vector3d> dense;std::vector<SupportHeightBand> bands;
  const double clearance=support_?support_->bodyClearance():environment_->bodyClearance();
  const double tolerance=support_?support_->heightTolerance():reactive_stair::Parameters{}.body_height_tolerance_m;
  const auto append=[&](Eigen::Vector3d p,int layer,double yaw=0.) {
    // Same half-open PCT lattice as the v228 native query. Query the source
    // surface at the canonical cell centre, away from float32 cloud edges.
    const double qx=(p.x()-cx_)/resolution_+nx_/2,qy=(p.y()-cy_)/resolution_+ny_/2;
    if(qx < -1.||qx > nx_+1.||qy < -1.||qy > ny_+1.)throw std::runtime_error("pct_support_height_out_of_map");
    const int x=supportGridIndex(qx),y=supportGridIndex(qy);
    if(x<0||x>=nx_||y<0||y>=ny_||layer<0||layer>=layers_)
      throw std::runtime_error("pct_support_height_invalid_layer");
    double proxy=planning_ground_(layer*nx_+x,y),surface=0.;
    if(support_) {
      // Query the actual continuous pose, not the nearby tomogram centre.
      // A missing slice alias cannot overrule the original native floor.
      if(!support_->surfaceHeight(p.x(),p.y(),p.z()-clearance,surface,
          reactive_stair::StepScoreParameters{}.critical_height_m))
        throw std::runtime_error("pct_support_height_no_associated_floor");
      proxy=surface;
      double best=reactive_stair::StepScoreParameters{}.critical_height_m;
      for(int k=0;k<layers_;++k) {
        const double h=planning_ground_(k*nx_+x,y),distance=std::abs(h-surface);
        if(h>-50.&&distance<best){best=distance;layer=k;}
      }
    } else {
      if(!ground_valid_[(layer*nx_+x)*ny_+y])throw std::runtime_error("pct_support_height_invalid_layer");
      if(!environment_->surfaceHeight((x-nx_/2)*resolution_+cx_,(y-ny_/2)*resolution_+cy_,proxy,surface))
        throw std::runtime_error("pct_support_height_missing_surface");
    }
    const double upper=support_?std::numeric_limits<double>::infinity():planning_ceiling_(layer*nx_+x,y);
    bands.push_back(supportHeightBand(proxy,surface,clearance,tolerance,reference_height_,upper));
    dense.push_back(p);if(yaws)dense_yaws.push_back(yaw);
  };
  append(points.front(),int(layers(0)),yaws?yaws->front():0.);
  for(size_t i=1;i<points.size();++i) {
    const Eigen::Vector3d delta=points[i]-points[i-1];
    const int count=std::max(1,int(std::ceil(delta.head<2>().norm()/.025)));
    for(int k=1;k<=count;++k)append(points[i-1]+delta*(double(k)/count),int(layers(k*2<count?i-1:i)),yaws?(*yaws)[i-1]+double(k)/count*std::remainder((*yaws)[i]-(*yaws)[i-1],2*M_PI):0.);
  }
  for(size_t i=0;i<dense.size();++i) {
    double lower=bands[i].lower,upper=bands[i].upper;
    for(size_t j=i?i-1:i;j<=std::min(i+1,dense.size()-1);++j) {
      lower=std::max(lower,bands[j].lower);upper=std::min(upper,bands[j].upper);
    }
    if(lower>upper)throw std::runtime_error("pct_support_height_disconnected_band sample="+std::to_string(i)+" lower="+std::to_string(lower)+" upper="+std::to_string(upper));
    dense[i].z()=std::clamp(bands[i].preferred,lower,upper);
  }
  // Preserve actual requested terminal heights, rather than silently modifying
  // the mission. RoutePolicy independently retains the exact terminal pose.
  for(const auto endpoint:{std::make_pair(size_t(0),start.z()),std::make_pair(dense.size()-1,goal.z())}) {
    const auto &band=bands[endpoint.first];
    if(endpoint.second<band.lower||endpoint.second>band.upper)throw std::runtime_error("pct_support_height_endpoint");
    dense[endpoint.first].z()=endpoint.second;
  }
  points=std::move(dense);if(yaws)*yaws=std::move(dense_yaws);
}
}  // namespace lite3_nav2
