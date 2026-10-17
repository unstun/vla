#include <gtest/gtest.h>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <yaml-cpp/yaml.h>
#include <cstdlib>

using lite3_nav2::RoutePolicy;
geometry_msgs::msg::PoseStamped pose(const YAML::Node &xyz,double yaw=0.) {
  geometry_msgs::msg::PoseStamped p;p.header.frame_id="world";
  p.pose.position.x=xyz[0].as<double>();p.pose.position.y=xyz[1].as<double>();p.pose.position.z=xyz[2].as<double>();
  p.pose.orientation.z=std::sin(yaw/2);p.pose.orientation.w=std::cos(yaw/2);return p;
}
TEST(RoutePolicy, MatchesFrozenV196OnFixedTraces) {
  ASSERT_NE(std::getenv("ROUTE_ORACLE"),nullptr);
  for(const auto &scenario:YAML::LoadFile(std::getenv("ROUTE_ORACLE"))) {
    SCOPED_TRACE(scenario["name"].as<std::string>());
    RoutePolicy policy;int serial=0,calls=0;int64_t time=1000000000;
    bool infer=scenario["yaw"].IsNull();double yaw=infer?0.:scenario["yaw"].as<double>();
    auto goal=pose(YAML::Load("[4,4,0.6]"),yaw);
    auto begin=[&]{policy.begin(std::to_string(++serial),goal,infer);};begin();
    int step_index=0;
    for(const auto &s:scenario["steps"]) {
      SCOPED_TRACE(++step_index);time+=100000000;
      if(s["new_session"])begin();
      if(s["body"])policy.measured(pose(s["body"]));
      auto start=pose(s["start"]?s["start"]:YAML::Load("[0,0,0.35]"));
      if(s["frame"])start.header.frame_id=s["frame"].as<std::string>();
      auto requested=s["goal"]?pose(s["goal"],yaw):goal;
      nav_msgs::msg::Path path;bool accepted=true;std::string message;
      try {
        // This is the public plugin's input gate, before route/cache handling.
        if(start.header.frame_id!="world")throw std::runtime_error("start must have finite coordinates in world");
        path=policy.plan(start,requested,[&]{return rclcpp::Time(time);},[&]{
          ++calls;
          if(s["during"] && s["during"].as<std::string>()=="cancel")policy.end(std::to_string(serial));
          if(s["during"] && s["during"].as<std::string>()=="replace")begin();
          if(s["reason"])throw std::runtime_error(s["reason"].as<std::string>());
          std::vector<Eigen::Vector3d> points;
          for(const auto &p:s["points"])points.emplace_back(p[0].as<double>(),p[1].as<double>(),p[2].as<double>());
          return points;});
      } catch(const std::exception &e) {accepted=false;message=e.what();}
      const auto &expected=s["expected"];
      EXPECT_EQ(accepted,expected["accepted"].as<bool>());
      if(!accepted) {EXPECT_EQ(message,expected["message"].as<std::string>());}
      EXPECT_EQ(calls,expected["calls"].as<int>());
      const auto context=policy.context();
      // A canceled session is removed in C++; v196 kept its completed job record.
      if(context) {
        EXPECT_EQ(context->retained_count,expected["retained_count"].as<unsigned>());
        EXPECT_EQ(context->refresh_status,expected["refresh_status"].as<std::string>());
      }
      ASSERT_EQ(path.poses.size(),expected["path"].size());
      for(size_t i=0;i<path.poses.size();++i) {
        const auto &p=path.poses[i].pose;
        const double actual[]={p.position.x,p.position.y,p.position.z,p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w};
        for(int j=0;j<7;++j)EXPECT_NEAR(actual[j],expected["path"][i][j].as<double>(),1e-12);
        EXPECT_EQ(rclcpp::Time(path.poses[i].header.stamp).nanoseconds(),time);
      }
    }
  }
}
TEST(RoutePolicy, RetentionIsDeepCopyAndOldEndCannotClearNewSession) {
  RoutePolicy policy;auto goal=pose(YAML::Load("[4,4,0.6]"));auto start=pose(YAML::Load("[0,0,0.35]"));
  policy.begin("old",goal,true);
  auto path=policy.plan(start,goal,[]{return rclcpp::Time(10);},[]{return std::vector<Eigen::Vector3d>{{0,0,.35},{4,3,.6},{4,4,.6}};});
  auto retained=policy.plan(start,goal,[]{return rclcpp::Time(20);},[]()->std::vector<Eigen::Vector3d>{throw std::runtime_error("pct_no_route");});
  retained.poses.front().pose.position.x=999;
  EXPECT_EQ(policy.context()->cached,path);
  policy.begin("new",goal,true);policy.end("old");
  ASSERT_TRUE(policy.context());EXPECT_EQ(policy.context()->id,"new");EXPECT_TRUE(policy.context()->cached.poses.empty());
}
