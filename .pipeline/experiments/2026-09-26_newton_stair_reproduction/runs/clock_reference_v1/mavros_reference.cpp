#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#define RCLCPP_ERROR(...) (void)0
#define RCLCPP_WARN(...) (void)0
struct Node { uint64_t value; Node now(){return *this;} uint64_t nanoseconds(){return value;} };
struct Dummy {void clear(){} void set_timestamp(uint64_t){} void set_time_offset(double){}};
class Filter {public:
 Node n; Node* node=&n; Dummy dt_diag, u; Dummy* uas=&u;
 double time_offset=0,time_skew=0,filter_alpha=.05,filter_beta=.05;
 uint32_t sequence=0;
 float filter_alpha_initial=.05f,filter_beta_initial=.05f,filter_alpha_final=.003f,filter_beta_final=.003f;
 int convergence_window=500,max_rtt_sample=10,max_deviation_sample=10;
 int max_cons_high_rtt=10,max_cons_high_deviation=10,high_rtt_count=0,high_deviation_count=0;
void add_timesync_observation(int64_t offset_ns, uint64_t local_time_ns, uint64_t remote_time_ns)
  {
    uint64_t now_ns = node->now().nanoseconds();

    // Calculate the round trip time (RTT) it took the timesync
    // packet to bounce back to us from remote system
    uint64_t rtt_ns = now_ns - local_time_ns;

    // Calculate the difference of this sample from the current estimate
    uint64_t deviation = llabs(int64_t(time_offset) - offset_ns);

    if (rtt_ns < max_rtt_sample * 1000000ULL) {                 // Only use samples with low RTT
      if (sync_converged() && (deviation > max_deviation_sample * 1000000ULL)) {
        // Increment the counter if we have a good estimate and are
        // getting samples far from the estimate
        high_deviation_count++;

        // We reset the filter if we received consecutive samples
        // which violate our present estimate.
        // This is most likely due to a time jump on the offboard system.
        if (high_deviation_count > max_cons_high_deviation) {
          RCLCPP_ERROR(get_logger(), "TM: Time jump detected. Resetting time synchroniser.");

          // Reset the filter
          reset_filter();

          // Reset diagnostics
          dt_diag.clear();
          dt_diag.set_timestamp(remote_time_ns);
        }
      } else {
        // Filter gain scheduling
        if (!sync_converged()) {
          // Interpolate with a sigmoid function
          float progress = static_cast<float>(sequence) / convergence_window;
          float p = 1.0f - expf(0.5f * (1.0f - 1.0f / (1.0f - progress)));
          filter_alpha = p * filter_alpha_final + (1.0f - p) * filter_alpha_initial;
          filter_beta = p * filter_beta_final + (1.0f - p) * filter_beta_initial;
        } else {
          filter_alpha = filter_alpha_final;
          filter_beta = filter_beta_final;
        }

        // Perform filter update
        add_sample(offset_ns);

        // Save time offset for other components to use
        uas->set_time_offset(sync_converged() ? time_offset : 0);

        // Increment sequence counter after filter update
        sequence++;

        // Reset high deviation count after filter update
        high_deviation_count = 0;

        // Reset high RTT count after filter update
        high_rtt_count = 0;
      }
    } else {
      // Increment counter if round trip time is too high for accurate timesync
      high_rtt_count++;

      if (high_rtt_count > max_cons_high_rtt) {
        // Issue a warning to the user if the RTT is constantly high
        RCLCPP_WARN(get_logger(), "TM: RTT too high for timesync: %0.2f ms.", rtt_ns / 1000000.0);

        // Reset counter
        high_rtt_count = 0;
      }
    }

    }
void add_sample(int64_t offset_ns)
  {
    /* Online exponential smoothing filter. The derivative of the estimate is also
     * estimated in order to produce an estimate without steady state lag:
     * https://en.wikipedia.org/wiki/Exponential_smoothing#Double_exponential_smoothing
     */

    double time_offset_prev = time_offset;

    if (sequence == 0) {                                // First offset sample
      time_offset = offset_ns;
    } else {
      // Update the clock offset estimate
      time_offset = filter_alpha * offset_ns + (1.0 - filter_alpha) * (time_offset + time_skew);

      // Update the clock skew estimate
      time_skew = filter_beta * (time_offset - time_offset_prev) + (1.0 - filter_beta) * time_skew;
    }
  }
void reset_filter()
  {
    // Do a full reset of all statistics and parameters
    sequence = 0;
    time_offset = 0.0;
    time_skew = 0.0;
    filter_alpha = filter_alpha_initial;
    filter_beta = filter_beta_initial;
    high_deviation_count = 0;
    high_rtt_count = 0;
  }
inline bool sync_converged()
  {
    return sequence >= uint32_t(convergence_window);
  }
};
int main(){Filter f; long long offset; unsigned long long rtt;
while(std::cin>>offset>>rtt){f.n.value=100000000000ULL+rtt;
f.add_timesync_observation(offset,100000000000ULL,1);
std::cout<<std::setprecision(17)<<f.time_offset<<" "<<f.time_skew<<" "<<f.sequence<<" "
<<f.high_rtt_count<<" "<<f.high_deviation_count<<"\n";}}
