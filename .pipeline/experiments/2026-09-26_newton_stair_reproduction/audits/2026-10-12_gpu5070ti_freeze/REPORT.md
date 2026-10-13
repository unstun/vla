# gpu5070ti SSH loss of response, 2026-10-12

Stage: experiment + analysis. **Root cause remains undetermined; no repair or
host-freeze reproduction is claimed.** Dr Sun reports SSH becoming unusable and
recovering after a manual reboot. He clarified that he was not using remote
desktop. The power-key events are his response to the incident.

The strongest new evidence is continuous computation across the period around
the power-key events. This weakens a sustained whole-host stall in that covered
interval and puts the SSH access path first for further diagnosis. It does not
exclude an earlier transient stall, nor identify a faulty tunnel or network hop.

## Incident timeline

Times below are **2026-10-12 UTC**; user-local Pacific time is UTC minus 7 hours.
The incident boot ID is `156d3e01bce64a6db2e8ab54e3718fbc`. It is distinct from
both later boots. Journal realtime-minus-monotonic offsets from 30 same-boot
events vary by less than 1 microsecond; that mapping aligns the simulation trace.

| UTC | Evidence | Interpretation |
|---|---|---|
| 08:50:00 | Last pre-power sysstat sample: MemAvailable 13,981,416 KiB (13.33 GiB), swap used 1.77 GiB | Not out of RAM at that sample; the next four minutes lack RAM samples |
| 08:53:08.888–08:55:33.868 | 7,171 clock-loop records, zero reported errors, largest gap 0.270075 s | This process kept executing through the power-key period |
| 08:53:39.146–08:55:33.382 | 1,147 backend snapshots, largest timestamp gap 0.120156 s, 18 duplicates, no backward timestamps | Navigation backend also remained active |
| 08:54:29.958 and 08:54:32.888 | Power-key presses | User recovery actions, not the initiating fault |
| 08:55:14.633 | SSH accepted a public-key login through a loopback-forwarded connection | At least one access path worked at this instant; other failed attempts are not disproved |
| 08:55:32.937–08:55:33.933 | Poweroff announcement and shutdown start | Later shutdown boundary |

The final simulator record reports arrival, measured PD hold and 114.682 native
seconds over 114.683 wall seconds after navigation starts, with no dropped
physics steps. Attempt05 lacks state copyback and retention completion; it
remains an **unqualified partial closeout**, not an accepted full-route trial.
Its 1,431-file inventory and original raw files are retained remotely.

## Tests of the proposed explanations

- **Memory exhaustion:** no OOM/kill match in the accessible journal from
  08:30:00 to 08:54:29 UTC. The 08:50 sample has 13.33 GiB available despite
  only 0.40 GiB free; cached memory must not be treated as exhausted memory.
  Ten-minute CPU/disk averages and one RAM snapshot cannot exclude a later peak.
- **GPU, kernel or storage stall:** no matching Xid/NVRM, lockup, blocked-task,
  I/O or thermal error in that same pre-power window. Earlier GPU errors from
  the preceding day do not establish this incident's cause. Missing log entries
  alone never rule out a failure; continuous process records are the stronger
  observation for the covered interval.
- **Network or SSH forwarding:** Cloudflare QUIC dial errors also occurred in
  the earlier accessible interval: 121 errors and 125 SSH accepts from
  08:00–08:30, versus 100 errors and 64 SSH accepts from 08:30–08:54:29.
  Their similar frequency prevents attributing the outage to those errors.
  No matching link/carrier change or watchdog-triggered FRP restart was found.
  Timer service executions alone are not FRP restarts.
- **Manual shutdown:** establishes the recovery timeline only. The earlier
  suggestion that manual shutdown explained the original freeze was incorrect
  and is explicitly withdrawn.

## Remaining access and evidence gaps

The exact first failed SSH timestamp and the user's connection path are not
recorded. The current task uses the verified gpu5070ti alias at the provider's
port 60023. Loopback-forwarded SSH accepts do not prove every remote entry worked.
FRP configuration/log destinations are root-only; sudo noninteractive access
requires a password. No permission boundary was bypassed. No service, firewall,
driver, workload or server restart was changed.

The next useful evidence is a simultaneous local host resource/SSH-listener
trace and an outside SSH/tunnel probe during a recurrence, plus the forwarding
service's incident logs. Existing history cannot resolve which access component
failed. No crash-inducing stress test or speculative service repair was run.

## Provenance and validation

The local collector ran remotely at low CPU/I/O priority with output root
`/data/sun/vla_mppi_20261009/results/freeze_20261012_retry02`.
Its source SHA-256 is
`c8a2850fefdf93086ca7479423c9a38e8d27c11c4aba125578ac3c1b4a90ee2a`.
Two earlier collector attempts are retained with their executed source: the
first incorrectly required every polled backend timestamp to advance; the
second incorrectly rejected journalctl's empty grep result. Neither changed raw
evidence. The successful collector reports duplicates and preserves query codes.

`remote_results/SUMMARY.json` contains the timeline, clock mapping and trace
hashes. `sysstat.json` binds the remote sa12 snapshot and original command output.
`raw_sources.json` lists remote raw journal/snapshot hashes. All **10 returned
files, 355,621 bytes**, match their remote manifest; see
`remote_results/return_verification.json`. Raw logs remain on gpu5070ti.

The related full-route cohorts are reported separately in
`../2026-10-12_original_full_route_repeats/REPORT.md`. No frozen v147/v148 source
changed and no main-task, MPPI, 30 Hz or Jetson acceptance was promoted.
