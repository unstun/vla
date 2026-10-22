#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <atomic>
#include <thread>
#include <iostream>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  using Service=lite3_nav2_interfaces::srv::CheckTraversability;
  auto provider=std::make_shared<rclcpp::Node>("v283_readiness_provider");
  std::atomic<int> calls{0},ready_after{3};
  auto service=provider->create_service<Service>("/scan/check_traversability",
      [&](std::shared_ptr<Service::Request> request,std::shared_ptr<Service::Response> reply) {
        reply->ready=++calls>ready_after;
        if(!reply->ready){reply->message="static_evidence_unavailable";return;}
        reply->verdicts.assign(request->poses.size(),0);
      });
  rclcpp::executors::SingleThreadedExecutor executor;executor.add_node(provider);
  std::thread worker([&]{executor.spin();});
  int code=0;
  try {
    lite3_nav2::SharedTraversability query("v283_readiness",false,"/unused/body");
    geometry_msgs::msg::PoseStamped start;start.header.frame_id="world";start.pose.orientation.w=1.;
    const auto before=std::chrono::steady_clock::now();
    const auto reply=query.query(start.header,start,{start.pose},Service::Request::STATIC_ONLY);
    const double ready_s=std::chrono::duration<double>(std::chrono::steady_clock::now()-before).count();
    if(!reply->ready||calls<4||ready_s>=1.5)throw std::runtime_error("Transient readiness did not resume within original deadline");
    ready_after=1000000;calls=0;
    const auto timeout_start=std::chrono::steady_clock::now();bool refused=false;
    try {query.query(start.header,start,{start.pose},Service::Request::STATIC_ONLY);}
    catch(const std::runtime_error &){refused=true;}
    const double timeout_s=std::chrono::duration<double>(std::chrono::steady_clock::now()-timeout_start).count();
    if(!refused||timeout_s<1.45||timeout_s>1.7)throw std::runtime_error("Missing evidence renewed or bypassed original deadline");
    std::cout<<"READINESS {\"resumed\":true,\"ready_s\":"<<ready_s<<",\"bounded_timeout_s\":"<<timeout_s<<"}\n";
  } catch(const std::exception &e){std::cerr<<e.what()<<'\n';code=1;}
  executor.cancel();worker.join();rclcpp::shutdown();return code;
}
