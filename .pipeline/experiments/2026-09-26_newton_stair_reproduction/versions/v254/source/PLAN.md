# v254 — Preserve legacy floating-point edge distance

Parent frozen v253. The continuous physical endpoint mechanism is unchanged.
Cast the integer index delta before norm in the legacy distance branch, restoring
the original sqrt(2) diagonal cost. Add a behavioral regression that observes the
actual accumulated search score. No scene rules or physics/profile changes.
Rebuild and qualify full unit/native gates, recorded A02, 12x5 and H00 on the
final installed binaries before the single A02 physical attempt bound by v255.
