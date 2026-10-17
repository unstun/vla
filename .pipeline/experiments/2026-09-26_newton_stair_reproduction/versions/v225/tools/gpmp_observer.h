#pragma once
#include <gtsam/linear/JacobianFactor.h>
#include <gtsam/linear/GaussianFactorGraph.h>
#include <cstdlib>
#include <iomanip>
#include <map>
#include <string>

inline const char *diagnosticMode() {
  const char *name=std::getenv("GPMP_DIAG_MODE");return name?name:"unset";
}
inline void diagnosticWitness(const gtsam::NonlinearFactorGraph &graph,const gtsam::Values &values) {
  double worst=-1.;gtsam::Vector6 point;std::shared_ptr<DenseElevationMap> map;int layer=0;double height=0.;
  for(const auto &factor:graph) {
    double error;gtsam::Vector6 x;std::shared_ptr<DenseElevationMap> m;int l;double h;
    if(const auto *f=dynamic_cast<const GPObstacleFactor*>(factor.get())) {
      auto copy=*f;x=values.at<gtsam::Vector6>(f->key());error=copy.evaluateError(x)(0);
      m=copy.map_;l=copy.current_layer_;h=copy.height_hint_;
    } else if(const auto *f=dynamic_cast<const GPInterpolateObstacleFactor*>(factor.get())) {
      auto copy=*f;const auto a=values.at<gtsam::Vector6>(f->key1()),b=values.at<gtsam::Vector6>(f->key2());
      error=copy.evaluateError(a,b)(0);x=copy.gp_interpolator_.Interpolate(a,b);
      m=copy.map_;l=copy.current_layer_;h=copy.height_hint_;
    } else continue;
    if(error>worst){worst=error;point=x;map=m;layer=l;height=h;}
  }
  if(!map)return;
  const double x=point(0),y=point(3),lx=std::max(std::floor(x-.5),0.),ly=std::max(std::floor(y-.5),0.);
  std::cout<<std::setprecision(17)<<"GPMP_WITNESS mode="<<diagnosticMode()<<" x="<<x<<" y="<<y<<" layer="<<layer<<" height="<<height
    <<" residual="<<worst<<" legacy_value="<<map->GetValueBilinearSafe(layer,x,y,height)<<" diff="<<x-lx<<','<<y-ly;
  for(int i=0;i<2;++i)for(int j=0;j<2;++j) {
    const int l=map->UpdateLayerSafe(layer,lx+i,ly+j,height);
    const double weight=(i?x-lx:1-x+lx)*(j?y-ly:1-y+ly);
    std::cout<<" corner"<<i<<j<<'='<<map->GetRealCostSafe(layer,lx+i,ly+j,height)<<','<<l<<','<<map->GetHeight(l,lx+i,ly+j)<<','<<weight;
  }
  for(int axis=0;axis<2;++axis) {
    double a=x,b=y;const double boundary=std::round((axis?y:x)-.5)+.5;double lo,hi;
    if(axis){b=boundary-1e-7;lo=map->GetValueBilinearSafe(layer,a,b,height);b=boundary+1e-7;hi=map->GetValueBilinearSafe(layer,a,b,height);}
    else {a=boundary-1e-7;lo=map->GetValueBilinearSafe(layer,a,b,height);a=boundary+1e-7;hi=map->GetValueBilinearSafe(layer,a,b,height);}
    std::cout<<" seam"<<axis<<'='<<boundary<<','<<lo<<','<<hi;
  }
  std::cout<<'\n';
}
class DiagnosticLM:public gtsam::LevenbergMarquardtOptimizer {
  std::vector<std::string> kinds_;
  mutable size_t linearizations_=0;
public:
  DiagnosticLM(const gtsam::NonlinearFactorGraph &graph,const gtsam::Values &values,const gtsam::LevenbergMarquardtParams &params)
      :gtsam::LevenbergMarquardtOptimizer(graph,values,params) {
    for(const auto &factor:graph) {
      const auto *f=factor.get();
      if(dynamic_cast<const GPObstacleFactor*>(f)||dynamic_cast<const GPInterpolateObstacleFactor*>(f))kinds_.push_back("obstacle");
      else if(dynamic_cast<const GPPriorFactor*>(f))kinds_.push_back("gp");
      else if(dynamic_cast<const GPHeadingRateFactor*>(f)||dynamic_cast<const GPInterpolateHeadingRateFactor*>(f))kinds_.push_back("heading");
      else kinds_.push_back("endpoint");
    }
    std::cout<<std::setprecision(17)<<"GPMP_PARAMETERS mode="<<diagnosticMode()<<" relative="<<params.relativeErrorTol
      <<" absolute="<<params.absoluteErrorTol<<" total="<<params.errorTol<<" lambda="<<params.lambdaInitial<<" max="<<params.maxIterations<<'\n';
    diagnosticWitness(graph,values);
  }
  gtsam::GaussianFactorGraph::shared_ptr linearize() const override {
    // Observe the linearization the optimizer already needs. Never re-evaluate
    // the live nonlinear factors, whose layer/height caches are mutable.
    auto linear=gtsam::LevenbergMarquardtOptimizer::linearize();
    struct Stats {double cost=0.;size_t rows=0;std::map<gtsam::Key,gtsam::Vector6> gradient;};
    std::map<std::string,Stats> stats;size_t skipped=0;
    for(size_t i=0;i<linear->size();++i) {
      const auto *factor=dynamic_cast<const gtsam::JacobianFactor*>((*linear)[i].get());
      if(!factor){++skipped;continue;}
      const auto ab=factor->jacobian();const auto &A=ab.first;const auto &b=ab.second;
      if(A.cols()!=6*int(factor->keys().size())){++skipped;continue;}
      for(int row=0;row<b.size();++row) {
        const std::string kind=kinds_[i]=="obstacle"?(row==0?"legacy_obstacle":"environment"):kinds_[i];
        auto &s=stats[kind];s.cost+=.5*b(row)*b(row);++s.rows;
        for(size_t k=0;k<factor->keys().size();++k) {
          auto entry=s.gradient.emplace(factor->keys()[k],gtsam::Vector6::Zero()).first;
          entry->second-=A.block(row,6*k,1,6).transpose()*b(row);
        }
      }
    }
    for(const auto &entry:stats) {
      double position=0.,velocity=0.,acceleration=0.;
      for(const auto &g:entry.second.gradient) {
        position+=g.second(0)*g.second(0)+g.second(3)*g.second(3);
        velocity+=g.second(1)*g.second(1)+g.second(4)*g.second(4);
        acceleration+=g.second(2)*g.second(2)+g.second(5)*g.second(5);
      }
      std::cout<<std::setprecision(17)<<"GPMP_LINEAR mode="<<diagnosticMode()<<" linearization="<<linearizations_
        <<" kind="<<entry.first<<" rows="<<entry.second.rows<<" cost="<<entry.second.cost<<" position_gradient="<<std::sqrt(position)
        <<" velocity_gradient="<<std::sqrt(velocity)<<" acceleration_gradient="<<std::sqrt(acceleration)<<" skipped="<<skipped<<'\n';
    }
    ++linearizations_;return linear;
  }
};
