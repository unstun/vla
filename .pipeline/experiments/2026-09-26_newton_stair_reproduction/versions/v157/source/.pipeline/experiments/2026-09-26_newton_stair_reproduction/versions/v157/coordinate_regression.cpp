#include <path_searching/dyn_a_star.h>
#include <cmath>
#include <stdexcept>
#include <iostream>
int main(){
  AStar search;search.initGridMap(nullptr,Eigen::Vector3i(100,100,100));
  search.step_size_=.05;search.inv_step_size_=20.;
  size_t cases=0;
  for(double yaw:{0.,.17,-2.72894166773,3.141592653589793})
    for(const Eigen::Vector3d start:{Eigen::Vector3d(7.0430316925,6.4653339386,3.36139893532),Eigen::Vector3d(-5.5,-6.25,.25)}){
      search.search_yaw_=yaw;
      const Eigen::Vector3d end=start+Eigen::Vector3d(-1.2,.7,.15);
      const auto a=search.toSearchFrame(start),b=search.toSearchFrame(end);
      for(int k=0;k<3;++k)search.center_[k]=reactive_stair::startAlignedSearchCenter(a[k],b[k],.05);
      Eigen::Vector3i index;
      if(!search.Coord2Index(start,index)||(search.Index2Coord(index)-start).norm()>1e-12)
        throw std::runtime_error("Exact physical start moved");
      for(int i=-5;i<=5;++i){
        const Eigen::Vector3i node=index+Eigen::Vector3i(i,-i,i/2);
        const auto world=search.Index2Coord(node);Eigen::Vector3i returned;
        if(!search.Coord2Index(world,returned)||returned!=node)throw std::runtime_error("Rotated grid roundtrip failed");
        if(yaw==0.){
          const Eigen::Vector3d legacy=((node-search.CENTER_IDX_).cast<double>()*search.step_size_)+search.center_;
          if(!(world.array()==legacy.array()).all())throw std::runtime_error("Original zero-rotation coordinates changed");
        }
        ++cases;
      }
    }
  Eigen::Vector3i invalid;
  if(search.Coord2Index(Eigen::Vector3d(std::nan(""),0,0),invalid))throw std::runtime_error("Invalid point admitted");
  std::cout<<"V157_COORDINATE_PASS cases="<<cases<<" exact_start=1 legacy_zero_frame_exact=1 invalid_rejected=1"<<std::endl;
}
