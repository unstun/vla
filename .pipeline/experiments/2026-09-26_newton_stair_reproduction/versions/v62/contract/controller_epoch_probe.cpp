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
 for(double delay:{0.,.04,.08,.6}) {
  clock(10.2+delay);auto m=message();node->bsplineCallback(m);
  require(std::abs(node->exec_time_-(parent?0.:delay))<1e-9,"receipt_phase_uses_declared_origin");
  double max_error=0.;auto a=old,b=next;for(int d=0;d<3;++d){max_error=std::max(max_error,(a.evaluateDeBoorT(.2+delay)-b.evaluateDeBoorT(node->exec_time_)).norm());if(d<2){a=a.getDerivative();b=b.getDerivative();}}
  require(parent&&delay>0 ? max_error>1e-6 : max_error<1e-10,"common_handover_time_pva");
  std::cout<<std::setprecision(12)<<"V59_CONTROLLER_PAIR delay_ms="<<delay*1000<<" parent="<<parent<<" max_pva_error="<<max_error<<std::endl;
 }
 if(parent){std::cout<<"V59_CONTROLLER_PARENT_RESET_REPRODUCED checks="<<checks<<std::endl;rclcpp::shutdown();return 0;}
 clock(10.28);node->bsplineCallback(message());node->have_odom_=true;node->odom_yaw_=0.;node->odom_pos_=next.evaluateDeBoorT(.113);
 clock(10.313);node->cmdCallback();require(std::abs(node->exec_time_-.113)<1e-9,"subsequent_control_tick_keeps_elapsed_phase");
 node->odom_yaw_=3.141592653589793;clock(10.346);node->cmdCallback();require(std::abs(node->exec_time_-.113)<1e-9,"heading_freeze_does_not_advance_curve");
 node->odom_yaw_=0.;clock(10.379);node->cmdCallback();require(std::abs(node->exec_time_-.146)<1e-9,"resume_does_not_catch_up_frozen_time");
 clock(10.4);node->bsplineCallback(message(true));require(node->emergency_stop_&&node->exec_time_==0.,"emergency_still_starts_at_zero_and_holds");clock(10.433);node->cmdCallback();require(node->exec_time_==0.,"emergency_callback_keeps_hold");
 auto owned=message();owned->run_id="epoch_test";owned->epoch=1;owned->request_id="r";owned->goal_id="g";owned->route_id="route";owned->command_id="c";owned->generation=3;owned->map_epoch="m";owned->map_revision=1;node->bsplineCallback(owned);
 auto cancel=std::make_shared<scan_planner_msgs::msg::P2BCancel>();cancel->run_id=owned->run_id;cancel->epoch=owned->epoch;cancel->request_id=owned->request_id;cancel->goal_id=owned->goal_id;cancel->route_id=owned->route_id;cancel->command_id=owned->command_id;cancel->generation=owned->generation;cancel->map_epoch=owned->map_epoch;cancel->map_revision=owned->map_revision;
 node->p2bCancelCallback(cancel);require(!node->receive_traj_&&node->exec_time_==0.,"matching_cancel_preserves_stop_protocol");node->bsplineCallback(owned);require(!node->receive_traj_,"cancelled_generation_cannot_restart");
 std::cout<<"V59_CONTROLLER_PASSED checks="<<checks<<std::endl;rclcpp::shutdown();
}
