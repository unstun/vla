from pathlib import Path
import hashlib,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
source=Path('/Users/sun/tongbu/study/phdproject/machine-dog-nav/.pipeline/experiments/2026-09-08_new_building_pct/runs/preflight03/tomogram_float32.npz')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='9adbbaf3754fc1a488ada560775407d4c684d57e19a6caea7075fa907b5c0c2d'
shutil.copyfile(source,HERE/'tomogram_float32.npz')
p=BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py';s=p.read_text()
anchor='def selected_ground_points(\n'
helper='''ELEVATION_SOURCE_SHA = "9adbbaf3754fc1a488ada560775407d4c684d57e19a6caea7075fa907b5c0c2d"


def load_paired_elevations(path: Path, source: dict) -> np.ndarray:
    """Read original ground precision only after exact map-pair verification."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != ELEVATION_SOURCE_SHA:
        raise ValueError("PCT original-precision source SHA-256 mismatch")
    with np.load(path, allow_pickle=False) as original:
        data = np.asarray(original["data"])
        stored = np.asarray(source["data"])
        if data.dtype != np.float32 or data.shape != stored.shape or stored.dtype != np.float16 or \\
           not np.array_equal(data.astype(np.float16), stored, equal_nan=True):
            raise ValueError("Original precision data does not round to the pinned map")
        for name in ("center", "resolution", "slice_h0", "slice_dh"):
            if not np.array_equal(np.asarray(original[name]), np.asarray(source[name])):
                raise ValueError("Original precision map metadata mismatch: " + name)
        return data[3].copy()


'''
assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor)
old='''    visual_z_offset_m: float = 0.03, cost_limit: Optional[float] = 20.0,
) -> np.ndarray:''';new='''    visual_z_offset_m: float = 0.03, cost_limit: Optional[float] = 20.0,
    paired_elevations: Optional[np.ndarray] = None,
) -> np.ndarray:''';assert s.count(old)==1;s=s.replace(old,new)
old='''    z = ground[layers, grid_x, grid_y] + visual_z_offset_m''';new='''    # Selection, layer deduplication and cost remain the original float16 map.
    # Only the already-selected ground heights may retain generation precision.
    if paired_elevations is not None:
        paired_elevations = np.asarray(paired_elevations)
        if paired_elevations.shape != elevation_raw.shape or paired_elevations.dtype != np.float32 or \\
           not np.array_equal(paired_elevations.astype(np.float16), elevation_raw.astype(np.float16), equal_nan=True):
            raise ValueError("Ground elevations do not match the stored map")
    height_source = ground if paired_elevations is None else paired_elevations
    z = height_source[layers, grid_x, grid_y] + visual_z_offset_m''';assert s.count(old)==1;s=s.replace(old,new)
(HERE/'pct_core_candidate.py').write_text(s)
