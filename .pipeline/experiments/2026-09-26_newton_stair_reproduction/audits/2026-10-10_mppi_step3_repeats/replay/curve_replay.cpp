#include <plan_manage/planner_manager.h>
#include <bspline_opt/timed_cubic_initialization.h>
#ifdef CANDIDATE
#include <plan_manage/trajectory_validation.h>
#endif
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <vector>
namespace fs=std::filesystem;
using namespace scan_planner;
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("replay_numeric");
  SCANPlannerManager manager;manager.node_=node.get();
  // Exact unchanged runtime YAML values plus the original default tolerances.
  manager.pp_.max_vel_=1.;manager.pp_.vel_tolerance_=1.;
  manager.pp_.max_acc_=.5;manager.pp_.acc_tolerance_=1.;
  const fs::path input=std::getenv("REPLAY_INPUT"),output=std::getenv("REPLAY_OUTPUT");
  std::ifstream in(input/"curves.txt");std::ofstream out(output/"curves.csv");
  if(!in || !out)throw std::runtime_error("Replay files unavailable");
  out<<"id,boundary,dynamics\n";
  std::ofstream times(output/"timing.csv");times<<std::setprecision(17)<<"id,validation_us\n";
  int id,n,m;size_t total=0,boundary_rejected=0,dynamic_rejected=0;double validation_us=0.;
  while(in>>id>>n>>m) {
    if(n<6 || m!=n+4)throw std::runtime_error("Invalid captured shape");
    Eigen::MatrixXd controls(3,n);Eigen::VectorXd knots(m);
    for(int i=0;i<n;++i)for(int j=0;j<3;++j)in>>controls(j,i);
    for(int i=0;i<m;++i)in>>knots[i];
    Eigen::Vector3d start,end;for(int i=0;i<3;++i)in>>start[i];for(int i=0;i<3;++i)in>>end[i];
    std::vector<Eigen::Vector3d> d(4);for(auto &v:d)for(int i=0;i<3;++i)in>>v[i];
    if(!in)throw std::runtime_error("Truncated captured curve");
    UniformBspline curve(controls,3,1.);curve.setKnot(knots);
    const auto before=std::chrono::steady_clock::now();
#ifdef CANDIDATE
    const bool boundary=NativeTrajectoryValidator::boundary(curve,start,end,d).valid();
#else
    const bool boundary=reactive_stair::matchesBoundaryPva(curve,start,end,d);
#endif
    // Preserve the actual manager short circuit; invalid boundary inputs do not
    // claim the dynamics-only entry point's preconditions.
    const int dynamics=boundary?int(manager.checkDynamicFeasibility(curve)):-1;
    const double elapsed_us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-before).count();
    validation_us+=elapsed_us;times<<id<<","<<elapsed_us<<"\n";
    if((curve.getControlPoint()-controls).norm()!=0. || (curve.getKnot()-knots).norm()!=0.)
      throw std::runtime_error("Validation modified curve");
    out<<id<<","<<boundary<<","<<dynamics<<"\n";
    ++total;boundary_rejected+=!boundary;dynamic_rejected+=dynamics==0;
  }
  if(!in.eof() || !total)throw std::runtime_error("No complete curve replay");
  std::ifstream epochs(input/"epochs.txt");std::ofstream epoch_out(output/"epochs.csv");
  double elapsed,duration;size_t epoch_count=0;
  while(epochs>>elapsed>>duration) {
#ifdef CANDIDATE
    const bool accepted=NativeTrajectoryValidator::publicationEpoch(elapsed,duration).valid();
#else
    const bool accepted=!(elapsed<0. || elapsed>=duration);
#endif
    epoch_out<<epoch_count++<<","<<accepted<<"\n";
  }
  if(!epochs.eof() || !epoch_count)throw std::runtime_error("No complete epoch replay");
  std::ofstream result(output/"numeric.json");result<<std::setprecision(17)
    <<"{\"curves\":"<<total<<",\"boundary_rejected\":"<<boundary_rejected
    <<",\"dynamic_rejected\":"<<dynamic_rejected<<",\"epochs\":"<<epoch_count
    <<",\"validation_us_total\":"<<validation_us<<",\"validation_us_mean\":"<<validation_us/total<<"}\n";
  std::cout<<"NUMERIC_REPLAY_PASS curves="<<total<<" epochs="<<epoch_count<<std::endl;
  rclcpp::shutdown();
}
