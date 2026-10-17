---
origin: ai+primary_sources
reviewed: false
date: 2026-09-18
status: surveyed
read_by: lead (full text, arXiv HTML v1; PDFs kept in the session scratchpad, not in the project)
---

# RAEM and TravExplorer: full reading for SCAN stair handling

Dr Sun asked (2026-09-18) whether any stair success avoids route labels and AI models, then asked for both papers to
be read in full. Sources: arXiv 2608.25366v1 (RAEM, 26 Aug 2026) and arXiv 2605.19958v1 (TravExplorer, 19 May 2026),
read through the arXiv HTML renderings. Section and table numbers below are the papers' own.

## RAEM (arXiv 2608.25366): geometry only

**What it is.** An autonomous exploration framework for multi-floor buildings. Its stair handling is purely geometric:
no learned model, no semantic labels, no route annotation.

**Stair-relevant mechanisms.**
1. **Local tomography from live LiDAR (Sec. IV-C).** PCT's tomography, rebuilt from scratch every cycle on the GPU
   over a robot-centred box, keeping only ground, ceiling and cost per slice. Each cell's cost (Eq. 1) requires:
   - vertical clearance `d^I = e^C - e^G >= d_min`;
   - either a gentle surface, gradient `m^grad < theta_s`;
   - or a steppable edge: directional gradient `m^xy <= theta_b` with the share `p_s` of gentle neighbours above
     `theta_p`;
   - otherwise the barrier cost `c^B`.
   The paper notes this is conservative: cells near step edges and under-observed stair regions are marked
   untraversable (Fig. 3).
2. **Four-state local 3-D grid (Sec. IV-D).** For each column, the voxel at the ground index is occupied, the voxel
   one above it is `traversable` (a valid stepping location), higher voxels are `free`, and voxels between one slice's
   ceiling and the next slice's ground are occupied. Traversable voxels are dilated by one cell horizontally if the
   voxel below is traversable or occupied. This grid ignores the conservative cost layer, so it is more permissive.
3. **Staircase-centre alignment (Sec. IV-G4).** If the goal differs in height from the robot by more than one grid
   cell, the goal is moved to the centroid of its tread, found by region growing over unoccupied cells whose ground
   height is within one cell of the seed (cluster size cap `gamma`).
4. **Dual path search (Sec. IV-H).** Search the topological graph first; if the stair region is disconnected, fall
   back to grid A* restricted to `traversable` voxels.
5. **Local planner (Sec. IV-J).** A modified EGO-Planner with a z-axis penalty that keeps trajectories on the ground,
   over a rolling inflated local 3-D terrain map. The paper does not say how that map keeps stair surfaces from being
   inflated as obstacles.

**Parameters (Table III, real-world column where given).** Tomography and grid resolution 0.2 m; 5 slices; local box
12 x 12 x 4-6 m; `d_min` 0.5 m; `theta_s` 0.6; `theta_b` 0.3; `theta_p` 0.1-0.5; `c^B` 50; safety margin 0.4 m;
LiDAR range 4 m; LiDAR pitched 45 degrees down.

**Evidence.**
- **Simulation (Gazebo, Unitree A1, simulated Mid-360):** 20 trials in each of four multi-floor scenes; RAEM reached
  every floor in 20/20; TARE and FAEL never left the first floor; HPHS failed more often (Table IV).
- **Ablations:** without centre alignment, 1 lateral rollover on the stairs in 20 trials (scene 2); with it, 0 in
  20. Dual path search completed the corner staircase 20/20 against 12/20 with graph search alone (Sec. V-E, V-F).
- **Real world (Unitree Go2, Mid-360S at 45 degrees, Jetson Orin NX 16 GB, FAST-LIO2):** one run per scene (Table
  VII). The five-floor stairwell run climbed four corner staircases in 233.9 s over 104.9 m. In building 2 a barricade
  was placed by hand to keep FAST-LIO2 out of a featureless corridor.
- **Limitation (Sec. V-H):** ascent only. Descent is not handled, because of the LiDAR blind spot and harder
  locomotion.
- The locomotion controller is not named in either setting.

**Code:** "upon acceptance"; not released.

## TravExplorer (arXiv 2605.19958): not geometry-only on stairs

**Correction to the lead's earlier summary.** Stairs depend on an AI model here. Sec. IV-A states that 2-D ray casting
on the support plane treats stairs and ramps as obstacles. On stairs the map switches to a semantic mode that marks
traversable voxels from open-vocabulary segmentation (SAM 3) of classes such as floor and stair. The switch happens
when stairs are detected over `N_enter` frames, or when the planner heads to a stair-entrance landmark, which also
comes from open-vocabulary detection. It switches back with hysteresis (`N_exit`). The Sec. VII-C ablation shows
segmentation alone is also insufficient: the hybrid is needed.

**Geometric pieces that transfer to SCAN (the authors are SCAN's group):**
1. **Anisotropic inflation (Sec. IV-B).** Inflate only occupied voxels that are *not* traversable, with a fixed xy
   radius and a downward-only z range around a bottom-support reference point, updated incrementally.
2. **Vertically constrained local optimisation (Sec. VI-D).** The B-spline optimiser (EGO-Planner costs) initialises
   z by arc-length interpolation along the 3-D path, then projects the gradient onto xy only (`P_xy = diag(1,1,0)`).
   The height profile comes from the ground-following 3-D path and is never deformed.
3. **Foothold-guided 3-D search (Sec. VI-B).** A* over traversable voxels with foothold-scale neighbourhoods to bridge
   small gaps on stairs, plus an ESDF clearance penalty.
4. **Descent sensing (Sec. IV-D).** A virtual plane below the robot; many points below it trigger a downward look.

**Evidence.**
- **Simulation:** Habitat ObjectNav with discrete 0.25 m / 30 degree actions (HM3D 70.0% SR, MP3D 48.8%; HM3D
  cross-floor 48.7%). Habitat has no legged physics, so this says nothing about climbing.
- **Real world (Unitree Go2, Mid-360 for FAST-LIO2, D435i on a pan-tilt head, RTX 4090 workstation as ROS master):**
  50 trials, 32 successes (64.0%), with 18 cross-floor episodes. The multi-floor villa had 7 trials and 4 successes
  (Table II). No stair-only success rate is given; failure causes are not attributed to stairs.
- The locomotion controller is not named.

**Code:** "will be released"; the repository holds a README.

## What this means for SCAN

- **The only geometry-only, label-free stair success is RAEM.** Its evidence is 80/80 simulated multi-floor runs and
  single real runs, ascent only. Its recipe is PCT tomography applied locally to live LiDAR, plus a four-state grid,
  tread-centre alignment and a fallback A* on traversable voxels.
- **SCAN's missing piece is the same in both papers:** a `traversable support surface` class that is excluded from
  obstacle inflation. RAEM derives it from local tomography (geometry); TravExplorer from segmentation on stairs.
- **Directly portable into SCAN, all geometric:**
  - RAEM-style traversable class from local tomography;
  - TravExplorer's inflation rule (skip traversable voxels; downward-only z);
  - TravExplorer's xy-only optimisation with z taken from a ground-following path;
  - RAEM's tread-centre alignment for any goal or waypoint on a stair.
- **Reuse status:** neither codebase is released. We already run PCT's tomography code (GPL-2.0); SCAN is Apache-2.0.
- **Open questions:** RAEM's 0.2 m resolution is close to a riser height; how its local planner's terrain map avoids
  inflating stairs is unstated; neither paper names its locomotion controller; neither handles descent with evidence.
