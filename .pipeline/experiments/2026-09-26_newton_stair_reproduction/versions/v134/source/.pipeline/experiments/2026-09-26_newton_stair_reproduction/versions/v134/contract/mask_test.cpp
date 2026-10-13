#include <plan_env/support_gap_mask.h>
#include <cassert>
#include <iostream>
#include <functional>
int main(int argc,char**argv) {
  assert(argc==3);
  reactive_stair::SupportGapMask mask(argv[1],argv[2],.35);
  assert(mask.blocks(7.778,5.968,4.819-.35)); // captured body before rejoin
  assert(mask.blocks(7.56,5.904,4.533)); // actual unsupported foot location
  assert(!mask.blocks(8.3,6.4,4.533)); // continuous landing away from the gap
  assert(mask.blocks(NAN,6,4.533));
  auto rejects=[](const std::function<void()> &f){bool caught=false;try{f();}catch(const std::runtime_error&){caught=true;}assert(caught);};
  rejects([&]{reactive_stair::SupportGapMask bad(argv[1],"0",.35);});
  rejects([&]{reactive_stair::SupportGapMask bad("/missing/coverage","0",.35);});
  rejects([&]{reactive_stair::SupportGapMask bad(argv[1],argv[2],-.1);});
  // A single synthetic gap must not veto a different floor or points outside its radius.
  const std::string data="0.05 0.05 1\n";std::ofstream out("synthetic.txt");out<<data;out.close();
  uint64_t fnv=UINT64_C(14695981039346656037);for(unsigned char b:data){fnv^=b;fnv*=UINT64_C(1099511628211);}
  reactive_stair::SupportGapMask single("synthetic.txt",std::to_string(fnv),.35);
  assert(single.blocks(.4,.05,1));assert(!single.blocks(.6,.05,1));assert(!single.blocks(.05,.05,2));
  std::cout<<"SUPPORT_GAP_MASK_CONTRACT_PASS 10\n";
}
