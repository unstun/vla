# v141: include the recorded startup from the beginning

Dr Sun requested the video from the start. v140 remains immutable and starts
at the first timed navigation frame (native11.04s). v141 includes the137
original untimed factory/startup frames, beginning at native0.08s, then the
unchanged navigation wall-time replay. The startup segment is sampled by its
recorded simulation timestamps and labeled accordingly; never invent wall
stamps for those frames. Navigation keeps original 1:1 wall timing.

Keep original states, geometry, admitted local curves and all physical/source
identities. Use a close camera from the first frame so crouch/stand is visible.
No new physics episode or navigation change. Render on gpu5070ti, verify clock
segment boundaries, no future curves in startup, complete decode and visual
start/mid/end samples. Return an actual MP4 and compact provenance.
