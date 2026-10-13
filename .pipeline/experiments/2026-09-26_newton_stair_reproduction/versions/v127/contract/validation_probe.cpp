// Compare this executable against actual parent/native manager and new interface.
#include "records.h"
#include <plan_manage/planner_manager.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <cstring>
#include <iomanip>
#include <limits>
#include <stdexcept>
#ifdef VALIDATOR_CANDIDATE
#include <plan_manage/trajectory_validation.h>
#endif
using namespace scan_planner;
void require(bool ok,const char *message) { if(!ok)throw std::runtime_error(message); }
void record(const std::string &name,bool value) {
  std::ostringstream record;
  record<<"{\"case\":\""<<name<<"\",\"accepted\":"<<(value?"true":"false")<<"}";
  writeTestRecord("V127_CHECK",record.str());
}
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("validator_contract");
  SCANPlannerManager parent;parent.node_=node.get();
  auto dynamics=[&](UniformBspline &curve,double vel,double acc) {
#ifdef VALIDATOR_CANDIDATE
    return NativeTrajectoryValidator::dynamics(curve,vel,acc).valid();
#else
    parent.pp_.max_vel_=vel;parent.pp_.vel_tolerance_=0.;
    parent.pp_.max_acc_=acc;parent.pp_.acc_tolerance_=0.;
    return parent.checkDynamicFeasibility(curve);
#endif
  };
  auto boundary=[&](UniformBspline &curve,Eigen::Vector3d start,Eigen::Vector3d end,std::vector<Eigen::Vector3d> d) {
#ifdef VALIDATOR_CANDIDATE
    return NativeTrajectoryValidator::boundary(curve,start,end,d).valid();
#else
    return reactive_stair::matchesBoundaryPva(curve,start,end,d);
#endif
  };
  for(int k=1;k<=24;++k) {
    Eigen::MatrixXd controls(3,9);
    for(int i=0;i<9;++i)controls.col(i)=Eigen::Vector3d(k*.02*i+.003*i*i,.03*std::sin(.7*i),3.3+.005*i*i);
    UniformBspline curve(controls,3,.08+.015*k);
    const auto points_before=curve.getControlPoint();const auto knots_before=curve.getKnot();
    const auto duration=curve.getTimeSum();auto velocity=curve.getDerivative(),acceleration=velocity.getDerivative();
    double max_v=0.,max_a=0.;const double dt=std::max(.01,std::min(.05,duration/50.));
    for(double t=0;t<duration+1e-6;t+=dt) {
      max_v=std::max(max_v,velocity.evaluateDeBoorT(std::min(t,duration)).norm());
      max_a=std::max(max_a,acceleration.evaluateDeBoorT(std::min(t,duration)).norm());
    }
    for(const auto &test:std::vector<std::pair<std::string,std::pair<double,double>>>{
        {"clear",{max_v+1.,max_a+1.}}, {"velocity",{max_v*.5,max_a+1.}},
        {"acceleration",{max_v+1.,max_a*.5}}, {"equal",{max_v,max_a}},
        {"v_below",{std::nextafter(max_v,0.),max_a+1.}},
        {"a_below",{max_v+1.,std::nextafter(max_a,0.)}}}) {
      const bool result=dynamics(curve,test.second.first,test.second.second);
      const bool expected=test.first=="clear" || test.first=="equal";
      require(result==expected,"dynamic boundary expectation");
      record("dynamics_"+std::to_string(k)+"_"+test.first,result);
#ifdef VALIDATOR_CANDIDATE
      const auto detail=NativeTrajectoryValidator::dynamics(curve,test.second.first,test.second.second);
      if(test.first=="velocity" || test.first=="v_below")require(detail.failure==ValidationFailure::VelocityLimit,"velocity reason");
      if(test.first=="acceleration" || test.first=="a_below")require(detail.failure==ValidationFailure::AccelerationLimit,"acceleration reason");
      if(!result)require(detail.measured>detail.limit && detail.time_s>=0 && detail.time_s<=duration,"dynamic detail");
#endif
    }
    const Eigen::Vector3d start=curve.evaluateDeBoorT(0.),end=curve.evaluateDeBoorT(duration);
    std::vector<Eigen::Vector3d> derivatives{velocity.evaluateDeBoorT(0.),velocity.evaluateDeBoorT(duration),
       acceleration.evaluateDeBoorT(0.),acceleration.evaluateDeBoorT(duration)};
    for(int change=0;change<7;++change) {
      auto p=start,q=end;auto d=derivatives;
      if(change==1)p.x()+=.001;if(change==2)q.z()+=.001;
      if(change==3)d[0].y()+=.001;if(change==4)d[3].z()+=.001;
      if(change==5)p.x()+=.5e-6;if(change==6)p.x()+=2e-6;
      const bool result=boundary(curve,p,q,d);require(result==(change==0||change==5),"PVA boundary expectation");
#ifdef VALIDATOR_CANDIDATE
      require(NativeTrajectoryValidator::boundary(curve,p,q,d).failure==
        (result?ValidationFailure::None:ValidationFailure::BoundaryPva),"boundary reason");
#endif
      record("boundary_"+std::to_string(k)+"_"+std::to_string(change),result);
    }
    require((curve.getControlPoint()-points_before).norm()==0. &&
            (curve.getKnot()-knots_before).norm()==0.,"validation changed source curve");
    auto bad=curve;auto invalid=controls;invalid(0,3)=std::numeric_limits<double>::quiet_NaN();
    bad=UniformBspline(invalid,3,.2);require(!boundary(bad,start,end,derivatives),"nonfinite PVA accepted");
    record("nonfinite_boundary_"+std::to_string(k),false);
  }
  for(double elapsed:{-.01,0.,.999999,1.,1.01}) {
#ifdef VALIDATOR_CANDIDATE
    const auto report=NativeTrajectoryValidator::publicationEpoch(elapsed,1.);
    const bool accepted=report.valid();
    if(!accepted)require(report.failure==ValidationFailure::PublicationEpoch && report.measured==elapsed,"epoch reason");
#else
    const bool accepted=!(elapsed<0. || elapsed>=1.);
#endif
    require(accepted==(elapsed>=0 && elapsed<1.),"epoch boundary expectation");
    record("epoch_"+std::to_string(elapsed),accepted);
  }
  std::cout<<"V127_VALIDATION_PASS\n";rclcpp::shutdown();
}
