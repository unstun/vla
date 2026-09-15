# NavDP trial and LightNav cleanup

Dr Sun requested a NavDP trial and removal of LightO after the reliability survey.
The ongoing robot choice is simulated Lite3 with the existing model_149999 export
on rented RTX 4090. Dr Sun confirmed X-NavDP (RGB-D local navigation), and
removing model/runtime copies while keeping evidence.

Acceptance: execute a bounded checkpoint inference and, if its interface works,
a physical Lite3 local-navigation screen with rendered RGB-D and real contacts;
return playable video and measured goal/contact/stop outcomes locally. Record
the exact checkpoint, source, observations, controller, and termination owner.
Remove the requested LightNav deployment bytes without losing retained experiment
evidence unless Dr Sun explicitly requests that broader deletion.

No training or real-robot actuation. No unrelated GPU processes, repository work,
or environments may be changed. Preserve every failed run with a unique ID.
