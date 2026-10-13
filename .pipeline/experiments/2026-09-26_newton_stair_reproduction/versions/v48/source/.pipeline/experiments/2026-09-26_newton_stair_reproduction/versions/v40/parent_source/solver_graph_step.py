"""Capture only the pinned fixed-dt solver call, preserving per-step guards."""
import warp as wp


class SolverGraphStep:
    def __init__(self, solver, first, second, control, contacts):
        if (not solver.model.device.is_cuda or solver.use_mujoco_cpu or
                solver.update_data_interval != 0 or solver.enable_sleeping):
            raise ValueError("Solver graph requires CUDA, update_data_interval=0 and sleeping disabled")
        self.solver = solver
        self.original_step = solver.step
        self.states = (first, second)
        self.control, self.contacts = control, contacts
        self.graphs = None
        self.launches = 0

    def __call__(self, state_in, state_out, control, contacts, dt):
        pair = (id(state_in), id(state_out))
        allowed = {(id(self.states[0]), id(self.states[1])), (id(self.states[1]), id(self.states[0]))}
        if pair not in allowed or control is not self.control or contacts is not self.contacts or dt != .001:
            raise ValueError("Captured solver inputs or fixed physical timestep changed")
        if self.graphs is None:
            # This first real integration warms lazy solver buffers/kernels.
            # CUDA capture records operations without advancing physical time.
            self.original_step(state_in, state_out, control, contacts, dt)
            counter = self.solver._step
            graphs = {}
            try:
                for first, second in (self.states, self.states[::-1]):
                    with wp.ScopedCapture(device=self.solver.model.device) as capture:
                        self.original_step(first, second, control, contacts, dt)
                    graphs[(id(first), id(second))] = capture.graph
            finally:
                # update_data_interval=0 and sleeping=False make this the only
                # host step counter; keep it equal to actual integrations.
                self.solver._step = counter
            self.graphs = graphs
            return
        wp.capture_launch(self.graphs[pair])
        self.solver._step += 1
        self.launches += 1
