"""Audit active published-trajectory time, respecting replacement ownership."""
import math

def active_gaps(rows, start_s, end_s, tolerance_s=1e-7):
    if not(math.isfinite(start_s) and math.isfinite(end_s) and start_s<end_s):
        raise ValueError('Invalid window')
    gaps=[];last_publication=-math.inf
    for i,row in enumerate(rows):
        publication=float(row['publication_s']);origin=float(row['start_s']);duration=float(row['duration_s'])
        if not all(map(math.isfinite,(publication,origin,duration))) or publication<last_publication or duration<0:
            raise ValueError('Invalid publication/trajectory time')
        last_publication=publication
        next_publication=float(rows[i+1]['publication_s']) if i+1<len(rows) else end_s
        lo,hi=max(start_s,publication),min(end_s,next_publication)
        if hi<=lo:continue
        if int(row['emergency']):
            gaps.append(dict(start_s=lo,end_s=hi,reason='emergency_stop'))
            continue
        if origin>lo+tolerance_s:
            gaps.append(dict(start_s=lo,end_s=min(hi,origin),reason='future_origin'))
        expiry=origin+duration
        if expiry<hi-tolerance_s:
            gaps.append(dict(start_s=max(lo,expiry),end_s=hi,reason='expired_active_curve'))
    if not rows or float(rows[0]['publication_s'])>start_s+tolerance_s:
        gaps.insert(0,dict(start_s=start_s,end_s=min(end_s,float(rows[0]['publication_s'])) if rows else end_s,reason='no_initial_curve'))
    return [dict(g,duration_s=g['end_s']-g['start_s']) for g in gaps if g['end_s']>g['start_s']+tolerance_s]
