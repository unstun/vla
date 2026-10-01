#include <plan_env/raw_return_classification.h>
#include <iostream>
#include <stdexcept>

using namespace reactive_stair;
void require(bool value, const char *message) {
  if (!value) throw std::runtime_error(message);
}

int main() {
  TerrainSnapshot terrain;
  terrain.resolution_m = .1;
  terrain.cells[{0, 0}] = {{Support::Stair, .30810546994209287}};
  terrain.cells[{0, 1}] = {{Support::Flat, .1945800793170929}};
  terrain.cells[{0, -1}] = {{Support::Flat, .33081054806709287}};
  require(selectedGroundReturn(terrain, .025, .025, .2252824474979938, .05),
          "recorded first riser is not positively classified");
  require(selectedGroundReturn(terrain, .025, .025, .19455199509596538, .05),
          "recorded lower tread in an edge cell is not classified");
  require(!selectedGroundReturn(terrain, .025, .025, .08, .05),
          "return below the neighboring tread must remain unclassified");
  require(!selectedGroundReturn(terrain, .025, .025, .40, .05),
          "object above mapped tread must remain an obstacle");
  terrain.cells[{0, 1}] = {{Support::Flat, 0.}};
  require(!selectedGroundReturn(terrain, .025, .025, .1, .05),
          "tall step cannot be associated to a lower level");
  terrain.cells[{0, 1}] = {{Support::Flat, .30810546994209287}};
  terrain.cells[{0, -1}] = terrain.cells[{0, 1}];
  require(!selectedGroundReturn(terrain, .025, .025, .2, .05),
          "flat slab underside must remain unclassified");
  terrain.cells[{0, 0}] = {{Support::Flat, 0.}, {Support::Flat, 4.}};
  require(!selectedGroundReturn(terrain, .025, .025, .18, .05),
          "low box must not borrow an overhead floor");
  terrain.cells.erase({0, 0});
  require(!selectedGroundReturn(terrain, .025, .025, .2, .05),
          "missing central support cannot be filled from a neighbor");
  require(!mayWaiveRawContributor(true, false, true),
          "existing nonterrain history must still win");
  std::cout << "bounded mapped riser classification: PASS\n";
}
