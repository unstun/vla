if (std::getenv("V59_EPOCH_CONTRACT")) {
  int epoch_checks=0;
  auto epoch_require=[&](bool ok,const char *name){if(!ok)throw std::runtime_error(std::string("V59_EPOCH_FAIL ")+name);++epoch_checks;std::cout<<"V59_EPOCH_CHECK "<<name<<" PASS\n";};
  for(bool warm:{true,false}) {
    restore();
    const double sample=std::min(.08,source.duration_*.1),delay=.08;
    const auto now=node->now();manager.local_data_.start_time_=now-rclcpp::Duration::from_seconds(sample+delay);
    const auto expected_origin=manager.local_data_.start_time_+rclcpp::Duration::from_seconds(sample);
    manager.setWarmStartContext(warm?context:context+"cold_clock_case",goal,sample);
    const auto sp=curve.evaluateDeBoorT(sample),sv=velocity.evaluateDeBoorT(sample),sa=acceleration.evaluateDeBoorT(sample);
    const bool ok=manager.reboundReplan(sp,sv,sa,target,end_v,false,false);
    epoch_require(ok,"delayed_sample_passes_full_native_replan");
    auto &accepted=manager.local_data_;
    epoch_require(std::abs((accepted.start_time_-expected_origin).seconds())<1e-9,"native_publication_retains_sample_epoch");
    epoch_require((accepted.position_traj_.evaluateDeBoorT(0)-sp).norm()<1e-6 &&
      (accepted.velocity_traj_.evaluateDeBoorT(0)-sv).norm()<1e-6 &&
      (accepted.acceleration_traj_.evaluateDeBoorT(0)-sa).norm()<1e-6,"original_boundary_pva_still_exact");
    const Eigen::Vector3d dp=accepted.position_traj_.evaluateDeBoorT(delay)-curve.evaluateDeBoorT(sample+delay);
    const Eigen::Vector3d dv=accepted.velocity_traj_.evaluateDeBoorT(delay)-velocity.evaluateDeBoorT(sample+delay);
    const Eigen::Vector3d da=accepted.acceleration_traj_.evaluateDeBoorT(delay)-acceleration.evaluateDeBoorT(sample+delay);
    epoch_require(dp.allFinite()&&dv.allFinite()&&da.allFinite()&&dp.norm()<map->getResolution(),"common_time_handover_position_within_existing_resolution");
    std::cout<<std::setprecision(12)<<"V59_HANDOVER warm="<<warm<<" delay_s="<<delay<<" position_m="<<dp.norm()<<" velocity_mps="<<dv.norm()<<" acceleration_mps2="<<da.norm()<<std::endl;
  }
  restore();manager.setWarmStartContext(context,goal,0.0);bool attempted=false;
  const auto expired_origin=rclcpp::Time(0,0,node->now().get_clock_type());
  epoch_require(node->now().seconds()>source.duration_*2,"expired_origin_fixture_is_older_than_curve");
  const auto id=manager.local_data_.traj_id_;
  const bool stale=manager.reboundReplanAttempt(p,v,a,target,end_v,false,false,attempted,true,nullptr,&expired_origin);
  epoch_require(!stale&&manager.local_data_.traj_id_==id,"already_elapsed_candidate_not_committed");
  restore();
  std::cout<<"V59_EPOCH_PASSED checks="<<epoch_checks<<std::endl;
}
