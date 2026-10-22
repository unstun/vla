from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
root=Path('/home/ubuntu/sun/vla_v288_20261020/evidence/upstream');root.mkdir(exist_ok=True)
urls={
 'rclcpp_pr1708.json':'https://api.github.com/repos/ros2/rclcpp/pulls/1708',
 'rclcpp_pr2012.json':'https://api.github.com/repos/ros2/rclcpp/pulls/2012',
 'foxy_executor.cpp':'https://raw.githubusercontent.com/ros2/rclcpp/foxy/rclcpp/src/rclcpp/executor.cpp',
 'foxy_multi_threaded_executor.cpp':'https://raw.githubusercontent.com/ros2/rclcpp/foxy/rclcpp/src/rclcpp/executors/multi_threaded_executor.cpp',
 'ego_planner_node.cpp':'https://raw.githubusercontent.com/HKUST-Aerial-Robotics/ego-planner-swarm/master/src/planner/plan_manage/src/ego_planner_node.cpp',
 'ego_optimizer.cpp':'https://raw.githubusercontent.com/HKUST-Aerial-Robotics/ego-planner-swarm/master/src/planner/bspline_opt/src/bspline_optimizer.cpp',
 'nav2_foxy_goal_checker.cpp':'https://raw.githubusercontent.com/ros-navigation/navigation2/foxy-devel/nav2_controller/plugins/simple_goal_checker.cpp'}
def get(item):
 name,url=item
 try:
  request=urllib.request.Request(url,headers={'User-Agent':'VLA-v288-source-review'})
  data=urllib.request.urlopen(request,timeout=20).read();(root/name).write_bytes(data)
  out=dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),passed=True)
  if name.endswith('.json'):
   j=json.loads(data);out.update(title=j['title'],merged=j['merged'],merge_commit_sha=j['merge_commit_sha'],body=j['body'])
  return name,out
 except Exception as e:return name,dict(url=url,passed=False,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:result=dict(pool.map(get,urls.items()))
(root/'sources.json').write_text(json.dumps(result,indent=2)+'\n')
for name,r in result.items():print(name,r.get('title',''),r['passed'])
