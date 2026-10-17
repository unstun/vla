#include "raw_reference.h"
#define EnvironmentalField PointCloudReference
#define EnvironmentalAssessment PointCloudAssessment
#include RAW_FIELD_SOURCE
#undef EnvironmentalAssessment
#undef EnvironmentalField

void *makePointField(const char *path,const char *fnv,bool single) {
  auto *field=new reactive_stair::PointCloudReference(path,fnv);
  // This private offline instance represents one offset-zero cylinder. The
  // original two-cylinder reference is retained for independent pose checks.
  if(single)field->data_->offset=0.;
  return field;
}
void freePointField(void *field){delete static_cast<reactive_stair::PointCloudReference*>(field);}
void pointAssessment(void *field,double x,double y,double z,double yaw,double *values) {
  const auto a=static_cast<reactive_stair::PointCloudReference*>(field)->assess({x,y,z},yaw);
  values[0]=a.edge_margin;values[1]=a.solid_margin;values[2]=a.terrain;values[3]=a.cost();
}
bool pointSwitchBand(void *field,double x,double y,double z,double yaw,double hxy,double hz,double az) {
  const auto &d=*static_cast<reactive_stair::PointCloudReference*>(field)->data_;
  const double low=az+std::floor((z-az)/hz)*hz,high=low+hz;
  const double reach=std::hypot(d.radius,.5*(d.up+d.down))+d.target+std::sqrt(3.)*d.voxel_half+std::sqrt(2.)*hxy+hz;
  for(double sign:{-1.,1.}) {
    pcl::PointXYZ center(x+sign*d.offset*std::cos(yaw),y+sign*d.offset*std::sin(yaw),z+.5*(d.down-d.up));
    for(const auto &entry:d.groups) {
      const auto &group=*entry.second;if(group.high<-1e90)continue;
      const Eigen::Vector3d q(center.x,center.y,center.z);
      if((group.lower-q).cwiseMax(q-group.upper).cwiseMax(0.).squaredNorm()>reach*reach)continue;
      std::vector<int> ids;std::vector<float> distances;group.tree.radiusSearch(center,reach,ids,distances);
      for(int i:ids) {
        const auto range=d.supporting_floor[group.original[i]];if(range.first<-1e90)continue;
        const double a=range.second-.26+d.clearance,b=range.first+.26+d.clearance;
        if(a<b&&((a>=low&&a<=high)||(b>=low&&b<=high)))return true;
      }
    }
  }
  return false;
}
