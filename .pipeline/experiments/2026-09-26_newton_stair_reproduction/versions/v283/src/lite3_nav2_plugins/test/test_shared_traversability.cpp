#include <gtest/gtest.h>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <nav2_core/global_planner.hpp>
#include <nav2_core/exceptions.hpp>
#include <pluginlib/class_loader.hpp>
#include <atomic>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <lite3_nav2_plugins/blocked_feedback.hpp>
#include <lite3_nav2_interfaces/srv/route_session.hpp>
#include <cstdlib>
#include <thread>

TEST(ReferenceSampling, IncludesConnectorAndIntermediateRotation) {
  geometry_msgs::msg::Pose start;start.orientation.w=1.;
  nav_msgs::msg::Path path;geometry_msgs::msg::PoseStamped target;
  target.pose.position.x=.2;target.pose.orientation.z=1.;target.pose.orientation.w=0.;path.poses.push_back(target);
  const auto samples=lite3_nav2::sampleReference(path,start);
  ASSERT_GT(samples.size(),60u);
  EXPECT_DOUBLE_EQ(samples.front().position.x,0.);
  EXPECT_DOUBLE_EQ(samples.back().position.x,.2);
  bool intermediate=false;
  for(const auto &pose:samples) if(std::abs(lite3_nav2::planarYaw(pose)-M_PI/2.)<.06)intermediate=true;
  EXPECT_TRUE(intermediate);
}

TEST(RouteCache, RejectedTerminalRetentionMustInvokeSolverAgain) {
  lite3_nav2::RoutePolicy policy;geometry_msgs::msg::PoseStamped start,goal;
  start.header.frame_id=goal.header.frame_id="world";start.pose.orientation.w=goal.pose.orientation.w=1.;
  goal.pose.position.x=2.;policy.begin("same-mission",goal,false);unsigned solves=0;
  auto solve=[&]{++solves;return std::vector<Eigen::Vector3d>{{0.,0.,.5},{1.,0.,.5},{2.,0.,.5}};};
  auto now=[] {return rclcpp::Time(10,0);};
  auto first=policy.plan(start,goal,now,solve);start.pose=first.poses.back().pose;
  auto cached=policy.plan(start,goal,now,solve);ASSERT_EQ(solves,1u);
  policy.rejectCached(cached);policy.plan(start,goal,now,solve);
  EXPECT_EQ(solves,2u);EXPECT_EQ(policy.context()->canonical,first.poses.back().pose);
}

class SharedPCTTest:public ::testing::Test {
protected:
  using Service=lite3_nav2_interfaces::srv::CheckTraversability;
  static void SetUpTestCase(){int argc=0;rclcpp::init(argc,nullptr);}
  static void TearDownTestCase(){rclcpp::shutdown();}
  void SetUp() override {
    ASSERT_NE(std::getenv("PCT_TEST_MAP"),nullptr);
    provider=std::make_shared<rclcpp::Node>("shared_query_test_provider");
    service=provider->create_service<Service>("/scan/check_traversability",
      [this](const std::shared_ptr<Service::Request> request,std::shared_ptr<Service::Response> reply) {
        ++queries;reply->ready=true;reply->map_revision=7;
        reply->source_identity="native-fixture-source";reply->observation.frame_id="world";
        reply->observation.stamp=provider->now();
        for(const auto &pose:request->poses) {
          const bool hit=block_all || (std::abs(pose.position.x-2.)<.22 && std::abs(pose.position.y+3.)<.22);
          if(request->mode==Service::Request::STATIC_AND_LIVE) {
            ++live_queries;
            const bool live_hit=live_block && std::hypot(pose.position.x-witness.position.x,pose.position.y-witness.position.y)<.15;
            reply->verdicts.push_back(live_unknown ? 6u : (live_hit ? 7u : 0u));
          } else reply->verdicts.push_back(!live_only&&hit ? 7u : 0u);
        }
      });
    executor=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();executor->add_node(provider);
    thread=std::thread([this]{executor->spin();});
    parent=std::make_shared<rclcpp_lifecycle::LifecycleNode>("pct_shared_test");
    parent->declare_parameter("PCT.map_bundle",std::string(std::getenv("PCT_TEST_MAP")));
    parent->declare_parameter("PCT.shared_traversability",true);
    loader=std::make_unique<pluginlib::ClassLoader<nav2_core::GlobalPlanner>>("nav2_core","nav2_core::GlobalPlanner");
    planner=loader->createSharedInstance("lite3_nav2/PCTPlanner");planner->configure(parent,"PCT",nullptr,nullptr);planner->activate();
    start.header.frame_id=goal.header.frame_id="world";start.pose.orientation.w=goal.pose.orientation.w=1.;
    start.pose.position.x=.5;start.pose.position.y=-4.;start.pose.position.z=.5;
    goal.pose.position.x=3.5;goal.pose.position.y=-2.;goal.pose.position.z=.5;
  }
  void TearDown() override {
    executor->cancel();if(thread.joinable())thread.join();
    if(planner){planner->deactivate();planner->cleanup();}planner.reset();loader.reset();parent.reset();
    executor->cancel();if(thread.joinable())thread.join();service.reset();provider.reset();
  }
  void save(const std::string &name,const nav_msgs::msg::Path &path) {
    if(const char *directory=std::getenv("FEEDBACK_OUTPUT")) {
      std::filesystem::create_directories(directory);std::ofstream out(std::filesystem::path(directory)/(name+".csv"));
      out<<std::setprecision(17)<<"x,y,z,yaw\n";
      for(const auto &p:path.poses)out<<p.pose.position.x<<','<<p.pose.position.y<<','<<p.pose.position.z<<','<<lite3_nav2::planarYaw(p.pose)<<'\n';
    }
  }
  void begin(const std::string &id) {
    if(!parent_spinning){executor->add_node(parent->get_node_base_interface());parent_spinning=true;}
    using Session=lite3_nav2_interfaces::srv::RouteSession;
    auto control=std::make_shared<rclcpp::Node>("feedback_session_client");
    auto client=control->create_client<Session>("/lite3_nav2/route_session");
    ASSERT_TRUE(client->wait_for_service(std::chrono::seconds(2)));
    auto request=std::make_shared<Session::Request>();request->operation=request->BEGIN;request->session_id=id;request->goal=goal;
    auto future=client->async_send_request(request);
    ASSERT_EQ(rclcpp::spin_until_future_complete(control,future,std::chrono::seconds(2)),rclcpp::FutureReturnCode::SUCCESS);
    ASSERT_TRUE(future.get()->accepted);
  }
  bool parent_spinning{false};geometry_msgs::msg::Pose witness;
  std::atomic<bool> live_only{false},live_block{false},live_unknown{false};
  std::atomic<unsigned> live_queries{0};
  std::atomic<bool> block_all{false};std::atomic<unsigned> queries{0};
  rclcpp::Node::SharedPtr provider; rclcpp::Service<Service>::SharedPtr service;
  rclcpp::executors::SingleThreadedExecutor::SharedPtr executor;std::thread thread;
  rclcpp_lifecycle::LifecycleNode::SharedPtr parent;
  std::unique_ptr<pluginlib::ClassLoader<nav2_core::GlobalPlanner>> loader;
  nav2_core::GlobalPlanner::Ptr planner;geometry_msgs::msg::PoseStamped start,goal;
};

TEST_F(SharedPCTTest, RepairsARejectedReferenceInsteadOfPublishingIt) {
  const auto path=planner->createPlan(start,goal);
  EXPECT_EQ(path.poses.back().pose,goal.pose);EXPECT_GE(queries.load(),2u);
  for(const auto &pose:lite3_nav2::sampleReference(path,start.pose))
    EXPECT_FALSE(std::abs(pose.position.x-2.)<.22 && std::abs(pose.position.y+3.)<.22);
}

TEST_F(SharedPCTTest, BlockedStartCannotBecomeAFalseSuccessfulRoute) {
  block_all=true;EXPECT_THROW(planner->createPlan(start,goal),nav2_core::PlannerException);
  EXPECT_LE(queries.load(),6u); // Three candidates, each with at most one explicit graph-heading batch.
}

TEST_F(SharedPCTTest, LiveCoordinatesChangeNextActualSearchAndNewMissionClearsThem) {
  live_only=true;begin("feedback-A");
  const auto first=planner->createPlan(start,goal);
  save("first",first);witness=first.poses[first.poses.size()/2].pose;live_block=true;
  const auto changed=planner->createPlan(start,goal);
  save("blocked",changed);ASSERT_GT(live_queries.load(),0u);EXPECT_EQ(changed.poses.back().pose,first.poses.back().pose);
  for(const auto &p:lite3_nav2::sampleReference(changed,start.pose))
    EXPECT_GE(std::hypot(p.position.x-witness.position.x,p.position.y-witness.position.y),.15);
  live_unknown=true;
  const auto unknown=planner->createPlan(start,goal);save("unknown",unknown);
  for(const auto &p:lite3_nav2::sampleReference(unknown,start.pose))
    EXPECT_GE(std::hypot(p.position.x-witness.position.x,p.position.y-witness.position.y),.15);
  live_unknown=false;live_block=false;
  const auto clear=planner->createPlan(start,goal);save("cleared",clear);
  ASSERT_EQ(clear.poses.size(),first.poses.size());
  for(size_t i=0;i<clear.poses.size();++i)EXPECT_EQ(clear.poses[i].pose,first.poses[i].pose);
  live_block=true;planner->createPlan(start,goal);live_unknown=true;begin("feedback-B");
  const auto reset=planner->createPlan(start,goal);
  save("new_mission",reset);ASSERT_EQ(reset.poses.size(),first.poses.size());
  for(size_t i=0;i<reset.poses.size();++i)EXPECT_EQ(reset.poses[i].pose,first.poses[i].pose);
}

TEST_F(SharedPCTTest, LiveHintDoesNotReclassifyStaticLegalTerminal) {
  live_only=true;begin("terminal-block");
  const auto first=planner->createPlan(start,goal);
  start.pose=first.poses.back().pose;witness=start.pose;live_block=true;
  // Global hint admission does not authorize local execution through a live
  // obstacle. The local native query retains that independent responsibility.
  EXPECT_NO_THROW(planner->createPlan(start,goal));
}

TEST(BlockedFeedback, FreshExactClearSourceMissionExpiryAndUnknownRules) {
  using Feedback=lite3_nav2::BlockedFeedback;Feedback f;auto wall=Feedback::Clock::now();
  f.bind("mission-A",wall);
  geometry_msgs::msg::Pose p;p.position.z=.5;p.orientation.w=1.;
  lite3_nav2::SharedTraversability::Service::Response reply;reply.ready=true;reply.source_identity="source-A";
  reply.map_revision=7;reply.observation.frame_id="world";reply.observation.stamp=rclcpp::Time(10,0);reply.verdicts={7};
  f.observe({p},reply,10000000000LL,wall);ASSERT_EQ(f.constraints().size(),1u);EXPECT_FALSE(f.constraints()[0].all_headings);
  reply.verdicts={6};reply.observation.stamp=rclcpp::Time(10,100000000);reply.map_revision=8;
  f.observe({p},reply,10100000000LL,wall);EXPECT_EQ(f.constraints().size(),1u);
  reply.verdicts={0};reply.observation.stamp=rclcpp::Time(10,0);
  f.observe({p},reply,10100000000LL,wall);EXPECT_EQ(f.constraints().size(),1u); // same observation
  reply.observation.stamp=rclcpp::Time(10,100000000);
  auto near=p;near.position.x=.01;f.observe({near},reply,10100000000LL,wall);EXPECT_EQ(f.constraints().size(),1u);
  f.observe({p},reply,10400000000LL,wall);EXPECT_EQ(f.constraints().size(),1u); // stale
  auto other_floor=p;other_floor.position.z+=3.;f.observe({other_floor},reply,10100000000LL,wall);EXPECT_EQ(f.constraints().size(),1u);
  auto other_heading=p;other_heading.orientation.w=other_heading.orientation.z=std::sqrt(.5);
  f.observe({other_heading},reply,10100000000LL,wall);EXPECT_EQ(f.constraints().size(),1u);
  f.observe({p},reply,10100000000LL,wall);EXPECT_TRUE(f.constraints().empty());
  reply.verdicts={7};f.observe({p},reply,10100000000LL,wall);ASSERT_EQ(f.constraints().size(),1u);
  f.bind("mission-A",wall+std::chrono::seconds(2));EXPECT_TRUE(f.constraints().empty());
  f.observe({p},reply,10100000000LL,wall);f.bind("mission-B",wall);EXPECT_TRUE(f.constraints().empty());
  f.observe({p},reply,10100000000LL,wall);reply.source_identity="source-B";reply.verdicts={6};
  f.observe({p},reply,10100000000LL,wall);EXPECT_TRUE(f.constraints().empty());
}

TEST_F(SharedPCTTest, PersistentConstraintSurvivesRepairResetAndKeepsFloorAndHeading) {
  lite3_nav2::PCTRoutePlanner pct(std::getenv("PCT_TEST_MAP"),.35);
  const Eigen::Vector3d point(start.pose.position.x,start.pose.position.y,start.pose.position.z);
  pct.setFeedbackConstraints({{point,0.,false}});pct.clearRepairConstraints();
  EXPECT_TRUE(pct.rejectedAt(point,0.));
  EXPECT_FALSE(pct.rejectedAt(point+Eigen::Vector3d(0.,0.,3.),0.));EXPECT_FALSE(pct.rejectedAt(point,M_PI/2.));
  pct.setFeedbackConstraints({});EXPECT_FALSE(pct.rejectedAt(point,0.));
}

TEST(BlockedFeedback, LocalSamplingStartsNearBodyWithoutOldStartConnector) {
  nav_msgs::msg::Path path;path.header.frame_id="world";
  for(double x:{-10.,-5.,0.,5.}) {
    geometry_msgs::msg::PoseStamped p;p.pose.position.x=x;p.pose.orientation.w=1.;path.poses.push_back(p);
  }
  geometry_msgs::msg::PoseStamped body;body.pose.position.x=4.;body.pose.orientation.w=1.;
  const auto samples=lite3_nav2::localFeedbackSamples(path,body,{});ASSERT_FALSE(samples.empty());
  EXPECT_NEAR(samples.front().position.x,4.,.025);
  for(const auto &p:samples){EXPECT_GE(p.position.x,3.975);EXPECT_LE(std::abs(p.position.x-4.),3.);}
  EXPECT_LE(samples.size(),384u);
}
