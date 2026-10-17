"""Plot received native cubic geometry; this is not measured robot motion."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
spline=json.loads((HERE/"accepted_spline.json").read_text())
result=json.loads((HERE/"RUNTIME_RESULT.json").read_text())
assert result["body_twist_frame_corrected"] and result["moving_spline_count"]==1
controls=np.array([[p[k] for k in ("x","y","z")] for p in spline["pos_pts"]])
knots=np.array(spline["knots"])
seed=np.array(json.loads((HERE.parent/"step8_spline_seed/GEOMETRY_TRACE.json").read_text())["points"]["seed"])
def evaluate(t):
    k=3
    while knots[k+1]<t:
        k+=1
    values=controls[k-3:k+1].copy()
    for r in range(1,4):
        for i in range(3,r-1,-1):
            a=(t-knots[i+k-3])/(knots[i+1+k-r]-knots[i+k-3])
            values[i]=(1-a)*values[i-1]+a*values[i]
    return values[3]
curve=np.array([evaluate(t) for t in np.linspace(0,result["duration_s"],2400)])
assert np.linalg.norm(curve[0]-seed[0])<1e-10 and np.linalg.norm(curve[-1]-seed[-1])<1e-10
plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False})
fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
forward=lambda p:seed[0,1]-p[:,1]
for data,label,color,width in [(seed,"Checked A* seed", "#8f9ea9",2.5),(curve,"Accepted cubic", "#167d91",1.5)]:
    axes[0].plot(forward(data),data[:,2],label=label,color=color,lw=width)
    axes[1].plot(forward(data),100*(data[:,0]-seed[0,0]),color=color,lw=width)
axes[0].set_ylabel("Body reference Z (m)")
axes[1].set_ylabel("Lateral X offset (cm)")
axes[1].set_xlabel("Forward progress along -Y (m)")
axes[0].legend(frameon=False,loc="upper left")
for ax in axes:
    ax.grid(alpha=.18)
fig.suptitle("SCAN28: a curve accepted by the native planner",x=.09,ha="left",fontsize=15)
fig.text(.09,.02,"Corrected velocity-frame replay | 93.223 s duration | 9,324 collision samples | Geometry, not robot motion",fontsize=9,color="#555555")
fig.tight_layout(rect=(0,.06,1,.95))
fig.savefig(HERE/"accepted_spline.png",dpi=180)
fig.savefig(HERE/"accepted_spline.svg")
print(HERE/"accepted_spline.png")
