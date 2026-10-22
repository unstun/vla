#pragma once
#include <filesystem>
#include <fstream>
#include <set>
#include <map>
#include <iomanip>
namespace {
struct SearchAudit {int id=0,queries=0,clear=0,blocked=0;std::set<std::array<double,3>> expanded;std::map<int,int> verdicts;};
SearchAudit search_audit;
std::ofstream edges,searches;
void beginSearch(const Eigen::Vector3d &from,const Eigen::Vector3d &to,double step) {
 int id=search_audit.id+1;search_audit=SearchAudit{};search_audit.id=id;
 std::cout<<std::setprecision(17)<<"SEARCH_BEGIN id="<<id<<" from="<<from.transpose()<<" to="<<to.transpose()<<" step="<<step<<std::endl;
}
ASTAR_RET auditReturn(ASTAR_RET result,int line) {
 searches<<search_audit.id<<','<<int(result)<<','<<line<<','<<search_audit.queries<<','<<search_audit.clear<<','<<search_audit.blocked<<','<<search_audit.expanded.size();
 for(const auto &v:search_audit.verdicts)searches<<','<<v.first<<':'<<v.second;
 searches<<'\n';searches.flush();return result;
}
bool auditSegment(GridMap *map,const Eigen::Vector3d &from,const Eigen::Vector3d &to) {
 int j=-1;const bool valid=map->collisionFreeSegment(from,to,&j);++search_audit.queries;
 search_audit.expanded.insert({from.x(),from.y(),from.z()});
 if(valid){++search_audit.clear;return true;}
 const int count=std::max(1,int(std::ceil((to-from).norm()/(.5*map->getResolution()))));
 const double yaw=map->collisionSegmentYaw(from,to);const Eigen::Vector3d point=from+(to-from)*(double(j)/count);
 const auto typed=map->liveTraversability(point,yaw);++search_audit.blocked;++search_audit.verdicts[int(typed)];
 if(typed==reactive_stair::Verdict::Free||map->getInflateOccupancy(point,yaw)==0)throw std::runtime_error("Trace binary/typed mismatch");
 if(search_audit.blocked<=64) {
  edges<<search_audit.id<<','<<search_audit.queries<<','<<map->queryNow().seconds()<<','<<map->mapRevision()<<','<<map->observationStamp()<<',';
  for(int k=0;k<3;++k)edges<<from(k)<<',';for(int k=0;k<3;++k)edges<<to(k)<<',';
  edges<<yaw<<','<<j<<','<<count<<','<<point.x()<<','<<point.y()<<','<<point.z()<<','<<int(typed)<<'\n';edges.flush();
 }
 return false;
}
}
