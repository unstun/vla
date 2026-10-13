#include <plan_env/body_time_buffer.h>
#include <iostream>
#include <stdexcept>

using scan_input_time::BodyTimeBuffer;
static void require(bool ok) {if(!ok)throw std::runtime_error("Body source-time contract failed");}
static nav_msgs::msg::Odometry::SharedPtr message(int64_t ns) {
  auto p=std::make_shared<nav_msgs::msg::Odometry>();
  p->header.stamp.sec=ns/1000000000LL;p->header.stamp.nanosec=ns%1000000000LL;
  p->header.frame_id="world";p->child_frame_id="base";p->pose.pose.orientation.w=1.0;
  p->pose.pose.position.x=double(ns%1000);return p;
}
int main() {
  BodyTimeBuffer q;auto a=message(1000000000LL),b=message(1000000001LL);
  require(q.push(a));require(q.takeDue(1000000000LL)==a);
  require(q.push(b));require(!q.takeDue(1000000000LL));
  require(q.takeDue(1000000001LL)==b);require(b->header.stamp.nanosec==1);
  require(q.push(b));require(!q.takeDue(2000000000LL));
  require(!q.push(a));require(!q.healthy());require(!q.takeDue(3000000000LL));
  BodyTimeBuffer burst;auto selected=message(1000000020LL),pending=message(1000000030LL);
  require(burst.push(message(1000000010LL)));require(burst.push(selected));require(burst.push(pending));
  require(burst.takeDue(1000000025LL)==selected);require(burst.takeDue(1000000030LL)==pending);
  BodyTimeBuffer overflow;
  for(int i=0;i<64;++i)require(overflow.push(message(2000000000LL+i)));
  require(!overflow.takeDue(1000000000LL));require(!overflow.push(message(2000000064LL)));
  require(!overflow.healthy());require(!overflow.takeDue(3000000000LL));
  BodyTimeBuffer invalid;auto bad=message(1);bad->header.stamp.nanosec=1000000000u;
  require(!invalid.push(bad));require(!invalid.takeDue(2000000000LL));
  BodyTimeBuffer zero;require(!zero.push(message(0)));
  std::cout<<"V114_BODY_BUFFER_PASS exact_future_duplicate_regression_burst_capacity_invalid_zero"<<std::endl;
}
