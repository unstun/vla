// Exercise the actual controller callback; no replica of its phase logic.
#define main v59_embedded_controller_main
#include "/workspace/src/plan_manage/src/closed_loop_controller.cpp"
#undef main
#include <rcl/time.h>
#include <iostream>
#include <iomanip>
#include <cstdlib>
int main(int argc,char **argv) {
 rclcpp::init(argc,argv);auto node=std::make_shared<scan_planner::ClosedLoopController>();node->cmd_timer_->cancel();
 auto clock=[&](double sec){auto*h=node->get_clock()->get_clock_handle();if(rcl_enable_ros_time_override(h)!=RCL_RET_OK||rcl_set_ros_time_override(h,std::llround(sec*1e9))!=RCL_RET_OK)throw std::runtime_error("clock override");};
 const bool parent=std::getenv("V59_EXPECT_PARENT_RESET");int checks=0;
 auto require=[&](bool ok,const char*name){if(!ok)throw std::runtime_error(name);++checks;std::cout<<"V59_CONTROLLER_CHECK "<<name<<" PASS\n";};
 Eigen::MatrixXd points(3,12);points.setZero();for(int i=0;i<12;++i)points(0,i)=.08*(i-1)+.004*(i-1)*(i-1);
 scan_planner::UniformBspline old(points,3,.2),next(points.rightCols(11),3,.2);
 auto message=[&](bool stop=false){auto m=std::make_shared<scan_planner_msgs::msg::Bspline>();m->order=3;m->traj_id=2;m->start_time=rclcpp::Time(10200000000LL,RCL_ROS_TIME);m->emergency_stop=stop;
  auto controls=next.getControlPoint();for(int i=0;i<controls.cols();++i){geometry_msgs::msg::Point p;p.x=controls(0,i);p.y=controls(1,i);p.z=controls(2,i);m->pos_pts.push_back(p);}auto k=next.getKnot();for(int i=0;i<k.size();++i)m->knots.push_back(k[i]);return m;};

 clock(20.);auto valid=message();valid->start_time=rclcpp::Time(19900000000LL,RCL_ROS_TIME);node->bsplineCallback(valid);
 require(std::abs(node->exec_time_-.1)<1e-9,"valid_elapsed_origin");
 const auto phase=node->exec_time_;const auto id=node->traj_id_;const auto last=node->last_update_time_;
 for(int bad=0;bad<2;++bad){auto invalid=message();invalid->traj_id=999;if(bad==0)invalid->start_time.sec=-1;else invalid->start_time.nanosec=1000000000u;node->bsplineCallback(invalid);require(node->traj_id_==id&&node->exec_time_==phase&&node->last_update_time_==last,"malformed_stamp_preserves_active_curve");}
 auto future=message();future->start_time=rclcpp::Time(20100000000LL,RCL_ROS_TIME);node->bsplineCallback(future);require(node->exec_time_==0.,"future_clock_skew_keeps_original_zero_phase");
 auto delayed=message();delayed->start_time=rclcpp::Time(1000000000LL,RCL_ROS_TIME);node->bsplineCallback(delayed);require(node->exec_time_==node->traj_duration_,"late_delivery_clamps_to_curve_lifetime");
 std::cout<<"V59_SUPPLEMENTAL_CLOCK_PASSED checks="<<checks<<std::endl;rclcpp::shutdown();
}
