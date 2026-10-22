from pathlib import Path
import math
B=Path('/data/sun/vla_mppi_20261009');out=B/'generic_mechanisms_v261/evaluation';out.mkdir(exist_ok=True)
with (out/'terminal_lattice.txt').open('w') as f:
 for cid,gx,gy,gz in [('E03',5.467685211181641,-6.303810874938965,4.839493293762207),('E02',-6.0323147888183595,4.696189125061035,4.833031196594238)]:
  for iy in range(-5,6):
   for ix in range(-5,6):
    x=gx-.013+ix*.1;y=gy+.017+iy*.1
    for h in range(8):f.write(f'{cid}_{ix}_{iy}_{h} {x:.17g} {y:.17g} {gz:.17g} {h*math.pi/4:.17g}\n')
  for i in range(-40,41):f.write(f'{cid}_continuous_{i} {gx:.17g} {gy+i*.025:.17g} {gz:.17g} {math.pi/2:.17g}\n')
