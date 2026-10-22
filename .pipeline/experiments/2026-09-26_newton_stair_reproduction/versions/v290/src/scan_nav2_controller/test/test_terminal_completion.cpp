#include <gtest/gtest.h>
#include <scan_nav2_controller/terminal_completion.hpp>
#include <limits>

using Completion=scan_nav2_controller::TerminalCompletion;
using Sample=Completion::Sample;
using namespace std::chrono_literals;

class CompletionTest : public ::testing::Test
{
protected:
  Completion completion;
  Completion::Time wall{};
  Sample sample;
  void SetUp() override {
    sample.run_epoch_ns=700;sample.stance_mode=Sample::FIXED_STAND;
    sample.navigation_ready=true;sample.policy_owns_joints=false;
    completion.updatePose(true,1000000000,wall);
  }
  void step(int tick) {
    sample.simulation_time_ns=1000000000ULL+tick*20000000ULL;
    sample.state_sequence=tick+1;
    completion.observe(sample,wall+tick*20ms);
  }
  bool ready(int tick) { return completion.ready(1000000000LL+tick*20000000LL,wall+tick*20ms); }
  void hold(int first,int last) { for(int i=first;i<=last;++i) step(i); }
};

TEST_F(CompletionTest, RequiresTwoSecondsOfMeasuredPdHold)
{
  hold(0,99);EXPECT_FALSE(ready(99));
  step(100);EXPECT_TRUE(ready(100));
}
TEST_F(CompletionTest, ZeroCommandWithRlOwnershipNeverCompletes)
{
  sample.stance_mode=Sample::RL;sample.policy_owns_joints=true;
  hold(0,120);EXPECT_FALSE(ready(120));
  sample.stance_mode=Sample::FIXED_STAND;sample.policy_owns_joints=false;
  hold(121,220);EXPECT_FALSE(ready(220));step(221);EXPECT_TRUE(ready(221));
}
TEST_F(CompletionTest, MotionOrOwnershipInterruptionRestartsWindow)
{
  hold(0,99);sample.measured_velocity.linear.x=.04;step(100);
  sample.measured_velocity.linear.x=0;hold(101,200);EXPECT_FALSE(ready(200));
  sample.policy_owns_joints=true;step(201);sample.policy_owns_joints=false;
  hold(202,302);EXPECT_TRUE(ready(302));
}
TEST_F(CompletionTest, AppliedCommandStalenessAndReadinessAreRequired)
{
  for(int reason=0;reason<3;++reason) {
    completion.resetGoal();completion.updatePose(true,1000000000,wall);
    sample.run_epoch_ns=700;
    sample.applied_command.linear.x=reason==0 ? .01 : 0;
    sample.command_stale=reason==1;sample.navigation_ready=reason!=2;
    hold(reason*150,reason*150+120);EXPECT_FALSE(ready(reason*150+120));
  }
}
TEST_F(CompletionTest, DuplicateForeignAndNonfiniteSamplesCannotAdvanceHold)
{
  hold(0,99);
  auto good=sample;
  sample.run_epoch_ns=701;step(100);EXPECT_FALSE(ready(100));
  sample=good;sample.measured_velocity.angular.z=std::numeric_limits<double>::quiet_NaN();
  step(101);EXPECT_FALSE(ready(101));
  sample=good;completion.observe(sample,wall+2020ms);EXPECT_FALSE(ready(101));
  sample=good;step(102);EXPECT_FALSE(ready(102));hold(103,202);EXPECT_TRUE(ready(202));
}
TEST_F(CompletionTest, FreshPacketsWithFrozenSourceTimeDoNotProveDuration)
{
  step(0);
  for(int i=1;i<150;++i) {sample.state_sequence=i+1;completion.observe(sample,wall+i*20ms);}
  EXPECT_FALSE(ready(149));
}
TEST_F(CompletionTest, GapAndStalledClockInvalidateFreshness)
{
  hold(0,100);EXPECT_TRUE(ready(100));
  EXPECT_FALSE(completion.ready(sample.simulation_time_ns,wall+2260ms));
  step(120);EXPECT_FALSE(ready(120));hold(121,220);EXPECT_TRUE(ready(220));
  EXPECT_FALSE(completion.ready(sample.simulation_time_ns+260000000,wall+4400ms));
}
TEST_F(CompletionTest, CancelNewGoalAndLeavingToleranceResetWindow)
{
  hold(0,100);completion.resetGoal();EXPECT_FALSE(ready(100));
  completion.updatePose(true,3000000000,wall+2s);hold(101,150);EXPECT_FALSE(ready(150));
  completion.updatePose(false,4000000000,wall+3s);EXPECT_FALSE(completion.waiting());
  completion.updatePose(true,4020000000,wall+3020ms);hold(151,250);EXPECT_FALSE(ready(250));
  step(251);EXPECT_TRUE(ready(251));
}
TEST_F(CompletionTest, TerminalTimeoutHasItsOwnDeadline)
{
  EXPECT_FALSE(completion.timedOut(wall+9999ms));
  EXPECT_TRUE(completion.timedOut(wall+10s));
  completion.resetGoal();EXPECT_FALSE(completion.timedOut(wall+11s));
}
