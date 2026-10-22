#include <csignal>
#include <thread>
#include <chrono>
#include <cstdlib>
__attribute__((noinline)) void fault_level_three(int sig) {
  if(sig==SIGSEGV)*static_cast<volatile int*>(nullptr)=1;
  else std::raise(sig);
}
__attribute__((noinline)) void fault_level_two(int sig){fault_level_three(sig);}
__attribute__((noinline)) void fault_level_one(int sig){fault_level_two(sig);}
int main(int argc,char **argv) {
  std::thread worker([]{for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));});
  worker.detach();fault_level_one(std::atoi(argv[1]));return 0;
}
