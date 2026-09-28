#include <plan_manage/scan_replan_fsm.h>
#include <chrono>
#include <thread>
#include <fstream>
#include <cstdlib>
#include <vector>
int main(int argc,char**argv){
 rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
 scan_planner::SCANReplanFSM fsm;fsm.init(node.get());fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
 std::vector<scan_planner_msgs::msg::P2BAdmission> notices;
 auto sub=node->create_subscription<scan_planner_msgs::msg::P2BAdmission>("/p2b/scan_admission",20,[&](scan_planner_msgs::msg::P2BAdmission::SharedPtr m){notices.push_back(*m);});
 auto spin=[&](int ms){auto end=std::chrono::steady_clock::now()+std::chrono::milliseconds(ms);do{rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(2));}while(std::chrono::steady_clock::now()<end);};
 spin(400);fsm.have_p2b_identity_=true;auto &id=fsm.active_p2b_identity_;
 id.run_id="run";id.epoch=1;id.request_id="request";id.goal_id="goal";id.route_id="route";id.command_id="command";id.generation=1;id.map_epoch="map";id.map_revision=1;
 fsm.replan_fail_count_=fsm.max_replan_fail_count_-1;fsm.finishProcess();spin(30);bool before=notices.empty();
 fsm.replan_fail_count_=fsm.max_replan_fail_count_;fsm.finishProcess();spin(100);
 bool one=notices.size()==1;bool payload=one&&notices[0].consumer=="fsm"&&notices[0].status=="rejected"&&notices[0].message=="native_replan_exhausted"&&notices[0].run_id=="run"&&notices[0].generation==1&&!notices[0].hold_confirmed&&!notices[0].measured_stillness_confirmed;
 fsm.finishProcess();spin(30);bool once=notices.size()==1;
 fsm.have_p2b_identity_=false;fsm.replan_fail_count_=fsm.max_replan_fail_count_;fsm.finishProcess();spin(30);bool absent=notices.size()==1;
 std::ofstream out(std::getenv("VLA_NOTICE_OUTPUT"));out<<"{\"before_threshold_quiet\":"<<before<<",\"notice_count\":"<<notices.size()<<",\"identity_reason_and_no_hold_claim\":"<<payload<<",\"exactly_once\":"<<once<<",\"no_identity_quiet\":"<<absent<<"}\n";out.close();rclcpp::shutdown();return before&&one&&payload&&once&&absent?0:3;
}
