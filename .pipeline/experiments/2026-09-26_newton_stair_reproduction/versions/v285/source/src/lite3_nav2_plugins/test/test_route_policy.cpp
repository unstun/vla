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

TEST(RoutePolicy, NativePoseHeadingsAreNotReplacedByPositionTangents) {
  RoutePolicy policy;geometry_msgs::msg::PoseStamped start,goal;
  start.header.frame_id=goal.header.frame_id="world";start.pose.orientation.w=1.;
  start.pose.position.z=goal.pose.position.z=.3;goal.pose.position.x=.2;
  goal.pose.orientation.z=std::sin(M_PI/4);goal.pose.orientation.w=std::cos(M_PI/4);
  const auto solve=[] {return std::vector<Eigen::Vector3d>{{0,0,.3},{.2,0,.3}};};
  const auto headings=[] {return std::vector<double>{M_PI/2,M_PI/2};};
  for(bool infer:{false,true}) {
    policy.begin(infer?"native_infer":"native_explicit",goal,infer);
    const auto result=policy.plan(start,goal,[]{return rclcpp::Time(1);},solve,headings);
    ASSERT_EQ(result.poses.size(),2u);
    for(const auto &p:result.poses)EXPECT_NEAR(p.pose.orientation.z,std::sin(M_PI/4),1e-12);
    EXPECT_DOUBLE_EQ(result.poses.back().pose.position.x,.2);
  }
  policy.begin("bad_heading_count",goal,false);
  EXPECT_THROW(policy.plan(start,goal,[]{return rclcpp::Time(1);},solve,[]{return std::vector<double>{0.};}),std::runtime_error);
}

TEST(RoutePolicy, FrozenInferredHeadingMustBePlannedOnSubsequentRequests) {
  RoutePolicy policy;geometry_msgs::msg::PoseStamped start,goal;
  start.header.frame_id=goal.header.frame_id="world";start.pose.orientation.w=goal.pose.orientation.w=1.;
  start.pose.position.z=goal.pose.position.z=.3;goal.pose.position.x=4.;
  const auto solve=[] {return std::vector<Eigen::Vector3d>{{0,0,.3},{3.9,0,.3},{4.,0,.3}};};
  policy.begin("inferred_pose",goal,true);
  const auto first=policy.plan(start,goal,[]{return rclcpp::Time(1);},solve,[]{return std::vector<double>(3,M_PI/2);});
  EXPECT_NEAR(first.poses.back().pose.orientation.z,std::sin(M_PI/4),1e-12);
  // Retaining a canonical task heading must never silently rotate a different
  // newly planned endpoint after the body-pose feasibility checks have run.
  EXPECT_THROW(policy.plan(start,goal,[]{return rclcpp::Time(2);},solve,[]{return std::vector<double>(3,0.);}),std::runtime_error);
  EXPECT_NO_THROW(policy.plan(start,goal,[]{return rclcpp::Time(3);},solve,[]{return std::vector<double>(3,M_PI/2);}));
}

TEST(RoutePolicy, StaticContinuationTrimsPrefixWithoutMovingStartSearchOrNewEpoch) {
  for(int rotation=0;rotation<4;++rotation) {
    RoutePolicy policy;const double angle=rotation*M_PI/2.;
    const Eigen::Vector3d axis(std::cos(angle),std::sin(angle),0.);
    const Eigen::Vector3d shift(.37*rotation,-.29*rotation,.3);
    auto start=pose(YAML::Load("[0,0,0.3]")),goal=start;
    const auto set=[](auto &p,const Eigen::Vector3d &v){p.pose.position.x=v.x();p.pose.position.y=v.y();p.pose.position.z=v.z();};
    set(start,shift);set(goal,shift+4*axis);policy.begin("mission",goal,false);
    EXPECT_FALSE(policy.retainedStatic(start,goal));
    int calls=0;
    const auto original=policy.plan(start,goal,[]{return rclcpp::Time(100);},[&]{
      ++calls;std::vector<Eigen::Vector3d> points;for(int i=0;i<5;++i)points.push_back(shift+i*axis);return points;});
    set(start,shift+2*axis+Eigen::Vector3d(0,0,.18)); // Moving stair-height excursion.
    start.pose.orientation.z=std::sin(1.6);start.pose.orientation.w=std::cos(1.6);
    for(int i=0;i<100;++i) {
      const auto retained=policy.retainedStatic(start,goal);ASSERT_TRUE(retained);
      EXPECT_EQ(retained->poses.size(),3u);EXPECT_EQ(retained->header.stamp,original.header.stamp);
      EXPECT_EQ(retained->poses.back(),original.poses.back());
    }
    EXPECT_EQ(calls,1);
    auto changed=goal;changed.pose.orientation.z=1.;changed.pose.orientation.w=0.;
    EXPECT_THROW(policy.retainedStatic(start,changed),std::runtime_error);
    policy.end("mission");EXPECT_FALSE(policy.retainedStatic(start,goal));
    policy.begin("new",goal,false);EXPECT_FALSE(policy.retainedStatic(start,goal));
  }
}
