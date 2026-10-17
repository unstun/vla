# Lite3 Custom Gait Hub (Airbotix Fork)

This repository is optimized for **Kinematic Gait Research** and **MuJoCo Simulation** for the Lite3 quadruped platform.

---

### 🌐 Project Central Hubs
- [**Master Hub (Root)**](https://github.com/Airbotix-Technology-Pvt-Ltd/Lite3Robot): Mission, specialized workspaces, and organizational identity.
- [**Contributors Hub**](../Contributors.md): Full technical attribution for the Airbotix development team.

---

## 🛠️ Technical Contributions (Airbotix)

The following technical components have been implemented for this stack:

- **Crawl Gait (Tripod)**: Implemented a tripod Crawl gait research for stable movement on stairs, utilizing high knee lift (`1.20rad`).
- **Keyboard Controller**: Created a direct `/dev/tty` access controller with WASD movement, speed scaling, and mode toggling.
- **Manual Pitch (Lean)**: Added manual body pitch adjustments (**F** for lean, **R** for reset) for slope stability research.
- **State Machine Integration**: Added `Hold()` state for idle stability and smooth phase transitions when initiating movement.
- **Docker Workflow**: Modified the Docker setup to allow MuJoCo and the Gait Runner to be restarted independently.

---

## 🚀 How to Run (Decoupled Mode)

1. **Terminal 1 — Reset/Start MuJoCo:**
   ```bash
   docker exec -it lite3_sim_gait /workspace/launch.sh
   ```

2. **Terminal 2 — Start Gait Runner:**
   ```bash
   docker exec -it lite3_sim_gait bash -c "source /workspace/custom_gait_ws/install/setup.bash && ros2 run lite3_custom_gait gait_runner"
   ```

### 🎮 Keyboard Bindings
| Key | Action |
|:---:|---|
| **W / S** | Forward / Backward |
| **A / D** | Turn Left / Right |
| **Q / E** | Strafe Left / Right |
| **T** | **Stair Mode (Crawl)** — Stable 3-leg tripod |
| **F / R** | **Manual Pitch (Lean)** — Keep front feet on ground |
| **+ / -** | Speed Up / Down |
| **Space** | Emergency Stop (Hold Position) |

---

## ❤️ Credits & Tribute
We pay tribute to **DeepRobotics** for providing the foundational `Lite3_MotionSDK` and robot models.

---
*Airbotix Technology Pvt Ltd - Lite3 P2P Autonomous Navigation Project*
*See our [**Contributors Hub**](../Contributors.md) for full project attribution.*
