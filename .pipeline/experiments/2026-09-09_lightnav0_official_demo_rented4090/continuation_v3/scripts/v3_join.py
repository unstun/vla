"""Exact joins between capture frames, the sidecar wire trace and official records.

Join keys are (connection_id, seq) plus the exact JPEG SHA-256. Nearby timestamps
and same-looking frames are never accepted as a join.
"""
from __future__ import annotations


def join_predictions(frames, requests, responses, records, connection_id):
    """Return (joined, problems).

    frames    -- capture index rows (frame_id, stamp_ns, front_sha256, ...)
    requests  -- sidecar 'request' traces
    responses -- sidecar 'response' traces
    records   -- official model records with 'seq' and 'image_sha256'
    """
    problems: list[dict] = []
    by_stamp = {}
    for frame in frames:
        stamp = frame.get("stamp_ns")
        if stamp in by_stamp:
            problems.append({"kind": "duplicate_stamp", "stamp_ns": stamp})
        by_stamp[stamp] = frame
    responses_by_seq = {}
    for response in responses:
        if response.get("connection_id") != connection_id:
            continue
        responses_by_seq.setdefault(response["seq"], []).append(response)
    records_by_seq = {}
    for record in records:
        records_by_seq.setdefault(record.get("seq"), []).append(record)

    joined = []
    for request in requests:
        if request.get("connection_id") != connection_id:
            continue
        seq = request.get("seq")
        frame = by_stamp.get(request.get("stamp_ns"))
        if frame is None:
            problems.append({"kind": "unknown_capture_stamp", "seq": seq,
                             "stamp_ns": request.get("stamp_ns")})
            continue
        if frame.get("front_sha256") != request.get("jpeg_sha256"):
            problems.append({"kind": "jpeg_hash_mismatch", "seq": seq,
                             "frame_id": frame.get("frame_id"),
                             "frame_sha256": frame.get("front_sha256"),
                             "request_sha256": request.get("jpeg_sha256")})
            continue
        candidates = responses_by_seq.get(seq, [])
        if len(candidates) != 1:
            problems.append({"kind": "response_count", "seq": seq, "count": len(candidates)})
            continue
        response = candidates[0]
        record_candidates = [r for r in records_by_seq.get(seq, [])
                             if r.get("image_sha256") == request.get("jpeg_sha256")]
        if len(record_candidates) > 1:
            problems.append({"kind": "ambiguous_official_record", "seq": seq})
            continue
        record = record_candidates[0] if record_candidates else None
        if records_by_seq.get(seq) and record is None:
            problems.append({"kind": "official_record_hash_mismatch", "seq": seq})
            continue
        joined.append({
            "seq": seq,
            "connection_id": connection_id,
            "frame_id": frame.get("frame_id"),
            "stamp_ns": request.get("stamp_ns"),
            "jpeg_sha256": request.get("jpeg_sha256"),
            "send_mono_ns": request.get("send_mono_ns"),
            "receive_mono_ns": response.get("receive_mono_ns"),
            "capture_mono_ns": frame.get("capture_mono_ns"),
            "decode_status": response.get("decode_status"),
            "enqueued": response.get("enqueued"),
            "record": record,
            "response": response,
            "frame": frame,
        })
    return joined, problems
