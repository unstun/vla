# v172: carry the configured robot frame into the recovery BT

Stage: experiment and analysis. Parentv170 arrived on its first local route but
its retry-renewal branch had no live coverage: Newton launches base_frame=base,
while the new BT used its base_link default. Keep all algorithms and limits.
Generate a run-owned BT XML alongside its existing Nav2 profile; write the exact
requested frame into MeasuredProgressRecovery as well as controller/costmaps and
navigator. Never overwrite either generated profile. Test bothbase/base_link,
actualBT TF lookup withbase, orphan preservation, and the existing6BT regressions.
A new original-start run must show actualbudgetrenewallogs plus full acceptance.
