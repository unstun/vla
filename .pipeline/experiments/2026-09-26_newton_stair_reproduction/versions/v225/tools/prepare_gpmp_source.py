"""Instrument a private diagnostic copy; never mutate the production source."""
from pathlib import Path
import hashlib,json
work=Path('/work');rel='src/pct_planner/lib/src/trajectory_optimization/gpmp_optimizer/gpmp_optimizer.cc'
path=work/rel;inventory=json.loads((work/'source_inventory.json').read_text())
assert hashlib.sha256(path.read_bytes()).hexdigest()==inventory[rel]
text=path.read_text();marker='bool GPMPOptimizer::GenerateTrajectory'
text=text.replace(marker,'#include "gpmp_ablation.h"\n#include "gpmp_observer.h"\n\n'+marker,1)
text=text.replace('graph.add(GPInterpolateObstacleFactor(', 'graph.add(DiagnosticInterFactor(GPInterpolateObstacleFactor(')
text=text.replace('0.1, kQc, dt, (i - 1) * dt, tau * (j + 1)));',
    '0.1, kQc, dt, (i - 1) * dt, tau * (j + 1)), path[i-1], path[i], kQc, dt, tau*(j+1)));')
text=text.replace('graph.add(GPObstacleFactor(', 'graph.add(DiagnosticNodeFactor(GPObstacleFactor(')
text=text.replace('0.1, safe_cost_margin_, true));',
    '0.1, safe_cost_margin_, true),diagnosticYaw(diagnosticState(path[i]))));')
old='gtsam::LevenbergMarquardtOptimizer opt(graph, init_values, param);'
assert text.count(old)==1;text=text.replace(old,'DiagnosticLM opt(graph, init_values, param);')
marker='  param.setMaxIterations(max_iterations_);'
assert text.count(marker)==1
text=text.replace(marker,marker+'''
  if(std::string(std::getenv("GPMP_DIAG_ABSOLUTE_ONLY"))=="1") {
    param.setRelativeErrorTol(0.0);param.setAbsoluteErrorTol(1e-5);param.setErrorTol(0.0);
  }
  param.iterationHook=[](size_t iteration,double before,double after) {
    std::cout<<std::setprecision(17)<<"GPMP_ITERATION mode="<<diagnosticMode()<<" iteration="<<iteration
      <<" before="<<before<<" after="<<after<<" delta="<<before-after
      <<" relative="<<(before-after)/std::max(before,1e-30)<<'\\n';
  };
''',1)
out=work/'diagnostic_source';out.mkdir(exist_ok=True)
(out/'gpmp_optimizer.cc').write_text(text)
(out/'provenance.json').write_text(json.dumps({'source':rel,'source_sha256':inventory[rel],
    'diagnostic_sha256':hashlib.sha256(text.encode()).hexdigest(),
    'changes':['observe existing linearization','iteration/error logging','absolute-only diagnostic option']},indent=2)+'\n')
rel='src/pct_planner/lib/src/map_manager/dense_elevation_map.cc'
path=work/rel;assert hashlib.sha256(path.read_bytes()).hexdigest()==inventory[rel]
text=path.read_text().replace('#include <cmath>','#include <cmath>\n#include <cstdlib>\n#include <string>')
old='  double x_lb = std::max(std::floor(x - 0.5), 0.0);\n  double y_lb = std::max(std::floor(y - 0.5), 0.0);'
assert text.count(old)==2
new='''  const char *setting=std::getenv("GPMP_DIAG_CONTINUOUS");
  const bool continuous=setting&&std::string(setting)=="1";
  double x_lb = std::max(std::floor(x - (continuous?0.:.5)), 0.0);
  double y_lb = std::max(std::floor(y - (continuous?0.:.5)), 0.0);'''
text=text.replace(old,new)
(out/'dense_elevation_map.cc').write_text(text)
(out/'interpolation_provenance.json').write_text(json.dumps({'source':rel,'source_sha256':inventory[rel],
    'diagnostic_sha256':hashlib.sha256(text.encode()).hexdigest(),
    'changes':['diagnostic-only integer-anchored interpolation option; original mode retained']},indent=2)+'\n')
