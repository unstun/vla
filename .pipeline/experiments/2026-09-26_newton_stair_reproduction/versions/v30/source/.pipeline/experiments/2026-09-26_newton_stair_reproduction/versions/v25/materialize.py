from pathlib import Path
import difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def replace(s,old,new):
 assert s.count(old)==1,old[:100]
 return s.replace(old,new)
def main():
 parent=json.loads((H.parent/'v24/manifest.json').read_text());assert not (H/'prepared.json').exists()
 for name,digest in parent['source_files'].items():assert sha(R/name)==digest,name
 profile=json.loads((B/'inputs/stair_scenario.json').read_text())
 profile.update(spawn_ground_xyz_m=[-5.545314788818359,6.01318883895874,.05804443359375],spawn_yaw_rad=-1.3258179441604312,goal_ground_xyz_m=[1.954685200623011,-2.9868112220934897,4.5330305099487305],max_sim_seconds=600.,max_wall_seconds=1500.,route_profile='historical_full',profile_source='Historical native_full02 start and goal; audited under2026-09-27_full_building_comparison and full_route_preflight',scene_condition='Complete archived Building; historical full-floor route; no added actor')
 data=B/'inputs/historical_full_building.json';assert not data.exists();data.write_text(json.dumps(profile,indent=2)+'\n');shutil.copyfile(data,H/'route_profile.json')
 paths=[B/'scripts/run_local_episode.py',B/'scripts/native_graph.py',B/'scripts/review_building_episode.py',B/'setup/source_identity.json'];before={p:p.read_bytes() for p in paths}
 for p,raw in before.items():q=H/'parent_source'/p.relative_to(B);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
 helper=(H/'building_profile_function.py.txt').read_text().replace('PINNED_PROFILE_SHA',sha(data))
 p=paths[0];s=p.read_text();s=replace(s,'\ndef main():','\n'+helper+'\n\ndef main():')
 s=replace(s,'    parser.add_argument("--integration-version")','    parser.add_argument("--building-route", choices=("short_stair", "historical_full"), default="short_stair")\n    parser.add_argument("--integration-version")')
 s=replace(s,'    full_building = args.scene == "building_full"','    full_building = args.scene == "building_full"\n    historical_full = full_building and args.building_route == "historical_full"\n    if args.building_route != "short_stair" and not full_building:\n        parser.error("Historical Building route requires scene building_full")')
 old='        scenario = json.loads(scenario_path.read_text())\n        scenario.update(max_sim_seconds=90., max_wall_seconds=args.goal_wall_budget,\n                        navigation_input="native PCT map, actual geometric LiDAR and simulator body localization",\n                        scene_condition="Complete archived Building; fixed architecture; no added actor")'
 s=replace(s,old,'        scenario = building_scenario(args.building_route, args.goal_wall_budget)')
 s=replace(s,'        "scene": args.scene,','        "scene": args.scene,\n        "building_route_profile": args.building_route if full_building else None,')
 s=replace(s,'(150 if long_route else 90 if full_building else 35)','(150 if long_route else 600 if historical_full else 90 if full_building else 35)');p.write_text(s)
 p=paths[1];s=p.read_text();anchor='        backend.update(run_id=out.name, run_epoch_ns=epoch)';s=replace(s,anchor,anchor+'\n        if request.get("building_route_profile") == "historical_full":\n            if request.get("scene") != "building_full":\n                raise ValueError("Historical profile requires the full Building geometry")\n            backend["map"]["pct_layer"] = None  # Existing native multi-floor selection.');p.write_text(s)
 p=paths[2];s=p.read_text();old='    original = json.loads((BASE / "inputs/stair_scenario.json").read_text())';new='    request = json.loads((run / "episode_request.json").read_text())\n    historical_full = request.get("building_route_profile") == "historical_full"\n    profile_file = "historical_full_building.json" if historical_full else "stair_scenario.json"\n    original = json.loads((BASE / "inputs" / profile_file).read_text())';s=replace(s,old,new)
 anchor='    checks = {k:bool(v) for k,v in checks.items()}'
 extra='    route_profile_checks = {}\n    if historical_full:\n        outcome = json.loads((run / "result.json").read_text())\n        pct = outcome["last_backend"]["pct"]\n        history = pct.get("plan_history", [])\n        planned = np.asarray(history[-1].get("waypoints_m", []) if history else [])\n        route_profile_checks = {\n            "automatic_native_layers": "configured_pct_layer" in pct and pct["configured_pct_layer"] is None,\n            "historical_route_length": len(planned) > 1 and np.linalg.norm(np.diff(planned[:,:2],axis=0),axis=1).sum() >= 70.,\n            "correct_goal_level": len(planned) > 1 and abs(planned[-1,2]-goal[2]-.30) <= .02,\n        }\n        checks.update(route_profile_checks)\n'
 s=replace(s,anchor,extra+anchor);s=replace(s,'    result = {"checks":checks,','    result = {"building_route_profile": request.get("building_route_profile", "short_stair"),\n              "actual_xy_path_m":float(np.linalg.norm(np.diff(positions[:,:2],axis=0),axis=1).sum()),\n              "checks":checks,')
 s=replace(s,'"scope":"One full Building simulation with fixed architecture; no added actor or physical-robot claim"','"scope":("Historical complete-floor route" if historical_full else "Short stair route in complete Building geometry") + "; no added actor or physical-robot claim"');p.write_text(s)
 p=paths[3];d=json.loads(p.read_text());d['inputs'].append({'path':str(data.relative_to(B)),'sha256':sha(data),'bytes':data.stat().st_size,'source':'Audited historical native_full02 spawn/yaw/goal; native auto-layer preflight and static endpoint surface audit','scope':'Explicit historical full Building route profile; no PD or safety threshold changes'});p.write_text(json.dumps(d,indent=2)+'\n')
 for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(H.parent/'v24'/name,H/name)
 (H/'changes.patch').write_text(''.join(''.join(difflib.unified_diff(raw.decode().splitlines(True),p.read_text().splitlines(True),fromfile='v24/'+str(p.relative_to(B)),tofile='v25/'+str(p.relative_to(B)))) for p,raw in before.items()))
 (H/'prepared.json').write_text(json.dumps({'parent':'v24','status':'unfrozen_candidate','native_build':parent['native_build'],'changed_files':[str(p.relative_to(R)) for p in paths+[data]],'profile_sha256':sha(data)},indent=2)+'\n')
 print('v25 historical route candidate prepared; validation pending')
if __name__=='__main__':main()
