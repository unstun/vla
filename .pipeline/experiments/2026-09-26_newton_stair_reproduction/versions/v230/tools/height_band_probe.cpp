#include <lite3_nav2_plugins/support_height.hpp>
#include <iostream>
#include <iomanip>
int main() {
  const auto b=lite3_nav2::supportHeightBand(4.53125,4.5330311966,.3,.12,.35,10.);
  const double target=4.831251896035036;
  std::cout<<std::setprecision(17)<<"HEIGHT_ENDPOINT target="<<target<<" lower="<<b.lower<<" upper="<<b.upper<<" admitted="<<(target>=b.lower&&target<=b.upper)<<'\n';
  return target>=b.lower&&target<=b.upper?0:1;
}
