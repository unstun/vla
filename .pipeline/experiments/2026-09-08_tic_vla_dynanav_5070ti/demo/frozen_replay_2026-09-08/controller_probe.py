"""Execute the verified upstream controller slice without importing Isaac Sim."""

import ast
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np


class ControllerProbe:
    def __init__(self, path):
        self.path = Path(path)
        source = self.path.read_text()
        self.source_sha256 = hashlib.sha256(source.encode()).hexdigest()
        tree = ast.parse(source)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                   and any(isinstance(m, ast.FunctionDef) and m.name == '_inference_task'
                           for m in n.body))
        limits = {}
        for node in cls.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in (
                            '_max_linear_velocity', '_max_angular_velocity'):
                        limits[target.id] = ast.literal_eval(node.value)
        assert len(limits) == 2
        self.limits = limits
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                      and n.name == '_inference_task')

        def assigns(node, name):
            return isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets)

        start = next(i for i, n in enumerate(method.body) if assigns(n, 'T'))
        end = next(i for i, n in enumerate(method.body) if assigns(n, 'should_skip_commands'))
        nodes = method.body[start:end]
        self.lines = [nodes[0].lineno, nodes[-1].end_lineno]
        self.code = compile(ast.Module(body=nodes, type_ignores=[]), str(self.path), 'exec')

    def __call__(self, waypoints, initial_yaw_filter=None):
        state = SimpleNamespace(**self.limits)
        if initial_yaw_filter is not None:
            state._yaw_err_filt = initial_yaw_filter
        context = {'np': np, 'math': math, 'self': state,
                   'wps': np.asarray(waypoints, dtype=np.float32)}
        assert context['wps'].shape == (30, 2)
        assert np.isfinite(context['wps']).all()
        exec(self.code, context)
        return {
            'v_desired_m_s': context['v_cmd'], 'w_desired_rad_s': context['w_cmd'],
            'lookahead_index': context['j'],
            'lookahead_xy_m': [context['xL'], context['yL']],
            'lookahead_distance_m': context['L'],
            'polyline_length_m': float(context['s'][-1]),
            'curvature_m_inv': context.get('kappa'),
            'yaw_error_rad': context.get('yaw_err'),
            'initial_yaw_filter': initial_yaw_filter,
            'boundary': 'desired command before slew limits, backup arbitration and wheel control',
        }
