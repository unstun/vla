# v166: Linux simulator service-port isolation

Stage: experiment and analysis. Native v165 is unchanged. Its fourth attempt
aborted during startup because the telemetry listener could not bind port46200.
The exact prior socket owner was not captured. These service ports lie inside
the Linux automatic client-port range; a client can also self-connect before
the listener starts. Reproduce that mechanism without attributing it as the
proven historical cause.

Move the four simulator transports to24600-24603 and PCT IPC to24651. All callers
and responders must agree. Check the actual Linux ephemeral range and reject
an overlap; never modify kernel networking settings. Probe availability on all
local addresses. Keep payloads, source timestamps, retries, maps and physics
unchanged. Verify actual listener start and actual Nav2 graph; no route-reliability
claim is implied by transport tests. v167 will separately address reverse recovery.
