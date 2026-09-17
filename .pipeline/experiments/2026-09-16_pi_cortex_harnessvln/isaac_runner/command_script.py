#!/usr/bin/env python3
"""Piecewise-constant velocity command scripts for the `scripted_walk` runner case.

Pure standard-library Python. `materialize_runner_patch.py` inserts the text
between the two body markers verbatim into the patched runner, so the executed
runner stays one hash-recorded file; `qualify_stand_runner.py` and the tests
import this file directly. Keep the body free of `from __future__` imports and
of Python syntax newer than 3.8.

Schema (version 1):

    {"schema_version": 1, "name": "...", "note": "...",
     "segments": [{"t_start_s": 0.0, "vx": 0.0, "vy": 0.0, "wz": 0.0, "label": "..."}, ...]}

`name`, `note` and `label` are optional strings. The first segment starts at
0.0 s, start times increase strictly, and every command lies within the
runner's own command limits (`--max-vx`, `--max-vy`, `--max-wz`,
`--max-horizontal-norm`, with the runner's 1e-9 admission slack). Values
outside the limits are refused, never clamped.

Task: .trellis/tasks/09-17-isaac-runner-stance-hold (PRD D5, AC8).
"""

# >>> command_script runner body begin
import hashlib
import json
import math

SCRIPTED_WALK_CASE = "scripted_walk"
COMMAND_SCRIPT_SCHEMA_VERSION = 1
COMMAND_SCRIPT_MAX_SEGMENTS = 64
# The runner's longest case (native_nominal) is capped at 600 s.
COMMAND_SCRIPT_MAX_START_S = 600.0
# Loop-top simulation time is float32-derived (for example 3.9999998 s at
# control step 200). A segment applies from the first control step whose sim
# time is within this slack of its start: 0.5 percent of the 20 ms period.
COMMAND_SCRIPT_TIME_EPS_S = 1.0e-4
# The runner's admission check allows the same slack on the horizontal norm.
COMMAND_SCRIPT_LIMIT_EPS = 1.0e-9
COMMAND_SCRIPT_TOP_KEYS = ("schema_version", "segments", "name", "note")
COMMAND_SCRIPT_SEGMENT_KEYS = ("t_start_s", "vx", "vy", "wz", "label")
COMMAND_SCRIPT_REQUIRED_SEGMENT_KEYS = ("t_start_s", "vx", "vy", "wz")
COMMAND_SCRIPT_LIMIT_KEYS = ("max_vx", "max_vy", "max_wz", "max_horizontal_norm")


class CommandScriptError(ValueError):
    """The command script is unreadable, malformed or outside the command limits."""


def _script_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CommandScriptError("%s must be a number, got %r" % (name, value))
    result = float(value)
    if not math.isfinite(result):
        raise CommandScriptError("%s is not finite" % name)
    return result


def _script_text(name, value):
    if value is not None and not isinstance(value, str):
        raise CommandScriptError("%s must be a string" % name)
    return value


def parse_command_script(payload, limits):
    """Validate a decoded script against the runner's command limits; return a normalized copy."""
    if not isinstance(payload, dict):
        raise CommandScriptError("command script must be a JSON object")
    unknown = sorted(set(payload) - set(COMMAND_SCRIPT_TOP_KEYS))
    if unknown:
        raise CommandScriptError("command script has unknown keys %s" % unknown)
    version = payload.get("schema_version")
    if type(version) is not int or version != COMMAND_SCRIPT_SCHEMA_VERSION:
        raise CommandScriptError("schema_version must be %d, got %r" % (COMMAND_SCRIPT_SCHEMA_VERSION, version))
    name = _script_text("name", payload.get("name"))
    note = _script_text("note", payload.get("note"))
    if not isinstance(limits, dict):
        raise CommandScriptError("command limits must be a mapping")
    bounds = {}
    for key in COMMAND_SCRIPT_LIMIT_KEYS:
        if key not in limits:
            raise CommandScriptError("command limit %s is missing" % key)
        bounds[key] = _script_number("command limit " + key, limits[key])
        if bounds[key] <= 0.0:
            raise CommandScriptError("command limit %s must be positive" % key)
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        raise CommandScriptError("segments must be a non-empty list")
    if len(segments) > COMMAND_SCRIPT_MAX_SEGMENTS:
        raise CommandScriptError("at most %d segments are allowed" % COMMAND_SCRIPT_MAX_SEGMENTS)
    result = []
    previous = None
    for index, item in enumerate(segments):
        where = "segments[%d]" % index
        if not isinstance(item, dict):
            raise CommandScriptError("%s must be an object" % where)
        unknown = sorted(set(item) - set(COMMAND_SCRIPT_SEGMENT_KEYS))
        if unknown:
            raise CommandScriptError("%s has unknown keys %s" % (where, unknown))
        missing = [key for key in COMMAND_SCRIPT_REQUIRED_SEGMENT_KEYS if key not in item]
        if missing:
            raise CommandScriptError("%s lacks %s" % (where, missing))
        start = _script_number(where + ".t_start_s", item["t_start_s"])
        vx = _script_number(where + ".vx", item["vx"])
        vy = _script_number(where + ".vy", item["vy"])
        wz = _script_number(where + ".wz", item["wz"])
        label = _script_text(where + ".label", item.get("label"))
        if index == 0 and start != 0.0:
            raise CommandScriptError("the first segment must start at 0.0 s, got %r" % start)
        if not 0.0 <= start <= COMMAND_SCRIPT_MAX_START_S:
            raise CommandScriptError("%s.t_start_s %r is outside [0, %g]" % (where, start, COMMAND_SCRIPT_MAX_START_S))
        if previous is not None and start <= previous:
            raise CommandScriptError("%s.t_start_s %r does not increase (previous %r)" % (where, start, previous))
        for axis, value, key in (("vx", vx, "max_vx"), ("vy", vy, "max_vy"), ("wz", wz, "max_wz")):
            if abs(value) > bounds[key] + COMMAND_SCRIPT_LIMIT_EPS:
                raise CommandScriptError("%s.%s %r exceeds the runner limit %s=%r" % (where, axis, value, key, bounds[key]))
        norm = math.hypot(vx, vy)
        if norm > bounds["max_horizontal_norm"] + COMMAND_SCRIPT_LIMIT_EPS:
            raise CommandScriptError("%s horizontal norm %r exceeds the runner limit max_horizontal_norm=%r"
                                     % (where, norm, bounds["max_horizontal_norm"]))
        result.append({"index": index, "t_start_s": start, "vx": vx, "vy": vy, "wz": wz, "label": label})
        previous = start
    return {
        "schema_version": COMMAND_SCRIPT_SCHEMA_VERSION,
        "name": name,
        "note": note,
        "segments": result,
        "limits": bounds,
        "time_eps_s": COMMAND_SCRIPT_TIME_EPS_S,
    }


def load_command_script(path, limits):
    """Read, hash and validate a command script file."""
    with open(str(path), "rb") as stream:
        data = stream.read()
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CommandScriptError("command script %s is not UTF-8 JSON: %s" % (path, exc))
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "script": parse_command_script(payload, limits),
    }


def command_script_at(script, sim_time_s):
    """(segment index, (vx, vy, wz)) of the last segment that has started at sim_time_s."""
    now = float(sim_time_s)
    if not math.isfinite(now):
        raise CommandScriptError("simulation time is not finite")
    chosen = None
    for segment in script["segments"]:
        if segment["t_start_s"] <= now + COMMAND_SCRIPT_TIME_EPS_S:
            chosen = segment
        else:
            break
    if chosen is None:
        raise CommandScriptError("no command segment has started at %r s" % now)
    return chosen["index"], (chosen["vx"], chosen["vy"], chosen["wz"])


def command_script_is_zero(segment):
    return segment["vx"] == 0.0 and segment["vy"] == 0.0 and segment["wz"] == 0.0


def command_script_phases(script, end_s):
    """Segments as [start, end) phases; the last phase ends at end_s."""
    segments = script["segments"]
    end = float(end_s)
    if not math.isfinite(end) or end <= segments[-1]["t_start_s"]:
        raise CommandScriptError("end_s %r must be finite and after the last segment start" % end_s)
    phases = []
    for position, segment in enumerate(segments):
        stop = segments[position + 1]["t_start_s"] if position + 1 < len(segments) else end
        phases.append({
            "index": segment["index"],
            "label": segment["label"],
            "start_s": segment["t_start_s"],
            "end_s": stop,
            "command": [segment["vx"], segment["vy"], segment["wz"]],
            "zero": command_script_is_zero(segment),
        })
    return phases
# <<< command_script runner body end
