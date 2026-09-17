#!/usr/bin/env python3
"""Materialize an isolated, explicitly labelled SCAN diagnostic source copy."""

import argparse
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'p2b_execution/builds/scan_03/src/plan_manage/src/planner_manager.cpp'


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise RuntimeError('Diagnostic insertion anchor is not unique: ' + before)
    return text.replace(before, after, 1)


def materialize(mode, output):
    original = SOURCE.read_bytes()
    text = SOURCE.read_text()
    helper = r'''
    void diagnosticSpline(const char *stage, UniformBspline traj)
    {
      auto vel = traj.getDerivative();
      auto acc = vel.getDerivative();
      const double duration = traj.getTimeSum();
      double max_acc = 0.0, max_vel = 0.0, max_acc_time = 0.0;
      for (int i = 0; i <= 1000; ++i)
      {
        const double t = duration * static_cast<double>(i) / 1000.0;
        const double value = acc.evaluateDeBoorT(t).norm();
        if (value > max_acc) { max_acc = value; max_acc_time = t; }
        max_vel = std::max(max_vel, vel.evaluateDeBoorT(t).norm());
      }
      const auto end = traj.evaluateDeBoorT(duration);
      std::printf("[DEBUG-scan-0916] stage=%s duration=%.17g max_acc=%.17g max_acc_t=%.17g max_vel=%.17g end_acc=%.17g end_vel=%.17g end_x=%.17g end_y=%.17g end_z=%.17g\n",
                  stage, duration, max_acc, max_acc_time, max_vel,
                  acc.evaluateDeBoorT(duration).norm(), vel.evaluateDeBoorT(duration).norm(),
                  end.x(), end.y(), end.z());
    }
'''
    text = replace_once(text, '    void applyLinearZReference', helper + '\n    void applyLinearZReference')
    endpoint_line = '        start_end_derivatives.push_back(gl_traj.evaluateAcc(t));'
    replacement = endpoint_line if mode == 'original' else '        start_end_derivatives.push_back(gl_traj.evaluateAcc(time));'
    replacement += r'''
        std::printf("[DEBUG-scan-0916] stage=poly_init total_time=%.17g sample_time=%.17g ts=%.17g point_count=%zu sampled_end_acc=%.17g true_end_acc=%.17g used_end_acc=%.17g endpoint_gap=%.17g\n",
                    time, t, ts, point_set.size(), gl_traj.evaluateAcc(t).norm(),
                    gl_traj.evaluateAcc(time).norm(), start_end_derivatives.back().norm(),
                    (point_set.back() - local_target_pt).norm());
'''
    text = replace_once(text, endpoint_line, replacement)
    text = replace_once(text,
        '    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);',
        '    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);\n'
        '    diagnosticSpline("initial", UniformBspline(ctrl_pts, 3, ts));')
    text = replace_once(text,
        '    pos.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);',
        '    pos.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);\n'
        '    diagnosticSpline("rebound", pos);')
    text = replace_once(text,
        '      cout << "Need to reallocate time." << endl;',
        '      cout << "Need to reallocate time." << endl;\n'
        '      std::printf("[DEBUG-scan-0916] stage=ratio ratio=%.17g ts=%.17g\\n", ratio, ts);')
    text = replace_once(text,
        '    if (!flag_step_2_success || !checkDynamicFeasibility(pos))',
        '    diagnosticSpline("refined", pos);\n'
        '    if (!flag_step_2_success || !checkDynamicFeasibility(pos))')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'planner_manager.cpp').write_text(text)
    manifest = {
        'mode': mode,
        'source': str(SOURCE),
        'source_sha256': hashlib.sha256(original).hexdigest(),
        'output_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'instrumentation_tag': '[DEBUG-scan-0916]',
        'behavior_change': ('none; stage diagnostics only' if mode == 'original' else
                            'Only use acceleration at the true polynomial end time instead of the last pre-end sample.'),
        'limits_changed': False,
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['original', 'true-end-acceleration'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    materialize(args.mode, args.output)
