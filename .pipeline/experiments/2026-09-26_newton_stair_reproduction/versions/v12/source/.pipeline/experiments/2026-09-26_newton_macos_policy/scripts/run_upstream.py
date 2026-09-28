"""Use the installed unmodified upstream CLI with a project-owned JIT cache."""
import os
import runpy
import warp as wp

wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
runpy.run_module("newton.examples", run_name="__main__")
