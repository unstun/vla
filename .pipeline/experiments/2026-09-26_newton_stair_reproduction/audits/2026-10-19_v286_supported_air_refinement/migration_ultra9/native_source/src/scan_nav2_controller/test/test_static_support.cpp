#include <gtest/gtest.h>
#include <plan_manage/scan_replan_fsm.h>
#include <fstream>
#include <cstdlib>

TEST(StaticSupport, NativeDecoderRetainsAllThreeRolesAndNegativeGapMask)
{
  int argc=0;rclcpp::init(argc,nullptr);
  {
    rclcpp::NodeOptions options;options.use_global_arguments(false);
    options.arguments({"--ros-args","--params-file",std::getenv("TERRAIN_NATIVE_PROFILE")});
    auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
    scan_planner::SCANReplanFSM planner;planner.init(node.get());
    auto map=planner.nav2Map();ASSERT_NE(map,nullptr);
    const std::string folder=std::getenv("TERRAIN_TEST_DIRECTORY");
    auto cloud=[&](const std::string &name) {
      auto msg=std::make_shared<sensor_msgs::msg::PointCloud2>();
      std::ifstream file(folder+"/"+name+".f32",std::ios::binary);
      msg->data.assign(std::istreambuf_iterator<char>(file),{});
      msg->header.frame_id="world";msg->header.stamp=rclcpp::Time(10,0);
      msg->height=1;msg->width=msg->data.size()/16;msg->point_step=16;msg->row_step=msg->data.size();
      for(const char *field:{"x","y","z","intensity"}) {
        sensor_msgs::msg::PointField f;f.name=field;f.offset=msg->fields.size()*4;f.datatype=f.FLOAT32;f.count=1;msg->fields.push_back(f);
      }
      return msg;
    };
    auto navigation=map->decodeReactiveGround(cloud("navigation"));
    auto surface=map->decodeReactiveGround(cloud("surface"));
    auto physical=map->decodePhysicalFloor(cloud("physical_floor"));
    EXPECT_EQ(navigation.source_id,"pct_tomogram/fnv64/5659108921681646177");
    EXPECT_EQ(surface.source_id,"pct_tomogram/fnv64/14798634034717650828");
    EXPECT_EQ(physical.source_id,"pct_physical_floor/fnv64/3260540598421060437");
    auto layers=[](const auto &snapshot) {size_t count=0;for(const auto &entry:snapshot.cells) count+=entry.second.size();return count;};
    EXPECT_EQ(layers(navigation),86775u);EXPECT_EQ(layers(surface),126659u);EXPECT_EQ(layers(physical),150500u);
    EXPECT_DOUBLE_EQ(physical.origin_x_m,-7.795314598083496);
    EXPECT_DOUBLE_EQ(physical.origin_y_m,-9.436811256408692);
    EXPECT_DOUBLE_EQ(physical.resolution_m,0.1);
    auto mask=map->mapState().mp_.support_gap_mask_;ASSERT_NE(mask,nullptr);
    std::ifstream gaps(folder+"/support_gap.txt");double x,y,z;gaps>>x>>y>>z;
    EXPECT_TRUE(mask->blocks(x,y,z));EXPECT_FALSE(mask->blocks(x,y,100.0));
    EXPECT_DOUBLE_EQ(map->mapState().mp_.double_cylinder_radius_,0.35);
    EXPECT_DOUBLE_EQ(map->mapState().mp_.double_cylinder_offset_,0.18);
  }
  rclcpp::shutdown();
}
