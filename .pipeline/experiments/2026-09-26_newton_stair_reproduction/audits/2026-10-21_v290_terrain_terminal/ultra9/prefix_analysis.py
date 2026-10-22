"""Analyze an aborted recorder from its actual last telemetry, without result fabrication."""
import hashlib,json,types,sys

def install(versions):
    sys.path.insert(0,str(versions/'v196'))
    import analyze_remote
    original=analyze_remote.analyze
    path=versions/'v196/analyze_remote.py'
    text=path.read_text()
    old="    result=capture.json('result.json');points=capture.rows('sensor.jsonl')"
    assert text.count(old)==1
    text=text.replace(old,"""    measured=capture.rows('telemetry.jsonl')[-1]
    # Analysis metadata only: no recorder result or terminal status is invented.
    result=dict(realtime_pacing=measured['realtime_pacing'],physics_duration_s=measured['physics_time_s'],physics_steps=measured['physics_steps'])
    points=capture.rows('sensor.jsonl')""")
    old="__import__('shared_state').verify_capture(capture)";assert text.count(old)==1
    text=text.replace(old,'False')
    partial=types.ModuleType('partial_recorded_metrics');partial.__file__=str(path)
    exec(compile(text,str(path),'exec'),partial.__dict__)
    def analyze(root,output,metrics_only=False):
        capture=analyze_remote.Capture(root)
        try:capture.json('result.json')
        except (FileNotFoundError,KeyError):
            partial.analyze(root,output,metrics_only)
            p=output/'metrics.json';data=json.loads(p.read_text())
            data.update(recorder_result_present=False,diagnostic_only=True,
                partial_recording=True,terminal=None,fallen=None,shared_state_verified=False,
                metadata_source='Actual last telemetry; no recorder result exists. Duration/steps are recorded lower bounds.',
                partial_analyzer_original_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                partial_analyzer_executed_sha256=hashlib.sha256(text.encode()).hexdigest())
            p.write_text(json.dumps(data,indent=2)+'\n')
            (output/'executed_prefix_analyzer.py').write_text(text)
        else:original(root,output,metrics_only)
    analyze_remote.analyze=analyze
