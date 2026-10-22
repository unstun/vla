#include <plan_manage/scan_replan_fsm.h>
#include <atomic>
#include <future>
#include <thread>
#include <iostream>
#include <chrono>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  auto map=std::make_shared<GridMap>();
  scan_planner::SCANReplanFSM fsm;
  auto node=std::make_shared<rclcpp::Node>("work_serialization_probe");
  fsm.node_=node.get();
  fsm.planner_manager_.reset(new scan_planner::SCANPlannerManager);
  fsm.planner_manager_->grid_map_=map;
  std::atomic<int> active{0},maximum{0},completed{0};
  std::atomic<bool> start{false};
  auto run=[&] {
    while(!start.load())std::this_thread::yield();
    for(int i=0;i<500;++i)fsm.callbackBoundary("concurrent_work_probe",[&] {
      const int n=++active;int old=maximum.load();while(n>old&&!maximum.compare_exchange_weak(old,n)){}
      // Re-entry on the very same production lock must not deadlock.
#ifndef PARENT_WORK_CONTROL
      std::lock_guard<std::recursive_mutex> nested(map->lockMutex());
#endif
      std::this_thread::sleep_for(std::chrono::microseconds(20));
      --active;++completed;
    });
  };
  std::thread first(run),second(run);start=true;first.join();second.join();
  bool independent=true;
#ifndef PARENT_WORK_CONTROL
  independent=false;
  {
    std::lock_guard<std::recursive_mutex> hold(map->lockMutex());
    // Snapshot-query GridMaps own their mutex and never share the work lock.
    auto view=std::make_shared<GridMap>();
    auto query=std::async(std::launch::async,[view] {
      std::lock_guard<std::recursive_mutex> lock(view->lockMutex());return true;
    });
    independent=query.wait_for(std::chrono::milliseconds(100))==std::future_status::ready;
  }
#endif
  const bool passed=maximum==1&&completed==1000&&independent;
  std::cout<<"WORK {\"passed\":"<<(passed?"true":"false")<<",\"maximum_concurrency\":"<<maximum
    <<",\"completed\":"<<completed<<",\"recursive_reentry\":true,\"independent_query_lock\":"<<(independent?"true":"false")<<",\"physics_steps\":0}\n";
  rclcpp::shutdown();return passed?0:1;
}
