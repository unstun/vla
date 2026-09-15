"""Verify synced evidence and plot the frozen first-call diagnostic."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from controller_probe import ControllerProbe


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def main():
    run = HERE / 'executions' / sys.argv[1]
    checks = []
    for entry in json.loads((run / 'artifact_sha256.json').read_text()):
        actual = hashlib.sha256((run / entry['path']).read_bytes()).hexdigest()
        assert actual == entry['sha256'], entry['path']
        checks.append({'path': entry['path'], 'sha256': actual})
    meta = json.loads((run / 'meta.json').read_text())
    report = json.loads((run / 'results/report.json').read_text())
    assert meta['exit_code'] == 0 and not meta['timed_out'] and report['completed']
    assert len(report['records']) == 16 and len(report['cache_interventions']) == 8
    assert len({r['id'] for r in report['records']}) == 16
    save(run / 'local_integrity.json', {'passed': True, 'checks': checks})
    plan = json.loads((run / 'source_snapshot/plan.json').read_text())
    assert hashlib.sha256((run / 'source_snapshot/plan.json').read_bytes()).hexdigest() == report['plan_sha256']
    by_id = {r['id']: r for r in report['records']}
    summary = {'run_id': meta['run_id'], 'wall_seconds': meta['wall_seconds'],
               'artifact_checks': len(checks), 'repeat_checks': [],
               'language_comparisons': [], 'original_run_parity': [],
               'image_comparisons': [], 'seed_comparisons': [], 'controller_controls': []}
    controller = ControllerProbe(HERE.parent / 'work/DynaNav/behavior/nova_carter_test_ticvla.py')
    for fixture in plan['fixtures']:
        context = fixture['id']
        for language in ['zh', 'en']:
            base = by_id[f'{context}_seed36_base_{language}']
            repeat = by_id[f'{context}_seed36_repeat_{language}']
            equal = {k: base[k] == repeat[k] for k in [
                'response', 'image_features', 'action_state', 'cache', 'waypoints_tensor']}
            summary['repeat_checks'].append({'fixture': context, 'language': language, **equal})
            for seed in [37, 38]:
                other = by_id[f'{context}_seed{seed}_base_{language}']
                summary['seed_comparisons'].append({
                    'fixture': context, 'language': language, 'seed': seed,
                    'max_abs_waypoint_delta_m': float(np.max(np.abs(
                        np.array(base['waypoints']) - np.array(other['waypoints'])))),
                    'same_response': base['response'] == other['response'],
                    'same_cache': base['cache']['sha256'] == other['cache']['sha256']})
        original = json.loads((HERE / fixture['original_first_inference']).read_text())
        original_lang = context.split('_')[0]
        replay = by_id[f'{context}_seed36_base_{original_lang}']
        summary['original_run_parity'].append({
            'fixture': context, 'original_run': fixture['original_run'],
            'max_abs_waypoint_delta_m': float(np.max(np.abs(
                np.array(original['waypoints']) - np.array(replay['waypoints'])))),
            'same_waypoints': original['waypoints'] == replay['waypoints']})
        for seed in [36, 37, 38]:
            zh, en = [by_id[f'{context}_seed{seed}_base_{lang}'] for lang in ['zh', 'en']]
            assert zh['image_features'] == en['image_features']
            assert zh['action_state'] == en['action_state']
            assert zh['vlm_extraction_inputs']['pixel_values'] == en['vlm_extraction_inputs']['pixel_values']
            delta = np.array(zh['waypoints']) - np.array(en['waypoints'])
            summary['language_comparisons'].append({
                'fixture': context, 'seed': seed,
                'same_current_features_and_delayed_pixels_and_state': True,
                'mean_point_distance_m': float(np.mean(np.linalg.norm(delta, axis=1))),
                'max_point_distance_m': float(np.max(np.linalg.norm(delta, axis=1))),
                'zh_controller': zh['controller'], 'en_controller': en['controller'],
                'same_cache': zh['cache']['sha256'] == en['cache']['sha256']})
        wps = np.array(by_id[f'{context}_seed36_base_zh']['waypoints'])
        for name, variant in [('original', wps), ('reflect_lateral', wps * [1, -1]),
                              ('zero_lateral', wps * [1, 0]), ('scale_xy_2', wps * 2)]:
            summary['controller_controls'].append({
                'fixture': context, 'intervention': name, 'controller': controller(variant),
                'boundary': 'synthetic geometric controller-only control, not model output or a navigation fix'})
    for language in ['zh', 'en']:
        a, b = [by_id[f'{context}_seed36_base_{language}'] for context in ['zh_rgb', 'en_rgb']]
        summary['image_comparisons'].append({
            'language': language, 'max_abs_waypoint_delta_m': float(np.max(np.abs(
                np.array(a['waypoints']) - np.array(b['waypoints'])))),
            'same_response': a['response'] == b['response']})
    summary['max_cache_intervention_error_m'] = max(
        r['max_abs_error_to_donor_original_m'] for r in report['cache_interventions'])
    save(HERE / 'analysis/summary.json', summary)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), gridspec_kw={'width_ratios': [1.45, 1]})
    colors = {'zh': '#d1495b', 'en': '#00798c'}
    for row, fixture in enumerate(plan['fixtures']):
        context = fixture['id']
        axes[row, 0].imshow(Image.open(HERE / fixture['image']))
        axes[row, 0].axis('off')
        axes[row, 0].set_title(f"Frozen RGB from {fixture['original_run']}", fontsize=10)
        ax = axes[row, 1]
        for lang in ['zh', 'en']:
            rec = by_id[f'{context}_seed36_base_{lang}']
            wps = np.asarray(rec['waypoints'])
            cmd = rec['controller']
            label = ('Chinese' if lang == 'zh' else 'English') + (
                f"\nv={cmd['v_desired_m_s']:.3f} m/s, w={cmd['w_desired_rad_s']:.3f} rad/s")
            ax.plot(-wps[:, 1], wps[:, 0], '.-', color=colors[lang], label=label, lw=1.3, ms=3)
            j = cmd['lookahead_index']
            ax.scatter(-wps[j, 1], wps[j, 0], s=80, facecolors='none', edgecolors=colors[lang])
        ax.scatter(0, 0, marker='^', c='black', s=55, label='Robot origin')
        ax.axhline(0, color='#cccccc', lw=.5)
        ax.axvline(0, color='#cccccc', lw=.5)
        ax.set(xlim=(-.085, .085), ylim=(-.06, .32),
               xlabel='Lateral offset: left < 0 < right (m)', ylabel='Forward offset (m)')
        ax.set_aspect('equal')
        ax.set_xticks([-.05, 0, .05], ['-.05', '0', '.05'])
        ax.tick_params(axis='x', labelsize=9)
        ax.grid(alpha=.18)
        ax.legend(fontsize=8, loc='upper left', bbox_to_anchor=(1.02, 1))
        ax.set_title('First model trajectory | seed 36', fontsize=10)
    fig.suptitle('Same pixels + state + delay; change only instruction language', fontsize=14)
    fig.text(.5, .012, 'Circles: controller lookahead. Commands are before slew limits. Offline diagnostic, not new robot motion.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .025, .99, .96))
    fig.savefig(HERE / 'analysis/frozen_trajectory_comparison.png', dpi=170)
    fig.savefig(HERE / 'analysis/frozen_trajectory_comparison.pdf')
    plt.close(fig)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
