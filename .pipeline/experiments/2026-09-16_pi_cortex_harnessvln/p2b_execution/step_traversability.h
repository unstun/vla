#ifndef PLAN_ENV_STEP_TRAVERSABILITY_H
#define PLAN_ENV_STEP_TRAVERSABILITY_H

#include <algorithm>
#include <cmath>
#include <vector>

// ROS-free translation of p2b_execution/step_traversability.py.
// ETH StepFilter is cited, not imported.

struct StepHeightSample
{
  int ix;
  int iy;
  double z;
};

struct StepTraversabilityParams
{
  double critical_height_m = 0.26;
  double window_radius_m = 0.30;
  double height_band_m = 0.05;
  double min_tread_depth_m = 0.15;
  double min_step_height_m = 0.04;
  double resolution_m = 0.05;
};

inline bool occupancyHitIsTraversableStep(const std::vector<StepHeightSample> &samples,
                                          const StepTraversabilityParams &params)
{
  if (samples.size() < 2)
    return false;

  double h_min = samples[0].z;
  double h_max = samples[0].z;
  for (const auto &sample : samples)
  {
    h_min = std::min(h_min, sample.z);
    h_max = std::max(h_max, sample.z);
  }

  const double delta = h_max - h_min;
  if (delta < params.min_step_height_m)
    return false;
  if (delta >= params.critical_height_m)
    return false;

  bool any_high = false;
  int min_ix = 0;
  int max_ix = 0;
  int min_iy = 0;
  int max_iy = 0;
  for (const auto &sample : samples)
  {
    if (std::abs(sample.z - h_max) > params.height_band_m)
      continue;
    if (!any_high)
    {
      min_ix = max_ix = sample.ix;
      min_iy = max_iy = sample.iy;
      any_high = true;
    }
    else
    {
      min_ix = std::min(min_ix, sample.ix);
      max_ix = std::max(max_ix, sample.ix);
      min_iy = std::min(min_iy, sample.iy);
      max_iy = std::max(max_iy, sample.iy);
    }
  }
  if (!any_high)
    return false;

  const double span_x = static_cast<double>(max_ix - min_ix + 1) * params.resolution_m;
  const double span_y = static_cast<double>(max_iy - min_iy + 1) * params.resolution_m;
  return std::min(span_x, span_y) >= params.min_tread_depth_m;
}

#endif
