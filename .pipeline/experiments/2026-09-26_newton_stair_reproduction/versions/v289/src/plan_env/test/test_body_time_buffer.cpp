#include <gtest/gtest.h>
#include <plan_env/body_time_buffer.h>
#include <condition_variable>
#include <mutex>
#include <thread>

namespace {
using Message=nav_msgs::msg::Odometry;
auto pose(int64_t ns,double x=0.) {
  auto m=std::make_shared<Message>();m->header.stamp.sec=ns/1000000000;
  m->header.stamp.nanosec=ns%1000000000;m->pose.pose.position.x=x;return m;
}
}
TEST(BodyTimeBuffer, SupersededDeliveryPreservesNewerAndAdmitsNext) {
  scan_input_time::BodyTimeBuffer b;
  ASSERT_TRUE(b.push(pose(2000000000,2)));
  EXPECT_FALSE(b.push(pose(1000000000,1)));
  EXPECT_TRUE(b.healthy());EXPECT_TRUE(b.error().empty());
  auto current=b.takeDue(2000000000);ASSERT_TRUE(current);EXPECT_DOUBLE_EQ(current->pose.pose.position.x,2);
  ASSERT_TRUE(b.push(pose(3000000000,3)));
  auto next=b.takeDue(3000000000);ASSERT_TRUE(next);EXPECT_DOUBLE_EQ(next->pose.pose.position.x,3);
}
TEST(BodyTimeBuffer, TakenBeforeGuardCannotPoisonManualDrain) {
  scan_input_time::BodyTimeBuffer b;std::recursive_mutex work;
  std::mutex phase_mutex;std::condition_variable phase;bool taken=false,accepted=true;
  std::unique_lock<std::recursive_mutex> current(work);
  std::thread callback([&]{auto older=pose(1000000000,1);
    {std::lock_guard<std::mutex> lock(phase_mutex);taken=true;}phase.notify_one();
    std::lock_guard<std::recursive_mutex> lock(work);accepted=b.push(older);
  });
  {std::unique_lock<std::mutex> lock(phase_mutex);phase.wait(lock,[&]{return taken;});}
  ASSERT_TRUE(b.push(pose(2000000000,2)));current.unlock();callback.join();
  EXPECT_FALSE(accepted);ASSERT_TRUE(b.healthy());
  ASSERT_TRUE(b.push(pose(3000000000,3)));auto next=b.takeDue(3000000000);
  ASSERT_TRUE(next);EXPECT_DOUBLE_EQ(next->pose.pose.position.x,3);
}
TEST(BodyTimeBuffer, DuplicateCannotRestampOrReplaceEvidence) {
  scan_input_time::BodyTimeBuffer b;ASSERT_TRUE(b.push(pose(1000000000,1)));
  EXPECT_TRUE(b.push(pose(1000000000,9)));auto m=b.takeDue(2000000000);
  ASSERT_TRUE(m);EXPECT_EQ(m->header.stamp.sec,1);EXPECT_DOUBLE_EQ(m->pose.pose.position.x,1);
  EXPECT_FALSE(b.takeDue(3000000000));
}
TEST(BodyTimeBuffer, FutureAndMalformedInputsRetainTheirContract) {
  scan_input_time::BodyTimeBuffer b;ASSERT_TRUE(b.push(pose(2000000000)));
  EXPECT_FALSE(b.takeDue(1000000000));EXPECT_TRUE(b.takeDue(2000000000));
  EXPECT_FALSE(b.push(pose(0)));EXPECT_FALSE(b.healthy());
  EXPECT_FALSE(b.push(pose(3000000000)));
}
