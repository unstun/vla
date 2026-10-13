# v43: timestamp-based 30 FPS display-only replay

Parent version v42. Copy the original renderer and heading-camera wrapper. Use actual native timestamps to select the nearest logged physical pose for each 1/30 second display frame; never interpolate poses or synthesize a trajectory. Video time advances 1 native second per video second. Display measured RTF, local/controller frequency and local deadline overruns. This changes rendering only; physics run remains v42. Retain raw logged timestamps and poses and record the chosen physical and display timestamp for every video frame.
