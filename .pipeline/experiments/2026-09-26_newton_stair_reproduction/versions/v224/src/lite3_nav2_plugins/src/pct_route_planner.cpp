#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>

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

bool PCTRoutePlanner::transitionAllowed(const Node &from,const Node &to) const {
  const auto world=[&](const Node &node) {
    return Eigen::Vector3d((node.idx[1]-nx_/2)*resolution_+cx_,
      (node.idx[2]-ny_/2)*resolution_+cy_,node.height+reference_height_);
  };
  const auto a=world(from),b=world(to);const auto delta=b-a;
  const double yaw=std::atan2(delta.y(),delta.x());
  for(const auto &pose:rejected_) {
    if(!pose.all_headings && std::abs(std::remainder(yaw-pose.yaw,M_PI))>.35) continue;
    for(double u:{0.,.5,1.}) {
      const Eigen::Vector3d point=a+u*delta;
      if(std::abs(point.z()-pose.position.z())<.26 &&
          (point-pose.position).head<2>().norm()<=resolution_*.75) return false;
    }
  }
  return true;
}

void PCTRoutePlanner::rebuildMap() {
  auto costs=costs_;
  for(const auto &pose:rejected_) {
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
  planner_.InitMap(20.,15.,resolution_,layers_,.2,costs,ground_,ceiling_,gateway_,gx,gy);
  planner_.SetReferenceHeight(reference_height_);
  if(environment_) planner_.SetEnvironmentalCost(
    [this](const Node &a,const Node &b) {
      const Eigen::Vector3d from((a.idx[1]-nx_/2)*resolution_+cx_,(a.idx[2]-ny_/2)*resolution_+cy_,a.height+reference_height_);
      const Eigen::Vector3d to((b.idx[1]-nx_/2)*resolution_+cx_,(b.idx[2]-ny_/2)*resolution_+cy_,b.height+reference_height_);
      const double yaw=std::atan2(to.y()-from.y(),to.x()-from.x());double total=0.;
      const int steps=std::max(1,int(std::ceil((to-from).norm()/.025)));
      for(int i=1;i<=steps;++i)total+=environment_->cost(from+(to-from)*(double(i)/steps),yaw);
      return 2.*total/steps*(to-from).norm()/resolution_;
    },[this](double x,double y,double height,double yaw) {
      return environment_->cost(Eigen::Vector3d((y-nx_/2)*resolution_+cx_,(x-ny_/2)*resolution_+cy_,height+reference_height_),yaw);
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
    if (!ground_valid_[(i*nx_+x)*ny_+y]) continue;
    // numpy subtracts the scalar from its float32 elevation array before argmin.
    const double candidate=std::abs(static_cast<float>(ground_(i*nx_+x,y))-static_cast<float>(pose.z()));
    if (candidate<distance) {distance=candidate;layer=i;}
  }
  if (layer<0) layer=static_cast<int>(std::clamp(roundEven((pose.z()-h0_)/dh_),0.0,static_cast<double>(layers_-1)));
  return Eigen::Vector3i(layer,y,x);
}

std::vector<Eigen::Vector3d> PCTRoutePlanner::plan(const Eigen::Vector3d &start,const Eigen::Vector3d &goal,bool smooth)
{
  Eigen::Vector3i first=poseToIndex(start),last=poseToIndex(goal);
  Eigen::Ref<const Eigen::Vector3i> first_ref(first),last_ref(last);
  if (!planner_.Plan(first_ref,last_ref,smooth) || planner_.get_path_finder().GetResultMatrix().rows()==0)
    throw std::runtime_error("pct_no_route");
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
  return result;
}
}  // namespace lite3_nav2
