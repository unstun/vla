"""Measured-motion audit, independent of stance labels and legacy >=1s counts."""
import math

def low_speed_intervals(samples, speed_limit=.05, max_gap_s=.1):
    """Right-sample rectangular integration; uncertainty is one sample interval.

    samples are (native_seconds, measured_horizontal_speed). A missing/nonfinite
    sample breaks an interval; gaps and moving periods never count as stopped.
    """
    result=[]; start=end=None; previous=None
    for time,speed in samples:
        if not math.isfinite(time) or (previous is not None and time<=previous):
            raise ValueError('Expected finite, strictly increasing native time')
        low=previous is not None and 0<time-previous<max_gap_s and math.isfinite(speed) and 0<=speed<speed_limit
        if low:
            if start is None:start=previous
            end=time
        elif start is not None:
            result.append(dict(start_s=start,end_s=end,duration_s=end-start));start=end=None
        previous=time
    if start is not None:result.append(dict(start_s=start,end_s=end,duration_s=end-start))
    return result

def summarize(intervals, start_s, end_s, cluster_gap_s=1.1):
    """Clip first, then threshold. Cluster span and stopped time stay distinct."""
    if not(math.isfinite(start_s) and math.isfinite(end_s) and start_s<end_s):
        raise ValueError('Invalid explicitly qualified audit window')
    parts=[]
    for row in intervals:
        lo,hi=max(start_s,row['start_s']),min(end_s,row['end_s'])
        if hi>lo:parts.append(dict(start_s=lo,end_s=hi,duration_s=hi-lo))
    clusters=[]
    for row in parts:
        if not clusters or row['start_s']-clusters[-1]['end_s']>cluster_gap_s:
            clusters.append(dict(start_s=row['start_s'],end_s=row['end_s'],low_s=row['duration_s'],episodes=1,gaps_s=[]))
        else:
            c=clusters[-1];c['gaps_s'].append(row['start_s']-c['end_s']);c['end_s']=row['end_s'];c['low_s']+=row['duration_s'];c['episodes']+=1
    for c in clusters:c['span_s']=c['end_s']-c['start_s']
    return dict(window_s=[start_s,end_s],speed_limit_mps=.05,intervals=parts,
        count_ge_05s=sum(p['duration_s']>=.5 for p in parts),count_ge_1s=sum(p['duration_s']>=1 for p in parts),
        max_single_s=max((p['duration_s'] for p in parts),default=0),
        cumulative_low_s=sum(p['duration_s'] for p in parts),
        cluster_gap_s=cluster_gap_s,clusters=clusters,
        split_clusters_ge_1s=[c for c in clusters if c['episodes']>1 and c['low_s']>=1])
