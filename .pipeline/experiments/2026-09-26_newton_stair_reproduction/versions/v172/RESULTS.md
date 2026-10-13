# v172: recovery renewal observed; PCT singleton crash prevents arrival

Mac01 recorded79.570m and173.562simseconds, four real measured-progress renewal
events, and ten qualified replacementstopproofs. It reached the goal region but
PCT then aborted on a singleton A* path; subsequent RPCs failed. Arrival gate
failed. Do not treat proximity to the goal as success. Raw292files578119680bytes
archivedSHA49adb91cdb99e5219889f66bb754f5eb2fd48462e3f0bd1b24a7487d3a4cf6b6.
v174 reproduces this exact native abort and repairs degenerate-query handling.
