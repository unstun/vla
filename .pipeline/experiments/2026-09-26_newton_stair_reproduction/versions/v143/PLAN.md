# v143 display of the actual-zero v142 recording

Stage: experiment + analysis. v141 began at recorded native 0.08 s; its frozen artifact remains unchanged. v142 records a new actual initial state at native 0.0 s with step count 0. v143 accepts only that verified initial state and reuses v141 causal full-timeline rendering, close camera, admitted local curve overlays and local solve latency labels.

Physics runs separately as recording v142 with unchanged native v139 navigation. Display builds the CPU model and uses gpu5070ti NVIDIA EGL without stepping physics. Startup uses recorded native timestamps; navigation uses original wall timestamps. No invented zero state, pose interpolation, future planning events, or relabeled old first frame.

Local source -> hash-gated sync -> closed physical outcome -> renderer on /data -> full decode / causal checks / visual review -> regular local MP4 and compact provenance. New recording is separate from v139 six-run acceptance.

The transfer allowlist is compact JSON/CSV/log receipts, three visual QA PNGs and one completed regular MP4. Planned return budget: MP4 below10 MB and compact provenance below2 MB; full raw capture, NPZ, states, logs and master remain on `/data`. All physical capture files are hash-verified before rendering and remain available for reanalysis.
