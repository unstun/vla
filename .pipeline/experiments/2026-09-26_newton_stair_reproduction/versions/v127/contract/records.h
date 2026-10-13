#pragma once
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

// ROS diagnostics and buffered stdout can interleave in a merged log. Verdicts
// have a dedicated per-executable record file; logs remain diagnostic evidence.
inline void writeTestRecord(const std::string &prefix,const std::string &json) {
  const char *directory=std::getenv("V127_RECORD_DIR");
  if(!directory)throw std::runtime_error("Missing explicit record directory");
  std::ofstream file(std::string(directory)+"/"+prefix+".jsonl",std::ios::app);
  if(!file)throw std::runtime_error("Test record file unavailable");
  file<<json<<"\n";file.close();
  if(!file)throw std::runtime_error("Test record write failed");
  std::cout<<prefix<<" "<<json<<std::endl;
}
