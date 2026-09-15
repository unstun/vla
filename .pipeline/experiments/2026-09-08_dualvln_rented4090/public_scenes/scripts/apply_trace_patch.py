"""Apply the output-only evidence patch to the pinned Habitat evaluator.

Every edit below writes information out. None of them changes which action is
chosen, what the model is shown, how the environment is stepped, or how the
official metrics are computed. The patch is idempotent and refuses to run if an
anchor is missing, so it cannot half-apply.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'work/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py'
MARK = '# ---- OUTPUT-ONLY EVIDENCE TRACE ----'

HELPER = '''
# ---- OUTPUT-ONLY EVIDENCE TRACE ----
# Added locally. Writes a per-step JSONL record next to the official outputs so
# that a timeout or a parse fallback can never be reported as a learned STOP,
# and so pixel goals can be redrawn offline on the exact image the model saw.
# Nothing here feeds back into the policy, the environment or the metrics.
import time as _time


class _RunTrace:
    def __init__(self, output_path, scene_id, episode_id, episode, epoch):
        self.dir = os.path.join(output_path, f'trace_{epoch}')
        os.makedirs(self.dir, exist_ok=True)
        self.goal_dir = os.path.join(self.dir, f'{scene_id}_{episode_id:04d}_goalframes')
        self.path = os.path.join(self.dir, f'{scene_id}_{episode_id:04d}.jsonl')
        self.f = open(self.path, 'w')
        self.t_episode = _time.perf_counter()
        self.s2_calls = 0
        self.s1_calls = 0
        self.s2_seconds = 0.0
        self.s1_seconds = 0.0
        self.write({
            'record': 'episode_header',
            'scene_id': scene_id,
            'episode_id': episode_id,
            'instruction': episode.instruction.instruction_text,
            'start_position': [float(v) for v in episode.start_position],
            'start_rotation': [float(v) for v in episode.start_rotation],
            'goal_position': [float(v) for v in episode.goals[0].position],
            'goal_radius': float(episode.goals[0].radius),
            'geodesic_distance': float(episode.info.get('geodesic_distance', float('nan'))),
        })

    def write(self, obj):
        self.f.write(json.dumps(obj, default=float) + '\\n')
        self.f.flush()

    def save_goal_frame(self, step_id, pil_image, tag):
        os.makedirs(self.goal_dir, exist_ok=True)
        p = os.path.join(self.goal_dir, f'step{step_id:04d}_{tag}.png')
        pil_image.save(p)
        return os.path.relpath(p, self.dir)

    def close(self, **kw):
        kw['record'] = 'episode_footer'
        kw['episode_wall_seconds'] = _time.perf_counter() - self.t_episode
        kw['s2_calls'] = self.s2_calls
        kw['s2_seconds_total'] = self.s2_seconds
        kw['s1_calls'] = self.s1_calls
        kw['s1_seconds_total'] = self.s1_seconds
        self.write(kw)
        self.f.close()
'''

# Applied to the whole module.
MODULE_EDITS = [
    # 0. keep the video for failed episodes too, and name it by outcome
    (
        """            if self.save_video and metrics['success'] == 1.0:
                images_to_video(
                    vis_frames,
                    os.path.join(self.output_path, f'vis_{self.epoch}', f'{scene_id}'),
                    f'{episode_id:04d}',""",
        """            # OUTPUT-ONLY LOCAL CHANGE: upstream writes the first-person +
            # top-down composite only when the episode succeeded, so every
            # failure loses its video. Write all episodes and record the
            # outcome in the file name. Policy, environment stepping, metrics
            # and control flow are untouched.
            if self.save_video and len(vis_frames) > 0:
                images_to_video(
                    vis_frames,
                    os.path.join(self.output_path, f'vis_{self.epoch}', f'{scene_id}'),
                    f'{episode_id:04d}_success{int(metrics[\"success\"])}',""",
        2,
    ),
    # 1. helper class after the action-code enum block
    (
        "class action_code(IntEnum):",
        HELPER + "\n\nclass action_code(IntEnum):",
        1,
    ),
]

# Applied only to `_run_eval_dual_system`, which is the mode this evaluation runs.
# `_run_eval_system2` is left byte-identical to upstream.
SPLIT_AT = "    def _run_eval_system2(self)"

EDITS = [
    # 2. open the trace once per episode
    (
        """            rgb_list = []
            action_seq = []
            input_images = []""",
        """            trace = _RunTrace(self.output_path, scene_id, episode_id, episode, self.epoch)
            termination = None

            rgb_list = []
            action_seq = []
            input_images = []""",
        1,
    ),
    # 3. time the System-2 generate call and record its raw output
    (
        """                    with torch.no_grad():
                        output_ids = self.model.generate(""",
        """                    _t_s2 = _time.perf_counter()
                    with torch.no_grad():
                        output_ids = self.model.generate(""",
        1,
    ),
    (
        """                    print('step_id:', step_id, 'output text:', llm_outputs)
""",
        """                    print('step_id:', step_id, 'output text:', llm_outputs)
                    _dt_s2 = _time.perf_counter() - _t_s2
                    # `action` still holds the previous applied action here; it is
                    # reassigned further down, so the branch must be captured now.
                    _s2_branch = 'look_down_followup' if action == action_code.LOOKDOWN else 'level_view'
                    trace.s2_calls += 1
                    trace.s2_seconds += _dt_s2
                    trace.write({
                        'record': 's2_call',
                        'step_id': step_id,
                        'whole_call_seconds': _dt_s2,
                        'raw_output_text': llm_outputs,
                        'branch': _s2_branch,
                        'n_input_images': len(input_images),
                        'model_input_image_size': list(input_images[-1].size) if input_images else None,
                        'image_grid_thw': [[int(v) for v in t] for t in inputs.image_grid_thw],
                    })
""",
        1,
    ),
    # 4. time System-1 and keep the raw trajectory before traj_to_actions divides in place
    (
        """                        with torch.no_grad():
                            dp_actions = self.model.generate_traj(traj_latents, images_dp, depths_dp)

                        action_list = traj_to_actions(dp_actions)""",
        """                        _t_s1 = _time.perf_counter()
                        with torch.no_grad():
                            dp_actions = self.model.generate_traj(traj_latents, images_dp, depths_dp)
                        _raw_traj = dp_actions.detach().float().cpu().numpy().tolist()

                        action_list = traj_to_actions(dp_actions)
                        _dt_s1 = _time.perf_counter() - _t_s1
                        trace.s1_calls += 1
                        trace.s1_seconds += _dt_s1
                        trace.write({
                            'record': 's1_call',
                            'step_id': step_id,
                            'whole_call_seconds': _dt_s1,
                            'raw_trajectory_before_inplace_divide': _raw_traj,
                            'action_list': list(action_list),
                        })""",
        2,
    ),
    # 5. STOP provenance: System-1 asked to stop immediately after a new pixel goal
    (
        """                        action = local_actions[0]
                        if action == action_code.STOP:
                            pixel_goal = None""",
        """                        action = local_actions[0]
                        if action == action_code.STOP:
                            trace.write({'record': 'stop_provenance', 'step_id': step_id,
                                         'kind': 's1_stop_at_first_local_action',
                                         'upstream_behaviour': 'replaced by TURN LEFT, episode continues',
                                         'is_learned_episode_stop': False})
                            pixel_goal = None""",
        1,
    ),
    # 6. pixel goal recorded together with the exact image the model was shown
    (
        """                        print('predicted goal', pixel_goal, flush=True)
""",
        """                        trace.write({
                            'record': 'pixel_goal',
                            'step_id': step_id,
                            'pixel_goal_row_col': [int(pixel_goal[0]), int(pixel_goal[1])],
                            'raw_coords_from_text': [int(c) for c in coord],
                            'model_input_image_size': list(input_images[-1].size),
                            'model_input_image_png': trace.save_goal_frame(
                                step_id, input_images[-1], 'model_input'),
                            'saved_raw_view_png': trace.save_goal_frame(
                                step_id, save_raw_image, 'saved_raw_view'),
                            'saved_raw_view_size': list(save_raw_image.size),
                            'view_kind': _s2_branch,
                        })
                        print('predicted goal', pixel_goal, flush=True)
""",
        1,
    ),
    # 7. STOP provenance: local action budget exhausted / System-1 stop mid-segment
    (
        """                    forward_action += 1
                    if forward_action > MAX_STEPS:""",
        """                    forward_action += 1
                    if forward_action > MAX_STEPS:
                        trace.write({'record': 'stop_provenance', 'step_id': step_id,
                                     'kind': 'forward_budget_exhausted',
                                     'upstream_behaviour': 'pixel goal cleared, System 2 replans',
                                     'is_learned_episode_stop': False})""",
        1,
    ),
    (
        """                    if action == action_code.STOP:
                        pixel_goal = None
                        output_ids = None
                        messages = []
                        step_id += 1""",
        """                    if action == action_code.STOP:
                        trace.write({'record': 'stop_provenance', 'step_id': step_id,
                                     'kind': 's1_stop_mid_segment',
                                     'upstream_behaviour': 'pixel goal cleared, System 2 replans',
                                     'is_learned_episode_stop': False})
                        pixel_goal = None
                        output_ids = None
                        messages = []
                        step_id += 1""",
        1,
    ),
    # 8. action source, including the empty-parse fallback that ends the episode
    (
        """                if len(action_seq) != 0:
                    action = action_seq[0]
                    action_seq.pop(0)
                elif pixel_goal is not None:""",
        """                if len(action_seq) != 0:
                    _action_source = 's2_action_sequence'
                    action = action_seq[0]
                    action_seq.pop(0)
                elif pixel_goal is not None:
                    _action_source = 's1_local_actions'""",
        1,
    ),
    (
        """                else:
                    action = 0

                info = self.env.get_metrics()""",
        """                else:
                    _action_source = 'fallback_no_action_parsed'
                    trace.write({'record': 'stop_provenance', 'step_id': step_id,
                                 'kind': 'fallback_stop_no_action_parsed',
                                 'upstream_behaviour': 'action forced to STOP(0), episode ends',
                                 'is_learned_episode_stop': False})
                    action = 0

                info = self.env.get_metrics()""",
        1,
    ),
    # 9. applied action and realised pose, every iteration
    (
        """                if action == action_code.LOOKDOWN:
                    self.env.step(action)
                    observations, _, done, _ = self.env.step(action)
                    flag = True""",
        """                _st = self.env._env.sim.get_agent_state()
                trace.write({
                    'record': 'step',
                    'step_id': step_id,
                    'applied_action': int(action),
                    'action_name': action_code(int(action)).name,
                    'action_source': _action_source,
                    'is_learned_episode_stop': bool(int(action) == 0
                                                    and _action_source == 's2_action_sequence'),
                    'pixel_goal_active': pixel_goal is not None,
                    'position': [float(v) for v in _st.position],
                    'rotation_wxyz': [float(_st.rotation.w), float(_st.rotation.x),
                                      float(_st.rotation.y), float(_st.rotation.z)],
                    'distance_to_goal': info.get('distance_to_goal'),
                    'collisions': (info.get('collisions') or {}).get('count'),
                })
                if action == action_code.LOOKDOWN:
                    self.env.step(action)
                    observations, _, done, _ = self.env.step(action)
                    flag = True""",
        1,
    ),
    # 10. termination reason, recorded once the loop is over
    (
        """            # ---------- 3. End of episode -----------
            # collect the metric result of this episode and write progress to the output_path/progress.json

            process_bar.update(1)""",
        """            # ---------- 3. End of episode -----------
            termination = 'habitat_episode_over' if done else 'evaluator_step_cap'

            # collect the metric result of this episode and write progress to the output_path/progress.json

            process_bar.update(1)""",
        1,
    ),
    (
        """            vis_frames.clear()
            if vis_writer is not None:
                vis_writer.close()

        self.env.close()""",
        """            trace.close(
                termination_reason=termination,
                final_step_id=step_id,
                evaluator_step_cap=self.max_steps_per_episode,
                metrics={k: (v if not isinstance(v, dict) else None) for k, v in metrics.items()},
                cuda_max_memory_allocated_bytes_whole_run_so_far=(
                    torch.cuda.max_memory_allocated(self.device)
                    if torch.cuda.is_available() else None),
            )

            vis_frames.clear()
            if vis_writer is not None:
                vis_writer.close()

        self.env.close()""",
        1,
    ),
]


def apply(text, edits, label):
    for i, (old, new, count) in enumerate(edits, 1):
        n = text.count(old)
        if n != count:
            print(f'{label} anchor {i} matched {n} times, expected {count}', file=sys.stderr)
            return None
        text = text.replace(old, new)
    return text


def main():
    src = TARGET.read_text()
    if MARK in src:
        print('TRACE_PATCH_ALREADY_APPLIED')
        return 0
    head, sep, tail = src.partition(SPLIT_AT)
    if not sep:
        print('split anchor not found', file=sys.stderr)
        return 2
    head = apply(head, EDITS, 'dual_system')
    if head is None:
        return 2
    src = apply(head + sep + tail, MODULE_EDITS, 'module')
    if src is None:
        return 2
    TARGET.write_text(src)
    print('TRACE_PATCH_APPLIED', len(MODULE_EDITS) + len(EDITS), 'edits')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
