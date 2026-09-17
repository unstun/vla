"""Boot the original MIP environment on its shipped rand100 split.

auto_host has no initialization-kwargs CLI. Its default val_unseen split would
load an unrelated episode before the driver can select rand100. Only that
startup default is changed here; actions, rendering and metrics stay upstream.
Shutdown is dispatched to the same executor that owns the OpenGL context.
"""
import asyncio

from workspace.nodesets.env.env_habitat import EnvHabitatNodeSet


class Rand100HabitatNodeSet(EnvHabitatNodeSet):
    async def initialize(self, **kwargs):
        kwargs.setdefault("dataset", "R2R-CE")
        kwargs.setdefault("split", "rand100")
        await super().initialize(**kwargs)

    async def shutdown(self):
        # Upstream calls this on the event-loop thread; Habitat-Sim 0.1.7 then
        # aborts with GL::Context::current(): no current context on this host.
        await asyncio.get_running_loop().run_in_executor(
            self._mgr.executor, self._mgr.shutdown)
