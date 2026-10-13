# Contemporaneous unchanged-baseline control

Stage: experiment and analysis. Reuse the frozen v177 code, parameters, native
receipt, RL model and original full route without modification. New attempt IDs
06-10 preserve the historical01-05 cohort. Run only after all five v186 attempts
close, with the same existing resource gate and no overlapping physical tasks.

Reason: v185 achieved3/5 arrivals; the first two v186 trials failed, and the
second failure had no V186_LOCAL_CAPTURE event. Earlier five v177 arrivals do
not establish current repeatability or attribute every failure to the endpoint
change. Measure five new unchanged-baseline attempts. Do not pool cohorts or
select successes; keep all original-start failures, closeout and actual inputs.
No RL training, real-robot actuation, or source mutation is authorized by this
control. Local VLA remains authoritative; remote files are execution copies.
