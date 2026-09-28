# v20: keep the Building replay camera inside the stair corridor

Stage: experiment + analysis. Parent: v19. One display-only change.

Both existing Building render attempts hide the robot behind scene surfaces:
the normal view offsets the camera 0.9 m laterally outside the stair corridor;
rear-right instead applies a fixed origin camera intended for standalone PD.
Use the existing Building follow camera with 0.1 m lateral offset, and prevent
the standalone origin override from replacing it in Building episodes.

Retain complete scene geometry and recorded body poses. No physics, sensing,
controller, planner, collision, or speed parameter changes. Validate with the
complete recorded v19 episode, inspect startup/motion/stop frames, and decode
the produced video. Bind the video to v19 physics plus v20 renderer. Navigation
acceptance remains unchanged and unsuccessful.
