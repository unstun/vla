#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rosgraph_msgs/msg/clock.hpp>
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

using namespace std::chrono_literals;

struct Result {int samples=0,future=0;int64_t max_future_ns=0;int maximum_work_overlap=0;};

Result run(bool separate) {
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("use_sim_time",true)});
  auto worker=std::make_shared<rclcpp::Node>(separate?"v108_clock_separate":"v108_clock_shared",options);
  auto source=std::make_shared<rclcpp::Node>("v108_clock_source");
  auto clock=source->create_publisher<rosgraph_msgs::msg::Clock>("/clock",10);
  auto body=source->create_publisher<nav_msgs::msg::Odometry>("/v108/body",10);
  auto group=separate?worker->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive):nullptr;
  rclcpp::SubscriptionOptions subscription_options;
  subscription_options.callback_group=group;
  int64_t body_stamp=0;
  std::atomic<int> active{0},maximum{0};
  auto enter=[&] { const int n=++active; int old=maximum.load(); while(n>old&&!maximum.compare_exchange_weak(old,n)){}; };
  auto subscription=worker->create_subscription<nav_msgs::msg::Odometry>("/v108/body",10,
    [&](nav_msgs::msg::Odometry::ConstSharedPtr msg) {
      enter();body_stamp=rclcpp::Time(msg->header.stamp).nanoseconds();--active;
    },subscription_options);
  std::vector<int64_t> lag;
  auto timer=worker->create_wall_timer(15ms,[&] {
    enter();
    if(worker->now().nanoseconds()!=0) {
      // Deliberately controlled compute stall. Source stamps are never changed.
      std::this_thread::sleep_for(120ms);
      nav_msgs::msg::Odometry message;rclcpp::MessageInfo info;
      while(subscription->take(message,info))body_stamp=rclcpp::Time(message.header.stamp).nanoseconds();
      if(body_stamp>0)lag.push_back(body_stamp-worker->now().nanoseconds());
    }
    --active;
  },group);
  rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(),separate?2:1);
  executor.add_node(worker);
  std::thread spin([&]{executor.spin();});
  // Match the bridge's clock-before-body order, with an explicit 10 ms delivery
  // separation so this scheduling test is not confounded by DDS arrival jitter.
  for(int i=0;i<150;++i) {
    const auto start=std::chrono::steady_clock::now();
    const int64_t ns=10000000000LL+i*20000000LL;
    rosgraph_msgs::msg::Clock tick;tick.clock=rclcpp::Time(ns,RCL_ROS_TIME);clock->publish(tick);
    std::this_thread::sleep_until(start+10ms);
    nav_msgs::msg::Odometry pose;pose.header.stamp=tick.clock;body->publish(pose);
    std::this_thread::sleep_until(start+20ms);
  }
  timer->cancel();executor.cancel();spin.join();
  Result result;result.samples=lag.size();result.maximum_work_overlap=maximum;
  for(auto value:lag) {result.future+=value>0;result.max_future_ns=std::max(result.max_future_ns,value);}
  return result;
}

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  auto shared=run(false),separate=run(true);
  for(const auto &item:{std::make_pair("shared",shared),std::make_pair("separate",separate)}) {
    const auto &r=item.second;
    std::cout<<"{\"mode\":\""<<item.first<<"\",\"samples\":"<<r.samples
      <<",\"future_body_samples\":"<<r.future<<",\"max_clock_lag_ns\":"<<r.max_future_ns
      <<",\"maximum_work_overlap\":"<<r.maximum_work_overlap<<"}"<<std::endl;
  }
  rclcpp::shutdown();
  return shared.samples>=10 && separate.samples>=10 && shared.future>=10 &&
    shared.max_future_ns>=100000000LL && separate.future==0 &&
    shared.maximum_work_overlap==1 && separate.maximum_work_overlap==1?0:1;
}
