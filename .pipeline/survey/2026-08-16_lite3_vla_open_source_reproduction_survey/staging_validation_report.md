---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# Staging validation report

- validation_command: `audit/validate_staging.py`
- checks_total: 294
- checks_passed: 294
- checks_failed: 0
- validated_on: 2026-08-16
- evidence_status: surveyed

## Result

**PASS** — staged files are internally consistent. This validates artifact structure, fixed-commit formatting, local links, PDF signatures/page counts/SHA-256 values, record counts and status fields only. It does not constitute upstream reproduction.

## Scope limits

- `/Users/sun/vla` was not mounted, so project governance/Trellis compliance remains unapplied.
- No candidate installation, inference, simulator, training, or robot command was executed.
- External URLs were verified during the survey, but future availability can change.
