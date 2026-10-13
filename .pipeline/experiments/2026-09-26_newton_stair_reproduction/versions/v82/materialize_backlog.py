"""Drop only exact, fixed-point duplicate observations in a real queued batch."""
from pathlib import Path
import argparse
import shutil

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--destination',type=Path,default=BASE/'runtime/scan85_backlog_map_v82')
destination=parser.parse_args().destination
assert not destination.exists()
shutil.copytree(BASE/'runtime/scan84_async_map_v81/src',destination/'src')
env=destination/'src/plan_env'
header=env/'include/plan_env/grid_map.h'
text=header.read_text().replace('    uint64_t applied_clouds = 0;',
    '    uint64_t applied_clouds = 0, reduced_clouds = 0, maximum_queued_clouds = 0;')
text=text.replace('    std::string error;', '    std::string error;\n    bool drop_backlogged_lidar = false;')
text=text.replace('  uint64_t map_revision_ = 0;', '  uint64_t map_revision_ = 0;\n  bool last_fusion_fixed_point_ = false;')
header.write_text(text)
cpp=env/'src/grid_map.cpp';text=cpp.read_text()
start=text.index('{',text.index('void GridMap::raycastProcess'))+1
text=text[:start]+'\n  last_fusion_fixed_point_ = true;\n'+text[start:]
selector='    int idx_ctns = toAddress(idx);'
assert text.count(selector)==1
text=text.replace(selector,selector+'''
    // Observe net occupancy changes without altering any fusion arithmetic.
    struct FusionFixedPoint {
      bool &fixed;
      const std::vector<double> &buffer;
      int address;
      double previous;
      ~FusionFixedPoint() { fixed = fixed && buffer[address] == previous; }
    } fixed_point{last_fusion_fixed_point_,mutableMapState().md_.occupancy_buffer_,idx_ctns,
                  mutableMapState().md_.occupancy_buffer_[idx_ctns]};''')
cpp.write_text(text)
inc=env/'include/plan_env/async_mapping_methods.inc';text=inc.read_text()
text=text.replace('  auto context = std::make_shared<AsyncMapping>();', '''  auto context = std::make_shared<AsyncMapping>();
  load_parameter(node_, "grid_map.drop_backlogged_lidar", context->drop_backlogged_lidar, false);''')
text=text.replace('    uint64_t revision = 0, clouds = 0;', '''    uint64_t revision = 0, clouds = 0, reduced = 0, maximum_queue = 0;
    sensor_msgs::msg::PointCloud2::ConstSharedPtr previous_cloud;
    nav_msgs::msg::Odometry::ConstSharedPtr previous_pose;
    std::shared_ptr<const GridMapSupportState> previous_support;
    Eigen::Vector3i previous_origin=Eigen::Vector3i::Zero();
    Eigen::Vector3d previous_body=Eigen::Vector3d::Zero();
    Eigen::Quaterniond previous_body_rotation=Eigen::Quaterniond::Identity();
    bool previous_fixed = false;''')
text=text.replace('        const auto began = std::chrono::steady_clock::now();', '''        std::set<int64_t> redundant;
        // Only fully paired, spatially identical observations of an unchanged
        // fixed-point map can be skipped without losing obstacle evidence or
        // the repeated log-odds updates required by an unsaturated map.
        std::map<int64_t,nav_msgs::msg::Odometry::ConstSharedPtr> paired=sensor_poses;
        for(const auto &input:inputs)if(input.kind==0)paired[input.stamp_ns]=input.pose;
        std::vector<const MappingInput *> queued_clouds;
        bool equivalent=context->drop_backlogged_lidar && previous_fixed && previous_cloud && previous_pose &&
          unpaired_clouds.empty() && previous_support==writer->mapState().support_ &&
          previous_origin==writer->mapState().mp_.map_origin_idx_ && writer->reactiveSurfaceGroundReady();
        for(const auto &input:inputs) {
          if(input.kind>=3)equivalent=false;
          if(input.kind==2) {
            const auto &p=input.pose->pose.pose.position;const auto &q=input.pose->pose.pose.orientation;
            const Eigen::Vector3d position(p.x,p.y,p.z);const Eigen::Quaterniond rotation(q.w,q.x,q.y,q.z);
            if(!position.allFinite() || !rotation.coeffs().allFinite() || rotation.norm()<1e-6 ||
               position!=previous_body || rotation.normalized().coeffs()!=previous_body_rotation.coeffs())equivalent=false;
          }
          if(input.kind==0 && previous_pose &&
             (input.pose->pose.pose!=previous_pose->pose.pose || input.pose->header.frame_id!=previous_pose->header.frame_id))equivalent=false;
          if(input.kind!=1)continue;
          queued_clouds.push_back(&input);
          const auto pose=paired.find(input.stamp_ns);
          const auto &c=*input.cloud;
          if(input.stamp_ns<=0 || pose==paired.end() || !previous_cloud || !previous_pose) {equivalent=false;continue;}
          const auto &position=pose->second->pose.pose.position;
          const auto &rotation=pose->second->pose.pose.orientation;
          const Eigen::Vector3d xyz(position.x,position.y,position.z);
          const Eigen::Quaterniond quaternion(rotation.w,rotation.x,rotation.y,rotation.z);
          if(!xyz.allFinite() || !quaternion.coeffs().allFinite() || quaternion.norm()<1e-6)equivalent=false;
          const auto &p=*previous_cloud;
          if(pose->second->pose.pose!=previous_pose->pose.pose || pose->second->header.frame_id!=previous_pose->header.frame_id ||
             c.header.frame_id!=p.header.frame_id || c.width!=p.width || c.height!=p.height || c.fields!=p.fields ||
             c.point_step!=p.point_step || c.row_step!=p.row_step || c.is_bigendian!=p.is_bigendian ||
             c.is_dense!=p.is_dense || c.data!=p.data)equivalent=false;
        }
        maximum_queue=std::max<uint64_t>(maximum_queue,queued_clouds.size());
        // Do not shortcut a full generation cycle; retain the original traversal
        // sequence when any cached ray flag could share the skipped generation.
        if(queued_clouds.size()<2 || queued_clouds.size()>=255)equivalent=false;
        int64_t preceding=previous_cloud?rclcpp::Time(previous_cloud->header.stamp).nanoseconds():0;
        for(const auto *input:queued_clouds) {
          if(input->stamp_ns<=preceding)equivalent=false;
          preceding=input->stamp_ns;
        }
        if(equivalent)for(std::size_t i=0;i+1<queued_clouds.size();++i)redundant.insert(queued_clouds[i]->stamp_ns);
        const auto began = std::chrono::steady_clock::now();''')
text=text.replace('          writer->cloudCallback(input.cloud);\n          ++clouds;', '''          writer->cloudCallback(input.cloud);
          previous_fixed=writer->mapState().reactive_cloud_ready_ && writer->last_fusion_fixed_point_;
          previous_cloud=input.cloud;previous_pose=pose->second;previous_support=writer->mapState().support_;
          previous_origin=writer->mapState().mp_.map_origin_idx_;
          previous_body=writer->mapState().md_.sliding_map_frame_pos_;
          previous_body_rotation=writer->reactive_body_quaternion_;
          ++clouds;''')
text=text.replace('''            case 1:
              unpaired_clouds.push_back(input);''','''            case 1:
              if(redundant.count(input.stamp_ns)) {
                ++writer->mutableMapState().md_.raycast_num_;
                ++reduced;
                break;
              }
              unpaired_clouds.push_back(input);''')
text=text.replace('        snapshot->applied_clouds = clouds;',
    '        snapshot->applied_clouds = clouds;\n        snapshot->reduced_clouds = reduced;\n        snapshot->maximum_queued_clouds = maximum_queue;')
text=text.replace('V81_MAP_SNAPSHOT revision=%lu clouds=%lu cloud_stamp=%.9f mapping_ms=%.3f copy_ms=%.3f',
    'V82_MAP_SNAPSHOT revision=%lu clouds=%lu cloud_stamp=%.9f mapping_ms=%.3f copy_ms=%.3f reduced=%lu max_queue=%lu')
text=text.replace('snapshot->mapping_ms,snapshot->copy_ms);', 'snapshot->mapping_ms,snapshot->copy_ms,reduced,maximum_queue);')
inc.write_text(text)
print('V82_CONDITIONAL_BACKLOG_MATERIALIZED')
