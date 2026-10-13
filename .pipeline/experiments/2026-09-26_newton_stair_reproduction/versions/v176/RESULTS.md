# v176 results

One Mac original-route trial qualified. Sensor-recorded navigation distance77.659m; finalphysics142.282s; RTF0.962589. Six replacement owners each have a qualified measured-stop proof. FinalXYerror0.139395m, yawerror0.116816rad, height error0.006926m; no fall; finalPDhold and copyback qualify. The robot started from exact original groundXY/yaw with physicalframe0factorycrouch.

This is one Mac trial, not repeatability. No claim that all post-revocation drift is repaired. Linuxv177 will test the identical native source/configuration separately.

The recorded native control counterfactual reproduces zero output at4.9246cm error with the old15cm tolerance, and an inward correction with2cm;1cmstillstops. Nineteen host checks,2profilechecks and actual graph/library checks passed. Controller parameter readback during physics was0.02. Source frozen4027pairs/618runtimeinputs.

A prephysics ROS parameter-service query was intentionally stopped because lifecycleconfiguration awaited a bodyTF; nophysics ran in that preflight. Its log is preserved. The rerun checks generatedconfig/mappedlibraries; actualparameter readback was obtained during fullphysics.

All295raw files are verified in the remote478064640B archive, SHA256 `70149c556dc894f177892aeff75d8e72963956fd5f40fc153ac1267036a1b2c8`. The native environment increment is remotely verified as `ec70606b38e4ad7321e1b3ad2a5bde55156424b0eef3ebd8a7f7c974a56a7b12`; it requires the already-verified v174 underlay. Local duplicate tar removed; raw directory and review evidence retained.
