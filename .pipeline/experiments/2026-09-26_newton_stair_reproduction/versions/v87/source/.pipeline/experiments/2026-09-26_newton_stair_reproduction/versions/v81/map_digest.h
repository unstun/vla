#pragma once
std::string map_digest(const GridMap &map) {
  SHA256_CTX context;
  SHA256_Init(&context);
  const auto vector_bytes = [&](const auto &v) {
    if (!v.empty()) SHA256_Update(&context, v.data(), v.size() * sizeof(v[0]));
  };
  vector_bytes(map.mapState().md_.occupancy_buffer_);
  vector_bytes(map.mapState().md_.occupancy_buffer_inflate_);
  vector_bytes(map.mapState().md_.occupancy_buffer_inflate_cnt_);
  vector_bytes(map.mapState().md_.count_hit_);
  vector_bytes(map.mapState().md_.count_hit_and_miss_);
  vector_bytes(map.mapState().md_.flag_rayend_);
  vector_bytes(map.mapState().md_.flag_traverse_);
  SHA256_Update(&context, map.mapState().mp_.map_origin_idx_.data(), 3 * sizeof(int));
  SHA256_Update(&context, &map.mapState().md_.raycast_num_, sizeof(map.mapState().md_.raycast_num_));
  for (const auto *set : {&map.mapState().reactive_terrain_hits_, &map.mapState().reactive_nonterrain_hits_, &map.mapState().reactive_nonterrain_history_}) {
    std::vector<std::tuple<int,int,int>> keys(set->begin(), set->end());
    std::sort(keys.begin(), keys.end());
    for (const auto &key : keys) {
      const int values[] = {std::get<0>(key), std::get<1>(key), std::get<2>(key)};
      SHA256_Update(&context, values, sizeof(values));
    }
    const auto size = set->size();
    SHA256_Update(&context, &size, sizeof(size));
  }
  unsigned char hash[SHA256_DIGEST_LENGTH];
  SHA256_Final(hash, &context);
  std::ostringstream text;
  for (auto c : hash) text << std::hex << std::setw(2) << std::setfill('0') << unsigned(c);
  return text.str();
}

