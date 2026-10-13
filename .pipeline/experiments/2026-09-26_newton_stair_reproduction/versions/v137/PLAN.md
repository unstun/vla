# v137: defer reference admission while inputs are unavailable/expired

Parent v136. Its three fixed pilots finish2/3without falls. The third now
processes recovery messages promptly, but admissions2/4/5/6 finish with original
observation ages264.854/254.860/259.857/269.852ms after103–164ms searches, beyond
the unchanged250ms limit. These temporary data failures consume retries as if
they were permanent bad geometry. Keep that failed batch and do not run its
formal comparison.

One change: the existing bounded deferred-route slot also waits for original
fresh completed map/body/support inputs. Check before admission and after its
search. If inputs expire, restore the previous owner/target/planner state and
retry the same queued route at a later work boundary after new input arrives.
No stamp is renewed, no future message applied early, no nonzero command is
allowed without the original independent curve/safety proof. Cancellation
high-water checks run before readiness. Fresh geometric rejection still rejects.
The controller's original2s startup deadline bounds missing-input waiting; the
finite six mission retries, all physical-stop criteria and static map stay fixed.

Validate real native FSM stale-to-fresh retry, unchanged missing/future rejection,
and cancellation while pending. Include actual geometry and fresh rejected routes.
Then freeze, three fixed pilots, and only after3/3arrivals/no falls, six fresh
trials per arm on gpu5070ti. Both arms share the v135 map and v137 host; baseline
nativev136 and candidatev137. No physical/Jetson/30Hz claim from component tests.
