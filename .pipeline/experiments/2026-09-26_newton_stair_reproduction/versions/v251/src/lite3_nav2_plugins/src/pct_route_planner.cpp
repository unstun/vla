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

bool PCTRoutePlanner::transitionAllowed(const Node &from,const Node &to) const {
  const auto world=[&](const Node &node) {
    return Eigen::Vector3d((node.idx[1]-nx_/2)*resolution_+cx_,
      (node.idx[2]-ny_/2)*resolution_+cy_,node.height+reference_height_);
  };
  if(support_) {
    const auto valid=[&](const Node &node) {
      const size_t index=(node.layer*nx_+node.idx[1])*ny_+node.idx[2];
      return ground_valid_[index]&&std::isfinite(node.height)&&node.height>-50.;
    };
    if(!valid(from)||!valid(to)||std::abs(to.height-from.height)>=reactive_stair::StepScoreParameters{}.critical_height_m)return false;
  }
  const auto a=world(from),b=world(to);const auto delta=b-a;
  const double yaw=std::atan2(delta.y(),delta.x());
  const int count=support_?std::max(1,int(std::ceil(delta.norm()/.025))):2;
  for(int i=0;i<=count;++i) {
    const auto p=a+delta*(double(i)/count);
    if(rejectedAt(p,yaw)||(support_&&support_->assess(p.x(),p.y(),p.z(),yaw)!=reactive_stair::Verdict::Free))return false;
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
      // Aliases of one physical surface share its least restrictive observed
      // slice upper bound. A lower cut through that floor is not a ceiling.
      for(int layer=0;layer<layers_;++layer) {
        const int row=layer*nx_+x;const double height=planning_ground_(row,y);
        if(height<=-50.)continue;
        double upper=ceiling_(row,y);
        for(int other=0;other<layers_;++other)
          if(planning_ground_(other*nx_+x,y)==height)upper=std::max(upper,ceiling_(other*nx_+x,y));
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
    if(!gap.blocked)return 0.;
    if(gradient)*gradient<<-gap.gradient[1],-gap.gradient[0],0.,-gap.gradient[2]/resolution_;
    // A violated hard domain has an indicator plus penetration, measured in
    // cells. A legal pose has exactly zero residual and no added margin.
    return 1.-gap.margin/resolution_;
  });
  else planner_.SetPhysicalGapCost({});
  if(environment_) planner_.SetEnvironmentalCost(
    [this](const Node &a,const Node &b) {
      const Eigen::Vector3d from((a.idx[1]-nx_/2)*resolution_+cx_,(a.idx[2]-ny_/2)*resolution_+cy_,a.height+reference_height_);
      const Eigen::Vector3d to((b.idx[1]-nx_/2)*resolution_+cx_,(b.idx[2]-ny_/2)*resolution_+cy_,b.height+reference_height_);
      const double yaw=std::atan2(to.y()-from.y(),to.x()-from.x());double total=0.;
      const int steps=std::max(1,int(std::ceil((to-from).norm()/.025)));
      for(int i=1;i<=steps;++i)total+=environment_->cost(from+(to-from)*(double(i)/steps),yaw,support_?support_->gapMask():nullptr);
      return 2.*total/steps*(to-from).norm()/resolution_;
    },[this](double x,double y,double height,double yaw,Eigen::Vector4d *gradient) {
      const Eigen::Vector3d p((y-nx_/2)*resolution_+cx_,(x-ny_/2)*resolution_+cy_,height+reference_height_);
      if(!gradient)return environment_->cost(p,yaw,support_?support_->gapMask():nullptr);
      Eigen::Vector4d world;const double cost=environment_->costGradient(p,yaw,world,support_?support_->gapMask():nullptr);
      *gradient<<world.y()*resolution_,world.x()*resolution_,world.z(),world(3);return cost;
    });
  else planner_.SetEnvironmentalCost({},{});
  planner_.SetTransitionValidator([this](const Node &a,const Node &b){return transitionAllowed(a,b);});
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
    if (!ground_valid_[(i*nx_+x)*ny_+y]||(support_&&planning_ground_(i*nx_+x,y)<=-50.)) continue;
    // numpy subtracts the scalar from its float32 elevation array before argmin.
    const double candidate=std::abs(static_cast<float>(planning_ground_(i*nx_+x,y))-static_cast<float>(pose.z()-(support_?reference_height_:0.)));
    if (candidate<distance) {distance=candidate;layer=i;}
  }
  if (layer<0&&support_)throw std::runtime_error("pct_no_physical_support_at_endpoint");
  if (layer<0) layer=static_cast<int>(std::clamp(roundEven((pose.z()-h0_)/dh_),0.0,static_cast<double>(layers_-1)));
  return Eigen::Vector3i(layer,y,x);
}

std::vector<Eigen::Vector3d> PCTRoutePlanner::plan(const Eigen::Vector3d &start,const Eigen::Vector3d &goal,bool smooth)
{
  Eigen::Vector3i first=poseToIndex(start),last=poseToIndex(goal);
  Eigen::Ref<const Eigen::Vector3i> first_ref(first),last_ref(last);
  if (!planner_.Plan(first_ref,last_ref,smooth) || planner_.get_path_finder().GetResultMatrix().rows()==0) {
    if(smooth&&planner_.get_path_finder().GetResultMatrix().rows()>0)throw PCTOptimizationFailure("pct_gpmp_no_route");
    throw std::runtime_error("pct_no_route");
  }
  if(!smooth) {
    std::vector<Eigen::Vector3d> result{start};
    for(const auto &point:planner_.get_path_finder().GetPathPoints())
      result.emplace_back((point.y-nx_/2)*resolution_+cx_,
        (point.x-ny_/2)*resolution_+cy_,point.height+reference_height_);
    if(result.size()<2)throw std::runtime_error("pct_no_route");
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
  if(environment_||support_) {
    const Eigen::VectorXd layers=quintic_ ? planner_.get_trajectory_optimizer_wnoj().GetResultLayers() :
        planner_.get_trajectory_optimizer().GetResultLayers();
    try {projectSupportHeights(result,layers,start,goal);}
    catch(const std::runtime_error &error){throw PCTOptimizationFailure(error.what());}
  }
  return result;
}

void PCTRoutePlanner::projectSupportHeights(std::vector<Eigen::Vector3d> &points,
    const Eigen::VectorXd &layers,const Eigen::Vector3d &start,const Eigen::Vector3d &goal) const {
  if(layers.size()!=int(points.size())||!layers.allFinite()||
      (layers.array()<0).any()||(layers.array()>=layers_).any())throw std::runtime_error("pct_height_layer_count_mismatch");
  std::vector<Eigen::Vector3d> dense;std::vector<SupportHeightBand> bands;
  const double clearance=support_?support_->bodyClearance():environment_->bodyClearance();
  const double tolerance=support_?support_->heightTolerance():reactive_stair::Parameters{}.body_height_tolerance_m;
  const auto append=[&](Eigen::Vector3d p,int layer) {
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
    bands.push_back(supportHeightBand(proxy,surface,clearance,tolerance,reference_height_,planning_ceiling_(layer*nx_+x,y)));
    dense.push_back(p);
  };
  append(points.front(),int(layers(0)));
  for(size_t i=1;i<points.size();++i) {
    const Eigen::Vector3d delta=points[i]-points[i-1];
    const int count=std::max(1,int(std::ceil(delta.head<2>().norm()/.025)));
    for(int k=1;k<=count;++k)append(points[i-1]+delta*(double(k)/count),int(layers(k*2<count?i-1:i)));
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
  points=std::move(dense);
}
}  // namespace lite3_nav2
