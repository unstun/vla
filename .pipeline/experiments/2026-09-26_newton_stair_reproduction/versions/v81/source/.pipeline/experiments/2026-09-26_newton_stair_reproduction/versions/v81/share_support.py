"""Share immutable ground/support tables; copy them only on support mutation."""
from pathlib import Path
import re

FIELDS = ('reactive_parameters_', 'reactive_decision_', 'reactive_terrain_',
          'reactive_ground_', 'reactive_navigation_ground_', 'reactive_surface_ground_',
          'reactive_physical_floor_', 'physical_floor_decoded_valid_', 'reactive_step_result_')


def share_support(env):
    header = env / 'include/plan_env/grid_map.h'
    text = header.read_text()
    assert 'struct GridMapSupportState' not in text
    start = text.index('struct GridMapState {')
    end = text.index('\n};', start)
    state = text[start:end]
    declarations = []
    for line in state.splitlines(True):
        if any(re.search(r'\b' + field + r'\b', line) for field in FIELDS):
            declarations.append(line)
            state = state.replace(line, '', 1)
    state = state.replace('struct GridMapState {', '''struct GridMapState {
  std::shared_ptr<const GridMapSupportState> support_{std::make_shared<GridMapSupportState>()};''')
    support = 'struct GridMapSupportState {\n' + ''.join(declarations) + '};\n\n'
    text = text[:start] + support + state + text[end:]
    text = text.replace('  std::unique_ptr<GridMapState> owned_state_;', '''  const GridMapSupportState &supportState() const { return *mapState().support_; }
  GridMapSupportState &mutableSupportState() {
    auto &pointer = mutableMapState().support_;
    if (!pointer.unique()) pointer = std::make_shared<GridMapSupportState>(*pointer);
    // Every allocation above has mutable underlying storage. The const view
    // protects readers; mutation requires exclusive writer ownership.
    return *std::const_pointer_cast<GridMapSupportState>(pointer);
  }
  std::unique_ptr<GridMapState> owned_state_;''')
    header.write_text(text)
    for path in (header, env / 'src/grid_map.cpp',
                 env / 'include/plan_env/scan_reactive_grid_methods.inc',
                 env / 'include/plan_env/async_mapping_methods.inc'):
        text = path.read_text()
        for field in FIELDS:
            text = re.sub(r'\bmutableMapState\(\)\.' + field + r'\b', 'mutableSupportState().' + field, text)
            text = re.sub(r'\bmapState\(\)\.' + field + r'\b', 'supportState().' + field, text)
        path.write_text(text)


if __name__ == '__main__':
    import sys
    share_support(Path(sys.argv[1]))
